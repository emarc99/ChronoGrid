# Product feedback (for the Devpost form)

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
- **Used for:** Planned as the primary target; we designed the 10-foot UI around D-pad navigation.
- **Needs work:** Windows isn't a documented host. The Vega Virtual Device does run under WSL2 once KVM is enabled by hand, but the VVD image lacks the WebView module, so the `vegaWebview` template can't be tested without a physical device.
