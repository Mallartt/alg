"""Thin client for a locally-running llama.cpp OpenAI-compatible server.

The server is expected to be started separately, e.g.

    python -m llama_cpp.server --config_file server_config.json

This module never spawns the server itself.
"""

from __future__ import annotations

import base64
import json
import logging
import re
from typing import Optional

import cv2
import numpy as np

log = logging.getLogger(__name__)


# ----------------------------------------------------------------------
def encode_image_jpeg(image: np.ndarray, quality: int = 90) -> str:
    """BGR ndarray -> base64-encoded JPEG (data only, no prefix)."""
    if image is None or not isinstance(image, np.ndarray):
        raise ValueError("encode_image_jpeg: expected a numpy ndarray")
    ok, buf = cv2.imencode(".jpg", image, [int(cv2.IMWRITE_JPEG_QUALITY), int(quality)])
    if not ok:
        raise RuntimeError("Failed to JPEG-encode image")
    return base64.b64encode(buf).decode("ascii")


# ----------------------------------------------------------------------
class LocalVlmClient:
    """OpenAI-style client wrapper for a local multimodal llama.cpp server."""

    def __init__(
        self,
        base_url: str = "http://localhost:8000/v1",
        api_key: str = "no-key",
        model_alias: str = "local-model",
        temperature: float = 0.05,
        timeout_sec: float = 90.0,
    ):
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "Install `openai` to talk to the llama.cpp server (pip install openai)."
            ) from exc

        self._client = OpenAI(base_url=base_url, api_key=api_key, timeout=timeout_sec)
        self.model_alias = model_alias
        self.temperature = temperature

    # ------------------------------------------------------------------
    def ask_about_image(self, prompt_text: str, image_bgr: np.ndarray) -> dict:
        """Send (text + image) and parse the response as JSON."""
        b64 = encode_image_jpeg(image_bgr)
        try:
            response = self._client.chat.completions.create(
                model=self.model_alias,
                temperature=self.temperature,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt_text},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
                            },
                        ],
                    }
                ],
            )
        except Exception as err:  # noqa: BLE001
            log.error("VLM request failed: %s", err)
            return {"_error": str(err)}

        raw = response.choices[0].message.content or ""
        return _coerce_json(raw)


# ----------------------------------------------------------------------
_JSON_BLOCK = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)


def _coerce_json(text: str) -> dict:
    candidate = text.strip()

    m = _JSON_BLOCK.search(candidate)
    if m:
        candidate = m.group(1).strip()

    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError:
        # try to slice out the first {...} object
        first = candidate.find("{")
        last = candidate.rfind("}")
        if first >= 0 and last > first:
            try:
                parsed = json.loads(candidate[first : last + 1])
            except json.JSONDecodeError:
                log.warning("VLM returned non-JSON: %s", text[:200])
                return {"_raw": text}
        else:
            return {"_raw": text}

    return parsed if isinstance(parsed, dict) else {"_raw": text}
