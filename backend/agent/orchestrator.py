"""Waypoint orchestrator.

Step 1 (kept, unchanged behavior): migrate_one_file(path) -- a single-file
tool-calling loop where the model migrates and commits one file itself.

Step 2 (this extension): plan() / run_loop() / resume() -- a durable,
multi-file migration across every requests-using file in demo-repo/.
State is checkpointed to disk after every single task, so a killed
process can be resumed without redoing finished work. Here the
orchestrator -- not the model -- verifies tests and does the commit, so
commit messages and pass/fail decisions are consistent regardless of what
the model itself believes happened.
"""
from __future__ import annotations

import json
import re
import subprocess
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..checkpoint import store
from ..checkpoint.models import Checkpoint, RunState, RunStatus, Task, TaskStatus, TestResult
from .claude_client import call_claude, get_client
from .prompts import (
    RUN_LOOP_ADDENDUM,
    SYSTEM_PROMPT,
    build_retry_prompt,
    build_user_prompt,
)
from .tools import TOOLS, ToolError, dispatch

REPO_ROOT = Path(__file__).resolve().parents[2]
DEMO_REPO = REPO_ROOT / "demo-repo"
MAX_TURNS = 12

REQUESTS_IMPORT_RE = re.compile(r"^\s*(import requests\b|from requests\b)", re.MULTILINE)

# --- Pause hook for backend/main.py's POST /run/pause ---------------------
# A single process-wide flag, checked only between tasks in run_loop() (see
# the check right after each task's checkpoint is persisted, below). This
# does NOT touch how a file gets migrated, tested, or committed -- it only
# decides whether the loop starts the *next* task.
_pause_event = threading.Event()


def request_pause() -> None:
    """Ask the currently running run_loop() to stop after its current
    file finishes. Takes effect at the next task boundary, not instantly."""
    _pause_event.set()


def pause_requested() -> bool:
    return _pause_event.is_set()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _state_path(repo_root: Path) -> Path:
    return repo_root / "backend" / "db" / "state.json"


# ---------------------------------------------------------------------------
# Shared low-level tool-calling loop, used by both migrate_one_file (step 1)
# and run_loop (step 2)
# ---------------------------------------------------------------------------

def _tool_result_block(tool_use_id: str, content: Any, is_error: bool = False) -> Dict[str, Any]:
    return {
        "type": "tool_result",
        "tool_use_id": tool_use_id,
        "content": content if isinstance(content, str) else json.dumps(content),
        "is_error": is_error,
    }


def _run_agent_loop(
    client: Any,
    repo_root: Path,
    system_prompt: str,
    initial_user_message: str,
) -> Tuple[bool, int]:
    """Run the tool-calling loop until the model stops calling tools.

    Returns (tests_passed_per_last_run_bash_call, expand_context_call_count).

    `expand_context` is Paritok's virtual tool for un-compressing content
    the model decided it needs back in full -- it's injected by the proxy,
    not one of our four. We don't have Paritok's documented wire contract
    for it, so we handle it defensively: count every call (this is the
    metric the spec asks for -- proof compressed context wasn't silently
    dropped), and answer with a generic tool_result so the conversation
    doesn't stall on a tool we don't implement ourselves. Paritok's own
    request-processing layer (visible in `paritok/middleware/wrapper.py` in
    your installed package -- its `process_request` already deals in a
    `stubbed` concept per the traceback you hit earlier) is the most likely
    place this actually gets resolved; if real behavior differs, that
    installed source is the ground truth to check against, not this
    comment.
    """
    messages: List[Dict[str, Any]] = [{"role": "user", "content": initial_user_message}]
    tests_passed = False
    expand_context_calls = 0

    for _ in range(MAX_TURNS):
        response = call_claude(client, system=system_prompt, messages=messages, tools=TOOLS)
        messages.append({"role": "assistant", "content": response.content})

        tool_calls = [block for block in response.content if block.type == "tool_use"]
        if not tool_calls:
            break

        result_blocks = []
        for call in tool_calls:
            if call.name == "expand_context":
                expand_context_calls += 1
                result_blocks.append(
                    _tool_result_block(
                        call.id,
                        {"note": "expand_context is handled by the Paritok proxy layer"},
                    )
                )
                continue
            try:
                result = dispatch(repo_root, call.name, call.input)
                if call.name == "run_bash" and isinstance(result, dict):
                    tests_passed = bool(result.get("passed"))
                result_blocks.append(_tool_result_block(call.id, result))
            except ToolError as exc:
                result_blocks.append(_tool_result_block(call.id, str(exc), is_error=True))

        messages.append({"role": "user", "content": result_blocks})

        if response.stop_reason != "tool_use":
            break

    return tests_passed, expand_context_calls


