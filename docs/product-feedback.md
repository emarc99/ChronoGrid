# Product feedback (for the Devpost form)

## Top feature requests
1. **Alexa+ MCP test console.** Let developers outside the Preview connect a self-hosted Streamable HTTP MCP server and see the planner's tool calls and the spoken reply, like the Alexa Skills Kit simulator did for skills.
2. **Rich, actionable cards on Alexa+ screens.** Render MCP Apps (`ui://` resources) on Echo Show and Fire TV, including video and in-card actions. ChronoGrid's rule pull request is approved in place on the screen, and that pattern needs a documented home in Alexa+.
3. **Alexa+ to Fire TV handoff.** A supported way for an Alexa+ add-on to open a specific view of a Vega app (a deep link with parameters), so "where are my keys?" can jump the TV straight to the rewind without the app keeping its own WebSocket open.
4. **Vega Virtual Device on Windows.** Document WSL2 + KVM, keep the VVD alive independently of the launching shell, and ship the WebView module in the VVD image.
5. **AgentCore Runtime warm capacity.** A minimum-warm-sessions setting for voice workloads, so a cold start (13–45 s in our tests) never lands on a spoken question.
6. **Privacy-preserving vision primitives.** On-device detection with cloud-side event schemas (labels, boxes, presence, no identity) as a first-class pattern for Ring and Fire TV camera apps.

Details per product follow; the step-by-step problems are in the [friction log](friction-log.md).

## Alexa+ (self-hosted MCP server, spec 2025-11-25, Streamable HTTP)
- **Used for:** ChronoGrid's integration surface: ten git-verb tools plus an MCP App (`ui://chronogrid/rewind.html`).
- **Worked well:** Building on the open MCP standard instead of a proprietary skill model meant one server works with Alexa+, Claude, VS Code and our own Strands agent. Streamable HTTP is simple to host next to the rest of the app (one FastAPI process).
- **Needs work:** There's no way for a developer outside the Preview to connect a self-hosted MCP server to Alexa+ and see what the planner does with the tool descriptions. It's also unclear whether Alexa+ screen devices render MCP Apps.
- **Onboarding:** Fast for MCP itself (the spec and SDKs are good); slow for the Alexa+ side because of the missing test surface.
- **Would build again:** Yes. An ambient assistant with long-term, physical-world memory is exactly what MCP enables.

## AWS Strands Agents SDK
- **Used for:** The Alexa+ brain: `Agent` + `BedrockModel` + `MCPClient(url=...)`, `SlidingWindowConversationManager`, `S3SessionManager`, `BeforeToolCallEvent` hooks.
- **Worked well:** `MCPClient(url=...)` to working tool use took a few lines; hooks are clean; S3 session persistence is a one-liner.
- **Needs work:** The PyPI 0.0.1 placeholder trap; no first-class per-invocation tool-call list on `AgentResult`; `FileSessionManager` can't recover a partial session directory.
- **Onboarding:** About 15 minutes to a working agent once the right version was installed.
- **Would build again:** Yes. It's the fastest path we've found from MCP tools to a production-style agent.

## Amazon Bedrock AgentCore (Runtime + Memory)
- **Used for:** Hosting the Alexa+ brain as a serverless runtime, and long-term household memory (semantic, user-preference, summary and episodic strategies).
- **Worked well:** `agentcore create` generated a Strands project with Memory already wired into `AgentCoreMemorySessionManager`; `agentcore deploy` produced a working runtime, memory and IAM role in one command. The runtime called our MCP server back over Streamable HTTP with custom headers and no extra glue. Warm turns take 3–4 s end to end.
- **Needs work:** Two tools share the `agentcore` name (the retiring Python starter toolkit and the new npm CLI), so tutorials disagree; `uv` is an unlisted prerequisite for CodeZip; the first deploy took about 8.5 minutes with little progress detail; cold starts ranged from 13 s to about 45 s, so we added a keep-warm ping. A documented warm-pool or minimum-instances option would help voice workloads.
- **Onboarding:** About an hour from `create` to a working cloud invocation, most of it on the first deploy.
- **Would build again:** Yes. Memory with built-in strategies is a big step up from storing raw transcripts in S3.

## Amazon Bedrock (Amazon Nova 2 Lite)
- **Used for:** Intent interpretation, tool selection, and compiling natural-language safety rules into typed ChronoLint rules.
- **Worked well:** Nova 2 Lite chose the correct tool on every test utterance, filled a nested discriminated-union schema correctly ("a couple of minutes" became `for_seconds: 120`), and answered in about 3.3 s end to end, which works for voice.
- **Needs work:** Anthropic model access behaved inconsistently (one call succeeded, then the use-case form was required); availability APIs should report that up front.
- **Would build again:** Yes. Nova 2 Lite is our default.

## Amazon Polly
- **Used for:** Alexa+'s voice on the ambient screen (replies and hazard announcements).
- **Worked well:** Generative voices sound natural, and one API call returns an MP3 a browser can play directly.
- **Needs work:** It would help to discover which voices support the generative engine without trial calls (we fall back to neural when needed).

## Amazon S3
- **Used for:** Private storage for face-blurred rewind clips (presigned URLs, 7-day lifecycle) and agent session memory.
- **Worked well:** Presigned GETs play directly in `<video>` and in the sandboxed MCP App iframe.

## Fire TV / Vega Developer Tools
- **Used for:** *ChronoGrid TV*, a React Native for Vega companion app tested on the Vega Virtual Device.
- **Worked well:** Once running, the RN for Vega workflow is familiar: `build-vega` plus `vega run-app` takes about a minute. `TVFocusGuideView` and `hasTVPreferredFocus` made D-pad focus predictable, and the VVD's on-screen remote is good enough for demos.
- **Needs work:** Windows isn't a documented host. The Vega Virtual Device does run under WSL2 once KVM is enabled by hand, but the VVD image lacks the WebView module, so the `vegaWebview` template can't be tested without a physical device. The VVD dies with the shell that started it, and its clock runs in UTC.
- **Onboarding:** One evening to get the VVD running on Windows, then about two hours for the app.
- **Would build again:** Yes, but we'd start with a native RN template instead of WebView.
