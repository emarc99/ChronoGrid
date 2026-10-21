"""ChronoGrid edge agent: camera -> YOLO-World -> placement tracker -> ledger events + rewind clips.

    python -m edge.run                       # default webcam
    python -m edge.run --source demo.mp4     # replay a recording
    keys in preview: [h] toggle the heat-source smart plug, [q] quit
"""

from __future__ import annotations

import argparse
import logging
import threading
import time
from pathlib import Path

import cv2
import httpx
import numpy as np

from .clips import FrameBuffer, clip_name, write_clip
from .detector import DEFAULT_VOCAB, Detector
from .tracker import PlacementTracker, TrackerEvent

log = logging.getLogger("chronogrid.edge")

ACCENT = (176, 224, 62)
WARN = (71, 181, 255)


class EdgeAgent:
    def __init__(self, server: str, presence_zone: str, appliance: str, appliance_zone: str, clip_dir: Path):
        self.http = httpx.Client(base_url=server, timeout=15)
        self.presence_zone = presence_zone
        self.appliance = appliance
        self.appliance_zone = appliance_zone
        self.appliance_on = False
        self.clip_dir = clip_dir
        self.buffer = FrameBuffer()
        self.zones = self._zones()

    def _zones(self) -> list[dict]:
        try:
            return self.http.get("/api/state").json()["zones"]
        except Exception:
            log.warning("server not reachable; zones overlay disabled")
            return []

    def post_event(self, kind: str, **payload) -> None:
        try:
            self.http.post("/api/events", json={"kind": kind, **payload}).raise_for_status()
        except Exception as exc:
            log.warning("failed to post %s: %s", kind, exc)

    def handle(self, ev: TrackerEvent) -> None:
        if ev.kind in ("person_enter", "person_exit"):
            self.post_event(ev.kind, zone_id=self.presence_zone, ts=ev.ts)
        elif ev.kind == "removed":
            self.post_event("removed", label=ev.label, bbox=list(ev.bbox) if ev.bbox else None, ts=ev.ts)
        elif ev.kind == "placed":
            threading.Timer(1.2, self._clip_and_post, args=(ev,)).start()
        log.info("%s %s", ev.kind, ev.label or "")

    def _clip_and_post(self, ev: TrackerEvent) -> None:
        clip = None
        frames = self.buffer.window(end=ev.ts + 1.2, seconds=5.0)
        if len(frames) > 6:
            path = self.clip_dir / clip_name(ev.label, ev.ts)
            try:
                write_clip(frames, path, fps=self.buffer.fps)
                with path.open("rb") as fh:
                    resp = self.http.post("/api/clips", files={"file": (path.name, fh, "video/mp4")})
                clip = resp.json()["clip"]
            except Exception as exc:
                log.warning("clip failed for %s: %s", ev.label, exc)
        self.post_event("placed", label=ev.label, bbox=list(ev.bbox), confidence=ev.confidence, clip=clip, ts=ev.ts)

    def toggle_appliance(self) -> None:
        self.appliance_on = not self.appliance_on
        try:
            self.http.post("/api/appliance", json={"label": self.appliance, "on": self.appliance_on,
                                                  "zone_id": self.appliance_zone})
        except Exception as exc:
            log.warning("appliance toggle failed: %s", exc)


def draw(frame: np.ndarray, agent: EdgeAgent, detections, tracker: PlacementTracker, fps: float) -> np.ndarray:
    h, w = frame.shape[:2]
    overlay = frame.copy()
    for z in agent.zones:
        pts = np.array([[int(x * w), int(y * h)] for x, y in z["polygon"]], np.int32)
        if len(pts) >= 3:
            cv2.polylines(overlay, [pts], True, (120, 120, 120), 1, cv2.LINE_AA)
            cv2.putText(overlay, z["name"], (pts[0][0] + 8, pts[0][1] + 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                        (200, 200, 200), 1, cv2.LINE_AA)
    for d in detections:
        x1, y1, x2, y2 = int(d.bbox[0] * w), int(d.bbox[1] * h), int(d.bbox[2] * w), int(d.bbox[3] * h)
        color = (160, 160, 160) if d.label == "person" else ACCENT
        cv2.rectangle(overlay, (x1, y1), (x2, y2), color, 2)
        cv2.putText(overlay, f"{d.label} {d.confidence:.2f}", (x1, max(18, y1 - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.55,
                    color, 2, cv2.LINE_AA)
    status = (f"ChronoGrid edge | on-device | {fps:.1f} det/s | person: {'yes' if tracker.person_present else 'no'}"
              f" | {agent.appliance}: {'ON' if agent.appliance_on else 'off'}")
    cv2.rectangle(overlay, (0, 0), (w, 34), (15, 15, 20), -1)
    cv2.putText(overlay, status, (12, 23), cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                WARN if agent.appliance_on else (230, 230, 230), 1, cv2.LINE_AA)
    return overlay


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--source", default="0", help="webcam index or video file")
    p.add_argument("--server", default="http://127.0.0.1:8787")
    p.add_argument("--vocab", default=",".join(DEFAULT_VOCAB), help="comma-separated labels to detect")
    p.add_argument("--conf", type=float, default=0.2)
    p.add_argument("--detect-every", type=float, default=0.35, help="seconds between detections")
    p.add_argument("--presence-zone", default="workbench")
    p.add_argument("--appliance", default="soldering iron")
    p.add_argument("--appliance-zone", default="workbench")
    p.add_argument("--no-preview", action="store_true")
    p.add_argument("--loop", action="store_true", help="loop a video file source")
    args = p.parse_args()

    source = int(args.source) if args.source.isdigit() else args.source
    cap = cv2.VideoCapture(source, cv2.CAP_DSHOW) if isinstance(source, int) else cv2.VideoCapture(source)
    if isinstance(source, int):
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    if not cap.isOpened():
        raise SystemExit(f"cannot open source {args.source}")
    file_fps = cap.get(cv2.CAP_PROP_FPS) if not isinstance(source, int) else 0

    detector = Detector([v.strip() for v in args.vocab.split(",") if v.strip()], conf=args.conf)
    tracker = PlacementTracker()
    agent = EdgeAgent(args.server, args.presence_zone, args.appliance, args.appliance_zone, Path("data/clips/edge"))
    detections, last_detect, det_rate = [], 0.0, 0.0

    while True:
        ok, frame = cap.read()
        if not ok:
            if args.loop and not isinstance(source, int):
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue
            break
        now = time.time()
        agent.buffer.push(now, frame)
        if now - last_detect >= args.detect_every:
            t0 = time.perf_counter()
            detections = detector.detect(frame)
            det_rate = 0.8 * det_rate + 0.2 * (1.0 / max(1e-3, time.perf_counter() - t0))
            last_detect = now
            for ev in tracker.update(now, detections):
                agent.handle(ev)
        if not args.no_preview:
            cv2.imshow("ChronoGrid Edge", draw(frame, agent, detections, tracker, det_rate))
            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break
            if key == ord("h"):
                agent.toggle_appliance()
        if file_fps:
            time.sleep(max(0.0, 1.0 / file_fps - (time.time() - now)))

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
