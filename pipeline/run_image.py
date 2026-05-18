"""Run only the recognition stage on a single already-cropped image.

Use this when you already have a price-tag crop and want to skip YOLO/tracking.

Example:
    python run_image.py --image crops/sample.jpg --out crops/sample.csv
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from src import config_loader
from src.pipeline_runner import process_single_image


def _parse() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Recognize a single pre-cropped price-tag image.")
    p.add_argument("--image", required=True, type=str)
    p.add_argument("--out", type=str, default=None)
    p.add_argument("--config", type=str, default=None)
    p.add_argument("-v", "--verbose", action="store_true")
    return p.parse_args()


def main() -> None:
    args = _parse()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    cfg = config_loader.load(args.config)

    image = Path(args.image).resolve()
    if not image.exists():
        raise SystemExit(f"image not found: {image}")

    out = Path(args.out) if args.out else Path(cfg.runtime.outputs_dir) / f"{image.stem}.csv"
    out = out if out.is_absolute() else (config_loader.ROOT / out).resolve()

    result = process_single_image(
        image_path=image,
        output_csv=out,
        cfg=cfg,
        source_filename=image.name,
    )
    print(f"\n[OK] wrote {result}")


if __name__ == "__main__":
    main()
