# Architecture

## How it works, in plain words

### 1. The camera names objects by itself, from a list of words
The edge program runs **YOLO-World**, an *open-vocabulary* detector. Instead of a fixed set of trained classes, you give it plain words and it looks for those things. The default list ([`edge/detector.py`](../edge/detector.py)) is:

> person, multimeter, safety goggles, pliers, screwdriver, keys, mug, tape measure, soldering iron, scissors, wallet, phone

Track something else by changing the words, with no code changes (keep `person`, which drives the "nobody at the bench" rules):

```powershell
.\.venv\Scripts\python -m edge.run --vocab "person,mug,keys,screwdriver,charger,printer cartridge,heat gun"
```

Wording matters more than you'd expect. On our desk, plain "pliers" was outscored by "scissors" while "red pliers" won at 0.45, and "smartphone" scored higher than "phone". A prompt can be recorded under a different label with `prompt=label`, e.g. `--vocab "person,red pliers=pliers,smartphone=phone"`. Each object keeps only its best-scoring label, and thin tools (screwdriver) get a lower confidence bar. Limits: we first ran YOLO-World on live webcam footage of our own tools, and every model size we tried (small, medium, large) gave poor results: pliers and the hammer were called "scissors", the screwdriver was barely seen, and the hammer was never recognised under any wording. The benchmark is in [friction log #12](friction-log.md#12-edge-vision-yolo-world-on-a-live-laptop-webcam-couldnt-name-our-hand-tools), reproducible with `scripts/bench_detector.py`. The demo video therefore replays stock footage through the same pipeline. The default model is the medium one (`yolov8m-worldv2`, about 0.4 s per frame on a laptop CPU); `--model data/models/yolov8s-worldv2.pt` is twice as fast and less accurate.

How a clip gets its tag:
1. **Detect:** about 3 times a second, each detection is a label plus a box.
2. **Confirm:** the same label must stay in the same spot for 3 detections in a row (about a second), which filters out hands passing through and one-off misreads.
3. **Record:** it becomes a **placed** event with that label, and the 5-second clip around that moment is saved under it (e.g. `20261022-113607-mug.mp4`).
4. **Remove:** if the object is gone for more than 4 seconds and isn't just hidden behind an arm, it becomes a **removed** event.

Limits:
- **Unlisted objects are invisible:** anything not on the list is ignored.
- **Lookalikes can be mislabelled:** the confidence threshold is low (`--conf 0.2`) so small tools get caught, which means a black pouch could come out as "wallet". Raise `--conf` if you see false labels.
- **One of each label:** two mugs are tracked as one "mug".
- **Small or edge-on items are harder:** a screwdriver seen edge-on or partly covered may be missed, so lay small tools flat.

### 2. The camera builds the real history; the seed is only a demo
Every camera event goes to the server's SQLite ledger first, and the clip is attached when it's ready. If a clip fails, the event is still recorded, just without video. The camera produces:
- **Object events:** placed and removed, each with label, box, time and clip.
- **Presence events:** a person entering or leaving.
- **Appliance events:** on/off, such as the soldering iron.

The server turns those events into the "git log":
1. **Zone:** it works out which zone the box falls in (Workbench, Drawer 2, …) from the zone outlines.
2. **Moved or placed:** it checks where the object was last seen. If that was a different zone, the event is stored as **moved** (Workbench → Drawer 2); otherwise **placed**.
3. **History:** each object's events, newest first, are its `git log`, e.g. *11:52 placed · Workbench, 11:36 removed · Workbench…*
4. **Where is it:** `where_is` returns the latest event and that history, and the screens show it.
5. **Commits and diffs:** "Commit the workbench" saves a snapshot of what's in the zone. "What changed?" compares the current state with that snapshot.

| | Seeded history (`seed/`) | Camera recordings (`edge/`) |
| --- | --- | --- |
| Source | `seed/seed.py`: a believable day of events | The webcam |
| Video clip | None (screens show the zone map) | Yes, about 5 s, faces blurred |
| Purpose | A lived-in heatmap, history, diffs and rules for demos and for judges without a camera | The real record, with video evidence |