# ---------------------------------------------------------------------------
# Step 1: single-file migration (unchanged public behavior/signature)
# ---------------------------------------------------------------------------

def migrate_one_file(path: str, repo_root: Optional[Path] = None) -> bool:
    """Migrate a single file; the model commits its own change via
    git_commit, per SYSTEM_PROMPT's instructions. Kept for step-1
    compatibility and ad-hoc/interactive use -- run_loop() below does NOT
    call this, since it needs to control commit messages and test
    verification itself."""
    repo_root = repo_root or REPO_ROOT
    client = get_client()
    _pause_event.clear()  # a fresh call to run_loop() always starts unpaused
    state.overall_status = RunStatus.IN_PROGRESS
    passed, _ = _run_agent_loop(client, repo_root, SYSTEM_PROMPT, build_user_prompt(path))
    return passed


# ---------------------------------------------------------------------------
# Step 2: plan / run_loop / resume
# ---------------------------------------------------------------------------

def _discover_requests_files(demo_repo: Path, repo_root: Path) -> List[str]:
    """Find top-level .py files under demo_repo/ (not tests/) that import
    `requests`, sorted for a deterministic, reproducible task order."""
    hits = []
    for f in sorted(demo_repo.glob("*.py")):
        if REQUESTS_IMPORT_RE.search(f.read_text(encoding="utf-8")):
            hits.append(str(f.relative_to(repo_root)))
    return hits


def plan(demo_repo: Path = DEMO_REPO, repo_root: Path = REPO_ROOT) -> RunState:
    """Scan demo-repo/ for files still using `requests`, build the ordered
    task list, and persist it as the initial RunState. Overwrites any
    previous state.json -- call this once per fresh run, not on resume."""
    files = _discover_requests_files(demo_repo, repo_root)
    now = _now()
    state = RunState(
        tasks=[Task(path=f) for f in files],
        current_index=0,
        overall_status=RunStatus.NOT_STARTED,
        checkpoints=[],
        expand_context_calls=0,
        started_at=now,
        updated_at=now,
    )
    store.save(state, path=_state_path(repo_root))
    return state


def _test_target_for(demo_repo: Path, repo_root: Path, source_rel_path: str) -> str:
    """Map a source file to its test file if one exists by convention
    (weather_client.py -> tests/test_weather_client.py); otherwise fall
    back to running the whole tests/ directory."""
    source_path = repo_root / source_rel_path
    candidate = demo_repo / "tests" / f"test_{source_path.stem}.py"
    if candidate.exists():
        return str(candidate.relative_to(repo_root))
    return str((demo_repo / "tests").relative_to(repo_root))


def _run_tests(repo_root: Path, test_target: str) -> Dict[str, Any]:
    return dispatch(repo_root, "run_bash", {"path": test_target})


def _summary_line(test_run: Dict[str, Any]) -> str:
    text = (test_run.get("stdout") or test_run.get("stderr") or "").strip()
    return text.splitlines()[-1] if text else ""


def _git_head_sha(repo_root: Path) -> Optional[str]:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo_root, capture_output=True, text=True
    )
    return result.stdout.strip() if result.returncode == 0 else None


def _has_uncommitted_changes(repo_root: Path, rel_path: str) -> bool:
    result = subprocess.run(
        ["git", "status", "--porcelain", rel_path], cwd=repo_root, capture_output=True, text=True
    )
    return bool(result.stdout.strip())


def _commit_task(repo_root: Path, rel_path: str, message: str) -> Optional[str]:
    """Commit rel_path with `message` if there's anything to commit.

    RUN_LOOP_ADDENDUM tells the model not to self-commit, but git_commit
    is still technically available to it as one of its four tools -- if it
    used it anyway, the working tree will already be clean here, and we
    just record the SHA of whatever commit already covers this file
    instead of failing on "nothing to commit".
    """
    if _has_uncommitted_changes(repo_root, rel_path):
        dispatch(repo_root, "git_commit", {"paths": [rel_path], "message": message})
    return _git_head_sha(repo_root)


