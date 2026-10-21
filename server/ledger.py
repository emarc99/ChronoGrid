"""Spatial-temporal ledger: the append-only "commit history" of a physical space.

Every observation from the edge becomes an immutable event. Derived tables
(object_state, presence, appliance_state) are the "working tree" and are only
ever updated from events, so any answer can be traced back to evidence.
"""

from __future__ import annotations

import difflib
import json
import sqlite3
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

SCHEMA = """
CREATE TABLE IF NOT EXISTS zones (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    kind TEXT NOT NULL DEFAULT 'area',
    polygon TEXT NOT NULL DEFAULT '[]'
);
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts REAL NOT NULL,
    kind TEXT NOT NULL,
    label TEXT,
    zone_id TEXT,
    from_zone TEXT,
    bbox TEXT,
    clip TEXT,
    confidence REAL,
    meta TEXT
);
CREATE INDEX IF NOT EXISTS idx_events_label_ts ON events(label, ts);
CREATE INDEX IF NOT EXISTS idx_events_zone_ts ON events(zone_id, ts);
CREATE TABLE IF NOT EXISTS object_state (
    label TEXT PRIMARY KEY,
    zone_id TEXT,
    present INTEGER NOT NULL,
    ts REAL NOT NULL,
    bbox TEXT,
    clip TEXT,
    event_id INTEGER
);
CREATE TABLE IF NOT EXISTS presence (
    zone_id TEXT PRIMARY KEY,
    present INTEGER NOT NULL,
    since REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS appliance_state (
    label TEXT PRIMARY KEY,
    zone_id TEXT,
    is_on INTEGER NOT NULL,
    since REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts REAL NOT NULL,
    zone_id TEXT NOT NULL,
    message TEXT NOT NULL,
    objects TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created REAL NOT NULL,
    status TEXT NOT NULL,
    source_text TEXT,
    spec TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts REAL NOT NULL,
    rule_id INTEGER NOT NULL,
    severity TEXT NOT NULL,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    status TEXT NOT NULL,
    snoozed_until REAL,
    resolved_ts REAL,
    evidence TEXT
);
"""

OBJECT_KINDS = {"placed", "moved", "removed", "seen"}
PRESENCE_KINDS = {"person_enter", "person_exit"}
APPLIANCE_KINDS = {"appliance_on", "appliance_off"}
EVENT_KINDS = OBJECT_KINDS | PRESENCE_KINDS | APPLIANCE_KINDS


def normalize_label(label: str) -> str:
    return " ".join(label.strip().lower().replace("_", " ").split())


@dataclass
class Event:
    id: int
    ts: float
    kind: str
    label: str | None
    zone_id: str | None
    from_zone: str | None
    bbox: list[float] | None
    clip: str | None
    confidence: float | None
    meta: dict[str, Any]

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "Event":
        return cls(
            id=row["id"],
            ts=row["ts"],
            kind=row["kind"],
            label=row["label"],
            zone_id=row["zone_id"],
            from_zone=row["from_zone"],
            bbox=json.loads(row["bbox"]) if row["bbox"] else None,
            clip=row["clip"],
            confidence=row["confidence"],
            meta=json.loads(row["meta"]) if row["meta"] else {},
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "ts": self.ts,
            "kind": self.kind,
            "label": self.label,
            "zone_id": self.zone_id,
            "from_zone": self.from_zone,
            "bbox": self.bbox,
            "clip": self.clip,
            "confidence": self.confidence,
            "meta": self.meta,
        }


def _point_in_polygon(x: float, y: float, polygon: list[list[float]]) -> bool:
    inside = False
    n = len(polygon)
    for i in range(n):
        x1, y1 = polygon[i]
        x2, y2 = polygon[(i + 1) % n]
        if (y1 > y) != (y2 > y):
            x_cross = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
            if x < x_cross:
                inside = not inside
    return inside


