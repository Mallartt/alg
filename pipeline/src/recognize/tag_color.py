"""Classify price-tag colour family (white / yellow / red) via HSV histograms."""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np


@dataclass(frozen=True)
class HsvBand:
    name: str
    lower: tuple[int, int, int]
    upper: tuple[int, int, int]


_BANDS = [
    HsvBand("yellow", (20, 70, 70), (35, 255, 255)),
    HsvBand("red_lo", (0, 70, 70), (15, 255, 255)),
    HsvBand("red_hi", (170, 70, 70), (180, 255, 255)),
    HsvBand("white", (0, 0, 180), (180, 40, 255)),
]


def classify_tag_color(image: np.ndarray, threshold: float = 0.2) -> str:
    """
    Returns one of: 'red', 'yellow', 'white', 'other'.
    Red comes from two HSV ranges merged.
    """
    if image is None or image.size == 0:
        return "other"

    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    total = float(hsv.shape[0] * hsv.shape[1])

    fractions: dict[str, float] = {}
    masks = {band.name: cv2.inRange(hsv, np.array(band.lower), np.array(band.upper)) for band in _BANDS}

    fractions["yellow"] = cv2.countNonZero(masks["yellow"]) / total
    fractions["white"] = cv2.countNonZero(masks["white"]) / total
    red_mask = cv2.bitwise_or(masks["red_lo"], masks["red_hi"])
    fractions["red"] = cv2.countNonZero(red_mask) / total

    winners = [(name, frac) for name, frac in fractions.items() if frac >= threshold]
    if not winners:
        return "other"

    winners.sort(key=lambda x: -x[1])
    return winners[0][0]