def run_loop(
    state: Optional[RunState] = None,
    repo_root: Path = REPO_ROOT,
    demo_repo: Path = DEMO_REPO,
) -> RunState:
    """Iterate pending tasks in order, migrating, verifying, and
    committing each. Persists state after every single task (pass or
    fail) -- if the process dies at any point, state.json on disk
    accurately reflects exactly which files are done, failed, or still
    pending, so resume() can pick up correctly.

    Tasks already DONE or FAILED are skipped unconditionally -- this
    function never redoes finished work, whether called fresh after
    plan() or via resume() after a restart.
    """
    state_path = _state_path(repo_root)
    if state is None:
        state = store.load(path=state_path)
        if state is None:
            raise RuntimeError("no RunState on disk -- call plan() first")

    client = get_client()
    state.overall_status = RunStatus.IN_PROGRESS
    state.updated_at = _now()
    store.save(state, path=state_path)

    for i, task in enumerate(state.tasks):
        if task.status in (TaskStatus.DONE, TaskStatus.FAILED):
            continue

        state.current_index = i
        task.status = TaskStatus.IN_PROGRESS
        store.save(state, path=state_path)

        test_target = _test_target_for(demo_repo, repo_root, task.path)
        system_prompt = SYSTEM_PROMPT + "\n\n" + RUN_LOOP_ADDENDUM

        # Attempt 1.
        task.attempts += 1
        _, expand_calls = _run_agent_loop(
            client, repo_root, system_prompt, build_user_prompt(task.path)
        )
        state.expand_context_calls += expand_calls
        test_run = _run_tests(repo_root, test_target)

        # Exactly one retry, with the failure output fed back as context.
        if not test_run["passed"]:
            task.attempts += 1
            retry_message = build_retry_prompt(
                task.path, test_run["stdout"] + test_run["stderr"]
            )
            _, expand_calls_retry = _run_agent_loop(
                client, repo_root, system_prompt, retry_message
            )
            state.expand_context_calls += expand_calls_retry
            test_run = _run_tests(repo_root, test_target)

        if test_run["passed"]:
            sha = _commit_task(repo_root, task.path, f"waypoint: migrate {task.path} (tests pass)")
            task.status = TaskStatus.DONE
            state.checkpoints.append(
                Checkpoint(
                    file=task.path,
                    git_commit_sha=sha,
                    test_result=TestResult(passed=True, summary=_summary_line(test_run)),
                )
            )
        else:
            task.status = TaskStatus.FAILED
            state.checkpoints.append(
                Checkpoint(
                    file=task.path,
                    git_commit_sha=None,
                    test_result=TestResult(passed=False, summary=_summary_line(test_run)),
                )
            )

        state.current_index = i + 1
        state.updated_at = _now()
        store.save(state, path=state_path)  # persist after EVERY task, pass or fail
        if _pause_event.is_set():
            state.overall_status = RunStatus.PAUSED
            state.updated_at = _now()
            store.save(state, path=state_path)
            return state

    state.overall_status = (
        RunStatus.COMPLETED_WITH_FAILURES
        if any(t.status == TaskStatus.FAILED for t in state.tasks)
        else RunStatus.COMPLETED
    )
    state.updated_at = _now()
    store.save(state, path=state_path)
    return state


def resume(repo_root: Path = REPO_ROOT, demo_repo: Path = DEMO_REPO) -> RunState:
    """Reload RunState from disk (a fresh process has no memory of any
    prior run) and continue run_loop() from the first pending task.

    Prints exactly what was reloaded before doing any work, so the
    resume behavior can be checked from the console output rather than
    taken on faith.
    """
    state_path = _state_path(repo_root)
    state = store.load(path=state_path)
    if state is None:
        raise RuntimeError("no RunState on disk -- call plan() first")

    done = [t.path for t in state.tasks if t.status == TaskStatus.DONE]
    pending = [t.path for t in state.tasks if t.status == TaskStatus.PENDING]
    failed = [t.path for t in state.tasks if t.status == TaskStatus.FAILED]
    in_progress = [t.path for t in state.tasks if t.status == TaskStatus.IN_PROGRESS]

    print(f"[resume] loaded state.json: {len(done)} done, {len(pending)} pending, "
          f"{len(failed)} failed, {len(in_progress)} left mid-flight")
    print(f"[resume] already committed (will NOT be redone): {done}")
    if in_progress:
        # A task marked in_progress when the process died gets retried
        # from scratch rather than assumed half-done -- its file may be
        # mid-edit, so it's treated like a fresh pending task.
        print(f"[resume] was mid-task when the process died, retrying from scratch: {in_progress}")
        for t in state.tasks:
            if t.status == TaskStatus.IN_PROGRESS:
                t.status = TaskStatus.PENDING
    print(f"[resume] will process next, in order: {pending + in_progress}")

    return run_loop(state=state, repo_root=repo_root, demo_repo=demo_repo)


if __name__ == "__main__":
    import sys

    cmd = sys.argv[1] if len(sys.argv) > 1 else "run"
    if cmd == "plan":
        s = plan()
        print(f"planned {len(s.tasks)} task(s): {[t.path for t in s.tasks]}")
    elif cmd == "resume":
        s = resume()
        print(f"final status: {s.overall_status}, expand_context_calls={s.expand_context_calls}")
    else:
        s = plan()
        s = run_loop(state=s)
        print(f"final status: {s.overall_status}, expand_context_calls={s.expand_context_calls}")