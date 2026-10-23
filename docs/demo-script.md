# Demo video script (target 2:50)

**Final video:** https://youtu.be/HXjRUBO-OiU

## How the video was made
- **Camera feed:** four free Pexels stock clips replayed through the unchanged edge pipeline (`edge.run --source clip.mp4`), each watching only for the objects in that shot. Our laptop webcam couldn't reliably name hand tools ([friction log #12](friction-log.md#12-edge-vision-yolo-world-on-a-live-laptop-webcam-couldnt-name-our-hand-tools)). Every label, 5-second clip, ledger event and S3 upload shown was produced live by ChronoGrid.
- **Alexa+:** simulated. Real Alexa+ can't connect to a self-hosted MCP server yet, so the web screen stands in for an Alexa+ ambient screen. The brain is our Strands agent on Amazon Bedrock AgentCore (Nova 2 Lite), and the voice is Amazon Polly. Voice input uses the browser's speech recognition. One rule was typed after it heard "soldering iron" as "sovereign union"; the rule pull-request card let us catch that before approving.
- **Fire TV:** ChronoGrid TV running on the Vega Virtual Device under WSL2, driven by the keyboard and on-screen remote.
- **Editing:** takes were recorded separately and joined. Loading pauses and mouse wiggles (the VVD repaint quirk, friction log #9) were trimmed. The Drawer 2 commit was recorded before the scissors and phone arrived, as the diff requires. The hazard fired about 2 s after the iron came on because the bench had already been empty for over 20 s, so both conditions were already true.

Recording order we used: reset, replay the first mug shot; Take 1 (edge preview of the pink mug, then "Where did I leave my mug?"); Take 2 (commit Drawer 2, replay scissors and phone, "What changed in drawer 2?"); Take 3 (TV D-pad, then "Where are the scissors?" driving the TV); Take 4 (the soldering-iron rule and hazard, snooze); Take 5 (MCP smoke test, AgentCore console, idle heatmap for the title card).

**Setup before recording**
- `.\scripts\run.ps1 -Seed` then open http://127.0.0.1:8787 in a full-screen Chrome window (F11).
- Camera feed: we replay free stock footage (Pexels, kept in the gitignored `online-clips/`) through the same edge pipeline, because the laptop webcam in a dim room couldn't name our own hand tools. Each replay watches only for the objects in that shot:
  ```powershell
  Invoke-RestMethod -Method Post http://127.0.0.1:8787/api/demo/reset
  .\.venv\Scripts\python -m edge.run --source online-clips\6889671-hd_1280_720_25fps.mp4 --vocab "person,mug" --conf 0.4
  .\.venv\Scripts\python -m edge.run --source online-clips\13591483_1280_720_30fps.mp4 --vocab "person,smartphone=phone,mug"
  # say "commit drawer 2 as clean" here if you're filming the diff scene, then:
  .\.venv\Scripts\python -m edge.run --source online-clips\trimmed\scissors.mp4 --vocab "person,scissors"
  .\.venv\Scripts\python -m edge.run --source online-clips\7821643-hd_1280_720_30fps.mp4 --vocab "person,smartphone=phone"
  ```
  The result: mug moved to the entry, then the shelf; scissors and phone placed in Drawer 2; each event has a 5-second clip in S3. Leave out `--no-preview` to film the edge window with its live boxes.
- With a live webcam instead: `.\.venv\Scripts\python -m edge.run` over the "workbench" (props: phone, mug, keys, scissors, and a desk lamp as the "soldering iron"). Good light matters.
- Screen recorder at 1080p capturing the browser. A phone filming the desk gives a nice picture-in-picture.
- Lint heartbeat: `CHRONOGRID_LINT_INTERVAL=3` in `.env`.
- AgentCore brain: `.\scripts\tunnel.ps1` running and `CHRONOGRID_AGENT_RUNTIME_ARN` set, and start the server at least a minute before recording; it warms the runtime and keeps it warm (warm turns take 3–4 s). Quick tunnels can silently expire overnight: if Alexa says *"Sorry, I couldn't reach ChronoGrid just now"*, close the tunnel window and run `.\scripts\tunnel.ps1` again; the server picks up the new URL on the next question.
- Fire TV: `wsl -e bash -l scripts/vega/vvd-up.sh`, then `scripts/vega/tv-deploy.sh`. Snap the "Vega Virtual Device" window to the right half of the screen for the Fire TV shots.
- Run only one `agentcore deploy` at a time. Two at once deadlock on `cdk.out\synth.lock`.

**Fire TV repaint quirk.** Under WSLg the Vega Virtual Device window only redraws while the real mouse moves over the TV picture (not the remote). After each Alexa question, wiggle the mouse over the TV picture for a second or the new screen won't appear. If the picture still looks stuck, minimize and restore the window. The app itself is fine; see friction log #9. Only camera-recorded events have a clip; seeded history (keys, multimeter) shows the zone map instead.

| Time | Shot | Voiceover / action |
| --- | --- | --- |
| 0:00–0:15 | The edge preview replaying the pink-mug shot, boxes on the mug and phone. Cut to the screen. | (hold Space) **"Alexa, where did I leave my mug?"** The screen jumps to the rewind clip looping the moment with a pulsing box; Polly: *"You put the mug on the tool shelf at …"* |
| 0:15–0:35 | Title card over the heatmap | "Cameras record everything and remember nothing. **ChronoGrid** gives your home a commit history: a self-hosted **MCP server** for **Alexa+** that turns an on-device camera into git for the physical world." |
| 0:35–0:55 | Fire TV (Vega Virtual Device) | "The same memory lives on the TV: **ChronoGrid TV** is a native React Native for Vega app." Use the remote's D-pad across the heatmap (zones by hour), OK on a busy cell to open the rewind, left/right through the object's history, Back. Then ask **"Alexa, where are the scissors?"** and the TV jumps to the rewind on its own and loops the scissors clip (wiggle the mouse over the TV picture). |
| 0:55–1:25 | git commit / diff | **"Alexa, commit drawer 2 as clean."** The commit card appears. Replay the scissors and phone shots (see setup). **"What changed in drawer 2?"** The green diff appears: *new the scissors, new the phone*. |
| 1:25–2:05 | The linter | **"Warn me if the soldering iron is on and nobody's at the bench for 20 seconds."** The lint-rule pull request card shows the typed conditions Bedrock compiled, on the web screen and on the TV. Approve it with **OK on the Fire TV remote**. Switch on the lamp (or press H in the edge window; with stock footage, nobody is at the bench once a replay ends, so switch the iron on with `Invoke-RestMethod -Method Post http://127.0.0.1:8787/api/appliance -ContentType application/json -Body '{"label":"soldering iron","on":true,"zone_id":"workbench"}'`), walk out of frame. After about 20 s the hazard card slides in on both screens, chimes, and Alexa speaks the warning. Walk back: **"I'm on it, snooze that."** (or OK on the TV's focused Snooze button). |
| 2:05–2:35 | Under the hood | Split screen: the edge preview (YOLO-World on-device, faces blurred in clips), the terminal running `scripts/mcp_smoke.py` (*protocol agreed: 2025-11-25*, `where_is [MCP App ui://chronogrid/rewind.html]`), and the AgentCore console showing the AlexaBrain runtime and its memory. "Alexa's brain is a Strands agent on **Amazon Bedrock AgentCore Runtime** running Nova 2 Lite, with **AgentCore Memory** for household preferences. It calls back into this home's MCP server through a tunnel that only exposes `/mcp`, behind a token. The LLM only interprets and writes rules; facts and alerts are deterministic. Clips live in private S3 with presigned URLs and 7-day expiry; Polly is the voice." |
| 2:35–2:50 | Close | "Makerspaces, caregivers, anyone who's ever lost their keys. ChronoGrid: git for the physical world. Open source, MIT." Repo URL on screen. |

**Tips**
- Say the wake phrase naturally; the agent ignores "Alexa," at the start.
- Re-take quickly with `curl -X POST http://127.0.0.1:8787/api/demo/reset` (or `Invoke-RestMethod -Method Post .../api/demo/reset`). Reset right before recording too: the seeded history is relative to the time you seed, so an old seed leaves the heatmap empty.
- Avoid phrasing like "remember that…" during takes; Alexa may turn it into a rule draft. Reject stray drafts on screen.
- Stock footage from Pexels is fine under its licence (don't redistribute the raw files); say on screen that the camera feed is stock footage replayed through the edge pipeline. No copyrighted music.
