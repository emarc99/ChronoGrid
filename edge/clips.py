"""Rolling frame buffer and privacy-preserving rewind clips (faces blurred, H.264 for browsers/TVs)."""

from __future__ import annotations

import subprocess
import time
from collections import deque
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np

_FACES = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")


class FrameBuffer:
    def __init__(self, seconds: float = 6.0, fps: int = 12, width: int = 960):
        self.fps = fps
        self.width = width
        self._frames: deque[tuple[float, np.ndarray]] = deque(maxlen=int(seconds * fps))
        self._last = 0.0

    def push(self, ts: float, frame: np.ndarray) -> None:
        if ts - self._last < 1.0 / self.fps:
            return
        self._last = ts
        h, w = frame.shape[:2]
        if w != self.width:
            frame = cv2.resize(frame, (self.width, int(h * self.width / w)))
        self._frames.append((ts, frame))

    def window(self, end: float, seconds: float = 5.0) -> list[tuple[float, np.ndarray]]:
        return [(ts, f) for ts, f in self._frames if end - seconds <= ts <= end]


def blur_faces(frame: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    for x, y, w, h in _FACES.detectMultiScale(gray, scaleFactor=1.15, minNeighbors=5, minSize=(40, 40)):
        pad = int(0.2 * w)
        x0, y0 = max(0, x - pad), max(0, y - pad)
        x1, y1 = min(frame.shape[1], x + w + pad), min(frame.shape[0], y + h + pad)
        frame[y0:y1, x0:x1] = cv2.GaussianBlur(frame[y0:y1, x0:x1], (0, 0), 25)
    return frame


def _stamp(frame: np.ndarray, ts: float) -> np.ndarray:
    text = datetime.fromtimestamp(ts).strftime("%a %H:%M:%S")
    cv2.putText(frame, text, (14, frame.shape[0] - 16), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 4, cv2.LINE_AA)
    cv2.putText(frame, text, (14, frame.shape[0] - 16), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (230, 240, 255), 1, cv2.LINE_AA)
    return frame


def resample(frames: list[tuple[float, np.ndarray]], fps: int) -> list[int]:
    """Indices of the frame showing at each output tick, so the clip lasts as long as the moment it covers.

    The buffer fills at whatever rate the detection loop allows (2-3 fps on a busy CPU), so encoding the
    raw frames at a fixed rate would play the moment back several times too fast.
    """
    t0, t1 = frames[0][0], frames[-1][0]
    ticks = max(1, round((t1 - t0) * fps) + 1)
    out, j = [], 0
    for i in range(ticks):
        t = t0 + i / fps
        while j + 1 < len(frames) and frames[j + 1][0] <= t:
            j += 1
        out.append(j)
    return out


def write_clip(frames: list[tuple[float, np.ndarray]], path: Path, fps: int = 12) -> Path:
    """Encode frames to an H.264 MP4 that plays in browsers, Echo Show and Fire TV."""
    import imageio_ffmpeg

    if not frames:
        raise ValueError("no frames to write")
    h, w = frames[0][1].shape[:2]
    w, h = w - w % 2, h - h % 2
    cmd = [
        imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{w}x{h}", "-r", str(fps), "-i", "-",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "26", "-pix_fmt", "yuv420p",
        "-movflags", "+faststart", str(path),
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    last, data = -1, b""
    for i in resample(frames, fps):
        if i != last:
            ts, frame = frames[i]
            last, data = i, _stamp(blur_faces(frame[:h, :w].copy()), ts).tobytes()
        proc.stdin.write(data)
    proc.stdin.close()
    if proc.wait() != 0:
        raise RuntimeError("ffmpeg failed to encode clip")
    return path


def clip_name(label: str, ts: float | None = None) -> str:
    ts = time.time() if ts is None else ts
    return f"{datetime.fromtimestamp(ts):%Y%m%d-%H%M%S}-{label.replace(' ', '-')}.mp4"
