"""Single callable that turns a CropEvent into a RecognitionOutcome."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Optional

from ..catalog import ProductCatalog
from ..core.schemas import CropEvent, RecognitionOutcome
from ..crops.enhance import boost_text_contrast, upscale_bicubic
from ..crops.geometry import deskew_quad
from .code_reader import CodeReader
from .llm_vision import LocalVlmClient
from .prompt import load_prompt
from .sharpness import is_sharp_enough
from .tag_color import classify_tag_color

log = logging.getLogger(__name__)

REQUIRED_PRICE_KEYS = ("price_default", "price_card", "price_discount")


class CropRecognizer:
    """
    Stateless processor that runs filters → LLM → code-reader on a single crop.
    Intentionally a plain class (no global state) so it can be reused by the
    image-only entry point as well as the video pipeline.
    """

    def __init__(
        self,
        prompt_path: str | Path,
        *,
        vlm_client: Optional[LocalVlmClient] = None,
        code_reader: Optional[CodeReader] = None,
        catalog: Optional[ProductCatalog] = None,
        blur_threshold: float = 8.0,
        color_threshold: float = 0.2,
        upscale_factor: float = 2.0,
        deskew: bool = True,
        enhance: bool = True,
        save_debug_dir: Optional[Path] = None,
    ):
        self.prompt_text = load_prompt(prompt_path)
        self.vlm = vlm_client or LocalVlmClient()
        self.codes = code_reader or CodeReader()
        self.catalog = catalog
        self.blur_threshold = blur_threshold
        self.color_threshold = color_threshold
        self.upscale_factor = upscale_factor
        self.deskew = deskew
        self.enhance = enhance
        self.save_debug_dir = save_debug_dir

    # ------------------------------------------------------------------
    def __call__(self, event: CropEvent) -> RecognitionOutcome:
        crop = event.image
        if crop is None or crop.size == 0:
            return RecognitionOutcome(ok=False, reason="empty_crop")

        # 1. blur gate
        sharp, score = is_sharp_enough(crop, self.blur_threshold)
        if not sharp:
            log.info("Track %s: blurry (score=%.1f)", event.track_id, score)
            return RecognitionOutcome(ok=False, reason="blurry", sharpness=score)

        # 2. colour tag
        color = classify_tag_color(crop, threshold=self.color_threshold)

        # 3. (optional) perspective de-skew
        if self.deskew:
            crop = deskew_quad(crop)

        # 4. (optional) contrast boost + upscale to help OCR
        if self.enhance:
            crop = boost_text_contrast(crop)
        if self.upscale_factor and self.upscale_factor != 1.0:
            crop = upscale_bicubic(crop, factor=self.upscale_factor)

        # 5. code scan (cheap, deterministic, runs before LLM)
        codes = self.codes.scan(crop)

        # 6. talk to the VLM
        llm_payload = self.vlm.ask_about_image(self.prompt_text, crop)
        if "_error" in llm_payload:
            return RecognitionOutcome(
                ok=False, reason=f"vlm_error: {llm_payload['_error']}", color_tag=color, sharpness=score
            )
        if "_raw" in llm_payload:
            return RecognitionOutcome(
                ok=False, reason="vlm_non_json", color_tag=color, sharpness=score
            )

        # 7. validate that LLM produced anything useful
        if not _has_required(llm_payload):
            return RecognitionOutcome(
                ok=False,
                reason="missing_required",
                fields=llm_payload,
                color_tag=color,
                sharpness=score,
                codes=codes,
            )

        # 8. enrich barcode from QR/EAN scanner if LLM missed it
        if not llm_payload.get("barcode") and codes:
            for entry in codes:
                if entry.get("data") and str(entry["data"]).isdigit():
                    llm_payload["barcode"] = entry["data"]
                    break

        # 9. cross-check against product catalogue
        if self.catalog and llm_payload.get("barcode"):
            llm_payload = self.catalog.enrich(llm_payload)

        llm_payload.setdefault("color", color)

        return RecognitionOutcome(
            ok=True,
            reason="ok",
            fields=llm_payload,
            codes=codes,
            color_tag=color,
            sharpness=score,
        )


# ----------------------------------------------------------------------
def _has_required(payload: dict[str, Any]) -> bool:
    if not isinstance(payload, dict):
        return False
    has_name = bool(payload.get("product_name"))
    has_code = bool(payload.get("barcode"))
    has_price = any(payload.get(k) for k in REQUIRED_PRICE_KEYS)

    if not (has_name or has_code):
        return False
    return has_price
