"""ChronoGrid MCP server: git verbs for a physical space, served over Streamable HTTP.

Every tool answers from the ledger and returns a deterministic `say` sentence,
so a voice assistant (Alexa+) can speak facts without paraphrasing numbers.
Tools also push a matching view to the ambient screen through the hub.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from mcp.server.apps import Apps, ResourceCsp
from mcp.server.mcpserver import MCPServer
from pydantic import ValidationError

from .humanize import ago, clock, join
from .hub import Hub
from .ledger import Ledger
from .rules import LintRule, referenced_zones
from .storage import ClipStore

REWIND_URI = "ui://chronogrid/rewind.html"

INSTRUCTIONS = """\
ChronoGrid is the long-term spatial memory of a home or workshop, built from an edge camera.
It works like git for physical space:
- where_is / object_log / blame: the history of an object (git log, git blame).
- room_status / commit_room / room_diff: snapshot a zone's known-good state and diff against it.
- lint_status / propose_lint_rule / approve_lint_rule / snooze_alert: real-world lint rules
  (e.g. an unattended heat source) that a deterministic daemon enforces.
Always speak the `say` field of a result when present; never invent times or places.
New lint rules are only *proposed*; the household approves them on the screen or by voice.
"""


def _event_view(ledger: Ledger, clips: ClipStore, e) -> dict[str, Any]:
    return {
        "event_id": e.id,
        "kind": e.kind,
        "zone_id": e.zone_id,
        "zone_name": ledger.zone_name(e.zone_id),
        "from_zone_name": ledger.zone_name(e.from_zone) if e.from_zone else None,
        "ts": e.ts,
        "time_text": clock(e.ts),
        "ago_text": ago(e.ts),
        "bbox": e.bbox,
        "clip_url": clips.url(e.clip),
    }


def build_mcp(ledger: Ledger, hub: Hub, clips: ClipStore, csp_domains: list[str] | None = None) -> MCPServer:
    apps = Apps()

    def not_found(query: str) -> dict[str, Any]:
        known = ledger.known_labels()
        return {
            "found": False,
            "object": query,
            "known_objects": known,
            "say": f"I haven't seen {query} yet. I'm tracking {join(known[:6]) or 'nothing so far'}.",
        }

    def zone_or_error(zone: str) -> tuple[str | None, dict[str, Any] | None]:
        zone_id = ledger.resolve_zone(zone)
        if zone_id:
            return zone_id, None
        names = [z["name"] for z in ledger.zones()]
        return None, {"error": "unknown_zone", "zones": names, "say": f"I don't know a zone called {zone}. Try {join(names)}."}

    @apps.tool(
        resource_uri=REWIND_URI,
        title="Where is it?",
        description=(
            "Find where an object was last put down. Returns the zone, time, a 5-second rewind clip "
            "with the object's bounding box, and its recent placement history."
        ),
    )
    def where_is(object: str) -> dict[str, Any]:
        label = ledger.resolve_label(object)
        if not label:
            return not_found(object)
        history = ledger.events(label=label, kinds=["placed", "moved", "removed"], limit=6)
        state = ledger.object_state(label)
        latest = next((e for e in history if e.kind != "removed"), None)
        result: dict[str, Any] = {
            "found": True,
            "object": label,
            "present": state["present"] if state else False,
            "history": [_event_view(ledger, clips, e) for e in history],
        }
        if latest is None:
            result["say"] = f"The {label} was taken away {ago(history[0].ts)} and I haven't seen it since."
        else:
            view = _event_view(ledger, clips, latest)
            result.update(view)
            removed_after = history and history[0].kind == "removed"
            result["say"] = (
                f"You put the {label} in {view['zone_name']} at {view['time_text']}, {view['ago_text']}."
                + (" It was picked up again after that." if removed_after else "")
            )
        hub.publish({"type": "screen", "view": "rewind", "data": result})
        return result

    rewind_html = (Path(__file__).parent / "apps" / "rewind.html").read_text(encoding="utf-8")
    apps.add_html_resource(
        REWIND_URI,
        rewind_html,
        name="ChronoGrid Rewind",
        description="Loops the moment an object was put down, with its bounding box and placement history.",
        csp=ResourceCsp(resource_domains=csp_domains or []),
        prefers_border=False,
    )

    mcp = MCPServer(
        "chronogrid",
        title="ChronoGrid",
        description="Git for the physical world: spatial memory and real-world lint rules for Alexa+.",
        instructions=INSTRUCTIONS,
        version="0.1.0",
        extensions=[apps],
    )

    @mcp.tool(description="The placement history (git log) of an object, newest first.")
    def object_log(object: str, limit: int = 5) -> dict[str, Any]:
        label = ledger.resolve_label(object)
        if not label:
            return not_found(object)
        events = ledger.events(label=label, kinds=["placed", "moved", "removed"], limit=max(1, min(limit, 20)))
        entries = [_event_view(ledger, clips, e) for e in events]
        lines = [
            f"{'took it from' if e['kind'] == 'removed' else 'put it in'} {e['zone_name']} at {e['time_text']}"
            for e in entries[:3]
        ]
        result = {"found": True, "object": label, "entries": entries, "say": f"For the {label}: you " + join(lines) + "."}
        hub.publish({"type": "screen", "view": "log", "data": result})
        return result

    @mcp.tool(description="Who or what last moved an object (git blame): the move, where it came from and whether a person was present.")
    def blame(object: str) -> dict[str, Any]:
        label = ledger.resolve_label(object)
        if not label:
            return not_found(object)
        moves = ledger.events(label=label, kinds=["placed", "moved", "removed"], limit=1)
        if not moves:
            return not_found(object)
        e = moves[0]
        nearby = ledger.events(
            since=e.ts - 30, until=e.ts + 5, zone_id=e.from_zone or e.zone_id, kinds=["person_enter"], limit=5
        )
        verb = {"moved": "moved", "removed": "picked up", "placed": "put down"}[e.kind]
        where = f"from {ledger.zone_name(e.from_zone)} to {ledger.zone_name(e.zone_id)}" if e.kind == "moved" else f"at {ledger.zone_name(e.zone_id)}"
        who = "while someone was at that spot" if nearby else "with nobody detected nearby"
        result = {
            "found": True,
            "object": label,
            "event": _event_view(ledger, clips, e),
            "person_present": bool(nearby),
            "say": f"The {label} was last {verb} {where} at {clock(e.ts)}, {who}.",
        }
        hub.publish({"type": "screen", "view": "rewind", "data": {**result, **result["event"], "history": [result["event"]]}})
        return result

    @mcp.tool(description="Current state of one zone or the whole space (git status): objects, people, active appliances, and uncommitted changes.")
    def room_status(zone: str | None = None) -> dict[str, Any]:
        zone_ids = [z["id"] for z in ledger.zones()]
        if zone:
            zone_id, err = zone_or_error(zone)
            if err:
                return err
            zone_ids = [zone_id]
        zones_out, sentences = [], []
        for zid in zone_ids:
            objects = [o["label"] for o in ledger.objects(zid)]
            diff = ledger.diff(zid)
            dirty = bool(diff["base"]) and bool(diff["added"] or diff["removed"])
            zones_out.append({
                "zone_id": zid,
                "zone_name": ledger.zone_name(zid),
                "objects": objects,
                "person_present": ledger.presence(zid)["present"],
                "uncommitted": {"added": diff["added"], "removed": [r["label"] for r in diff["removed"]]} if dirty else None,
            })
            if zone or objects:
                sentences.append(f"{ledger.zone_name(zid)} has {join(objects) or 'nothing'}")
        on = [a for a in ledger.appliances() if a["on"]]
        appliances = [{"label": a["label"], "zone_name": ledger.zone_name(a["zone_id"]), "on_since": clock(a["since"])} for a in on]
        say = ". ".join(sentences) + "."
        if appliances:
            say += " Still on: " + join([f"the {a['label']} since {a['on_since']}" for a in appliances]) + "."
        result = {"zones": zones_out, "appliances_on": appliances, "say": say}
        hub.publish({"type": "screen", "view": "status", "data": result})
        return result

    @mcp.tool(description="Save a zone's current layout as its known-good state (git commit), e.g. 'commit the workbench as clean'.")
    def commit_room(zone: str, message: str = "known-good layout") -> dict[str, Any]:
        zone_id, err = zone_or_error(zone)
        if err:
            return err
        snap = ledger.commit(zone_id, message)
        result = {**snap, "zone_name": ledger.zone_name(zone_id),
                  "say": f"Committed {ledger.zone_name(zone_id)} with {len(snap['objects'])} items: {join(snap['objects'])}."}
        hub.publish({"type": "screen", "view": "commit", "data": result})
        return result

    @mcp.tool(description="What changed in a zone (git diff) since its last commit, or since N minutes ago if since_minutes is given.")
    def room_diff(zone: str, since_minutes: int | None = None) -> dict[str, Any]:
        zone_id, err = zone_or_error(zone)
        if err:
            return err
        since = time.time() - since_minutes * 60 if since_minutes else None
        diff = ledger.diff(zone_id, since=since)
        name = ledger.zone_name(zone_id)
        if diff["base"] is None:
            say = f"{name} has no commit yet. Say 'commit the {name}' to save its known-good state."
        elif not diff["added"] and not diff["removed"]:
            say = f"{name} is clean. Nothing changed since {clock(diff['base']['ts'])}."
        else:
            parts = []
            if diff["removed"]:
                parts.append("missing " + join([
                    f"the {r['label']}" + (f" (now in {r['now_in_name']})" if r["now_in_name"] else "") for r in diff["removed"]
                ]))
            if diff["added"]:
                parts.append("new " + join([f"the {a}" for a in diff["added"]]))
            say = f"{name} changed since {clock(diff['base']['ts'])}: " + "; ".join(parts) + "."
        result = {**diff, "zone_name": name, "say": say}
        hub.publish({"type": "screen", "view": "diff", "data": result})
        return result

    @mcp.tool(description="Active real-world lint alerts and the rules being enforced.")
    def lint_status() -> dict[str, Any]:
        open_alerts = ledger.alerts(status="open")
        rules = ledger.rules()
        active = [r for r in rules if r["status"] == "active"]
        proposed = [r for r in rules if r["status"] == "proposed"]
        if open_alerts:
            say = f"{len(open_alerts)} warning{'s' if len(open_alerts) > 1 else ''}: " + " ".join(a["body"] for a in open_alerts)
        else:
            say = f"All clear. {len(active)} rule{'s' if len(active) != 1 else ''} active."
        if proposed:
            say += f" {len(proposed)} new rule{'s' if len(proposed) > 1 else ''} waiting for approval."
        return {"open_alerts": open_alerts, "rules": rules, "say": say}

    @mcp.tool(
        description=(
            "Propose a new lint rule from the user's request. Fill `rule` with typed conditions that ALL must hold. "
            "Use zone ids from room_status. The rule is NOT enforced until approved."
        )
    )
    def propose_lint_rule(rule: LintRule, request_text: str) -> dict[str, Any]:
        unknown = [z for z in referenced_zones(rule) if z not in {zz["id"] for zz in ledger.zones()}]
        fixed = rule.model_dump()
        for cond in fixed["when"]:
            for key in ("zone",):
                if cond.get(key) in unknown:
                    cond[key] = ledger.resolve_zone(cond[key]) or cond[key]
        try:
            rule = LintRule.model_validate(fixed)
        except ValidationError as exc:
            return {"error": "invalid_rule", "detail": str(exc), "say": "I couldn't turn that into a rule."}
        still_unknown = [z for z in referenced_zones(rule) if z not in {zz["id"] for zz in ledger.zones()}]
        if still_unknown:
            return {"error": "unknown_zone", "zones": [z["id"] for z in ledger.zones()],
                    "say": f"I don't know the zone {join(still_unknown)}."}
        row = ledger.add_rule(rule.model_dump(), status="proposed", source_text=request_text)
        result = {"rule": row, "say": f"I drafted a rule called {rule.name}. Approve it on the screen, or say 'approve it'."}
        hub.publish({"type": "screen", "view": "rule_pr", "data": row})
        return result

    @mcp.tool(description="Approve (activate) a proposed lint rule. Use the most recent proposed rule if the user just says 'approve it'.")
    def approve_lint_rule(rule_id: int | None = None) -> dict[str, Any]:
        if rule_id is None:
            proposed = ledger.rules(status="proposed")
            if not proposed:
                return {"error": "nothing_to_approve", "say": "There are no rules waiting for approval."}
            rule_id = proposed[-1]["id"]
        row = ledger.set_rule_status(rule_id, "active")
        if not row:
            return {"error": "unknown_rule", "say": f"I couldn't find rule {rule_id}."}
        hub.publish({"type": "rule_updated", "rule": row})
        return {"rule": row, "say": f"Rule {row['spec']['name']} is now active."}

    @mcp.tool(description="Snooze an open alert for some minutes. Defaults to the most recent open alert.")
    def snooze_alert(alert_id: int | None = None, minutes: int = 10) -> dict[str, Any]:
        if alert_id is None:
            open_alerts = ledger.alerts(status="open")
            if not open_alerts:
                return {"error": "nothing_open", "say": "There's nothing to snooze."}
            alert_id = open_alerts[0]["id"]
        alert = ledger.snooze_alert(alert_id, minutes)
        if not alert:
            return {"error": "unknown_alert", "say": f"I couldn't find alert {alert_id}."}
        hub.publish({"type": "alert_snoozed", "alert": alert})
        return {"alert": alert, "say": f"Okay, snoozed for {minutes} minutes."}

    @mcp.resource("chronogrid://zones", name="zones", description="Zones of the space with their ids and names.", mime_type="application/json")
    def zones_resource() -> list[dict[str, Any]]:
        return ledger.zones()

    return mcp
