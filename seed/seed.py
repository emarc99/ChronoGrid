"""Seed a believable day of workshop history so the demo works without a camera.

    python -m seed.seed            # reset + seed data/chronogrid.db
    python -m seed.seed --keep     # add zones and rules only, keep existing events
"""

from __future__ import annotations

import argparse
import json
import random
import time
from pathlib import Path

from server.config import load_settings
from server.ledger import Ledger

HERE = Path(__file__).parent

UNATTENDED_IRON = {
    "source_text": "Warn me if the soldering iron is on and nobody's at the bench for two minutes.",
    "spec": {
        "name": "unattended-soldering-iron",
        "message": "The soldering iron is on and nobody is at the workbench.",
        "severity": "critical",
        "cooldown_seconds": 120,
        "when": [
            {"type": "appliance_on", "appliance": "soldering iron"},
            {"type": "person_absent", "zone": "workbench", "for_seconds": 120},
        ],
    },
}

RULES = [
    {
        "source_text": "On weekday mornings, remind me if my keys aren't on the entry table.",
        "spec": {
            "name": "preflight-keys",
            "message": "Heads up: your keys are not on the entry table.",
            "severity": "info",
            "cooldown_seconds": 900,
            "when": [
                {"type": "time_window", "start": "07:30", "end": "08:30"},
                {"type": "object_missing", "object": "keys", "zone": "entry"},
            ],
        },
    },
]

# (minutes ago, kind, label, zone, bbox)
HISTORY = [
    (540, "placed", "multimeter", "shelf", [0.10, 0.12, 0.22, 0.30]),
    (530, "placed", "safety goggles", "shelf", [0.28, 0.10, 0.42, 0.24]),
    (525, "placed", "pliers", "workbench", [0.08, 0.62, 0.20, 0.80]),
    (520, "placed", "keys", "entry", [0.62, 0.18, 0.72, 0.30]),
    (480, "removed", "keys", "entry", None),
    (300, "placed", "keys", "entry", [0.64, 0.20, 0.74, 0.31]),
    (240, "placed", "mug", "workbench", [0.34, 0.55, 0.44, 0.72]),
    (190, "placed", "multimeter", "workbench", [0.14, 0.58, 0.30, 0.82]),
    (150, "placed", "safety goggles", "workbench", [0.26, 0.48, 0.42, 0.62]),
    (95, "placed", "tape measure", "drawer-2", [0.58, 0.62, 0.70, 0.78]),
    (60, "placed", "safety goggles", "drawer-2", [0.74, 0.60, 0.90, 0.74]),
    (35, "placed", "multimeter", "drawer-2", [0.60, 0.70, 0.78, 0.92]),
]


def seed(ledger: Ledger, keep: bool = False, now: float | None = None, with_iron_rule: bool = False) -> None:
    now = time.time() if now is None else now
    if not keep:
        ledger.reset()
    for z in json.loads((HERE / "zones.json").read_text()):
        ledger.upsert_zone(z["id"], z["name"], z["kind"], z["polygon"])
    for rule in RULES + ([UNATTENDED_IRON] if with_iron_rule else []):
        if not any(r["spec"]["name"] == rule["spec"]["name"] for r in ledger.rules()):
            ledger.add_rule(rule["spec"], status="active", source_text=rule["source_text"])
    if keep:
        return
    rng = random.Random(7)
    for minutes in range(520, 0, -rng.randint(18, 40)):
        ledger.record_event("person_enter", zone_id="workbench", ts=now - minutes * 60)
        ledger.record_event("person_exit", zone_id="workbench", ts=now - minutes * 60 + rng.randint(300, 900))
    committed = False
    for minutes, kind, label, zone, bbox in HISTORY:
        if not committed and minutes < 180:
            ledger.commit("workbench", "clean bench before soldering", ts=now - 180 * 60)
            committed = True
        ledger.record_event(kind, label, zone, ts=now - minutes * 60, bbox=bbox, confidence=0.9)
    ledger.record_event("person_enter", zone_id="workbench", ts=now - 120)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--keep", action="store_true", help="keep existing events")
    parser.add_argument("--with-iron-rule", action="store_true",
                        help="pre-activate the unattended soldering iron rule instead of authoring it by voice")
    args = parser.parse_args()
    settings = load_settings()
    ledger = Ledger(settings.db_path)
    seed(ledger, keep=args.keep, with_iron_rule=args.with_iron_rule)
    print(f"seeded {settings.db_path}: {len(ledger.zones())} zones, {len(ledger.rules())} rules, "
          f"{len(ledger.events(limit=10000))} events")


if __name__ == "__main__":
    main()
