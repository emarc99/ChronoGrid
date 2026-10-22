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

### 7. Fire TV: Vega Virtual Device on Windows works through WSL2, but only off the documented path
- **Tool:** Vega Developer Tools 0.24.12112, Vega CLI 1.4.5, WSL2 Ubuntu 24.04 (kernel 6.18), Intel i5-1135G7
- **Task:** Run a Vega app on the Vega Virtual Device (VVD) from a Windows laptop with no Vega device.
- **Expected:** The docs list only macOS and native Ubuntu, so we first assumed Windows developers were locked out of the Fire TV track.
- **Actual:** It works, but it took about 45 minutes of trial and error:
  1. `/dev/kvm` is missing in WSL2 until `modprobe kvm_intel` is run and the user is added to the `kvm` group.
  2. The `ppa:deadsnakes` step in the install guide returned HTTP 503. It's only needed for crash symbolication, but the guide presents it as required.
  3. The VVD is killed when the shell that ran `vega virtual-device start` exits, so `start` followed by `run-app` in a new shell fails with "Device not found".
  4. A warm re-boot of a killed instance failed with "failed to access shell" after the 60 s deadline; deleting the instance fixed it.
  5. The `vegaWebview` template builds, but the VVD can't install it: "missing modules ... `/com.amazon.kepler.webview_4@IWebview_4` ... Test your app using a Fire TV Stick instead." The stock `helloWorld` React Native template runs fine.
- **Severity:** S2 (blocked us for an evening; a hosted web app can't be wrapped for the simulator)
- **Workaround:** Our setup scripts are in [`scripts/vega/`](../scripts/vega/).
- **Suggestion:** Document WSL2 + KVM as a supported (or at least known-good) host, make the Python 3.8 step optional, keep the VVD alive independently of the launching shell, and ship the WebView module in the VVD image (or say up front in the template list that `vegaWebview` needs a physical device).

### 8. AgentCore: two CLIs, and an unlisted `uv` prerequisite
- **Tool:** Amazon Bedrock AgentCore CLI `@aws/agentcore` 0.31.1 on Windows 11
- **Task:** Move the Strands Alexa+ brain to AgentCore Runtime with AgentCore Memory.
- **Actual:**
  1. Most blog posts and samples still use the Python `bedrock-agentcore-starter-toolkit` (`agentcore configure/launch`), which is being retired in favour of the npm CLI (`agentcore create/deploy`). The commands share a name but not a workflow, so it's easy to follow the wrong guide.
  2. CodeZip packaging shells out to `uv`, which isn't mentioned as a prerequisite; the deploy failed until `uv` was on `PATH`.
  3. `agentcore create` printed a "folder already exists" message but did create the project.
  4. The first deploy took about 8.5 minutes (CDK bootstrap plus stack), with no indication of which step was slow.
- **Severity:** S3
- **Suggestion:** Check for `uv` up front with an install hint, add a migration note at the top of the starter-toolkit README, and show per-resource progress during the first deploy.
