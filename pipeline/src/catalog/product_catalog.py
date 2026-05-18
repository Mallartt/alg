"""Look-up table built from db_hack.csv (barcode -> product name).

The CSV is shipped in cp1251 with `;` as the separator. By default the
entire file is loaded into memory; pass a positive ``max_rows`` only when
you want a hard cap (e.g. inside unit tests).
"""

from __future__ import annotations

import csv
import logging
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)


class ProductCatalog:
    """Small in-memory dictionary keyed by barcode (as string)."""

    def __init__(self, table: dict[str, str]):
        self._table = table

    # ------------------------------------------------------------
    @classmethod
    def from_csv(
        cls,
        path: str | Path,
        *,
        encoding: str = "cp1251",
        delimiter: str = ";",
        max_rows: int = 0,
    ) -> "ProductCatalog":
        """
        Load barcode -> product_name mapping from db_hack.csv.

        ``max_rows = 0`` means "no limit": the whole catalogue is loaded
        into memory. Pass a positive value only if you want a hard cap.
        """
        table: dict[str, str] = {}
        try:
            with open(
                path,
                "r",
                encoding=encoding,
                errors="replace",
                newline="",
            ) as fh:
                reader = csv.DictReader(fh, delimiter=delimiter)
                for i, row in enumerate(reader):
                    if max_rows and i >= max_rows:
                        break
                    code = (
                        row.get("code") or row.get("barcode") or ""
                    ).strip()
                    name = (
                        row.get("fullname") or row.get("name") or ""
                    ).strip()
                    if code:
                        table[code] = name
        except FileNotFoundError:
            log.warning(
                "Product catalog not found at %s; running without it.",
                path,
            )
        except Exception as err:  # noqa: BLE001
            log.warning(
                "Could not load product catalog (%s); running without it.",
                err,
            )

        log.info("ProductCatalog loaded: %s rows", len(table))
        return cls(table)

    # ------------------------------------------------------------
    def lookup(self, barcode: str | int | None) -> Optional[str]:
        if barcode is None:
            return None
        return self._table.get(str(barcode))

    def enrich(self, payload: dict) -> dict:
        """If the LLM result has a barcode but no name, patch it."""
        code = payload.get("barcode")
        if not code:
            return payload
        catalog_name = self.lookup(code)
        if not catalog_name:
            return payload

        current_name = payload.get("product_name") or ""
        if (
            not current_name
            or len(current_name) < len(catalog_name) // 2
        ):
            payload["product_name"] = catalog_name

        return payload

    def __len__(self) -> int:
        return len(self._table)
