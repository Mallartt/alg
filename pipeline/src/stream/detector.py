"""YOLO + ByteTrack adapter that emits CropEvent objects."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Iterable, Iterator, Optional

import cv2
import numpy as np

from ..core.schemas import CropEvent
from ..crops.extractor import build_crop, frame_centerness
from .lens_correction import LensUndistorter
from .video_sampler import FrameSampler

# Turn off ultralytics phone-home behaviours.
os.environ.setdefault("YOLO_AUTOINSTALL", "0")
os.environ.setdefault("YOLO_OFFLINE", "1")

log = logging.getLogger(__name__)


class PriceTagDetector:
    """
    Wraps Ultralytics' tracker mode. Each `__iter__` produces CropEvent items
    for the orchestrator. ByteTrack assigns stable IDs across frames.
    """

    def __init__(
        self,
        weights: str | Path,
        sampler: FrameSampler,
        *,
        confidence: float = 0.5,
        iou: float = 0.45,
        imgsz: int = 640,
        device: Optional[str] = None,
        tracker_yaml: str = "bytetrack.yaml",
        margin_px: int = 12,
        rotation_deg: int = 90,
        undistorter: Optional[LensUndistorter] = None,
        source_name: str = "",
    ):
        from ultralytics import YOLO  # imported lazily so unit tests don't need it

        self.weights_path = str(weights)
        self.sampler = sampler
        self.confidence = float(confidence)
        self.iou = float(iou)
        self.imgsz = int(imgsz)
        self.tracker_yaml = tracker_yaml
        self.margin_px = max(0, int(margin_px))
        self.rotation_deg = int(rotation_deg) % 360
        self.undistorter = undistorter
        self.source_name = source_name

        if device is None:
            try:
                import torch

                device = "cuda" if torch.cuda.is_available() else "cpu"
            except Exception:
                device = "cpu"
        self.device = device

        log.info("Loading detector weights: %s (device=%s)", self.weights_path, self.device)
        self.model = YOLO(self.weights_path)

    # ------------------------------------------------------------------
    def __iter__(self) -> Iterator[CropEvent]:
        return self.iter_events()

    def iter_events(self) -> Iterable[CropEvent]:
        for frame_idx, ts_ms, raw_frame in self.sampler:
            frame = raw_frame if self.undistorter is None else self.undistorter(raw_frame)
            h, w = frame.shape[:2]

            try:
                results = self.model.track(
                    frame,
                    conf=self.confidence,
                    iou=self.iou,
                    imgsz=self.imgsz,
                    device=self.device,
                    persist=True,
                    tracker=self.tracker_yaml,
                    verbose=False,
                )
            except Exception as err:  # noqa: BLE001
                log.error("YOLO.track failed on frame %s: %s", frame_idx, err)
                continue

            if not results:
                continue
            res = results[0]
            if res.boxes is None or len(res.boxes) == 0:
                continue

            ids_tensor = getattr(res.boxes, "id", None)
            xyxy = res.boxes.xyxy.cpu().numpy()
            ids: list[int] = (
                ids_tensor.cpu().int().numpy().tolist()
                if ids_tensor is not None
                else [-1] * len(xyxy)
            )

            for box, t_id in zip(xyxy, ids):
                if t_id is None or int(t_id) < 0:
                    continue

                crop = build_crop(frame, box, margin=self.margin_px)
                if crop is None or crop.size == 0:
                    continue

                if self.rotation_deg:
                    crop = _rotate_axis_aligned(crop, self.rotation_deg)

                yield CropEvent(
                    track_id=int(t_id),
                    image=crop,
                    frame_index=int(frame_idx),
                    timestamp_ms=float(ts_ms),
                    bbox_xyxy=(float(box[0]), float(box[1]), float(box[2]), float(box[3])),
                    centerness=frame_centerness(box, (w, h)),
                    frame_size=(w, h),
                    source_filename=self.source_name,
                )


def _rotate_axis_aligned(image: np.ndarray, angle: int) -> np.ndarray:
    angle %= 360
    if angle == 0:
        return image
    if angle == 90:
        return cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)
    if angle == 180:
        return cv2.rotate(image, cv2.ROTATE_180)
    if angle == 270:
        return cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)

    # arbitrary angle — keep full content
    (h, w) = image.shape[:2]
    matrix = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
    cos, sin = abs(matrix[0, 0]), abs(matrix[0, 1])
    nw, nh = int(h * sin + w * cos), int(h * cos + w * sin)
    matrix[0, 2] += nw / 2 - w / 2
    matrix[1, 2] += nh / 2 - h / 2
    return cv2.warpAffine(image, matrix, (nw, nh))
