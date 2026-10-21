# Demo video script (target 2:50)

**Setup before recording**
- `.\scripts\run.ps1 -Seed` then open http://127.0.0.1:8787 in a full-screen Chrome window (F11).
- In a second terminal, run `.\.venv\Scripts\python -m edge.run` with the webcam over the "workbench" (props: multimeter, safety goggles, keys, mug, and a desk lamp as the "soldering iron").
- Screen recorder at 1080p capturing the browser. A phone filming the desk gives a nice picture-in-picture.
- Lint heartbeat: `CHRONOGRID_LINT_INTERVAL=3` in `.env`.

| Time | Shot | Voiceover / action |
| --- | --- | --- |
| 0:00–0:15 | Phone shot: you drop the safety goggles in a drawer and walk off. Cut to the screen. | (hold Space) **"Alexa, where did I leave my safety goggles?"** The screen jumps to the rewind clip looping the moment with a pulsing box; Polly: *"You put the safety goggles in Drawer 2 at …"* |
| 0:15–0:35 | Title card over the heatmap | "Cameras record everything and remember nothing. **ChronoGrid** gives your home a commit history: a self-hosted **MCP server** for **Alexa+** that turns an on-device camera into git for the physical world." |
| 0:35–0:55 | Remote navigation | Arrow keys across the ChronoGrid heatmap (zones by hour), OK on a busy cell to open the rewind, left/right through the object's history, Back. "It's a 10-foot UI: voice, D-pad and visuals in one flow." |
| 0:55–1:25 | git commit / diff | **"Alexa, commit the workbench as clean."** The commit card appears. Move the multimeter to the drawer and add a mug. **"What changed on the bench?"** The red and green diff appears: *missing the multimeter (now in Drawer 2); new the mug*. |
| 1:25–2:05 | The linter | **"Warn me if the soldering iron is on and nobody's at the bench for 20 seconds."** The lint-rule pull request card shows the typed conditions Bedrock compiled. **"Approve it."** Switch on the lamp (or press H), walk out of frame. After about 20 s the hazard HUD slides in, chimes, and Alexa speaks the warning. Walk back: **"I'm on it, snooze that."** |
| 2:05–2:35 | Under the hood | Split screen: the edge preview (YOLO-World on-device, faces blurred in clips), the terminal running `scripts/mcp_smoke.py` (*protocol agreed: 2025-11-25*, `where_is [MCP App ui://chronogrid/rewind.html]`), and the tool-trace chips. "The LLM, Amazon Nova 2 Lite via the Strands Agents SDK, only interprets and writes rules; facts and alerts are deterministic. Clips live in private S3 with presigned URLs and 7-day expiry; Polly is the voice." |
| 2:35–2:50 | Close | "Makerspaces, caregivers, anyone who's ever lost their keys. ChronoGrid: git for the physical world. Open source, MIT." Repo URL on screen. |

**Tips**
- Say the wake phrase naturally; the agent ignores "Alexa," at the start.
- Re-take quickly with `curl -X POST http://127.0.0.1:8787/api/demo/reset` (or `Invoke-RestMethod -Method Post .../api/demo/reset`).
- Use only your own footage, no copyrighted music.
