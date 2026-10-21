from server.ledger import Ledger
from server.rules import LintRule, evaluate

UNATTENDED_IRON = LintRule.model_validate(
    {
        "name": "unattended-soldering-iron",
        "message": "The soldering iron is on and nobody is at the bench.",
        "severity": "critical",
        "when": [
            {"type": "appliance_on", "appliance": "soldering iron"},
            {"type": "person_absent", "zone": "workbench", "for_seconds": 120},
        ],
    }
)


def make_ledger() -> Ledger:
    ledger = Ledger(":memory:")
    ledger.upsert_zone("workbench", "Workbench")
    ledger.upsert_zone("entry", "Entry Table")
    return ledger


def test_unattended_appliance_fires_only_after_threshold():
    ledger = make_ledger()
    ledger.record_event("person_enter", zone_id="workbench", ts=0)
    ledger.record_event("appliance_on", "soldering iron", "workbench", ts=10)
    assert not evaluate(UNATTENDED_IRON, ledger, now=50).fired
    ledger.record_event("person_exit", zone_id="workbench", ts=60)
    assert not evaluate(UNATTENDED_IRON, ledger, now=100).fired
    finding = evaluate(UNATTENDED_IRON, ledger, now=200)
    assert finding.fired
    assert any("nobody at Workbench" in e for e in finding.evidence)


def test_appliance_off_clears_rule():
    ledger = make_ledger()
    ledger.record_event("appliance_on", "soldering iron", "workbench", ts=0)
    ledger.record_event("person_exit", zone_id="workbench", ts=0)
    assert evaluate(UNATTENDED_IRON, ledger, now=500).fired
    ledger.record_event("appliance_off", "soldering iron", "workbench", ts=510)
    assert not evaluate(UNATTENDED_IRON, ledger, now=520).fired


def test_preflight_keys_missing():
    rule = LintRule.model_validate(
        {
            "name": "preflight-keys",
            "message": "Your keys are not on the entry table.",
            "when": [{"type": "object_missing", "object": "keys", "zone": "entry"}],
        }
    )
    ledger = make_ledger()
    ledger.record_event("placed", "keys", "workbench", ts=1)
    assert evaluate(rule, ledger, now=2).fired
    ledger.record_event("placed", "keys", "entry", ts=3)
    assert not evaluate(rule, ledger, now=4).fired


def test_broken_routine_sequence():
    rule = LintRule.model_validate(
        {
            "name": "thawing-chicken",
            "message": "The chicken left the freezer but never made it to the fridge.",
            "when": [
                {
                    "type": "sequence_not_followed",
                    "first": {"kind": "removed", "label": "chicken"},
                    "then": {"kind": "placed", "label": "chicken"},
                    "within_seconds": 600,
                }
            ],
        }
    )
    ledger = make_ledger()
    ledger.record_event("placed", "chicken", "workbench", ts=0)
    ledger.record_event("removed", "chicken", "workbench", ts=100)
    assert not evaluate(rule, ledger, now=200).fired
    assert evaluate(rule, ledger, now=800).fired
    ledger.record_event("placed", "chicken", "entry", ts=900)
    assert not evaluate(rule, ledger, now=950).fired


def test_rule_rejects_unknown_condition():
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        LintRule.model_validate({"name": "x", "message": "y", "when": [{"type": "vibes"}]})
