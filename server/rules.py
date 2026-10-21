"""ChronoLint: a small typed rule language for physical spaces.

The LLM never decides whether an alert fires. It only *authors* a LintRule
(validated by Pydantic), a human approves it, and `evaluate` runs it
deterministically against the ledger on every linter heartbeat.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field

from .ledger import Ledger, normalize_label


class EventPattern(BaseModel):
    kind: Literal["placed", "moved", "removed", "person_enter", "person_exit", "appliance_on", "appliance_off"]
    label: str | None = Field(None, description="Object or appliance label, e.g. 'frozen chicken'")
    zone: str | None = Field(None, description="Zone id the event must happen in")


class ApplianceOn(BaseModel):
    """True while an appliance (heat source, tool) is switched on."""

    type: Literal["appliance_on"] = "appliance_on"
    appliance: str = Field(description="Appliance label, e.g. 'soldering iron' or 'stove'")
    for_seconds: int = Field(0, ge=0, description="Only true once it has been on at least this long")


class PersonAbsent(BaseModel):
    """True when nobody has been seen in a zone for at least `for_seconds`."""

    type: Literal["person_absent"] = "person_absent"
    zone: str = Field(description="Zone id, e.g. 'workbench'")
    for_seconds: int = Field(ge=0)


class ObjectMissing(BaseModel):
    """True when an object is not currently in a zone."""

    type: Literal["object_missing"] = "object_missing"
    object: str
    zone: str


class ObjectPresent(BaseModel):
    """True when an object is currently in a zone."""

    type: Literal["object_present"] = "object_present"
    object: str
    zone: str


class TimeWindow(BaseModel):
    """True when the local clock is between start and end (HH:MM, may wrap midnight)."""

    type: Literal["time_window"] = "time_window"
    start: str = Field(pattern=r"^\d{2}:\d{2}$")
    end: str = Field(pattern=r"^\d{2}:\d{2}$")


class SequenceNotFollowed(BaseModel):
    """Broken routine: `first` happened but `then` did not follow within `within_seconds`."""

    type: Literal["sequence_not_followed"] = "sequence_not_followed"
    first: EventPattern
    then: EventPattern
    within_seconds: int = Field(gt=0)


Condition = Annotated[
    Union[ApplianceOn, PersonAbsent, ObjectMissing, ObjectPresent, TimeWindow, SequenceNotFollowed],
    Field(discriminator="type"),
]


class LintRule(BaseModel):
    """A rule fires when *all* conditions in `when` hold at the same time."""

    name: str = Field(description="Short kebab-case name, e.g. 'unattended-soldering-iron'")
    message: str = Field(description="What the household should hear, e.g. 'The soldering iron is on and nobody is at the bench.'")
    severity: Literal["info", "warning", "critical"] = "warning"
    when: list[Condition] = Field(min_length=1)
    cooldown_seconds: int = Field(300, ge=0, description="Minimum gap before the same rule re-alerts")


@dataclass
class Finding:
    fired: bool
    evidence: list[str] = field(default_factory=list)


def _ago(seconds: float) -> str:
    seconds = max(0, int(seconds))
    if seconds < 90:
        return f"{seconds}s"
    if seconds < 5400:
        return f"{round(seconds / 60)}m"
    return f"{seconds / 3600:.1f}h"


def _minutes(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def _check(cond, ledger: Ledger, now: float) -> tuple[bool, str]:
    if isinstance(cond, ApplianceOn):
        state = ledger.appliance(cond.appliance)
        if not state or not state["on"]:
            return False, f"{cond.appliance} is off"
        on_for = now - state["since"]
        return on_for >= cond.for_seconds, f"{state['label']} on for {_ago(on_for)}"

    if isinstance(cond, PersonAbsent):
        p = ledger.presence(cond.zone)
        name = ledger.zone_name(cond.zone)
        if p["present"]:
            return False, f"someone is at {name}"
        absent_for = now - (p["since"] or 0)
        return absent_for >= cond.for_seconds, f"nobody at {name} for {_ago(absent_for)}"

    if isinstance(cond, (ObjectMissing, ObjectPresent)):
        state = ledger.object_state(cond.object)
        here = bool(state and state["present"] and state["zone_id"] == cond.zone)
        where = ledger.zone_name(state["zone_id"]) if state and state["present"] else "not seen"
        detail = f"{normalize_label(cond.object)}: {where}"
        return (not here, detail) if isinstance(cond, ObjectMissing) else (here, detail)

    if isinstance(cond, TimeWindow):
        t = datetime.fromtimestamp(now)
        cur, start, end = t.hour * 60 + t.minute, _minutes(cond.start), _minutes(cond.end)
        inside = start <= cur < end if start <= end else (cur >= start or cur < end)
        return inside, f"time {t:%H:%M} {'inside' if inside else 'outside'} {cond.start}-{cond.end}"

    if isinstance(cond, SequenceNotFollowed):
        first = _last_match(ledger, cond.first, until=now)
        if first is None:
            return False, f"no {cond.first.kind} {cond.first.label or ''}".strip()
        elapsed = now - first.ts
        follow = _last_match(ledger, cond.then, since=first.ts, until=now)
        if follow is not None:
            return False, f"{cond.then.kind} {cond.then.label or ''} followed".strip()
        return elapsed >= cond.within_seconds, (
            f"{cond.first.kind} {first.label or ''} {_ago(elapsed)} ago, no {cond.then.kind} {cond.then.label or ''}"
        )

    raise TypeError(f"unsupported condition {cond!r}")


def _last_match(ledger: Ledger, pattern: EventPattern, since: float | None = None, until: float | None = None):
    events = ledger.events(
        since=since, until=until, label=pattern.label, zone_id=pattern.zone, kinds=[pattern.kind], limit=1
    )
    return events[0] if events else None


def evaluate(rule: LintRule, ledger: Ledger, now: float | None = None) -> Finding:
    now = time.time() if now is None else now
    evidence, fired = [], True
    for cond in rule.when:
        ok, detail = _check(cond, ledger, now)
        evidence.append(detail)
        fired = fired and ok
    return Finding(fired=fired, evidence=evidence)


def referenced_zones(rule: LintRule) -> set[str]:
    zones = set()
    for cond in rule.when:
        if isinstance(cond, (PersonAbsent, ObjectMissing, ObjectPresent)):
            zones.add(cond.zone)
        if isinstance(cond, SequenceNotFollowed):
            zones |= {z for z in (cond.first.zone, cond.then.zone) if z}
    return zones
