"""Turns noisy per-frame detections into ledger events (placed / removed / person enter / exit).

Assumes one instance per label, which matches how people ask ("where are my keys?").
"""

from __future__ import annotations

from dataclasses import dataclass, field

BBox = tuple[float, float, float, float]


@dataclass
class Detection:
    label: str
    confidence: float
    bbox: BBox  # normalized x1, y1, x2, y2


@dataclass
class Track:
    label: str
    bbox: BBox
    last_seen: float
    hits: int = 1
    reported_bbox: BBox | None = None


@dataclass
class TrackerEvent:
    kind: str
    label: str | None = None
    bbox: BBox | None = None
    confidence: float | None = None
    ts: float = 0.0
    extra: dict = field(default_factory=dict)


def iou(a: BBox, b: BBox) -> float:
    ix1, iy1, ix2, iy2 = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    inter = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union > 0 else 0.0


def covers(a: BBox, b: BBox) -> float:
    """Fraction of b covered by a (is a hand/person occluding the object?)."""
    ix1, iy1, ix2, iy2 = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    inter = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
    area = (b[2] - b[0]) * (b[3] - b[1])
    return inter / area if area > 0 else 0.0


class PlacementTracker:
    def __init__(
        self,
        stable_hits: int = 3,
        same_place_iou: float = 0.5,
        moved_iou: float = 0.3,
        removed_after: float = 4.0,
        presence_grace: float = 3.0,
        person_label: str = "person",
    ):
        self.stable_hits = stable_hits
        self.same_place_iou = same_place_iou
        self.moved_iou = moved_iou
        self.removed_after = removed_after
        self.presence_grace = presence_grace
        self.person_label = person_label
        self.tracks: dict[str, Track] = {}
        self.person_present = False
        self._last_person = -1e9
        self._persons: list[BBox] = []

    def update(self, ts: float, detections: list[Detection]) -> list[TrackerEvent]:
        events: list[TrackerEvent] = []
        persons = [d for d in detections if d.label == self.person_label]
        self._persons = [p.bbox for p in persons]
        if persons:
            self._last_person = ts
            if not self.person_present:
                self.person_present = True
                events.append(TrackerEvent("person_enter", ts=ts, bbox=persons[0].bbox))
        elif self.person_present and ts - self._last_person > self.presence_grace:
            self.person_present = False
            events.append(TrackerEvent("person_exit", ts=ts))

        best: dict[str, Detection] = {}
        for d in detections:
            if d.label != self.person_label and (d.label not in best or d.confidence > best[d.label].confidence):
                best[d.label] = d

        for label, det in best.items():
            track = self.tracks.get(label)
            if track is None:
                track = self.tracks[label] = Track(label, det.bbox, ts)
            elif iou(track.bbox, det.bbox) >= self.same_place_iou:
                track.hits += 1
            else:
                track.hits = 1
            track.bbox, track.last_seen = det.bbox, ts
            if track.hits >= self.stable_hits and (
                track.reported_bbox is None or iou(track.bbox, track.reported_bbox) < self.moved_iou
            ):
                track.reported_bbox = track.bbox
                events.append(TrackerEvent("placed", label, track.bbox, det.confidence, ts))

        for track in self.tracks.values():
            if track.label in best or track.reported_bbox is None:
                continue
            if ts - track.last_seen < self.removed_after:
                continue
            if any(covers(p, track.reported_bbox) > 0.5 for p in self._persons):
                continue  # probably just occluded by a hand or arm
            events.append(TrackerEvent("removed", track.label, track.reported_bbox, None, ts))
            track.reported_bbox, track.hits = None, 0
        return events
