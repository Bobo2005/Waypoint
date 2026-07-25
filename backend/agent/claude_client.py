"""Thin wrapper around the `anthropic` Python SDK, pointed at Paritok.

Paritok runs as a local reverse proxy in front of the real Anthropic API:
your agent's traffic goes agent -> Paritok (compresses tool outputs / file
contents / history) -> api.anthropic.com. Pointing at it is just a base_url
change, driven entirely by the ANTHROPIC_BASE_URL environment variable so
nothing here has to know Paritok exists.

    export ANTHROPIC_BASE_URL=http://127.0.0.1:8080   # paritok up's default
    export ANTHROPIC_API_KEY=sk-ant-...                # still required --
                                                         # Paritok forwards it,
                                                         # it doesn't supply one
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
load_dotenv()  # reads .env in the current working directory (or a parent) into os.environ

import anthropic

DEFAULT_MODEL = os.environ.get("WAYPOINT_MODEL", "claude-sonnet-4-6")
DEFAULT_MAX_TOKENS = int(os.environ.get("WAYPOINT_MAX_TOKENS", "4096"))


def get_client() -> anthropic.Anthropic:
    """Build an Anthropic client honoring ANTHROPIC_BASE_URL if it's set.

    The SDK already reads ANTHROPIC_API_KEY from the environment on its
    own; the only thing we add here is base_url, since that's what routes
    requests through Paritok instead of straight to Anthropic.
    """
    base_url = os.environ.get("ANTHROPIC_BASE_URL")
    kwargs: Dict[str, Any] = {}
    if base_url:
        kwargs["base_url"] = base_url
    return anthropic.Anthropic(**kwargs)


def call_claude(
    client: anthropic.Anthropic,
    *,
    system: str,
    messages: List[Dict[str, Any]],
    tools: List[Dict[str, Any]],
    model: str = DEFAULT_MODEL,
    max_tokens: int = DEFAULT_MAX_TOKENS,
) -> Any:
    """Single non-streaming call to the Messages API with tools attached."""
    return client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=messages,
        tools=tools,
    )