"""Open-vocabulary detection with YOLO-World, running on-device (CPU is enough at ~6 fps)."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from .tracker import Detection

DEFAULT_VOCAB = [
    "person",
    "multimeter",
    "safety goggles",
    "pliers",
    "screwdriver",
    "keys",
    "mug",
    "tape measure",
    "soldering iron",
    "scissors",
    "wallet",
    "phone",
]


class Detector:
    def __init__(self, vocab: list[str] | None = None, model_path: str | Path = "data/models/yolov8s-worldv2.pt",
                 conf: float = 0.2, imgsz: int = 640):
        from ultralytics import YOLOWorld

        self.vocab = vocab or DEFAULT_VOCAB
        self.model = YOLOWorld(str(model_path))
        self.model.set_classes(self.vocab)
        self.conf = conf
        self.imgsz = imgsz

    def detect(self, frame: np.ndarray) -> list[Detection]:
        h, w = frame.shape[:2]
        result = self.model.predict(frame, imgsz=self.imgsz, conf=self.conf, verbose=False)[0]
        out = []
        for box, cls, score in zip(result.boxes.xyxy.tolist(), result.boxes.cls.tolist(), result.boxes.conf.tolist()):
            x1, y1, x2, y2 = box
            out.append(Detection(self.vocab[int(cls)], float(score), (x1 / w, y1 / h, x2 / w, y2 / h)))
        return out
