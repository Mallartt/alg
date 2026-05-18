"""Top-level pipeline glue: stream → detect → recognize → vote → export."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable, Iterable, Optional

from .consensus import MajorityVoter
from .schemas import CropEvent, RecognitionOutcome, TrackRecord
from .track_buffer import TrackRegistry

log = logging.getLogger(__name__)

EventStream = Iterable[CropEvent]
Recognizer = Callable[[CropEvent], RecognitionOutcome]


class RecognitionFlow:
    """
    Drives the end-to-end recognition flow for a single video.
    The class deliberately knows nothing about YOLO / OpenCV / LLM directly —
    those concerns are injected via callables and iterables.
    """

    def __init__(
        self,
        event_stream: EventStream,
        recognizer: Recognizer,
        registry: Optional[TrackRegistry] = None,
        voter: Optional[MajorityVoter] = None,
        source_filename: str = "",
    ):
        self.events = event_stream
        self.recognize = recognizer
        self.registry = registry or TrackRegistry()
        self.voter = voter or MajorityVoter()
        self.source_filename = source_filename
        self._last_frame_seen = 0

    # ------------------------------------------------------------------
    def run(self) -> list[dict]:
        """Consume the event stream and return aggregated rows."""
        try:
            for evt in self.events:
                self._last_frame_seen = max(self._last_frame_seen, evt.frame_index)
                self.registry.observe(evt)
                self._drain_ready_tracks(evt.frame_index)
        except KeyboardInterrupt:
            log.warning("Interrupted by user")
        finally:
            self._close_all_tracks()

        return self._collect()

    # ------------------------------------------------------------------
    def _drain_ready_tracks(self, current_frame: int) -> None:
        for rec in list(self.registry.take_ready_for_recognition(current_frame)):
            self._recognize_record(rec)

    def _close_all_tracks(self) -> None:
        """At EOF: force at least one OCR pass on every track that has a crop."""
        for rec in self.registry.finalize_all():
            if rec.finalized:
                continue
            while rec.attempts < self.registry.min_attempts and rec.best_event is not None:
                self._recognize_record(rec)
            if rec.attempts == 0 and rec.best_event is not None:
                self._recognize_record(rec)

            payload = self.voter.reduce(rec.outcomes)
            self.registry.finalize(rec.track_id, payload or None)

    def _recognize_record(self, rec: TrackRecord) -> None:
        if rec.best_event is None or rec.attempts >= self.registry.max_attempts:
            return
        try:
            outcome = self.recognize(rec.best_event)
        except Exception as err:  # noqa: BLE001
            log.error("Recognizer failed on track %s: %s", rec.track_id, err, exc_info=True)
            outcome = RecognitionOutcome(ok=False, reason=f"recognizer_error: {err}")

        self.registry.store_outcome(rec.track_id, outcome)
        log.info(
            "Track %s: attempt %s/%s — %s",
            rec.track_id,
            rec.attempts,
            self.registry.max_attempts,
            "ok" if outcome.ok else f"skip ({outcome.reason})",
        )

    # ------------------------------------------------------------------
    def _collect(self) -> list[dict]:
        rows: list[dict] = []
        for rec in self.registry.finalize_all():
            if not rec.final_payload:
                continue
            row = dict(rec.final_payload)
            row["track_id"] = rec.track_id
            row["filename"] = self.source_filename or row.get("filename", "")
            if rec.best_event is not None:
                evt = rec.best_event
                row.setdefault("frame_timestamp", int(evt.timestamp_ms))
                row.setdefault("x_min", round(float(evt.bbox_xyxy[0]), 1))
                row.setdefault("y_min", round(float(evt.bbox_xyxy[1]), 1))
                row.setdefault("x_max", round(float(evt.bbox_xyxy[2]), 1))
                row.setdefault("y_max", round(float(evt.bbox_xyxy[3]), 1))
            rows.append(row)
        return rows


# ----------------------------------------------------------------------
# Convenience: build a recognizer for a single, already-cropped image.
# Used by run_image.py to bypass the whole video stage.
# ----------------------------------------------------------------------
def recognize_single_crop(
    image_path: str | Path,
    recognizer: Recognizer,
    source_filename: str = "",
) -> dict:
    import cv2

    img = cv2.imread(str(image_path))
    if img is None:
        raise FileNotFoundError(f"Cannot read image: {image_path}")

    h, w = img.shape[:2]
    evt = CropEvent(
        track_id=0,
        image=img,
        frame_index=0,
        timestamp_ms=0.0,
        bbox_xyxy=(0.0, 0.0, float(w), float(h)),
        centerness=1.0,
        frame_size=(w, h),
        source_filename=source_filename or Path(image_path).name,
    )
    outcome = recognizer(evt)
    voter = MajorityVoter()
    payload = voter.reduce([outcome]) if outcome.ok else {}
    payload["track_id"] = 0
    payload["filename"] = source_filename or Path(image_path).name
    payload["x_min"] = 0
    payload["y_min"] = 0
    payload["x_max"] = w
    payload["y_max"] = h
    payload["frame_timestamp"] = 0
    return payload
