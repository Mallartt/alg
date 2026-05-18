"""Reject motion-blurred crops before they reach the LLM."""

from __future__ import annotations

import cv2
import numpy as np


def sharpness_score(image: np.ndarray) -> float:
    """
    Brightness-normalised variance of Laplacian. Higher == sharper.
    The normalisation step makes the metric robust to dim shots.
    """
    if image is None or image.size == 0:
        return 0.0
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
    stretched = cv2.normalize(gray, None, 0, 255, cv2.NORM_MINMAX)
    return float(cv2.Laplacian(stretched, cv2.CV_64F).var())


def is_sharp_enough(image: np.ndarray, threshold: float = 8.0) -> tuple[bool, float]:
    score = sharpness_score(image)
    return score >= threshold, score
