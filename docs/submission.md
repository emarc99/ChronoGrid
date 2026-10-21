# Devpost submission text

## Tagline
Git for the physical world: ask Alexa+ where you left anything, diff your workbench, and lint your home for hazards.

## Tracks
- **Primary:** Alexa+ (self-hosted MCP server, spec 2025-11-25, Streamable HTTP, plus a simulated Alexa+ ambient screen)
- **Mini challenge:** AWS Builder (Strands Agents SDK, Amazon Bedrock / Nova 2 Lite, Amazon Polly, Amazon S3)

## Inspiration
Homes and workshops are full of cameras that record everything and remember nothing. Meanwhile we lose tools, forget the soldering iron, and walk out without our keys. Developers solved "what changed and who changed it" for code decades ago with git. We wanted the same for physical space, with an assistant you can just ask.

## What it does
ChronoGrid turns an on-device camera into an append-only **ledger** of what was put where and when, and exposes it to **Alexa+** through a self-hosted **MCP server** as git-style verbs:
- **git log / blame:** "Alexa, where did I leave my safety goggles?" Alexa answers by voice while the screen shows a **rewind MCP App** looping the 5-second moment they were set down, with a box around them. The D-pad steps through the object's history.
- **git commit / diff:** "Commit the workbench as clean." Later: "What changed?" A red and green diff shows *missing: multimeter (now in Drawer 2)* and *new: mug*.
- **Real-world linter:** "Warn me if the soldering iron is on and nobody's at the bench for two minutes." Amazon Bedrock compiles that into a typed rule, shown as a **pull request** you approve. A deterministic daemon enforces it and slides a hazard card onto the ambient screen while Alexa speaks the warning.

## How we built it
- **Edge (Python):** YOLO-World open-vocabulary detection on a laptop CPU (~6 fps) and a placement tracker that emits placed, moved and removed events plus person presence, with occlusion handling. 5-second **H.264 clips with faces blurred** are uploaded to a private **Amazon S3** bucket (presigned URLs, 7-day expiry).
- **MCP server:** official MCP Python SDK over **Streamable HTTP**, negotiating **2025-11-25**. Ten tools, each returning a deterministic `say` sentence, and an **MCP App** (`ui://chronogrid/rewind.html`).
- **ChronoLint:** a Pydantic rule language whose JSON schema *is* the `propose_lint_rule` tool input, so the LLM authors rules and never judges them.
- **Alexa+ simulation:** a **Strands Agents SDK** agent on **Amazon Bedrock (Nova 2 Lite)** connects to the MCP server as a regular MCP client. **S3SessionManager** gives it cross-session memory; **Amazon Polly** is its voice.
- **Ambient screen:** React 10-foot UI with D-pad navigation, push-to-talk, a live MCP tool trace, and a minimal **MCP Apps host** implementing the ext-apps postMessage protocol.

## Challenges
- Getting the Vega Virtual Device running on a Windows laptop meant enabling KVM inside WSL2 by hand, and the simulator can't load WebView apps.
- Bedrock Anthropic access changed mid-build; Nova 2 Lite turned out faster and handled the nested rule schema well.
- Turning noisy per-frame detections into trustworthy "placed" and "removed" facts required stability counting and occlusion checks.

## Accomplishments
- A voice answer grounded in evidence: every answer cites a ledger row and has a clip behind it.
- Safety rules authored in plain English but enforced deterministically.
- One MCP server that works with any MCP host, including MCP Apps.

## What we learned
MCP is a good fit for ambient assistants: long-lived state lives in the server and any assistant can borrow it. Keeping the LLM on the language side of a deterministic boundary is what makes a safety feature believable.

## What's next
Ring camera ingestion via the Ring APIs, a Vega client for Fire TV, multi-camera homes, and a caregiver mode with family-approved rules.

## Built with
python, fastapi, mcp, mcp-apps, strands-agents, amazon-bedrock, amazon-nova, amazon-polly, amazon-s3, yolo-world, opencv, ffmpeg, react, vite, typescript, sqlite

## Built during the submission window
Everything; the repository history starts during the hackathon.
