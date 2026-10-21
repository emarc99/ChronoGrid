import asyncio
import json
import time

from server.hub import Hub
from server.ledger import Ledger
from server.mcp_server import REWIND_URI, build_mcp
from server.storage import ClipStore


def build(tmp_path):
    ledger = Ledger(":memory:")
    ledger.upsert_zone("workbench", "Workbench")
    ledger.upsert_zone("drawer-2", "Drawer 2")
    now = time.time()
    ledger.record_event("placed", "multimeter", "workbench", ts=now - 3600, bbox=[0.1, 0.2, 0.3, 0.4])
    ledger.record_event("placed", "multimeter", "drawer-2", ts=now - 600, bbox=[0.6, 0.5, 0.8, 0.7], clip="m.mp4")
    clips = ClipStore(tmp_path, "http://localhost:8787")
    return ledger, build_mcp(ledger, Hub(), clips)


def structured(result):
    if isinstance(result, tuple):
        return result[1]
    if hasattr(result, "structured_content"):
        return result.structured_content
    return json.loads(result[0].text)


def test_where_is_speaks_from_ledger(tmp_path):
    _, mcp = build(tmp_path)
    out = structured(asyncio.run(mcp.call_tool("where_is", {"object": "the multimeter"})))
    assert out["zone_name"] == "Drawer 2"
    assert out["clip_url"] == "http://localhost:8787/clips/m.mp4"
    assert out["say"].startswith("You put the multimeter in Drawer 2")
    assert [h["kind"] for h in out["history"]] == ["moved", "placed"]


def test_rewind_tool_is_bound_to_ui_resource(tmp_path):
    _, mcp = build(tmp_path)
    tools = {t.name: t for t in asyncio.run(mcp.list_tools())}
    meta = tools["where_is"].meta or {}
    assert meta["ui"]["resourceUri"] == REWIND_URI
    resources = asyncio.run(mcp.list_resources())
    assert any(str(r.uri) == REWIND_URI for r in resources)


def test_commit_then_diff(tmp_path):
    ledger, mcp = build(tmp_path)
    asyncio.run(mcp.call_tool("commit_room", {"zone": "drawer two", "message": "tidy"}))
    ledger.record_event("removed", "multimeter", "drawer-2")
    out = structured(asyncio.run(mcp.call_tool("room_diff", {"zone": "drawer-2"})))
    assert out["removed"][0]["label"] == "multimeter"
    assert "missing the multimeter" in out["say"]


def test_propose_and_approve_rule(tmp_path):
    ledger, mcp = build(tmp_path)
    rule = {
        "name": "unattended-iron",
        "message": "The iron is on and the bench is empty.",
        "when": [
            {"type": "appliance_on", "appliance": "soldering iron"},
            {"type": "person_absent", "zone": "the workbench", "for_seconds": 60},
        ],
    }
    out = structured(asyncio.run(mcp.call_tool("propose_lint_rule", {"rule": rule, "request_text": "warn me"})))
    assert out["rule"]["status"] == "proposed"
    assert out["rule"]["spec"]["when"][1]["zone"] == "workbench"
    approved = structured(asyncio.run(mcp.call_tool("approve_lint_rule", {})))
    assert approved["rule"]["status"] == "active"
    assert ledger.rules(status="active")
