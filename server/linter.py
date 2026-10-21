"""Background daemon that lints the physical space on a fixed heartbeat."""

from __future__ import annotations

import asyncio
import logging
import time

from pydantic import ValidationError

from .hub import Hub
from .ledger import Ledger
from .rules import LintRule, evaluate

log = logging.getLogger("chronogrid.linter")


class Linter:
    def __init__(self, ledger: Ledger, hub: Hub, interval: float = 30.0):
        self.ledger = ledger
        self.hub = hub
        self.interval = interval

    async def run(self) -> None:
        while True:
            try:
                self.tick()
            except Exception:
                log.exception("lint tick failed")
            await asyncio.sleep(self.interval)

    def tick(self, now: float | None = None) -> list[dict]:
        now = time.time() if now is None else now
        changes = []
        for rule_row in self.ledger.rules(status="active"):
            try:
                rule = LintRule.model_validate(rule_row["spec"])
            except ValidationError:
                log.warning("rule %s has an invalid spec; skipping", rule_row["id"])
                continue
            finding = evaluate(rule, self.ledger, now)
            latest = self.ledger.latest_alert_for_rule(rule_row["id"])
            if finding.fired:
                if latest and latest["status"] == "open":
                    continue
                if latest and latest["status"] == "snoozed" and (latest["snoozed_until"] or 0) > now:
                    continue
                if latest and latest["status"] == "resolved" and now - (latest["resolved_ts"] or 0) < rule.cooldown_seconds:
                    continue
                alert = self.ledger.create_alert(
                    rule_row["id"], rule.severity, rule.name, rule.message, finding.evidence
                )
                changes.append({"type": "alert", "alert": alert})
            elif latest and latest["status"] in ("open", "snoozed"):
                alert = self.ledger.resolve_alert(latest["id"])
                changes.append({"type": "alert_resolved", "alert": alert})
        for change in changes:
            self.hub.publish(change)
        return changes
