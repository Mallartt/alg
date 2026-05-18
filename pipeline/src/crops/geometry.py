"""Perspective deskew + safe rotation for skewed price-tag crops."""

from __future__ import annotations

from typing import Optional

import cv2
import numpy as np


def rotate_image(image: np.ndarray, angle_deg: int) -> np.ndarray:
    angle_deg %= 360
    if angle_deg == 0:
        return image
    if angle_deg == 90:
        return cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)
    if angle_deg == 180:
        return cv2.rotate(image, cv2.ROTATE_180)
    if angle_deg == 270:
        return cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
    (h, w) = image.shape[:2]
    matrix = cv2.getRotationMatrix2D((w / 2, h / 2), angle_deg, 1.0)
    return cv2.warpAffine(image, matrix, (w, h))


def deskew_quad(
    image: np.ndarray,
    *,
    canny_lo: int = 60,
    canny_hi: int = 180,
    min_area_ratio: float = 0.25,
) -> np.ndarray:
    """
    Try to find the largest light-coloured quadrilateral (the price tag itself)
    and warp it into a rectangle. If detection fails, return the original.
    """
    if image is None or image.size == 0:
        return image

    h, w = image.shape[:2]
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, canny_lo, canny_hi)
    edges = cv2.dilate(edges, np.ones((3, 3), np.uint8), iterations=1)

    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    quad = _largest_quadrilateral(contours, min_area=min_area_ratio * h * w)
    if quad is None:
        return image

    return _warp_to_rect(image, quad)


# ----------------------------------------------------------------------
def _largest_quadrilateral(contours, *, min_area: float) -> Optional[np.ndarray]:
    best: Optional[np.ndarray] = None
    best_area = 0.0

    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < min_area:
            continue
        peri = cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)
        if len(approx) == 4 and area > best_area:
            best = approx.reshape(4, 2).astype(np.float32)
            best_area = area
    return best


def _warp_to_rect(image: np.ndarray, quad: np.ndarray) -> np.ndarray:
    ordered = _order_points(quad)
    (tl, tr, br, bl) = ordered

    width = int(max(np.linalg.norm(br - bl), np.linalg.norm(tr - tl)))
    height = int(max(np.linalg.norm(tr - br), np.linalg.norm(tl - bl)))

    if width < 10 or height < 10:
        return image

    dst = np.array(
        [[0, 0], [width - 1, 0], [width - 1, height - 1], [0, height - 1]],
        dtype=np.float32,
    )
    M = cv2.getPerspectiveTransform(ordered, dst)
    return cv2.warpPerspective(image, M, (width, height))


def _order_points(pts: np.ndarray) -> np.ndarray:
    """Top-left, top-right, bottom-right, bottom-left."""
    rect = np.zeros((4, 2), dtype=np.float32)
    s = pts.sum(axis=1)
    diff = np.diff(pts, axis=1).flatten()
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect
