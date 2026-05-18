"""Data containers passed between pipeline stages."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

import numpy as np


@dataclass(slots=True)
class CropEvent:
    """One observation of a price-tag candidate produced by the detector."""

    track_id: int
    image: np.ndarray
    frame_index: int
    timestamp_ms: float
    bbox_xyxy: tuple[float, float, float, float]
    centerness: float          # 0..1, higher = closer to frame center
    frame_size: tuple[int, int]  # (width, height)
    source_filename: str = ""

    @property
    def width(self) -> int:
        return self.image.shape[1] if self.image is not None else 0

    @property
    def height(self) -> int:
        return self.image.shape[0] if self.image is not None else 0


@dataclass(slots=True)
class RecognitionOutcome:
    """Recognition result of a single crop. Mirrors a row of the submission CSV."""

    ok: bool
    reason: str = "ok"
    fields: dict[str, Any] = field(default_factory=dict)
    codes: list[dict[str, str]] = field(default_factory=list)
    color_tag: Optional[str] = None
    sharpness: float = 0.0


@dataclass(slots=True)
class TrackRecord:
    """Per-track accumulator inside the registry."""

    track_id: int
    first_seen_frame: int
    last_seen_frame: int
    best_event: Optional[CropEvent] = None
    attempts: int = 0
    outcomes: list[RecognitionOutcome] = field(default_factory=list)
    finalized: bool = False
    final_payload: Optional[dict[str, Any]] = None
