# Devpost submission text

## Tagline
Git for the physical world: ask Alexa+ where you left anything, diff your workbench, and lint your home for hazards.

## Tracks
Select every one that applies; a project can win at most one track and one mini challenge.
- **Alexa+:** self-hosted MCP server (spec 2025-11-25, Streamable HTTP) with an MCP App, driving a simulated Alexa+ ambient screen
- **Fire TV:** *ChronoGrid TV*, a native React Native for Vega app driven by Alexa+ over the same MCP server
- **Mini challenge, AWS Builder:** Amazon Bedrock AgentCore Runtime + Memory, Strands Agents SDK, Bedrock / Nova 2 Lite, Amazon Polly, Amazon S3
- **Mini challenge, Open Source:** MIT-licensed, public repository

## How judges can test it
No camera, Alexa+ device or Fire TV is required; `.\scripts\run.ps1 -Seed` loads a day of workshop history.
1. **MCP only, no AWS account:** connect MCP Inspector, Claude Desktop, VS Code or Cursor to `http://127.0.0.1:8787/mcp` and call `where_is`, `room_diff` or `room_status`.
2. **Full Alexa+ flow:** with AWS credentials (Bedrock in `us-east-1`), open `http://127.0.0.1:8787` and talk or type.
3. **Fire TV:** `scripts/vega/` builds and installs ChronoGrid TV on the Vega Virtual Device.
Step-by-step: the "Try it (for judges)" section of the README.

## Inspiration
<!-- TODO(emarc): open with your own moment, in first person, 2-3 sentences: the tool you lost, the iron you left on, who you'd build this for. Judges said the human story is what stands out. -->
Homes and workshops are full of cameras that record everything and remember nothing. Meanwhile we lose tools, forget the soldering iron, and walk out without our keys. Developers solved "what changed and who changed it" for code decades ago with git. We wanted the same for physical space, with an assistant you can just ask.

## What it does
ChronoGrid turns an on-device camera into an append-only **ledger** of what was put where and when, and exposes it to **Alexa+** through a self-hosted **MCP server** as git-style verbs:
- **git log / blame:** "Alexa, where did I leave my safety goggles?" Alexa answers by voice while the screen shows a **rewind MCP App** looping the 5-second moment they were set down, with a box around them. The D-pad steps through the object's history.
- **git commit / diff:** "Commit the workbench as clean." Later: "What changed?" A red and green diff shows *missing: multimeter (now in Drawer 2)* and *new: mug*.
- **Real-world linter:** "Warn me if the soldering iron is on and nobody's at the bench for two minutes." Amazon Bedrock compiles that into a typed rule, shown as a **pull request** you approve. A deterministic daemon enforces it and slides a hazard card onto the ambient screen while Alexa speaks the warning.
- **On the TV:** *ChronoGrid TV*, a native Fire TV app, follows the conversation. Ask Alexa where your keys are and the TV jumps to the rewind; approve a rule PR or snooze a hazard with the remote's OK button.

## How we built it
- **Edge (Python):** YOLO-World open-vocabulary detection on a laptop CPU (~6 fps) and a placement tracker that emits placed, moved and removed events plus person presence, with occlusion handling. 5-second **H.264 clips with faces blurred** are uploaded to a private **Amazon S3** bucket (presigned URLs, 7-day expiry).
- **MCP server:** official MCP Python SDK over **Streamable HTTP**, negotiating **2025-11-25**. Ten tools, each returning a deterministic `say` sentence, and an **MCP App** (`ui://chronogrid/rewind.html`).
- **ChronoLint:** a Pydantic rule language whose JSON schema *is* the `propose_lint_rule` tool input, so the LLM authors rules and never judges them.
- **Alexa+ brain on AgentCore:** a **Strands Agents SDK** agent with **Amazon Nova 2 Lite**, deployed to **Amazon Bedrock AgentCore Runtime** (CDK, CodeZip). It reaches the household's MCP server as a regular MCP client, through a Cloudflare tunnel that exposes only `/mcp` behind a bearer token. **AgentCore Memory** (semantic, user-preference, summary and episodic strategies) remembers the household across sessions; **Amazon Polly** is its voice. Turns take 3–4 s end to end, and a model-free keep-warm ping avoids cold starts. The same agent also runs in-process for offline development.
- **Ambient screen:** React 10-foot UI with D-pad navigation, push-to-talk, a live MCP tool trace, and a minimal **MCP Apps host** implementing the ext-apps postMessage protocol.
- **Fire TV:** *ChronoGrid TV*, built with **React Native for Vega**: a scaled 1920x1080 canvas, `TVFocusGuideView` D-pad focus, a spring-animated hazard card and a live WebSocket link to the server. Developed on Windows by running the **Vega Virtual Device under WSL2 with KVM**.

## Challenges
- Getting the Vega Virtual Device running on a Windows laptop meant enabling KVM inside WSL2 by hand, and the simulator can't load WebView apps, so the TV app had to be rewritten natively in React Native for Vega.
- Letting a cloud agent call an MCP server in someone's home without exposing the home: the tunnel guard rejects everything except `/mcp` with the right token.
- Bedrock Anthropic access changed mid-build; Nova 2 Lite turned out faster and handled the nested rule schema well.
- Turning noisy per-frame detections into trustworthy "placed" and "removed" facts required stability counting and occlusion checks.

## Accomplishments
- A voice answer grounded in evidence: every answer cites a ledger row and has a clip behind it.
- Safety rules authored in plain English but enforced deterministically.
- One MCP server that works with any MCP host, including MCP Apps, and drives both a web screen and a native Fire TV app.
- A production-shaped Alexa+ brain: serverless on AgentCore with managed long-term memory, answering in 3–4 s.

## What we learned
MCP is a good fit for ambient assistants: long-lived state lives in the server and any assistant can borrow it. Keeping the LLM on the language side of a deterministic boundary is what makes a safety feature believable.

## What's next
Ring camera ingestion via the Ring APIs, testing ChronoGrid TV on a real Fire TV Stick, multi-camera homes, and a caregiver mode with family-approved rules.

## Built with
python, fastapi, mcp, mcp-apps, strands-agents, amazon-bedrock, amazon-bedrock-agentcore, amazon-nova, amazon-polly, amazon-s3, aws-cdk, vega, react-native, fire-tv, cloudflare-tunnel, yolo-world, opencv, ffmpeg, react, vite, typescript, sqlite, wsl

## Built during the submission window
Everything; the repository history starts during the hackathon.
