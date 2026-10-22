# Demo video script (target 2:50)

**Setup before recording**
- `.\scripts\run.ps1 -Seed` then open http://127.0.0.1:8787 in a full-screen Chrome window (F11).
- In a second terminal, run `.\.venv\Scripts\python -m edge.run` with the webcam over the "workbench" (props: multimeter, safety goggles, keys, mug, and a desk lamp as the "soldering iron").
- Screen recorder at 1080p capturing the browser. A phone filming the desk gives a nice picture-in-picture.
- Lint heartbeat: `CHRONOGRID_LINT_INTERVAL=3` in `.env`.
- AgentCore brain: `.\scripts\tunnel.ps1` running and `CHRONOGRID_AGENT_RUNTIME_ARN` set, and start the server at least a minute before recording; it warms the runtime and keeps it warm (warm turns take 3–4 s).
- Fire TV: `wsl -e bash -l scripts/vega/vvd-up.sh`, then `scripts/vega/tv-deploy.sh`. Snap the "Vega Virtual Device" window to the right half of the screen for the Fire TV shots.

| Time | Shot | Voiceover / action |
| --- | --- | --- |
| 0:00–0:15 | Phone shot: you drop the safety goggles in a drawer and walk off. Cut to the screen. | (hold Space) **"Alexa, where did I leave my safety goggles?"** The screen jumps to the rewind clip looping the moment with a pulsing box; Polly: *"You put the safety goggles in Drawer 2 at …"* |
| 0:15–0:35 | Title card over the heatmap | "Cameras record everything and remember nothing. **ChronoGrid** gives your home a commit history: a self-hosted **MCP server** for **Alexa+** that turns an on-device camera into git for the physical world." |
| 0:35–0:55 | Fire TV (Vega Virtual Device) | "The same memory lives on the TV: **ChronoGrid TV** is a native React Native for Vega app." Use the remote's D-pad across the heatmap (zones by hour), OK on a busy cell to open the rewind, left/right through the object's history, Back. Then ask **"Alexa, where are my keys?"** and the TV jumps to the rewind on its own. |
| 0:55–1:25 | git commit / diff | **"Alexa, commit the workbench as clean."** The commit card appears. Move the multimeter to the drawer and add a mug. **"What changed on the bench?"** The red and green diff appears: *missing the multimeter (now in Drawer 2); new the mug*. |
| 1:25–2:05 | The linter | **"Warn me if the soldering iron is on and nobody's at the bench for 20 seconds."** The lint-rule pull request card shows the typed conditions Bedrock compiled, on the web screen and on the TV. Approve it with **OK on the Fire TV remote**. Switch on the lamp (or press H), walk out of frame. After about 20 s the hazard card slides in on both screens, chimes, and Alexa speaks the warning. Walk back: **"I'm on it, snooze that."** (or OK on the TV's focused Snooze button). |
| 2:05–2:35 | Under the hood | Split screen: the edge preview (YOLO-World on-device, faces blurred in clips), the terminal running `scripts/mcp_smoke.py` (*protocol agreed: 2025-11-25*, `where_is [MCP App ui://chronogrid/rewind.html]`), and the AgentCore console showing the AlexaBrain runtime and its memory. "Alexa's brain is a Strands agent on **Amazon Bedrock AgentCore Runtime** running Nova 2 Lite, with **AgentCore Memory** for household preferences. It calls back into this home's MCP server through a tunnel that only exposes `/mcp`, behind a token. The LLM only interprets and writes rules; facts and alerts are deterministic. Clips live in private S3 with presigned URLs and 7-day expiry; Polly is the voice." |
| 2:35–2:50 | Close | "Makerspaces, caregivers, anyone who's ever lost their keys. ChronoGrid: git for the physical world. Open source, MIT." Repo URL on screen. |

**Tips**
- Say the wake phrase naturally; the agent ignores "Alexa," at the start.
- Re-take quickly with `curl -X POST http://127.0.0.1:8787/api/demo/reset` (or `Invoke-RestMethod -Method Post .../api/demo/reset`). Reset right before recording too: the seeded history is relative to the time you seed, so an old seed leaves the heatmap empty.
- Avoid phrasing like "remember that…" during takes; Alexa may turn it into a rule draft. Reject stray drafts on screen.
- Use only your own footage, no copyrighted music.
