"""Tool definitions and handlers for the Waypoint migration agent.

Exactly four tools are exposed to the model: read_file, write_file,
run_bash, and git_commit. `run_bash` is intentionally narrow -- its only
job is to run `pytest <path>`, so the agent can verify its own work
without being handed a general-purpose shell.
"""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any, Dict, List

# ---------------------------------------------------------------------------
# Tool schemas (Anthropic Messages API "tools" format)
# ---------------------------------------------------------------------------

TOOLS: List[Dict[str, Any]] = [
    {
        "name": "read_file",
        "description": "Read and return the full UTF-8 text content of a file on disk.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the file, relative to the repo root.",
                },
            },
            "required": ["path"],
        },
    },
    {
        "name": "write_file",
        "description": "Overwrite a file on disk with the given content. Creates the file if it doesn't already exist.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the file, relative to the repo root.",
                },
                "content": {
                    "type": "string",
                    "description": "The full new content of the file.",
                },
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "run_bash",
        "description": (
            "Run `pytest <path>` and return combined stdout/stderr plus the exit code. "
            "This is the ONLY command this tool runs -- it is not a general shell, so "
            "don't try to use it for anything other than running tests."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": (
                        "File or directory to pass to pytest, e.g. "
                        "'demo-repo/tests/test_weather_client.py' or 'demo-repo/tests'."
                    ),
                },
            },
            "required": ["path"],
        },
    },
    {
        "name": "git_commit",
        "description": "Stage the given file(s) and create a git commit with the given message.",
        "input_schema": {
            "type": "object",
            "properties": {
                "paths": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Paths to stage, relative to the repo root.",
                },
                "message": {
                    "type": "string",
                    "description": "Commit message.",
                },
            },
            "required": ["paths", "message"],
        },
    },
]


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------

class ToolError(Exception):
    """Raised when a tool call can't be carried out safely or successfully."""


def _resolve(repo_root: Path, path: str) -> Path:
    """Resolve `path` under repo_root, refusing anything that would escape it."""
    root = repo_root.resolve()
    candidate = (root / path).resolve()
    if candidate != root and root not in candidate.parents:
        raise ToolError(f"path '{path}' escapes the repo root")
    return candidate


def read_file(repo_root: Path, path: str) -> str:
    target = _resolve(repo_root, path)
    if not target.is_file():
        raise ToolError(f"no such file: {path}")
    return target.read_text(encoding="utf-8")


def write_file(repo_root: Path, path: str, content: str) -> str:
    target = _resolve(repo_root, path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return f"wrote {len(content)} bytes to {path}"


def run_bash(repo_root: Path, path: str) -> Dict[str, Any]:
    """Run `pytest <path>` inside repo_root.

    `path` is passed as a single argv element to a fixed argv list -- never
    interpolated into a shell string -- so this can't be used to inject
    arbitrary shell commands even though the model chooses `path`.
    """
    target = _resolve(repo_root, path)
    if not target.exists():
        raise ToolError(f"no such path: {path}")

    result = subprocess.run(
        ["pytest", str(target), "-q"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        timeout=120,
    )
    return {
        "exit_code": result.returncode,
        "stdout": result.stdout[-8000:],
        "stderr": result.stderr[-4000:],
        "passed": result.returncode == 0,
    }


def git_commit(repo_root: Path, paths: List[str], message: str) -> Dict[str, Any]:
    root = repo_root.resolve()
    resolved = [str(_resolve(repo_root, p).relative_to(root)) for p in paths]

    add = subprocess.run(
        ["git", "add", *resolved], cwd=repo_root, capture_output=True, text=True
    )
    if add.returncode != 0:
        raise ToolError(f"git add failed: {add.stderr.strip()}")

    commit = subprocess.run(
        ["git", "commit", "-m", message], cwd=repo_root, capture_output=True, text=True
    )
    return {
        "exit_code": commit.returncode,
        "stdout": commit.stdout,
        "stderr": commit.stderr,
    }


HANDLERS = {
    "read_file": read_file,
    "write_file": write_file,
    "run_bash": run_bash,
    "git_commit": git_commit,
}


def dispatch(repo_root: Path, name: str, tool_input: Dict[str, Any]) -> Any:
    """Call the handler for `name` with `tool_input`, scoped to repo_root."""
    if name not in HANDLERS:
        raise ToolError(f"unknown tool: {name}")
    return HANDLERS[name](repo_root, **tool_input)