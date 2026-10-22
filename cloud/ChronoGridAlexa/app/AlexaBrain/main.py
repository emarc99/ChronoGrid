"""ChronoGrid's Alexa+ brain on Amazon Bedrock AgentCore Runtime.

A Strands agent that reaches the household's self-hosted ChronoGrid MCP server over
Streamable HTTP, remembers the household across sessions with AgentCore Memory,
and returns the spoken reply plus the MCP tool trace for the ambient screen.

Payload: {"prompt": str, "mcp_url": str, "mcp_token": str?, "now": "Thursday 10:30 AM", "household": str?}
"""

from __future__ import annotations

from typing import Any

from bedrock_agentcore.runtime import BedrockAgentCoreApp
from strands import Agent
from strands.agent.conversation_manager import SlidingWindowConversationManager
from strands.hooks import BeforeToolCallEvent

from mcp_client.client import chronogrid_mcp_client
from memory.session import get_memory_session_manager
from model.load import load_model

app = BedrockAgentCoreApp()
log = app.logger

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

Memory: you may remember the household's preferences from earlier conversations (for example how
they name things or how long they like rules to wait), but object locations always come from tools.

The current local time is {now}.
"""

_agents: dict[str, tuple[Agent, list[dict[str, Any]]]] = {}


def _agent_for(session_id: str, actor_id: str, mcp_url: str, mcp_token: str | None) -> tuple[Agent, list[dict[str, Any]]]:
    key = f"{session_id}/{actor_id}/{mcp_url}"
    if key not in _agents:
        trace: list[dict[str, Any]] = []
        agent = Agent(
            model=load_model(),
            tools=[chronogrid_mcp_client(mcp_url, mcp_token)],
            system_prompt=SYSTEM_PROMPT,
            conversation_manager=SlidingWindowConversationManager(window_size=24),
            session_manager=get_memory_session_manager(session_id, actor_id),
            callback_handler=None,
            name="alexa-plus",
        )
        agent.hooks.add_callback(
            BeforeToolCallEvent,
            lambda e: trace.append({"tool": e.tool_use.get("name"), "input": e.tool_use.get("input")}),
        )
        _agents[key] = (agent, trace)
    return _agents[key]


@app.entrypoint
async def invoke(payload: dict[str, Any], context) -> dict[str, Any]:
    prompt = payload.get("prompt", "")
    mcp_url = payload.get("mcp_url")
    if not prompt or not mcp_url:
        return {"error": "payload needs prompt and mcp_url"}
    session_id = getattr(context, "session_id", None) or "household-default-session-000000000"
    actor_id = payload.get("household", "household")
    agent, trace = _agent_for(session_id, actor_id, mcp_url, payload.get("mcp_token"))
    agent.system_prompt = SYSTEM_PROMPT.format(now=payload.get("now", "unknown"))
    trace.clear()
    log.info("utterance: %s", prompt)
    result = await agent.invoke_async(prompt)
    return {"reply": str(result).strip(), "tools": list(trace)}


if __name__ == "__main__":
    app.run()
