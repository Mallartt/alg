"""Majority voting across multiple OCR attempts for the same track."""

from __future__ import annotations

from collections import Counter
from typing import Any

from .schemas import RecognitionOutcome


def _vote_single(values: list[Any]) -> Any:
    cleaned = [v for v in values if v not in (None, "", "нет")]
    if not cleaned:
        return None
    try:
        counter = Counter(cleaned)
    except TypeError:
        # values contain unhashable items (lists / dicts) — just return the first one
        return cleaned[0]
    return counter.most_common(1)[0][0]


class MajorityVoter:
    """Reduces a list of OCR outcomes into one consensus dictionary."""

    PRICE_KEYS = ("price_card", "price_discount", "price_default")

    def __init__(self, quorum: int = 2):
        self.quorum = quorum

    def reduce(self, outcomes: list[RecognitionOutcome]) -> dict[str, Any]:
        successful = [o for o in outcomes if o.ok]
        if not successful:
            return {}

        all_keys: set[str] = set()
        for out in successful:
            all_keys.update(out.fields.keys())

        merged: dict[str, Any] = {}
        for key in all_keys:
            merged[key] = _vote_single([out.fields.get(key) for out in successful])

        # collect codes (first observed wins)
        for out in successful:
            for entry in out.codes:
                merged.setdefault("qr_code_barcode", entry.get("data"))
                if entry.get("data") and not merged.get("barcode"):
                    merged["barcode"] = entry["data"]

        # carry through color/sharpness signals
        colors = [out.color_tag for out in successful if out.color_tag]
        if colors:
            merged["color"] = Counter(colors).most_common(1)[0][0]

        merged["_attempts"] = len(outcomes)
        merged["_successful_attempts"] = len(successful)
        merged["_confidence"] = self._score(successful)
        return merged

    # ------------------------------------------------------------------
    def _score(self, outs: list[RecognitionOutcome]) -> str:
        if len(outs) < self.quorum:
            return f"single_pass ({len(outs)})"

        for key in self.PRICE_KEYS:
            vals = [o.fields.get(key) for o in outs if o.fields.get(key) is not None]
            if len(vals) >= self.quorum and Counter(vals).most_common(1)[0][1] >= self.quorum:
                return "stable"

        return "ambiguous"