class Ledger:
    def __init__(self, path: Path | str = ":memory:"):
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.RLock()
        with self._lock:
            self._conn.executescript(SCHEMA)
            self._conn.commit()

    def _query(self, sql: str, params: Iterable[Any] = ()) -> list[sqlite3.Row]:
        with self._lock:
            return self._conn.execute(sql, tuple(params)).fetchall()

    def _exec(self, sql: str, params: Iterable[Any] = ()) -> int:
        with self._lock:
            cur = self._conn.execute(sql, tuple(params))
            self._conn.commit()
            return cur.lastrowid or 0

    # ---- zones -------------------------------------------------------------

    def upsert_zone(self, zone_id: str, name: str, kind: str = "area", polygon: list[list[float]] | None = None) -> None:
        self._exec(
            "INSERT INTO zones(id, name, kind, polygon) VALUES (?,?,?,?) "
            "ON CONFLICT(id) DO UPDATE SET name=excluded.name, kind=excluded.kind, polygon=excluded.polygon",
            (zone_id, name, kind, json.dumps(polygon or [])),
        )

    def zones(self) -> list[dict[str, Any]]:
        return [
            {"id": r["id"], "name": r["name"], "kind": r["kind"], "polygon": json.loads(r["polygon"])}
            for r in self._query("SELECT * FROM zones ORDER BY id")
        ]

    def zone_name(self, zone_id: str | None) -> str:
        if not zone_id:
            return "an unknown spot"
        rows = self._query("SELECT name FROM zones WHERE id=?", (zone_id,))
        return rows[0]["name"] if rows else zone_id

    def zone_for_point(self, x: float, y: float) -> str | None:
        for zone in self.zones():
            if len(zone["polygon"]) >= 3 and _point_in_polygon(x, y, zone["polygon"]):
                return zone["id"]
        return None

    def resolve_zone(self, query: str) -> str | None:
        """Map free text like 'the bench' or 'drawer two' to a zone id."""
        q = normalize_label(query).replace("the ", "")
        zones = self.zones()
        for z in zones:
            if q in (z["id"], normalize_label(z["name"])):
                return z["id"]
        for z in zones:
            if q in normalize_label(z["name"]) or normalize_label(z["name"]) in q or q in z["id"]:
                return z["id"]
        names = {normalize_label(z["name"]): z["id"] for z in zones}
        match = difflib.get_close_matches(q, list(names), n=1, cutoff=0.5)
        return names[match[0]] if match else None

    # ---- ingest ------------------------------------------------------------

    def record_event(
        self,
        kind: str,
        label: str | None = None,
        zone_id: str | None = None,
        *,
        ts: float | None = None,
        bbox: list[float] | None = None,
        clip: str | None = None,
        confidence: float | None = None,
        from_zone: str | None = None,
        meta: dict[str, Any] | None = None,
    ) -> Event:
        if kind not in EVENT_KINDS:
            raise ValueError(f"unknown event kind {kind!r}")
        ts = time.time() if ts is None else ts
        label = normalize_label(label) if label else None
        with self._lock:
            if kind in OBJECT_KINDS and label and from_zone is None:
                prev = self.object_state(label)
                if prev and prev["present"] and prev["zone_id"] != zone_id:
                    from_zone = prev["zone_id"]
                    if kind == "placed":
                        kind = "moved"
            event_id = self._exec(
                "INSERT INTO events(ts, kind, label, zone_id, from_zone, bbox, clip, confidence, meta) "
                "VALUES (?,?,?,?,?,?,?,?,?)",
                (
                    ts,
                    kind,
                    label,
                    zone_id,
                    from_zone,
                    json.dumps(bbox) if bbox else None,
                    clip,
                    confidence,
                    json.dumps(meta) if meta else None,
                ),
            )
            self._apply(event_id, ts, kind, label, zone_id, bbox, clip)
        return self.event(event_id)

    def _apply(self, event_id, ts, kind, label, zone_id, bbox, clip) -> None:
        if kind in {"placed", "moved"}:
            self._exec(
                "INSERT INTO object_state(label, zone_id, present, ts, bbox, clip, event_id) VALUES (?,?,1,?,?,?,?) "
                "ON CONFLICT(label) DO UPDATE SET zone_id=excluded.zone_id, present=1, ts=excluded.ts, "
                "bbox=excluded.bbox, clip=COALESCE(excluded.clip, object_state.clip), event_id=excluded.event_id",
                (label, zone_id, ts, json.dumps(bbox) if bbox else None, clip, event_id),
            )
        elif kind == "seen":
            self._exec(
                "INSERT INTO object_state(label, zone_id, present, ts, bbox, clip, event_id) VALUES (?,?,1,?,?,?,?) "
                "ON CONFLICT(label) DO UPDATE SET present=1, bbox=COALESCE(excluded.bbox, object_state.bbox)",
                (label, zone_id, ts, json.dumps(bbox) if bbox else None, clip, event_id),
            )
        elif kind == "removed":
            self._exec("UPDATE object_state SET present=0, ts=?, event_id=? WHERE label=?", (ts, event_id, label))
        elif kind in PRESENCE_KINDS:
            present = 1 if kind == "person_enter" else 0
            self._exec(
                "INSERT INTO presence(zone_id, present, since) VALUES (?,?,?) "
                "ON CONFLICT(zone_id) DO UPDATE SET present=excluded.present, "
                "since=CASE WHEN presence.present=excluded.present THEN presence.since ELSE excluded.since END",
                (zone_id, present, ts),
            )
        elif kind in APPLIANCE_KINDS:
            is_on = 1 if kind == "appliance_on" else 0
            self._exec(
                "INSERT INTO appliance_state(label, zone_id, is_on, since) VALUES (?,?,?,?) "
                "ON CONFLICT(label) DO UPDATE SET zone_id=COALESCE(excluded.zone_id, appliance_state.zone_id), "
                "is_on=excluded.is_on, "
                "since=CASE WHEN appliance_state.is_on=excluded.is_on THEN appliance_state.since ELSE excluded.since END",
                (label, zone_id, is_on, ts),
            )

    # ---- reads -------------------------------------------------------------

    def event(self, event_id: int) -> Event:
        return Event.from_row(self._query("SELECT * FROM events WHERE id=?", (event_id,))[0])

    def events(
        self,
        *,
        since: float | None = None,
        until: float | None = None,
        zone_id: str | None = None,
        label: str | None = None,
        kinds: Iterable[str] | None = None,
        limit: int = 200,
        newest_first: bool = True,
    ) -> list[Event]:
        sql, params = "SELECT * FROM events WHERE 1=1", []
        if since is not None:
            sql += " AND ts >= ?"
            params.append(since)
        if until is not None:
            sql += " AND ts <= ?"
            params.append(until)
        if zone_id:
            sql += " AND (zone_id = ? OR from_zone = ?)"
            params += [zone_id, zone_id]
        if label:
            sql += " AND label = ?"
            params.append(normalize_label(label))
        if kinds:
            kinds = list(kinds)
            sql += f" AND kind IN ({','.join('?' * len(kinds))})"
            params += kinds
        sql += f" ORDER BY ts {'DESC' if newest_first else 'ASC'}, id {'DESC' if newest_first else 'ASC'} LIMIT ?"
        params.append(limit)
        return [Event.from_row(r) for r in self._query(sql, params)]

    def known_labels(self) -> list[str]:
        return [r["label"] for r in self._query("SELECT label FROM object_state ORDER BY label")]

    def resolve_label(self, query: str) -> str | None:
        """Map 'my safety goggles' to the tracked label 'goggles'."""
        q = normalize_label(query)
        for prefix in ("my ", "the ", "a "):
            if q.startswith(prefix):
                q = q[len(prefix):]
        labels = self.known_labels()
        if q in labels:
            return q
        for label in labels:
            if label in q or q in label:
                return label
        match = difflib.get_close_matches(q, labels, n=1, cutoff=0.6)
        return match[0] if match else None

    def object_state(self, label: str) -> dict[str, Any] | None:
        rows = self._query("SELECT * FROM object_state WHERE label=?", (normalize_label(label),))
        if not rows:
            return None
        r = rows[0]
        return {
            "label": r["label"],
            "zone_id": r["zone_id"],
            "present": bool(r["present"]),
            "ts": r["ts"],
            "bbox": json.loads(r["bbox"]) if r["bbox"] else None,
            "clip": r["clip"],
            "event_id": r["event_id"],
        }

    def objects(self, zone_id: str | None = None, present_only: bool = True) -> list[dict[str, Any]]:
        sql, params = "SELECT label FROM object_state WHERE 1=1", []
        if present_only:
            sql += " AND present=1"
        if zone_id:
            sql += " AND zone_id=?"
            params.append(zone_id)
        return [self.object_state(r["label"]) for r in self._query(sql + " ORDER BY label", params)]

    def presence(self, zone_id: str) -> dict[str, Any]:
        rows = self._query("SELECT * FROM presence WHERE zone_id=?", (zone_id,))
        if not rows:
            return {"zone_id": zone_id, "present": False, "since": None}
        return {"zone_id": zone_id, "present": bool(rows[0]["present"]), "since": rows[0]["since"]}

    def appliance(self, label: str) -> dict[str, Any] | None:
        rows = self._query("SELECT * FROM appliance_state WHERE label=?", (normalize_label(label),))
        if not rows:
            return None
        r = rows[0]
        return {"label": r["label"], "zone_id": r["zone_id"], "on": bool(r["is_on"]), "since": r["since"]}

    def appliances(self) -> list[dict[str, Any]]:
        return [self.appliance(r["label"]) for r in self._query("SELECT label FROM appliance_state ORDER BY label")]

    def activity_grid(self, hours: int = 12, now: float | None = None) -> dict[str, Any]:
        """Zone x hour event counts: the 'ChronoGrid' heatmap."""
        now = time.time() if now is None else now
        start = (int(now // 3600) - hours + 1) * 3600
        buckets = [start + i * 3600 for i in range(hours)]
        zones = [z["id"] for z in self.zones()]
        counts = {z: [0] * hours for z in zones}
        for r in self._query(
            "SELECT zone_id, ts FROM events WHERE ts >= ? AND zone_id IS NOT NULL AND kind != 'seen'", (start,)
        ):
            idx = int((r["ts"] - start) // 3600)
            if r["zone_id"] in counts and 0 <= idx < hours:
                counts[r["zone_id"]][idx] += 1
        return {"hours": buckets, "zones": zones, "counts": counts}

    # ---- snapshots (git commit / diff) --------------------------------------

    def commit(self, zone_id: str, message: str, ts: float | None = None) -> dict[str, Any]:
        ts = time.time() if ts is None else ts
        objects = {o["label"]: o["bbox"] for o in self.objects(zone_id)}
        snap_id = self._exec(
            "INSERT INTO snapshots(ts, zone_id, message, objects) VALUES (?,?,?,?)",
            (ts, zone_id, message, json.dumps(objects)),
        )
        return {"id": snap_id, "ts": ts, "zone_id": zone_id, "message": message, "objects": sorted(objects)}

    def last_commit(self, zone_id: str) -> dict[str, Any] | None:
        rows = self._query("SELECT * FROM snapshots WHERE zone_id=? ORDER BY ts DESC, id DESC LIMIT 1", (zone_id,))
        if not rows:
            return None
        r = rows[0]
        return {"id": r["id"], "ts": r["ts"], "zone_id": r["zone_id"], "message": r["message"],
                "objects": json.loads(r["objects"])}

    def diff(self, zone_id: str, since: float | None = None) -> dict[str, Any]:
        """Compare a zone now against its last commit (or its state at `since`)."""
        if since is None:
            base = self.last_commit(zone_id)
            if base is None:
                return {"zone_id": zone_id, "base": None, "added": [], "removed": [], "unchanged": []}
            base_labels = set(base["objects"])
            base_info = {"kind": "commit", "id": base["id"], "ts": base["ts"], "message": base["message"]}
        else:
            base_labels = self._labels_in_zone_at(zone_id, since)
            base_info = {"kind": "time", "ts": since}
        now_labels = {o["label"] for o in self.objects(zone_id)}
        removed = []
        for label in sorted(base_labels - now_labels):
            state = self.object_state(label)
            now_in = state["zone_id"] if state and state["present"] else None
            removed.append({"label": label, "now_in": now_in, "now_in_name": self.zone_name(now_in) if now_in else None})
        return {
            "zone_id": zone_id,
            "base": base_info,
            "added": sorted(now_labels - base_labels),
            "removed": removed,
            "unchanged": sorted(base_labels & now_labels),
        }

    def _labels_in_zone_at(self, zone_id: str, ts: float) -> set[str]:
        labels = set()
        for r in self._query(
            "SELECT e.label, e.kind, e.zone_id FROM events e JOIN ("
            "  SELECT label, MAX(id) AS id FROM events WHERE ts <= ? AND kind IN ('placed','moved','removed') "
            "  GROUP BY label) last ON e.id = last.id",
            (ts,),
        ):
            if r["kind"] != "removed" and r["zone_id"] == zone_id:
                labels.add(r["label"])
        return labels

    # ---- rules -------------------------------------------------------------

    def add_rule(self, spec: dict[str, Any], status: str = "proposed", source_text: str | None = None) -> dict[str, Any]:
        rule_id = self._exec(
            "INSERT INTO rules(created, status, source_text, spec) VALUES (?,?,?,?)",
            (time.time(), status, source_text, json.dumps(spec)),
        )
        return self.rule(rule_id)

    def rule(self, rule_id: int) -> dict[str, Any] | None:
        rows = self._query("SELECT * FROM rules WHERE id=?", (rule_id,))
        if not rows:
            return None
        r = rows[0]
        return {"id": r["id"], "created": r["created"], "status": r["status"], "source_text": r["source_text"],
                "spec": json.loads(r["spec"])}

    def rules(self, status: str | None = None) -> list[dict[str, Any]]:
        sql, params = "SELECT id FROM rules", []
        if status:
            sql += " WHERE status=?"
            params.append(status)
        return [self.rule(r["id"]) for r in self._query(sql + " ORDER BY id", params)]

    def set_rule_status(self, rule_id: int, status: str) -> dict[str, Any] | None:
        self._exec("UPDATE rules SET status=? WHERE id=?", (status, rule_id))
        return self.rule(rule_id)

    # ---- alerts ------------------------------------------------------------

    def create_alert(self, rule_id: int, severity: str, title: str, body: str, evidence: list[str]) -> dict[str, Any]:
        alert_id = self._exec(
            "INSERT INTO alerts(ts, rule_id, severity, title, body, status, evidence) VALUES (?,?,?,?,?, 'open', ?)",
            (time.time(), rule_id, severity, title, body, json.dumps(evidence)),
        )
        return self.alert(alert_id)

    def alert(self, alert_id: int) -> dict[str, Any] | None:
        rows = self._query("SELECT * FROM alerts WHERE id=?", (alert_id,))
        if not rows:
            return None
        r = rows[0]
        return {
            "id": r["id"], "ts": r["ts"], "rule_id": r["rule_id"], "severity": r["severity"],
            "title": r["title"], "body": r["body"], "status": r["status"],
            "snoozed_until": r["snoozed_until"], "resolved_ts": r["resolved_ts"],
            "evidence": json.loads(r["evidence"]) if r["evidence"] else [],
        }

    def alerts(self, status: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        sql, params = "SELECT id FROM alerts", []
        if status:
            sql += " WHERE status=?"
            params.append(status)
        sql += " ORDER BY ts DESC LIMIT ?"
        params.append(limit)
        return [self.alert(r["id"]) for r in self._query(sql, params)]

    def latest_alert_for_rule(self, rule_id: int) -> dict[str, Any] | None:
        rows = self._query("SELECT id FROM alerts WHERE rule_id=? ORDER BY ts DESC, id DESC LIMIT 1", (rule_id,))
        return self.alert(rows[0]["id"]) if rows else None

    def resolve_alert(self, alert_id: int) -> dict[str, Any] | None:
        self._exec("UPDATE alerts SET status='resolved', resolved_ts=? WHERE id=?", (time.time(), alert_id))
        return self.alert(alert_id)

    def snooze_alert(self, alert_id: int, minutes: float) -> dict[str, Any] | None:
        self._exec(
            "UPDATE alerts SET status='snoozed', snoozed_until=? WHERE id=?",
            (time.time() + minutes * 60, alert_id),
        )
        return self.alert(alert_id)

    def reset(self) -> None:
        with self._lock:
            for table in ("events", "object_state", "presence", "appliance_state", "snapshots", "rules", "alerts"):
                self._conn.execute(f"DELETE FROM {table}")
            self._conn.commit()
