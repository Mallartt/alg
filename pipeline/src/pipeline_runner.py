"""High-level helpers that glue config + modules together.

These wrappers are shared by the CLI (`run.py`, `run_image.py`) and the API.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from .catalog import ProductCatalog
from .config_loader import AppConfig, absolute_path
from .core.orchestrator import RecognitionFlow, recognize_single_crop
from .core.consensus import MajorityVoter
from .core.track_buffer import TrackRegistry
from .export.csv_writer import write_submission
from .recognize import CropRecognizer, LocalVlmClient, CodeReader
from .stream.detector import PriceTagDetector
from .stream.lens_correction import LensUndistorter, lens_from_dict
from .stream.video_sampler import FrameSampler

log = logging.getLogger("pipeline_runner")


# ----------------------------------------------------------------------
def _build_recognizer(cfg: AppConfig) -> CropRecognizer:
    catalog = None
    if cfg.paths.product_catalog:
        catalog = ProductCatalog.from_csv(
            absolute_path(cfg.paths.product_catalog),
            max_rows=cfg.recognize.catalog_max_rows,
        )

    vlm = LocalVlmClient(
        base_url=cfg.vlm.base_url,
        model_alias=cfg.vlm.model_alias,
        temperature=cfg.vlm.temperature,
        timeout_sec=cfg.vlm.timeout_sec,
    )

    return CropRecognizer(
        prompt_path=absolute_path(cfg.paths.prompt),
        vlm_client=vlm,
        code_reader=CodeReader(),
        catalog=catalog,
        blur_threshold=cfg.recognize.blur_threshold,
        color_threshold=cfg.recognize.color_threshold,
        upscale_factor=cfg.recognize.upscale_factor,
        deskew=cfg.recognize.deskew,
        enhance=cfg.recognize.enhance,
    )


def _build_lens(cfg: AppConfig) -> Optional[LensUndistorter]:
    calib = lens_from_dict(
        {
            "enabled": cfg.lens.enabled,
            "image_size": cfg.lens.image_size,
            "diagonal_mm": cfg.lens.diagonal_mm,
            "focal_length_mm": cfg.lens.focal_length_mm,
            "distortion": cfg.lens.distortion,
        }
    )
    if calib is None:
        return None
    return LensUndistorter(calib, crop_to_roi=True)


# ----------------------------------------------------------------------
def process_video(
    *,
    video_path: str | Path,
    output_csv: str | Path,
    cfg: AppConfig,
    source_filename: str = "",
    rotation_deg: Optional[int] = None,
    frames_per_second: Optional[float] = None,
) -> Path:
    sampler = FrameSampler(
        video_path,
        frames_per_second=frames_per_second or cfg.stream.frames_per_second,
        start_offset_sec=cfg.stream.start_offset_sec,
    )

    undistort = _build_lens(cfg)

    detector = PriceTagDetector(
        weights=absolute_path(cfg.paths.weights),
        sampler=sampler,
        confidence=cfg.detector.confidence,
        iou=cfg.detector.iou,
        imgsz=cfg.detector.imgsz,
        device=cfg.detector.device,
        tracker_yaml=cfg.detector.tracker_yaml,
        margin_px=cfg.stream.margin_px,
        rotation_deg=rotation_deg if rotation_deg is not None else cfg.stream.rotation_deg,
        undistorter=undistort,
        source_name=source_filename or Path(video_path).name,
    )

    flow = RecognitionFlow(
        event_stream=detector,
        recognizer=_build_recognizer(cfg),
        registry=TrackRegistry(
            min_attempts=cfg.tracking.min_attempts,
            max_attempts=cfg.tracking.max_attempts,
            stale_after_frames=cfg.tracking.stale_after_frames,
            center_improve_eps=cfg.tracking.center_improve_eps,
        ),
        voter=MajorityVoter(quorum=cfg.tracking.quorum),
        source_filename=source_filename or Path(video_path).name,
    )

    rows = flow.run()
    return write_submission(rows, output_csv, source_filename=source_filename or Path(video_path).name)


# ----------------------------------------------------------------------
def process_single_image(
    *,
    image_path: str | Path,
    output_csv: str | Path,
    cfg: AppConfig,
    source_filename: str = "",
) -> Path:
    recognizer = _build_recognizer(cfg)
    row = recognize_single_crop(image_path, recognizer, source_filename=source_filename)
    return write_submission(
        [row],
        output_csv,
        source_filename=source_filename or Path(image_path).name,
    )
