"""Boost text contrast on price-tag crops before sending them to OCR."""

from __future__ import annotations

import cv2
import numpy as np


def boost_text_contrast(
    image: np.ndarray,
    *,
    clip_limit: float = 2.5,
    tile_grid: int = 8,
    sharpen: bool = True,
) -> np.ndarray:
    """
    Apply CLAHE on the luminance channel, then optionally unsharp-mask the
    result. The output preserves colour for downstream OCR.
    """
    if image is None or image.size == 0:
        return image

    if image.ndim == 2:
        clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(tile_grid, tile_grid))
        out = clahe.apply(image)
    else:
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(tile_grid, tile_grid))
        l = clahe.apply(l)
        out = cv2.cvtColor(cv2.merge([l, a, b]), cv2.COLOR_LAB2BGR)

    if sharpen:
        blur = cv2.GaussianBlur(out, (0, 0), sigmaX=1.4)
        out = cv2.addWeighted(out, 1.5, blur, -0.5, 0)
        out = np.clip(out, 0, 255).astype(np.uint8)

    return out


def upscale_bicubic(image: np.ndarray, factor: float = 2.0) -> np.ndarray:
    if factor == 1.0:
        return image
    return cv2.resize(image, None, fx=factor, fy=factor, interpolation=cv2.INTER_CUBIC)
