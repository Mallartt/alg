"""Load and expose the project-wide TOML configuration."""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

if sys.version_info >= (3, 11):
    import tomllib as _toml
else:  # pragma: no cover
    import tomli as _toml  # type: ignore


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = ROOT / "config.toml"


# ----------------------------------------------------------------------
@dataclass
class PathsCfg:
    weights: str
    prompt: str
    product_catalog: Optional[str] = None


@dataclass
class StreamCfg:
    frames_per_second: float = 1.5
    rotation_deg: int = 90
    margin_px: int = 12
    start_offset_sec: float = 0.0


@dataclass
class DetectorCfg:
    confidence: float = 0.5
    iou: float = 0.45
    imgsz: int = 640
    device: Optional[str] = None
    tracker_yaml: str = "bytetrack.yaml"


@dataclass
class RecognizeCfg:
    blur_threshold: float = 8.0
    color_threshold: float = 0.2
    upscale_factor: float = 2.0
    deskew: bool = True
    enhance: bool = True
    # 0 == load every row from db_hack.csv
    catalog_max_rows: int = 0


@dataclass
class VlmCfg:
    base_url: str = "http://localhost:8000/v1"
    model_alias: str = "local-model"
    temperature: float = 0.05
    timeout_sec: float = 90.0


@dataclass
class TrackingCfg:
    min_attempts: int = 1
    max_attempts: int = 3
    stale_after_frames: int = 30
    center_improve_eps: float = 0.04
    quorum: int = 2


@dataclass
class LensCfg:
    enabled: bool = False
    image_size: list = field(default_factory=lambda: [3840, 2160])
    diagonal_mm: float = 16.0 / 2.8
    focal_length_mm: float = 2.8
    distortion: list = field(default_factory=lambda: [-0.276, 0.06, 0.0084, -0.0016, -0.0044])


@dataclass
class RuntimeCfg:
    uploads_dir: str = "runtime/uploads"
    outputs_dir: str = "runtime/outputs"
    tmp_dir: str = "runtime/tmp"


@dataclass
class AppConfig:
    paths: PathsCfg
    stream: StreamCfg = field(default_factory=StreamCfg)
    detector: DetectorCfg = field(default_factory=DetectorCfg)
    recognize: RecognizeCfg = field(default_factory=RecognizeCfg)
    vlm: VlmCfg = field(default_factory=VlmCfg)
    tracking: TrackingCfg = field(default_factory=TrackingCfg)
    lens: LensCfg = field(default_factory=LensCfg)
    runtime: RuntimeCfg = field(default_factory=RuntimeCfg)


# ----------------------------------------------------------------------
def load(path: str | Path | None = None) -> AppConfig:
    cfg_path = Path(path or DEFAULT_CONFIG_PATH)
    if not cfg_path.exists():
        raise FileNotFoundError(f"config not found: {cfg_path}")
    with cfg_path.open("rb") as fh:
        data = _toml.load(fh)

    def _section(name: str) -> dict:
        return dict(data.get(name) or {})

    return AppConfig(
        paths=PathsCfg(**_section("paths")),
        stream=StreamCfg(**_section("stream")),
        detector=DetectorCfg(**_section("detector")),
        recognize=RecognizeCfg(**_section("recognize")),
        vlm=VlmCfg(**_section("vlm")),
        tracking=TrackingCfg(**_section("tracking")),
        lens=LensCfg(**_section("lens")),
        runtime=RuntimeCfg(**_section("runtime")),
    )


def absolute_path(rel_or_abs: str | Path) -> Path:
    """Resolve a path relative to the pipeline root."""
    p = Path(rel_or_abs)
    return p if p.is_absolute() else (ROOT / p).resolve()
