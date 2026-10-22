# Architecture

## Data model: an append-only ledger
`server/ledger.py` stores every observation as an immutable **event**:

| kind | produced by | meaning |
| --- | --- | --- |
| `placed` / `moved` | edge tracker | an object became stationary in a zone (a `placed` in a new zone is recorded as `moved` with `from_zone`) |
| `removed` | edge tracker | an object disappeared for longer than `removed_after` and was not merely occluded by a person |
| `person_enter` / `person_exit` | edge tracker | presence per zone (no identity, no face recognition) |
| `appliance_on` / `appliance_off` | smart plug, edge, or `/api/appliance` | heat sources and tools |

The derived tables (`object_state`, `presence`, `appliance_state`) are the "working tree". `snapshots` are commits, and `diff` compares a zone's working tree against its last commit or against any past timestamp, which it replays from events.

## Edge pipeline (`edge/`)
1. `FrameBuffer` keeps the last 6 seconds of frames at 12 fps (960 px wide).
2. `Detector` runs **YOLO-World v2** (open vocabulary) every ~0.35 s, at about 0.15 s per frame on a laptop CPU.
3. `PlacementTracker` assumes one instance per label (which matches how people ask questions) and emits:
   - `placed` after N stable hits (IoU ≥ 0.5 between consecutive detections) when the object is new or moved (IoU < 0.3 versus the last reported box)
   - `removed` after 4 s of absence, unless a person box covers more than 50% of the last known box (occlusion)
   - presence enter/exit with a 3 s grace period
4. On `placed`, `write_clip` encodes the surrounding 5 s to **H.264 MP4** (`libx264`, `+faststart`, browser- and TV-playable), **blurring faces** and stamping the time, then uploads it to the server, which mirrors it to S3.

## MCP server (`server/mcp_server.py`)
- Built on the official MCP Python SDK (`MCPServer`), served over **Streamable HTTP** at `/mcp`. It negotiates **2025-11-25** with clients that offer it (`scripts/mcp_smoke.py`) and the SDK's newer revisions with newer clients.
- Ten tools (git verbs) plus a `chronogrid://zones` resource.
- **MCP Apps:** `where_is` carries `_meta.ui.resourceUri = ui://chronogrid/rewind.html`, served as `text/html;profile=mcp-app` with a CSP that allows only the clip origins. Hosts that support MCP Apps render the rewind card inline; others still receive the `say` text and structured content.
- Every tool returns a deterministic `say` sentence, which keeps the voice answer grounded.
- Tools also publish the matching view to the ambient screen through the hub (`server/hub.py`), so voice and screen stay in sync no matter which MCP host asked.

## ChronoLint (`server/rules.py`, `server/linter.py`)
- A Pydantic discriminated union of conditions, with `LintRule.when` meaning *all must hold*.
- `propose_lint_rule(rule: LintRule)` exposes the rule schema to the model as the tool's input schema, so the model "compiles" natural language straight into a validated rule. Zone names are resolved fuzzily ("the bench" becomes `workbench`).
- Rules start as `proposed`; only `active` rules are evaluated.
- The linter ticks every `CHRONOGRID_LINT_INTERVAL` seconds and manages the alert lifecycle: one open alert per rule, snooze windows, a cooldown after resolve, and auto-resolve when the condition clears.

## Alexa+ simulation (`agent/`, `web/`)
- `AlexaBrain` is a **Strands Agents** `Agent` with a `BedrockModel` (Amazon **Nova 2 Lite** by default) whose tools come from `MCPClient(url=/mcp)`. Conversation memory persists across sessions through Strands' `S3SessionManager`, falling back to `FileSessionManager`.
- A `BeforeToolCallEvent` hook records the MCP tool trace that the screen displays.
- **On AgentCore** (when `CHRONOGRID_AGENT_RUNTIME_ARN` is set): the server's `CloudBrain` calls `InvokeAgentRuntime` with the utterance, the public MCP URL and a bearer token. The runtime (`cloud/ChronoGridAlexa/app/AlexaBrain`) builds the same Strands agent, with AgentCore Memory as its session manager (`actor_id = household`, one session per day), and calls back into `/mcp` through the tunnel. It returns `{reply, tools}`, which the server publishes to every screen.
- **Tunnel guard:** requests that arrive through the tunnel (they carry a `cf-ray` header) can only reach `/mcp`, and only with `Authorization: Bearer <CHRONOGRID_MCP_TOKEN>`. Everything else returns 404, and the screen WebSocket is closed with code 1008. MCP's DNS-rebinding check is turned off only when the token is configured, because the token replaces it.
- The **web ambient screen** is a 10-foot UI (Vite + React):
  - It is a minimal **MCP Apps host**: it loads `rewind.html` in a sandboxed iframe and speaks the ext-apps protocol (`ui/initialize`, `ui/notifications/initialized`, `tool-input`, `tool-result`, `size-changed`, `request-teardown`).
  - Remote-style navigation uses arrows, Enter and Esc/Back.
  - Push-to-talk uses browser speech recognition; replies and hazard announcements are spoken with **Amazon Polly**.

## ChronoGrid TV: Fire TV companion (`tv/`)
- A native **React Native for Vega** app (`com.emarc99.chronotv`). The Vega Virtual Device lacks the WebView module, so the web screen couldn't simply be wrapped.
- It lays out a 1920x1080 design canvas and scales it to the window, so the same layout works on the VVD and on a 4K TV.
- It fetches `/api/state`, `/api/grid` and `/api/events`, and subscribes to `/ws` with automatic reconnects. When an MCP tool runs, the server publishes a `screen` message (rewind, diff, status, commit or rule PR) and the TV opens the matching view, so asking Alexa+ "where are my keys?" switches the TV to the rewind. Hazard alerts slide in as a card, and the Alexa strip shows the utterance, the MCP tool chips and the reply.
- D-pad focus uses `TVFocusGuideView` and `hasTVPreferredFocus`. The Snooze button takes focus only after its card has finished sliding in, because the focus engine skips off-screen views. Back returns home, and after 60 s idle the screen falls back to the heatmap.
- On the emulator the server is `10.0.2.2:8787`. Times use the server's UTC offset because the VVD clock runs in UTC.

## Why Alexa+ (and not Fire TV) as the primary track
Voice is the primary interface and the MCP server is the core of the project, which is exactly the Alexa+ brief. The server is UI-agnostic: the web ambient screen and ChronoGrid TV are two clients of the same `/ws` stream, so the Fire TV app is a companion rather than the main entry.
