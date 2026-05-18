"""Lens-distortion correction for the on-robot 4K camera.

Calibration values are supplied by the camera vendor and live in
``config.toml``. This module builds remap tables once and reuses them.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np


@dataclass
class LensCalibration:
    """Intrinsic parameters of the camera (no extrinsics needed for undistort)."""

    width: int
    height: int
    diagonal_mm: float
    focal_length_mm: float
    distortion: tuple[float, float, float, float, float]  # k1, k2, p1, p2, k3


class LensUndistorter:
    """Applies cached undistortion remap tables to frames."""

    def __init__(self, calib: LensCalibration, crop_to_roi: bool = True):
        self.calib = calib
        self.crop_to_roi = crop_to_roi
        self._k = self._compute_intrinsic_matrix()
        self._dist = np.asarray(calib.distortion, dtype=np.float32)
        self._maps, self._roi = self._build_maps()

    # ------------------------------------------------------------------
    def __call__(self, frame: np.ndarray) -> np.ndarray:
        return self.apply(frame)

    def apply(self, frame: np.ndarray) -> np.ndarray:
        out = cv2.remap(frame, self._maps[0], self._maps[1], cv2.INTER_LINEAR)
        if not self.crop_to_roi:
            return out
        x, y, w, h = self._roi
        if w == 0 or h == 0:
            return out
        return out[y : y + h, x : x + w]

    # ------------------------------------------------------------------
    def _compute_intrinsic_matrix(self) -> np.ndarray:
        w, h = self.calib.width, self.calib.height
        aspect = w / h
        height_mm = self.calib.diagonal_mm / math.sqrt(aspect**2 + 1)
        width_mm = aspect * height_mm

        fx = (self.calib.focal_length_mm * w) / width_mm
        fy = (self.calib.focal_length_mm * h) / height_mm

        return np.array(
            [[fx, 0, w / 2], [0, fy, h / 2], [0, 0, 1]],
            dtype=np.float32,
        )

    def _build_maps(self):
        w, h = self.calib.width, self.calib.height
        new_k, roi = cv2.getOptimalNewCameraMatrix(
            self._k, self._dist, (w, h), 0, (w, h)
        )
        map1, map2 = cv2.initUndistortRectifyMap(
            self._k, self._dist, None, new_k, (w, h), cv2.CV_32FC1
        )
        return (map1, map2), roi


# --- factory helpers ---------------------------------------------------
def lens_from_dict(spec: dict) -> Optional[LensCalibration]:
    """Build a LensCalibration from a config-section dict; returns None if disabled."""
    if not spec or not spec.get("enabled", False):
        return None

    size = spec.get("image_size", [3840, 2160])
    return LensCalibration(
        width=int(size[0]),
        height=int(size[1]),
        diagonal_mm=float(spec.get("diagonal_mm", 16.0 / 2.8)),
        focal_length_mm=float(spec.get("focal_length_mm", 2.8)),
        distortion=tuple(spec.get("distortion", [-0.276, 0.06, 0.0084, -0.0016, -0.0044])),
    )
