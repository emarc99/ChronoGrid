"""Compare YOLO-World model sizes and prompt wordings on one still image (see friction log #12).

    python scripts/bench_detector.py                     # snapshot from webcam 0
    python scripts/bench_detector.py --image desk.jpg --imgsz 640 960
    python scripts/bench_detector.py --vocab "person,smartphone,red pliers,screwdriver,hammer"

Prints every detection above --conf with its score and normalized centre, so you can check
which label landed on which object. The image is only read, never saved.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from edge.detector import parse_vocab  # noqa: E402

PLAIN = "person,phone,pliers,screwdriver,hammer,scissors,mug,keys"
WORDY = "person,smartphone,red pliers,screwdriver,hammer with wooden handle,scissors,mug,keys"


def snapshot(index: int) -> cv2.typing.MatLike:
    cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
    for _ in range(30):  # let exposure settle
        cap.read()
    ok, frame = cap.read()
    cap.release()
    if not ok:
        raise SystemExit("webcam returned no frame")
    return frame


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--image", help="still image to test (default: webcam snapshot)")
    p.add_argument("--camera", type=int, default=0)
    p.add_argument("--models", nargs="+", default=["s", "m", "l"], help="YOLO-World v2 sizes in data/models")
    p.add_argument("--vocab", nargs="+", default=[PLAIN, WORDY], help="one comma-separated list per run")
    p.add_argument("--imgsz", nargs="+", type=int, default=[640])
    p.add_argument("--conf", type=float, default=0.08)
    args = p.parse_args()

    from ultralytics import YOLOWorld

    frame = cv2.imread(args.image) if args.image else snapshot(args.camera)
    if frame is None:
        raise SystemExit(f"cannot read {args.image}")
    h, w = frame.shape[:2]
    print(f"image {w}x{h}")
    for size in args.models:
        model = YOLOWorld(f"data/models/yolov8{size}-worldv2.pt")
        for vocab in args.vocab:
            prompts, labels = parse_vocab([v for v in vocab.split(",") if v.strip()])
            model.set_classes(prompts)
            for imgsz in args.imgsz:
                model.predict(frame, imgsz=imgsz, conf=args.conf, verbose=False)  # warm-up
                t0 = time.perf_counter()
                r = model.predict(frame, imgsz=imgsz, conf=args.conf, agnostic_nms=True, verbose=False)[0]
                ms = (time.perf_counter() - t0) * 1000
                found = sorted(zip(r.boxes.conf.tolist(), r.boxes.cls.tolist(), r.boxes.xyxy.tolist()), reverse=True)
                rows = [f"{prompts[int(k)]} {s:.2f} @({(x1 + x2) / 2 / w:.2f},{(y1 + y2) / 2 / h:.2f})"
                        for s, k, (x1, y1, x2, y2) in found]
                print(f"\n{size} imgsz={imgsz} {ms:.0f} ms  vocab={vocab}")
                print("  " + ("\n  ".join(rows) or "nothing"))


if __name__ == "__main__":
    main()
