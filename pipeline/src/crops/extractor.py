"""Cut sub-images out of a frame and score how centered the detection was."""

from __future__ import annotations

from typing import Optional

import numpy as np


def build_crop(
    frame: np.ndarray,
    bbox_xyxy: np.ndarray,
    margin: int = 12,
) -> Optional[np.ndarray]:
    """Slice the frame using xyxy coordinates with a safety margin."""
    if frame is None or frame.size == 0:
        return None

    h, w = frame.shape[:2]
    x1, y1, x2, y2 = (int(round(v)) for v in bbox_xyxy[:4])

    x1 = max(0, x1 - margin)
    y1 = max(0, y1 - margin)
    x2 = min(w, x2 + margin)
    y2 = min(h, y2 + margin)

    if x2 <= x1 or y2 <= y1:
        return None

    return frame[y1:y2, x1:x2].copy()


def frame_centerness(bbox_xyxy, frame_size: tuple[int, int]) -> float:
    """
    Return a scalar in [0, 1]: how close the bbox center is to the frame
    center (1.0 == perfectly centered).
    Used by the orchestrator to pick the "ценник максимально приблизился к
    центру кадра" moment.
    """
    fw, fh = frame_size
    if fw <= 0 or fh <= 0:
        return 0.0

    x1, y1, x2, y2 = (float(v) for v in bbox_xyxy[:4])
    cx, cy = (x1 + x2) / 2.0, (y1 + y2) / 2.0
    dx = (cx - fw / 2.0) / (fw / 2.0)
    dy = (cy - fh / 2.0) / (fh / 2.0)

    dist = float(np.sqrt(dx * dx + dy * dy))
    # clamp and invert so larger means closer to center
    dist = min(1.0, dist)
    return round(1.0 - dist, 4)