Both go into the same ledger and can sit side by side. In production you skip the demo history: run `python -m seed.seed --keep` once to load only the zones and default rules, start with `run.ps1` or `run.sh` (no seed flag, no demo reset), and the history grows from what the camera sees. The one setup step is redrawing the zone outlines in [`seed/zones.json`](../seed/zones.json) (polygons in fractions of the camera picture) to match where your camera points.

**Order matters for demos:** `/api/demo/reset` deletes **all** events, camera ones included, and reseeds. The clip files stay on disk and in S3, but the ledger no longer points to them. Reset first, then start the camera and record.

### 3. Clips are saved locally first, then mirrored to S3
1. The edge encodes the clip (faces blurred) and uploads it to the ChronoGrid server.
2. The server saves it to `data/clips/` and replies straight away, so the busy edge never waits on the cloud.
3. A background job copies it to the private S3 bucket under `clips/`.

Which copy the screens get:
- **Before the S3 copy is confirmed:** a link to the local copy (`/clips/<file>`).
- **After it's in S3:** a presigned S3 URL valid for 1 hour.
- **Without `CHRONOGRID_S3_BUCKET`:** everything is served locally, which is fine for judges running without AWS.

On startup the server treats every local clip as local-only until it has checked S3. Clips that S3 already has switch to presigned links, and any upload a restart cut short is retried. A restart therefore never produces a broken link.

**Where S3 fits:** it's the private, durable archive of the video evidence. The facts (what was placed where, and when) live in the SQLite ledger, and each event stores only its clip's file name. S3 keeps the clips private and encrypted, and deletes them after 7 days. The server hands out short-lived links to the browser screen, the Fire TV app and the MCP App, so nothing has to be public. Faces are blurred on the device before anything is uploaded.

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
2. `Detector` runs **YOLO-World v2** (open vocabulary, medium model, class-agnostic NMS) every ~0.35 s, at about 0.4 s per frame on a laptop CPU.
3. `PlacementTracker` assumes one instance per label (which matches how people ask questions) and emits:
   - `placed` after N stable hits (IoU ≥ 0.5 between consecutive detections) when the object is new or moved (IoU < 0.3 versus the last reported box)
   - `removed` after 4 s of absence, unless a person box covers more than 50% of the last known box (occlusion)
   - presence enter/exit with a 3 s grace period
4. On `placed`, `write_clip` encodes the surrounding 5 s to **H.264 MP4** (`libx264`, `+faststart`, browser- and TV-playable), **blurring faces** and stamping the time, then uploads it to the server (60 s timeout). The server stores it in `data/clips/` and mirrors it to S3 in a background thread (`server/storage.py`), so the upload returns immediately even when the CPU is busy with detection.

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
- The rewind view loops the real placement clip with **W3C Media** (`@amazon-devices/react-native-w3cmedia`, `ClipPlayer.tsx`) and draws the pulsing box over the letterboxed video. Events without a clip (seeded history) or a playback error fall back to the zone map. Each new player waits for the previous one's `deinitialize()`, because the VVD can't open a second playback session while the first is tearing down.
- The WebSocket client reassembles messages that Vega delivers as several `onmessage` chunks; a rewind with a presigned S3 URL is large enough to be split.
- D-pad focus uses `TVFocusGuideView` and `hasTVPreferredFocus`. The Snooze button takes focus only after its card has finished sliding in, because the focus engine skips off-screen views. Back returns home, and after 60 s idle the screen falls back to the heatmap.
- On the emulator the server is `10.0.2.2:8787`. Times use the server's UTC offset because the VVD clock runs in UTC.

## Why Alexa+ (and not Fire TV) as the primary track
Voice is the primary interface and the MCP server is the core of the project, which is exactly the Alexa+ brief. The server is UI-agnostic: the web ambient screen and ChronoGrid TV are two clients of the same `/ws` stream, so the Fire TV app is a companion rather than the main entry.
