"""FastAPI wrapper around Waypoint's orchestrator (steps 1-2).

This file adds no new migration logic of its own -- every route just
calls plan() / run_loop() / resume() / the checkpoint store exactly as
they already work. The only changes made to the orchestrator itself for
this step are additive: a pause flag it checks between tasks
(orchestrator.request_pause() / pause_requested()) and a new
RunStatus.PAUSED value in checkpoint/models.py. Neither touches how a
file actually gets read, migrated, tested, or committed.

Run with (from the repo root, with your venv active and .env set):
    uvicorn backend.main:app --reload --port 8000
"""
from __future__ import annotations

import threading
from typing import Any, Dict, List, Optional

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .agent import orchestrator
from .checkpoint import store

app = FastAPI(title="Waypoint")

# Vite's default dev server origin -- the frontend built next will call
# this API directly from the browser, so it needs CORS explicitly.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PARITOK_STATS_URL = "http://127.0.0.1:8080/stats"

# --- Background run tracking -----------------------------------------------
# run_loop()/resume() are long-running, blocking, synchronous calls (real
# HTTP to Claude, real subprocess pytest runs). We run them on a plain
# background thread rather than as an async task so nothing about the
# orchestrator itself has to change to be "async-friendly". A lock plus a
# single thread handle is enough to stop two runs from starting at once.
_run_lock = threading.Lock()
_run_thread: Optional[threading.Thread] = None


def _is_running() -> bool:
    return _run_thread is not None and _run_thread.is_alive()


class StartRequest(BaseModel):
    # Accepted for forward-compatibility with a future multi-task API --
    # right now the orchestrator only knows how to do the one thing it did
    # in steps 1-2 (requests -> httpx across demo-repo/), same as before.
    task: str = "migrate requests to httpx"


def _background_run_loop() -> None:
    orchestrator.run_loop()


def _background_resume() -> None:
    orchestrator.resume()


@app.post("/run/start")
def start_run(body: StartRequest) -> Dict[str, Any]:
    global _run_thread
    with _run_lock:
        if _is_running():
            raise HTTPException(status_code=409, detail="a run is already in progress")
        state = orchestrator.plan()
        _run_thread = threading.Thread(target=_background_run_loop, daemon=True)
        _run_thread.start()
    return {
        "status": "started",
        "task": body.task,
        "planned_tasks": [t.path for t in state.tasks],
    }


@app.post("/run/pause")
def pause_run() -> Dict[str, Any]:
    if not _is_running():
        raise HTTPException(status_code=409, detail="no run is currently in progress")
    orchestrator.request_pause()
    return {"status": "pause requested -- will stop after the current file finishes"}


@app.post("/run/resume")
def resume_run() -> Dict[str, Any]:
    global _run_thread
    with _run_lock:
        if _is_running():
            raise HTTPException(status_code=409, detail="a run is already in progress")
        if not store.exists():
            raise HTTPException(
                status_code=404, detail="no run state on disk -- call /run/start first"
            )
        _run_thread = threading.Thread(target=_background_resume, daemon=True)
        _run_thread.start()
    return {"status": "resumed"}


@app.get("/run/status")
def get_status() -> Dict[str, Any]:
    state = store.load()
    if state is None:
        raise HTTPException(
            status_code=404, detail="no run has been planned yet -- call /run/start first"
        )
    current_file = None
    if 0 <= state.current_index < len(state.tasks):
        current_file = state.tasks[state.current_index].path
    return {
        "overall_status": state.overall_status,
        "current_file": current_file,
        "is_running": _is_running(),
        "expand_context_calls": state.expand_context_calls,
        "tasks": [
            {"path": t.path, "status": t.status, "attempts": t.attempts} for t in state.tasks
        ],
    }


@app.get("/checkpoints")
def get_checkpoints() -> List[Dict[str, Any]]:
    state = store.load()
    if state is None:
        return []
    checkpoints = [
        {
            "file": c.file,
            "git_commit_sha": c.git_commit_sha,
            "timestamp": c.timestamp.isoformat(),
            "test_result": {"passed": c.test_result.passed, "summary": c.test_result.summary},
        }
        for c in state.checkpoints
    ]
    return list(reversed(checkpoints))  # most recent first


@app.get("/stats")
def get_stats() -> Dict[str, Any]:
    state = store.load()
    expand_context_calls = state.expand_context_calls if state else 0

    try:
        resp = httpx.get(PARITOK_STATS_URL, timeout=5.0)
        resp.raise_for_status()
        paritok_stats: Any = resp.json()
    except Exception as exc:  # Paritok not running, unreachable, bad JSON, etc.
        paritok_stats = {"error": f"could not reach Paritok /stats: {exc}"}

    return {
        "paritok": paritok_stats,
        "expand_context_calls": expand_context_calls,
    }