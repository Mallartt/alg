"""Sample 1..N frames per second from a video file."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterator

import cv2
import numpy as np

log = logging.getLogger(__name__)


class FrameSampler:
    """
    Iterates over a video and yields frames at a target rate (default 1 fps).
    Heavy 4K frames are skipped via cap.grab() — actual decode happens only
    for sampled positions.
    """

    def __init__(
        self,
        video_path: str | Path,
        frames_per_second: float = 1.0,
        start_offset_sec: float = 0.0,
    ):
        self.video_path = str(video_path)
        self.target_fps = max(0.1, float(frames_per_second))
        self.start_offset_sec = max(0.0, start_offset_sec)

        self._cap = cv2.VideoCapture(self.video_path)
        if not self._cap.isOpened():
            raise RuntimeError(f"Cannot open video: {video_path}")

        self.src_fps = self._cap.get(cv2.CAP_PROP_FPS) or 30.0
        self.total_frames = int(self._cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.frame_w = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.frame_h = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self._stride = max(1, int(round(self.src_fps / self.target_fps)))

        log.info(
            "Video %s | %sx%s | %.2f src fps | %s total | sampling 1/%s",
            self.video_path,
            self.frame_w,
            self.frame_h,
            self.src_fps,
            self.total_frames,
            self._stride,
        )

    # ------------------------------------------------------------------
    def __iter__(self) -> Iterator[tuple[int, float, np.ndarray]]:
        return self.iter_samples()

    def iter_samples(self) -> Iterator[tuple[int, float, np.ndarray]]:
        """Yield (frame_index, timestamp_ms, frame_bgr) tuples."""
        try:
            self._seek_to_offset()
            idx = int(self._cap.get(cv2.CAP_PROP_POS_FRAMES))

            while True:
                if (idx % self._stride) == 0:
                    ok, frame = self._cap.read()
                    if not ok or frame is None:
                        break
                    timestamp_ms = (idx / self.src_fps) * 1000.0
                    yield idx, timestamp_ms, frame
                else:
                    if not self._cap.grab():
                        break
                idx += 1
        finally:
            self.release()

    # ------------------------------------------------------------------
    def _seek_to_offset(self) -> None:
        if self.start_offset_sec <= 0:
            return
        target = int(self.start_offset_sec * self.src_fps)
        self._cap.set(cv2.CAP_PROP_POS_FRAMES, max(0, target))

    def release(self) -> None:
        if self._cap is not None and self._cap.isOpened():
            self._cap.release()
            self._cap = None
