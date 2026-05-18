"""Read QR / EAN barcodes off price-tag crops.

We try several backends in order: pyzbar (if available) → OpenCV barcode →
OpenCV QR. The first non-empty result wins; we still return everything we
saw so the caller can pick.
"""

from __future__ import annotations

import logging
from typing import Callable, Optional

import cv2
import numpy as np

log = logging.getLogger(__name__)


class CodeReader:
    """Tiny façade around several OpenCV / pyzbar decoders."""

    def __init__(self, enable_pyzbar: bool = True, pad_border: int = 16):
        self.pad_border = pad_border
        self._pyzbar = _try_load_pyzbar() if enable_pyzbar else None
        self._cv_bar = cv2.barcode.BarcodeDetector() if hasattr(cv2, "barcode") else None
        self._cv_qr = cv2.QRCodeDetector()

    # ------------------------------------------------------------------
    def scan(self, image: np.ndarray) -> list[dict]:
        if image is None or image.size == 0:
            return []

        padded = cv2.copyMakeBorder(
            image,
            self.pad_border,
            self.pad_border,
            self.pad_border,
            self.pad_border,
            cv2.BORDER_CONSTANT,
            value=(255, 255, 255),
        )

        records: list[dict] = []
        records.extend(self._read_pyzbar(padded))
        records.extend(self._read_cv_barcode(padded))
        records.extend(self._read_cv_qr(padded))

        return _dedup(records)

    # ------------------------------------------------------------------
    def _read_pyzbar(self, image: np.ndarray) -> list[dict]:
        if self._pyzbar is None:
            return []
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            decoded = self._pyzbar(gray)
        except Exception as err:  # noqa: BLE001
            log.debug("pyzbar failed: %s", err)
            return []

        out: list[dict] = []
        for obj in decoded:
            value = obj.data.decode("utf-8", errors="replace") if hasattr(obj, "data") else ""
            if value:
                out.append({"data": value, "type": getattr(obj, "type", "BAR"), "engine": "pyzbar"})
        return out

    def _read_cv_barcode(self, image: np.ndarray) -> list[dict]:
        if self._cv_bar is None:
            return []
        try:
            ok, values, *_ = self._cv_bar.detectAndDecode(image)
        except cv2.error as err:
            log.debug("cv.barcode failed: %s", err)
            return []
        if not ok:
            return []
        return [{"data": v, "type": "BAR", "engine": "cv2"} for v in values if v]

    def _read_cv_qr(self, image: np.ndarray) -> list[dict]:
        try:
            ok, decoded, *_ = self._cv_qr.detectAndDecodeMulti(image)
        except cv2.error as err:
            log.debug("cv.qr failed: %s", err)
            return []
        if not ok:
            return []
        return [{"data": v, "type": "QR", "engine": "cv2"} for v in decoded if v]


# ----------------------------------------------------------------------
def _try_load_pyzbar() -> Optional[Callable]:
    try:
        from pyzbar.pyzbar import decode as _decode

        return _decode
    except Exception as err:  # noqa: BLE001
        log.info("pyzbar unavailable (%s); falling back to OpenCV only", err)
        return None


def _dedup(records: list[dict]) -> list[dict]:
    seen: set[str] = set()
    out: list[dict] = []
    for rec in records:
        key = rec.get("data", "")
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(rec)
    return out
