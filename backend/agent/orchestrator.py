"""Step-one orchestrator for Waypoint.

Just `migrate_one_file(path)`: read the file, ask Claude (routed through
Paritok) to migrate it, write the result, run its tests, and report
pass/fail. No planning across multiple files and no checkpointing yet --
that's the next step, once this loop is solid on its own.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from .claude_client import call_claude, get_client
from .prompts import SYSTEM_PROMPT, build_user_prompt
from .tools import TOOLS, ToolError, dispatch

# backend/agent/orchestrator.py -> backend/agent -> backend -> repo root
REPO_ROOT = Path(__file__).resolve().parents[2]
MAX_TURNS = 12


def _tool_result_block(tool_use_id: str, content: Any, is_error: bool = False) -> Dict[str, Any]:
    return {
        "type": "tool_result",
        "tool_use_id": tool_use_id,
        "content": content if isinstance(content, str) else json.dumps(content),
        "is_error": is_error,
    }


def migrate_one_file(path: str, repo_root: Optional[Path] = None) -> bool:
    """Run the migration tool-loop for a single file.

    Returns True if the last `run_bash` (pytest) call the agent made
    during this run exited 0, False otherwise -- including if the agent
    never got around to running tests, or the loop hit MAX_TURNS first.
    """
    repo_root = repo_root or REPO_ROOT
    client = get_client()

    messages: List[Dict[str, Any]] = [
        {"role": "user", "content": build_user_prompt(path)}
    ]
    tests_passed = False

    for _ in range(MAX_TURNS):
        response = call_claude(
            client,
            system=SYSTEM_PROMPT,
            messages=messages,
            tools=TOOLS,
        )
        messages.append({"role": "assistant", "content": response.content})

        tool_calls = [block for block in response.content if block.type == "tool_use"]
        if not tool_calls:
            # Plain text with no further tool calls -- the agent is done.
            break

        result_blocks = []
        for call in tool_calls:
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

    return tests_passed


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("usage: python -m agent.orchestrator <path-to-file>")
        raise SystemExit(1)

    ok = migrate_one_file(sys.argv[1])
    print("tests passed" if ok else "tests did NOT pass")
    raise SystemExit(0 if ok else 1)