"""Write recognition rows out as the contest-format CSV."""

from __future__ import annotations

import csv
import logging
from pathlib import Path
from typing import Iterable, Sequence

log = logging.getLogger(__name__)


SUBMISSION_COLUMNS: Sequence[str] = (
    "filename",
    "product_name",
    "price_default",
    "price_card",
    "price_discount",
    "barcode",
    "discount_amount",
    "id_sku",
    "print_datetime",
    "code",
    "additional_info",
    "color",
    "special_symbols",
    "frame_timestamp",
    "x_min",
    "y_min",
    "x_max",
    "y_max",
    "qr_code_barcode",
    "price1_qr",
    "price2_qr",
    "price3_qr",
    "price4_qr",
    "wholesale_level_1_count",
    "wholesale_level_1_price",
    "wholesale_level_2_count",
    "wholesale_level_2_price",
    "action_price_qr",
    "action_code_qr",
)

PLACEHOLDER = "нет"


def _normalize_row(row: dict, source_filename: str) -> dict:
    out = {col: PLACEHOLDER for col in SUBMISSION_COLUMNS}
    out["filename"] = source_filename or row.get("filename", "")

    for col in SUBMISSION_COLUMNS:
        value = row.get(col)
        if value is None or value == "":
            continue
        out[col] = value
    return out


def write_submission(
    rows: Iterable[dict],
    output_path: str | Path,
    source_filename: str = "",
) -> Path:
    """Serialize rows in the strict submission column order."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    materialized = list(rows)
    log.info("Writing %s rows to %s", len(materialized), output_path)

    with output_path.open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(SUBMISSION_COLUMNS))
        writer.writeheader()
        for row in materialized:
            writer.writerow(_normalize_row(row, source_filename))

    return output_path
