from server.hub import Hub
from server.ledger import Ledger
from server.linter import Linter

SPEC = {
    "name": "unattended-iron",
    "message": "Iron on, bench empty.",
    "severity": "critical",
    "cooldown_seconds": 60,
    "when": [
        {"type": "appliance_on", "appliance": "soldering iron"},
        {"type": "person_absent", "zone": "workbench", "for_seconds": 30},
    ],
}


def setup():
    ledger = Ledger(":memory:")
    ledger.upsert_zone("workbench", "Workbench")
    rule = ledger.add_rule(SPEC, status="active")
    return ledger, Linter(ledger, Hub(), interval=1), rule


def test_alert_opens_once_and_resolves():
    ledger, linter, rule = setup()
    ledger.record_event("appliance_on", "soldering iron", "workbench", ts=0)
    ledger.record_event("person_exit", zone_id="workbench", ts=0)
    first = linter.tick(now=100)
    assert [c["type"] for c in first] == ["alert"]
    assert linter.tick(now=110) == []
    ledger.record_event("appliance_off", "soldering iron", "workbench", ts=120)
    resolved = linter.tick(now=121)
    assert [c["type"] for c in resolved] == ["alert_resolved"]


def test_proposed_rules_are_not_enforced():
    ledger = Ledger(":memory:")
    ledger.upsert_zone("workbench", "Workbench")
    ledger.add_rule(SPEC, status="proposed")
    ledger.record_event("appliance_on", "soldering iron", "workbench", ts=0)
    assert Linter(ledger, Hub()).tick(now=1000) == []


def test_cooldown_after_resolve():
    ledger, linter, _ = setup()
    ledger.record_event("appliance_on", "soldering iron", "workbench", ts=0)
    ledger.record_event("person_exit", zone_id="workbench", ts=0)
    linter.tick(now=100)
    ledger.record_event("appliance_off", "soldering iron", "workbench", ts=101)
    linter.tick(now=102)
    ledger.record_event("appliance_on", "soldering iron", "workbench", ts=103)
    import time

    # resolved_ts uses wall clock, so a tick "now" inside the cooldown window is silent
    assert linter.tick(now=time.time()) == []
