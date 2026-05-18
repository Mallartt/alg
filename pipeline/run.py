"""Command-line entry point for end-to-end video processing.

Usage:
    python run.py --video path/to/video.mp4 [--out result.csv]
                  [--fps 1.5] [--rot 90] [--config config.toml]
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from src import config_loader
from src.pipeline_runner import process_video


def _build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Run the price-tag recognition pipeline on a video.")
    p.add_argument("--video", required=True, type=str, help="Path to the input mp4")
    p.add_argument("--out", type=str, default=None, help="Where to write the resulting CSV")
    p.add_argument("--fps", type=float, default=None, help="Frames to sample per second (e.g. 1.5)")
    p.add_argument("--rot", type=int, default=None, help="Rotate each crop CCW by this many degrees")
    p.add_argument("--config", type=str, default=None, help="Path to config.toml")
    p.add_argument("-v", "--verbose", action="store_true")
    return p


def main() -> None:
    args = _build_argparser().parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    cfg = config_loader.load(args.config)

    video = Path(args.video).resolve()
    if not video.exists():
        raise SystemExit(f"video not found: {video}")

    out = Path(args.out) if args.out else Path(cfg.runtime.outputs_dir) / f"{video.stem}.csv"
    out = out if out.is_absolute() else (config_loader.ROOT / out).resolve()

    result = process_video(
        video_path=video,
        output_csv=out,
        cfg=cfg,
        source_filename=video.name,
        rotation_deg=args.rot,
        frames_per_second=args.fps,
    )
    print(f"\n[OK] wrote {result}")


if __name__ == "__main__":
    main()
