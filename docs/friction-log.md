# Friction log

Real friction hit while building ChronoGrid during the hackathon window, in order of occurrence.
Severity: **S1** blocks progress · **S2** costs significant time or forces a design change · **S3** annoyance.

---

### 1. Bedrock: Anthropic model worked once, then failed with "use case details not submitted"
- **Tool:** Amazon Bedrock (Converse / ConverseStream), `us.anthropic.claude-haiku-4-5-20251001-v1:0`
- **Task:** Run the Strands agent on Claude Haiku 4.5.
- **Steps:** `list-inference-profiles` listed the profile, and a one-shot `Agent("Reply with exactly: ok")` call **succeeded**. Minutes later the same model failed inside the agent loop.
- **Expected:** If the model is listed and a call succeeds, it keeps working.
- **Actual:** `ResourceNotFoundException: Model use case details have not been submitted for this account. Fill out the Anthropic use case details form...` on every following call.
- **Severity:** S2 (it would have been S1 mid-demo)
- **Workaround:** Switched the default to **Amazon Nova 2 Lite**, which worked first time with tool use, so the code stays model-agnostic.
- **Suggestion:** Surface the use-case-form requirement in `list-inference-profiles` / `get-foundation-model-availability` (e.g. `"agreementStatus": "USE_CASE_REQUIRED"`), and fail the *first* call consistently instead of letting one through.

### 2. `pip install strands-agents` silently resolved to the 0.0.1 placeholder
- **Tool:** Strands Agents SDK (PyPI)
- **Task:** Install `mcp[cli]` and `strands-agents` together in a fresh Python 3.13 venv.
- **Expected:** The latest Strands (1.6x).
- **Actual:** pip picked `strands-agents==0.0.1` (an empty placeholder) because the latest `mcp` (2.3.0) was outside Strands' supported range, and no error was raised. `from strands import Agent` then failed.
- **Severity:** S2
- **Workaround:** Pin `strands-agents>=1.40`, which let pip backtrack `mcp` to 2.1.1.
- **Suggestion:** Yank 0.0.1 or make it raise on import with a pointer to the real package; publish the supported `mcp` range in the README.

### 3. Strands `FileSessionManager` can't recover a half-written session directory
- **Tool:** Strands Agents SDK, `strands.session.file_session_manager`
- **Task:** Restart the agent process with the same `session_id`.
- **Actual:** After an interrupted cleanup, `session_<id>/agents/...` existed without `session.json`. `read_session` returned `None`, then `create_session` raised `SessionException: Session ... already exists` on every request.
- **Severity:** S3
- **Workaround:** Delete the directory. In production, use `S3SessionManager`.
- **Suggestion:** Treat a directory without `session.json` as corrupt: repair it, or raise a clearer error with the path.

### 4. Getting a per-turn tool trace from a Strands agent
- **Tool:** Strands Agents SDK
- **Task:** Show which MCP tools Alexa+ called on each turn (for the screen and the demo).
- **Actual:** Slicing `agent.messages[len_before:]` returned nothing once `SlidingWindowConversationManager` began trimming history.
- **Severity:** S3
- **Workaround:** `agent.hooks.add_callback(BeforeToolCallEvent, ...)`, which works well.
- **Suggestion:** Expose `AgentResult.tool_calls` (name, input, duration) for the current invocation; it's the first thing every UI needs.

### 5. Alexa+: no way to point a real Alexa+ device or simulator at a self-hosted MCP server
- **Tool:** Alexa+ (MCP integration path)
- **Task:** Test the ChronoGrid MCP server from Alexa+ itself.
- **Actual:** Outside the brand Preview, there's no console, simulator or device setting to register a Streamable HTTP MCP endpoint, so the experience had to be simulated with Strands + Bedrock + Polly.
- **Severity:** S2
- **Suggestion:** An "Alexa+ MCP test console", like the Alexa Skills Kit simulator, that connects to a developer's `/mcp` URL and shows the tool calls and the spoken response. Even text-only would let developers validate tool descriptions against the real Alexa+ planner.

### 6. Alexa+ and MCP Apps: unclear what renders on Echo Show / Fire TV
- **Tool:** Alexa+ / MCP Apps (`io.modelcontextprotocol/ui`)
- **Task:** Ship the rewind card as an MCP App so screen devices show the clip.
- **Actual:** No documentation on whether Alexa+ multimodal devices render `ui://` resources, which CSP and `resourceDomains` apply, or whether video is allowed in MCP App iframes.
- **Severity:** S3 (ChronoGrid falls back to text plus its own screen)
- **Suggestion:** A short "MCP on Alexa+ screens" doc covering supported `_meta.ui` fields, size limits, and media policy.

### 7. Fire TV: Vega SDK / Vega Virtual Device can't run on Windows (or WSL)
- **Tool:** Vega Developer Tools 0.24
- **Task:** Run the 10-foot UI on the Vega Virtual Device without owning a Vega device.
- **Actual:** The docs state that Windows and WSL aren't supported build hosts and that the SDK needs native macOS or Ubuntu with KVM. A Windows-only developer can't produce the Fire TV track's required "running on device or simulator" video.
- **Severity:** S1 for the Fire TV track (it forced the switch to Alexa+ as the primary track)
- **Workaround:** Built the ambient screen as a web app with Fire TV remote key mapping; the server is client-agnostic.
- **Suggestion:** A cloud-hosted VVD (streamed like a remote emulator), or a supported WSL2 + KVM path. Even an unsupported-but-documented recipe would unblock hackathon developers on Windows.
