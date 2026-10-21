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
- The **web ambient screen** is a 10-foot UI (Vite + React):
  - It is a minimal **MCP Apps host**: it loads `rewind.html` in a sandboxed iframe and speaks the ext-apps protocol (`ui/initialize`, `ui/notifications/initialized`, `tool-input`, `tool-result`, `size-changed`, `request-teardown`).
  - Remote-style navigation uses arrows, Enter and Esc/Back.
  - Push-to-talk uses browser speech recognition; replies and hazard announcements are spoken with **Amazon Polly**.

## Why Alexa+ (and not Fire TV) as the primary track
The 10-foot UI ships as a web ambient screen designed for D-pad navigation. The Vega Virtual Device does run under WSL2 (see `scripts/vega/`), but it lacks the WebView module, so a Vega client has to be a native React Native for Vega app. The server is UI-agnostic, so a Vega or Fire OS client only needs to consume `/ws` and `/apps/rewind.html`.
