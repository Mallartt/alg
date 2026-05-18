"""Build prompts for the local VLM from a TOML schema."""

from __future__ import annotations

import sys
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib as _toml
else:  # pragma: no cover
    import tomli as _toml  # type: ignore


def load_prompt(prompt_path: str | Path) -> str:
    """Return a single text prompt assembled from the TOML schema."""
    data = _read_toml(prompt_path)

    system_instr = (data.get("instruction") or "").strip()
    schema_lines = ['{']
    for field, spec in (data.get("fields") or {}).items():
        ftype = spec.get("type", "string")
        descr = spec.get("description", "")
        schema_lines.append(f'  "{field}": <{ftype}> — {descr}')
    schema_lines.append("}")

    return f"{system_instr}\n\nSCHEMA:\n" + "\n".join(schema_lines)


# ----------------------------------------------------------------------
def _read_toml(path: str | Path) -> dict:
    with open(path, "rb") as f:
        return _toml.load(f)
