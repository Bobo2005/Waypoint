"""Persist and load RunState to backend/db/state.json.

Plain JSON, not SQLite -- a run's entire state is one small document, so a
file keeps this readable with `cat`/`git diff` and avoids a DB layer for
something this size. Writes are atomic (write to a temp file, then
os.replace) so a process killed mid-write can never leave a half-written,
corrupt state.json behind -- os.replace is atomic on both POSIX and
Windows, so either the old file or the fully-new file is what's there,
never a partial one.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from .models import RunState

DEFAULT_STATE_PATH = Path(__file__).resolve().parents[1] / "db" / "state.json"


def save(state: RunState, path: Path = DEFAULT_STATE_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(state.model_dump_json(indent=2), encoding="utf-8")
    os.replace(tmp_path, path)


def load(path: Path = DEFAULT_STATE_PATH) -> Optional[RunState]:
    if not path.exists():
        return None
    return RunState.model_validate_json(path.read_text(encoding="utf-8"))


def exists(path: Path = DEFAULT_STATE_PATH) -> bool:
    return path.exists()