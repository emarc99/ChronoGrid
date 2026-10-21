"""Alexa+ simulation: Strands Agents SDK + Amazon Bedrock, with ChronoGrid as an MCP tool server.

The agent connects to ChronoGrid exactly the way Alexa+ connects to a self-hosted
MCP server: over Streamable HTTP. It only interprets requests and phrases replies;
facts come from tool results.
"""

from __future__ import annotations

import logging
import threading
import time
from datetime import datetime
from typing import Any

from strands import Agent
from strands.agent.conversation_manager import SlidingWindowConversationManager
from strands.models import BedrockModel
from strands.tools.mcp import MCPClient

log = logging.getLogger("chronogrid.agent")

SYSTEM_PROMPT = """\
You are Alexa+, speaking through a household ambient screen. ChronoGrid gives you a long-term
spatial memory of the home and workshop through MCP tools.

Voice rules:
- Answer in one or two short spoken sentences. No markdown, no lists, no emojis.
- For any question about where things are, what changed, or what is on, call a ChronoGrid tool first.
- When a tool result has a `say` field, speak it (you may lightly smooth it, but never change times, places or counts).
- Never guess locations or times that are not in a tool result.

Rules and alerts:
- If the user asks to be warned, reminded or alerted about a situation, call room_status first if you
  need zone ids, then call propose_lint_rule with a typed rule (all conditions must hold together).
  Pick sensible thresholds (e.g. 'a couple of minutes' = 120 seconds). Then tell them it is waiting for approval.
- "approve it" / "yes, turn it on" -> approve_lint_rule. "snooze" / "I'm on it" -> snooze_alert.
- "commit the bench", "save this as clean" -> commit_room. "what changed", "is it tidy" -> room_diff.

The current local time is {now}.
"""


class AlexaBrain:
    def __init__(self, mcp_url: str, model_id: str, region: str, session_bucket: str | None = None):
        self.mcp_url = mcp_url
        self.model_id = model_id
        self.region = region
        self.session_bucket = session_bucket
        self._client: MCPClient | None = None
        self._agent: Agent | None = None
        self._lock = threading.Lock()

    def _session_manager(self):
        session_id = "household-" + datetime.now().strftime("%Y%m%d")
        if self.session_bucket:
            from strands.session.s3_session_manager import S3SessionManager

            return S3SessionManager(session_id=session_id, bucket=self.session_bucket, prefix="sessions/",
                                    region_name=self.region)
        from strands.session.file_session_manager import FileSessionManager

        return FileSessionManager(session_id=session_id, storage_dir="data/sessions")

    def _ensure(self) -> Agent:
        if self._agent is not None:
            return self._agent
        self._client = MCPClient(url=self.mcp_url, application_name="alexa-plus-simulator")
        self._client.start()
        tools = self._client.list_tools_sync()
        log.info("loaded %d ChronoGrid MCP tools", len(tools))
        self._agent = Agent(
            model=BedrockModel(model_id=self.model_id, region_name=self.region, temperature=0.2, max_tokens=600),
            tools=tools,
            system_prompt=SYSTEM_PROMPT.format(now=datetime.now().strftime("%A %I:%M %p")),
            conversation_manager=SlidingWindowConversationManager(window_size=24),
            session_manager=self._session_manager(),
            callback_handler=None,
            name="alexa-plus",
        )
        return self._agent

    def ask(self, utterance: str) -> dict[str, Any]:
        with self._lock:
            agent = self._ensure()
            agent.system_prompt = SYSTEM_PROMPT.format(now=datetime.now().strftime("%A %I:%M %p"))
            start = len(agent.messages)
            t0 = time.perf_counter()
            result = agent(utterance)
            latency_ms = int((time.perf_counter() - t0) * 1000)
            trace = _tool_trace(agent.messages[start:])
        return {"reply": str(result).strip(), "tools": trace, "latency_ms": latency_ms, "model": self.model_id}

    def close(self) -> None:
        if self._client is not None:
            self._client.stop(None, None, None)
            self._client = None
            self._agent = None


def _tool_trace(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    trace = []
    for message in messages:
        for block in message.get("content", []):
            if "toolUse" in block:
                use = block["toolUse"]
                trace.append({"tool": use.get("name"), "input": use.get("input")})
    return trace
