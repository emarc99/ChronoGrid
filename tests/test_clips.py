import numpy as np
import pytest

cv2 = pytest.importorskip("cv2")
pytest.importorskip("imageio_ffmpeg")

from edge.clips import resample, write_clip  # noqa: E402


def slow_buffer(seconds: float = 5.0, rate: float = 2.0) -> list[tuple[float, np.ndarray]]:
    frame = np.zeros((96, 128, 3), np.uint8)
    return [(1000.0 + i / rate, frame) for i in range(int(seconds * rate) + 1)]


def test_resample_spans_real_time():
    frames = slow_buffer()
    ticks = resample(frames, fps=12)
    assert len(ticks) == 61  # 5 s at 12 fps
    assert ticks[0] == 0 and ticks[-1] == len(frames) - 1
    assert ticks == sorted(ticks)


def test_clip_lasts_as_long_as_the_moment(tmp_path):
    path = write_clip(slow_buffer(), tmp_path / "clip.mp4", fps=12)
    cap = cv2.VideoCapture(str(path))
    duration = cap.get(cv2.CAP_PROP_FRAME_COUNT) / cap.get(cv2.CAP_PROP_FPS)
    cap.release()
    assert duration == pytest.approx(5.0, abs=0.2)
