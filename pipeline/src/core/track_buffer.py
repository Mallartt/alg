"""Per-track buffering: keeps best (centered) crops and OCR attempts."""

from __future__ import annotations

import logging
from typing import Iterable, Iterator

from .schemas import CropEvent, RecognitionOutcome, TrackRecord

log = logging.getLogger(__name__)


class TrackRegistry:
    """
    Stores crops grouped by track_id. For each track we keep:
        * the most-centered crop seen so far
        * how many OCR attempts were performed
        * accumulated recognition outcomes for later voting
    """

    def __init__(
        self,
        min_attempts: int = 1,
        max_attempts: int = 3,
        stale_after_frames: int = 30,
        center_improve_eps: float = 0.04,
    ):
        self.min_attempts = min_attempts
        self.max_attempts = max_attempts
        self.stale_after_frames = stale_after_frames
        self.center_improve_eps = center_improve_eps

        self._records: dict[int, TrackRecord] = {}

    # ------------------------------------------------------------------
    # incoming events
    # ------------------------------------------------------------------
    def observe(self, event: CropEvent) -> None:
        rec = self._records.get(event.track_id)
        if rec is None:
            rec = TrackRecord(
                track_id=event.track_id,
                first_seen_frame=event.frame_index,
                last_seen_frame=event.frame_index,
                best_event=event,
            )
            self._records[event.track_id] = rec
            log.debug("Track %s opened on frame %s", event.track_id, event.frame_index)
            return

        rec.last_seen_frame = event.frame_index

        if rec.finalized:
            return

        # Replace best event only if the new one is noticeably closer to center.
        if rec.best_event is None or (
            event.centerness - rec.best_event.centerness > self.center_improve_eps
        ):
            rec.best_event = event
            log.debug(
                "Track %s: best crop updated (centerness=%.3f, frame=%s)",
                event.track_id,
                event.centerness,
                event.frame_index,
            )

    def store_outcome(self, track_id: int, outcome: RecognitionOutcome) -> None:
        rec = self._records.get(track_id)
        if rec is None:
            return
        rec.outcomes.append(outcome)
        rec.attempts += 1

    # ------------------------------------------------------------------
    # selection of next track to recognize
    # ------------------------------------------------------------------
    def take_ready_for_recognition(self, current_frame: int) -> Iterator[TrackRecord]:
        """
        Yields track records that should be sent to OCR right now.
        A track is "ready" when either:
            * the object visibly leaves the frame (stale by N frames), or
            * we already have a good centered crop and at least one attempt is
              allowed (the orchestrator will throttle to <= max_attempts).
        """
        for rec in self._records.values():
            if rec.finalized:
                continue
            if rec.best_event is None:
                continue
            if rec.attempts >= self.max_attempts:
                continue

            gone = (current_frame - rec.last_seen_frame) > self.stale_after_frames
            need_first = rec.attempts == 0 and gone  # robot stopped / object left
            extra_pass = 0 < rec.attempts < self.max_attempts and rec.best_event.centerness > 0.85

            if need_first or extra_pass:
                yield rec

    # ------------------------------------------------------------------
    # finalisation
    # ------------------------------------------------------------------
    def finalize(self, track_id: int, payload: dict | None) -> None:
        rec = self._records.get(track_id)
        if rec is None:
            return
        rec.finalized = True
        rec.final_payload = payload

    def finalize_all(self) -> Iterable[TrackRecord]:
        for rec in self._records.values():
            yield rec

    def __contains__(self, track_id: int) -> bool:
        return track_id in self._records

    def __len__(self) -> int:
        return len(self._records)
