# Devpost form, field by field

Copy each block into the matching field. The longer narrative lives in [submission.md](submission.md); the feedback answers come from [product-feedback.md](product-feedback.md).

---

## Page 1: Project overview

**Project name**
```
ChronoGrid: git for the physical world
```

**Elevator pitch**
```
Git for the physical world: ask Alexa+ where you left anything, diff your workbench, and lint your home for hazards.
```

**Thumbnail:** `docs/images/thumbnail.jpg` (1500x1000, 3:2)

---

## Page 2: Project details

### About the project
````markdown
![ChronoGrid](https://raw.githubusercontent.com/emarc99/ChronoGrid/main/docs/images/thumbnail.jpg)

## Inspiration
I did my apprenticeship in computer repair shops, fixing printers, motherboards, chargers and power supplies. Several of us shared the same benches, so the screwdriver or multimeter you'd just put down was never where you left it, half-finished jobs got moved, and a hot soldering iron could sit on a bench with nobody watching it. "Who had the…?" was the most-asked question in the shop, and nothing could answer it.

Homes and workshops are full of cameras that record everything and remember nothing. Developers solved "what changed and who changed it" for code decades ago with git. We wanted the same for physical space, with an assistant you can just ask.

## What it does
ChronoGrid turns an on-device camera into an append-only **ledger** of what was put where and when, and exposes it to **Alexa+** through a self-hosted **MCP server** as git-style verbs:

- **git log / blame:** *"Alexa, where did I leave my mug?"* Alexa answers by voice while the screen shows a **rewind MCP App** looping the 5-second moment it was set down, with a box around it. The D-pad steps through the object's history.
- **git commit / diff:** *"Commit drawer 2 as clean."* Later: *"What changed?"* A red and green diff shows what went missing, where it went, and what's new.
- **Real-world linter:** *"Warn me if the soldering iron is on and nobody's at the bench for two minutes."* Amazon Bedrock compiles that into a typed rule, shown as a **pull request** you approve. A deterministic daemon enforces it and slides a hazard card onto the screen while Alexa speaks the warning.
- **On the TV:** *ChronoGrid TV*, a native Fire TV app built with React Native for Vega, follows the conversation. Ask where something is and the TV jumps to the rewind and loops the real clip; approve a rule PR or snooze a hazard with the remote's OK button.

![Ambient screen](https://raw.githubusercontent.com/emarc99/ChronoGrid/main/docs/media/ambient-screen.png)

## How we built it
- **Edge (Python):** YOLO-World open-vocabulary detection on a laptop CPU and a placement tracker that turns noisy per-frame detections into `placed`, `moved` and `removed` events plus person presence, with stability counting and occlusion checks. Objects are named from a plain word list, so a new item means a new word, not retraining. **5-second H.264 clips with faces blurred** are saved locally first and mirrored to a private **Amazon S3** bucket (presigned URLs, 7-day expiry).
- **MCP server:** the official MCP Python SDK over **Streamable HTTP**, negotiating spec **2025-11-25**. Ten git-verb tools, each returning a deterministic `say` sentence, plus an **MCP App** (`ui://chronogrid/rewind.html`).
- **ChronoLint:** a Pydantic rule language whose JSON schema *is* the `propose_lint_rule` tool input, so the LLM writes rules but never judges them.
- **Alexa+ brain on AWS:** a **Strands Agents SDK** agent on **Amazon Nova 2 Lite**, deployed to **Amazon Bedrock AgentCore Runtime**. It reaches the household's MCP server as a normal MCP client through a tunnel that exposes only `/mcp` behind a bearer token. **AgentCore Memory** remembers the household across sessions, and **Amazon Polly** is the voice. Warm turns take 3–4 s end to end.
- **Ambient screen:** a React 10-foot UI with D-pad navigation, push-to-talk, a live MCP tool trace and a minimal MCP Apps host.
- **Fire TV:** *ChronoGrid TV* in **React Native for Vega**, with D-pad focus, W3C Media clip playback and a live WebSocket link to the server, developed on Windows by running the **Vega Virtual Device under WSL2 with KVM**.

The seeded day of history exists only so judges can try ChronoGrid without a camera; real use builds the git log from camera events. **In the demo video the camera feed is free stock footage (Pexels) replayed through the same edge pipeline**; every label, clip and S3 upload you see was produced live by ChronoGrid.

## Challenges we ran into
- **Naming hand tools on a live webcam.** We first ran YOLO-World on live footage of our own props, and every model size (small, medium, large) gave poor results: only the phone was reliable, pliers and a hammer were called "scissors", and the hammer was never recognised under any wording. Wordier prompts ("red pliers"), the medium model and one label per object helped; the full benchmark is in our friction log (#12).

![Webcam benchmark](https://raw.githubusercontent.com/emarc99/ChronoGrid/main/docs/images/desk-labels.jpg)

- **Fire TV on Windows:** the Vega Virtual Device needed KVM enabled inside WSL2 by hand, can't load WebView apps (so the TV app was rewritten natively), only repaints under WSLg while the mouse moves, and splits large WebSocket messages.
- **A cloud agent calling into a home safely:** the tunnel guard rejects everything except `/mcp` with the right token.
- **Bedrock access changed mid-build;** Nova 2 Lite turned out faster and handled the nested rule schema well.

## Accomplishments that we're proud of
- Voice answers grounded in evidence: every answer cites a ledger row and has a clip behind it.
- Safety rules written in plain English but enforced deterministically.
- One MCP server that works with any MCP host, including MCP Apps, and drives both a web screen and a native Fire TV app.
- A production-shaped Alexa+ brain: serverless on AgentCore with managed long-term memory, answering in 3–4 s.

## What we learned
MCP fits ambient assistants well: long-lived state lives in the server and any assistant can borrow it. Keeping the LLM on the language side of a deterministic boundary is what makes a safety feature believable. And open-vocabulary vision is impressive on everyday objects but still needs light, distance and wording care for tools.

## What's next for ChronoGrid
Ring camera ingestion, testing ChronoGrid TV on a real Fire TV Stick, multi-camera homes, a caregiver mode with family-approved rules, and better tool recognition (a short fine-tune on the household's own objects, or a Nova second opinion on the object crop when a placement is detected).

**Code (MIT):** https://github.com/emarc99/ChronoGrid
````

### Built with (23 tags; type each and press Enter)
```
python, fastapi, mcp, mcp-apps, strands-agents, amazon-bedrock, amazon-bedrock-agentcore, amazon-nova, amazon-polly, amazon-s3, aws-cdk, vega, react-native, fire-tv, cloudflare-tunnel, yolo-world, opencv, ffmpeg, react, vite, typescript, sqlite, wsl
```

### "Try it out" links
```
https://github.com/emarc99/ChronoGrid
```
```
https://github.com/emarc99/ChronoGrid#try-it-for-judges
```

### Image gallery (in this order)
1. `docs/images/thumbnail.jpg`
2. `docs/media/ambient-screen.png`
3. `docs/media/tv-rewind.png`
4. `docs/media/tv-rule-pr.png`
5. `docs/media/tv-alert.png`
6. `docs/media/tv-home.png`
7. `docs/images/desk-labels.jpg`

### Video demo link
The YouTube URL, once uploaded.

---

## Page 3: Additional info

| Field | Answer |
| --- | --- |
| Submitter type | Individual |
| Organization name | N/A |
| Country of residence | Nigeria |
| Canadian province | N/A |
| Primary tracks | **Alexa+** and **Fire TV** |
| Code repository URL | `https://github.com/emarc99/ChronoGrid` |
| New or existing before Aug 31, 2026? | New (the repository history starts on Oct 21, 2026) |
| AWS Builder Mini Challenge? | Yes |
| Open Source Mini Challenge? | Yes |
| Contribution URL | `https://github.com/emarc99/ChronoGrid` |
| Project repository URL | `https://github.com/emarc99/ChronoGrid` |
| GitHub username | `emarc99` |
| Friction log URL | `https://github.com/emarc99/ChronoGrid/blob/main/docs/friction-log.md` |
| Project testing link | `https://github.com/emarc99/ChronoGrid#try-it-for-judges` |

### AWS Builder: which AWS services did you incorporate and how?
```
ChronoGrid's Alexa+ brain runs on AWS; the full write-up with code links is in docs/aws-integration.md (https://github.com/emarc99/ChronoGrid/blob/main/docs/aws-integration.md).

- Amazon Bedrock AgentCore Runtime: the production home of the Alexa+ brain. A Strands agent deployed as a serverless runtime with the AgentCore CLI (CDK stack, CodeZip). The home server calls InvokeAgentRuntime; the runtime calls back into the household's MCP server over Streamable HTTP through a tunnel that exposes only /mcp behind a bearer token. Warm turns take 3–4 s; a model-free keep-warm ping avoids 13–45 s cold starts.
- Amazon Bedrock AgentCore Memory: long-term household memory with semantic, user-preference, summary and episodic strategies, wired in through Strands' AgentCoreMemorySessionManager. Object locations still come only from MCP tools, never from memory.
- Strands Agents SDK: Agent + BedrockModel + MCPClient loads ChronoGrid's ten MCP tools; a BeforeToolCallEvent hook drives the on-screen tool trace.
- Amazon Bedrock (Amazon Nova 2 Lite): interprets requests, picks git-verb tools, and compiles plain-English safety rules into typed ChronoLint rules through the propose_lint_rule tool schema ("a couple of minutes" becomes for_seconds: 120).
- Amazon Polly (generative, falling back to neural): Alexa's voice for replies and spoken hazard warnings.
- Amazon S3: private, encrypted bucket for face-blurred 5-second rewind clips (saved locally first, mirrored in the background, presigned 1-hour URLs, 7-day lifecycle) and agent session memory.
- AWS CDK / CloudFormation and CloudWatch: the AgentCore stack (runtime, memory, least-privilege role), logs and traces.

Design choice: detection stays on-device for privacy (no frames leave the home, only events and blurred clips); AWS handles language, the agent runtime and memory, voice and evidence storage. Facts and alerts stay deterministic.
```

### Open Source: what you did, how it works, why it matters
```
What: ChronoGrid is a new, MIT-licensed open-source project built entirely during the hackathon (repository history starts Oct 21, 2026; ~100 atomic commits). It includes the edge vision pipeline, the MCP server with an MCP App, the ChronoLint rule engine, the Strands/AgentCore Alexa+ brain, a React ambient screen and a React Native for Vega Fire TV app, with tests, docs and a friction log.

How it works: an on-device camera pipeline (YOLO-World + a placement tracker) writes placed/moved/removed events into an append-only SQLite ledger and saves face-blurred 5-second clips. A self-hosted MCP server (Streamable HTTP, spec 2025-11-25) exposes that ledger as git verbs (where_is, room_commit, room_diff, lint rules). Any MCP host can use it: our Alexa+ brain on Bedrock AgentCore, Claude Desktop, VS Code or Cursor. Judges can run it with one script (scripts/run.ps1 or run.sh) and seeded data, no camera or AWS account needed for the MCP tools.

Why it matters: it's a reusable reference for "physical-world memory" over MCP: privacy-first on-device detection, evidence-backed answers, and safety rules that an LLM writes but a deterministic engine enforces. Our Vega-on-WSL2 setup scripts, W3C Media playback fixes and friction log also help other developers building Fire TV apps on Windows.
```

### [Optional] Feature requests
```
1. Alexa+ MCP test console (Critical): let developers outside the Preview connect a self-hosted Streamable HTTP MCP server to Alexa+ and see the planner's tool calls and spoken reply, like the Alexa Skills Kit simulator. We had to simulate Alexa+ because there's no way to point a real device at our server.
2. MCP Apps on Alexa+ screens (Important): render ui:// resources on Echo Show and Fire TV, including video and in-card actions, so ChronoGrid's rewind and rule-approval cards work natively.
3. Alexa+ to Fire TV handoff (Important): a supported deep link with parameters from an Alexa+ add-on into a Vega app view, so "where are my keys?" can open the TV rewind without our own WebSocket.
4. Vega Virtual Device on Windows (Important): document WSL2 + KVM, keep the VVD alive independently of the launching shell, include the WebView module, and fix repainting under WSLg.
5. AgentCore Runtime warm capacity (Important): a minimum-warm-sessions setting for voice workloads; cold starts of 13–45 s can't land on a spoken question.
6. Privacy-preserving vision primitives (Nice-to-have): on-device detection with cloud-side event schemas (labels, boxes, presence, no identity) as a first-class pattern for Ring and Fire TV camera apps.
```

### Feedback 1: Which developer tools, APIs and SDKs did you use and for what?
```
- Alexa+ via a self-hosted MCP server (official MCP Python SDK, Streamable HTTP, spec 2025-11-25, plus an MCP App): ChronoGrid's integration surface, ten git-verb tools and a rewind UI.
- AWS Strands Agents SDK: the Alexa+ brain (Agent, BedrockModel, MCPClient, hooks, session managers).
- Amazon Bedrock AgentCore Runtime + Memory (AgentCore CLI, CDK): serverless hosting and long-term household memory for the brain.
- Amazon Bedrock with Amazon Nova 2 Lite: intent, tool selection and compiling plain-English safety rules into typed rules.
- Amazon Polly: Alexa's voice and spoken hazard warnings.
- Amazon S3: private storage for face-blurred rewind clips and session memory.
- Fire TV / Vega SDK (React Native for Vega, Vega Virtual Device, W3C Media): ChronoGrid TV.
- Also: YOLO-World (ultralytics) and OpenCV on-device, FastAPI, React/Vite, SQLite, Cloudflare quick tunnel, WSL2.
```

### Feedback 2: What worked well?
```
- MCP / Alexa+: building on the open MCP standard meant one server works with Alexa+, Claude, VS Code and our own agent. Streamable HTTP is easy to host inside one FastAPI process.
- Strands Agents SDK: MCPClient(url=...) to working tool use in a few lines; hooks are clean; S3 session persistence is one line.
- AgentCore: "agentcore create" generated a Strands project with Memory already wired in, and "agentcore deploy" produced runtime, memory and IAM role in one command. The runtime called our MCP server back with custom headers and no glue. Warm turns take 3–4 s.
- Bedrock / Nova 2 Lite: picked the right tool on every test utterance and filled a nested discriminated-union schema correctly, in about 3.3 s end to end, fast enough for voice.
- Polly: generative voices sound natural; one call returns an MP3 the browser plays directly.
- S3: presigned GETs play directly in <video> and inside the sandboxed MCP App iframe.
- Vega: once running, build-vega plus vega run-app takes about a minute; TVFocusGuideView and hasTVPreferredFocus make D-pad focus predictable; W3C Media plays H.264 clips with a few lines of code.
```

### Feedback 3: What needs work?
```
- Alexa+: no way for a developer outside the Preview to connect a self-hosted MCP server and see what the planner does; unclear whether Alexa+ screens render MCP Apps.
- Strands: "pip install strands-agents" can resolve to the 0.0.1 placeholder; no per-invocation tool-call list on AgentResult; FileSessionManager can't recover a half-written session.
- AgentCore: two different tools share the "agentcore" name (retiring Python toolkit vs new npm CLI) so tutorials disagree; uv is an unlisted prerequisite; first deploy took ~8.5 min with little progress detail; cold starts of 13–45 s needed a keep-warm ping; two deploys at once deadlock on cdk.out\synth.lock.
- Bedrock: Anthropic model access worked once, then required the use-case form; availability APIs should say so up front.
- Polly: no way to discover which voices support the generative engine without trial calls.
- Vega: Windows isn't a documented host (WSL2 + KVM by hand); the VVD image lacks WebView; the VVD dies with its launching shell, runs in UTC, and under WSLg only repaints while the mouse moves over it; WebSocket messages arrive split into chunks; W3C Media reports a kepler-compatibility "ERROR" that is only a warning, needs the previous player deinitialized before a new one, and loadedmetadata never fired.
- Details with steps, severity and workarounds: https://github.com/emarc99/ChronoGrid/blob/main/docs/friction-log.md
```

### Feedback 4: Onboarding (zero to hello world)?
```
- MCP: fast; the spec and Python SDK are good. Alexa+ side: slow, because there's no test surface for self-hosted servers.
- Strands Agents SDK: about 15 minutes to a working agent once the right version was installed.
- AgentCore: about an hour from "agentcore create" to a working cloud invocation, most of it waiting on the first deploy.
- Bedrock / Nova: minutes; Nova needed no access request.
- Polly and S3: minutes.
- Vega: one evening to get the Vega Virtual Device running on Windows through WSL2, then about two hours to a working native app. We lost time starting with the WebView template, which the VVD can't run.
```

### Feedback 5: Would you build with these devices and services again?
```
Yes. MCP plus Alexa+ is the right shape for an ambient assistant with long-term, physical-world memory; Strands + AgentCore is the fastest path we've found from MCP tools to a production-style agent with real memory; Nova 2 Lite is now our default model; and Fire TV is a natural big screen for the household. Next time we'd start the TV app from a native React Native for Vega template and test on a real Fire TV Stick.
```

### Checkboxes and the last three questions
- Tick the age, eligible-jurisdiction and not-an-employee boxes only if they're true for you.
- **AI tools used:**
  ```
  Cursor (AI coding agent) for pair-programming, debugging, test writing and documentation; Amazon Bedrock (Nova 2 Lite) inside the product itself. All design decisions, testing and the demo were driven by me.
  ```
- **Level of learning** and **AI value for your career:** your call.
