"""Open-vocabulary detection with YOLO-World, running on-device on a plain laptop CPU.

Each vocab entry is a prompt, optionally followed by the label to record: "red pliers=pliers"
asks the model about red pliers but writes "pliers" to the ledger. Wordier prompts often score
far better than the bare noun (on our desk "pliers" lost to "scissors", "red pliers" won at 0.45).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from .tracker import Detection

DEFAULT_VOCAB = [
    "person",
    "multimeter",
    "safety goggles",
    "pliers",
    "red pliers=pliers",
    "screwdriver",
    "keys",
    "mug",
    "tape measure",
    "soldering iron",
    "scissors",
    "wallet",
    "smartphone=phone",
]

# Thin tools score low even when found; the tracker's "stable for 3 looks" rule filters the noise.
DEFAULT_MIN_CONF = {"screwdriver": 0.1}

DEFAULT_MODEL = "data/models/yolov8m-worldv2.pt"


def parse_vocab(entries: list[str]) -> tuple[list[str], list[str]]:
    prompts, labels = [], []
    for entry in entries:
        prompt, _, label = entry.partition("=")
        prompts.append(prompt.strip())
        labels.append((label or prompt).strip())
    return prompts, labels


class Detector:
    def __init__(self, vocab: list[str] | None = None, model_path: str | Path = DEFAULT_MODEL,
                 conf: float = 0.2, imgsz: int = 640, min_conf: dict[str, float] | None = None):
        from ultralytics import YOLOWorld

        self.prompts, self.labels = parse_vocab(vocab or DEFAULT_VOCAB)
        self.model = YOLOWorld(str(model_path))
        self.model.set_classes(self.prompts)
        self.conf = conf
        self.min_conf = DEFAULT_MIN_CONF if min_conf is None else min_conf
        self.imgsz = imgsz

    def floor(self, label: str) -> float:
        return self.min_conf.get(label, self.conf)

    def detect(self, frame: np.ndarray) -> list[Detection]:
        h, w = frame.shape[:2]
        lowest = min([self.conf, *self.min_conf.values()])
        # agnostic NMS: one object gets one label, so "scissors" can't shadow "pliers" on the same box
        result = self.model.predict(frame, imgsz=self.imgsz, conf=lowest, agnostic_nms=True, verbose=False)[0]
        out = []
        for box, cls, score in zip(result.boxes.xyxy.tolist(), result.boxes.cls.tolist(), result.boxes.conf.tolist()):
            label = self.labels[int(cls)]
            if score < self.floor(label):
                continue
            x1, y1, x2, y2 = box
            out.append(Detection(label, float(score), (x1 / w, y1 / h, x2 / w, y2 / h)))
        return out
