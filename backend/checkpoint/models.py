"""Pydantic models for Waypoint's durable run state.

This is the on-disk shape of a migration run: which files need
migrating, what's happened to each one so far, and enough metadata to
resume a killed process without redoing finished work.
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    FAILED = "failed"


class RunStatus(str, Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    PAUSED = "paused"
    COMPLETED = "completed"
    COMPLETED_WITH_FAILURES = "completed_with_failures"


class Task(BaseModel):
    """One file that needs (or needed) migrating."""

    path: str
    status: TaskStatus = TaskStatus.PENDING
    attempts: int = 0


class TestResult(BaseModel):
    """Outcome of the pytest run backing a checkpoint."""

    passed: bool
    summary: str = ""  # last non-empty line of pytest output, trimmed


class Checkpoint(BaseModel):
    """Durable record of one file having gone through the migration loop."""

    file: str
    git_commit_sha: Optional[str] = None
    timestamp: datetime = Field(default_factory=_utcnow)
    test_result: TestResult


class RunState(BaseModel):
    """The full state of a migration run -- this is what gets persisted
    to disk after every task, and reloaded whole on resume()."""

    tasks: List[Task] = Field(default_factory=list)
    current_index: int = 0
    overall_status: RunStatus = RunStatus.NOT_STARTED
    checkpoints: List[Checkpoint] = Field(default_factory=list)
    expand_context_calls: int = 0
    started_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def task_for(self, path: str) -> Optional[Task]:
        return next((t for t in self.tasks if t.path == path), None)

    def pending_tasks(self) -> List[Task]:
        return [t for t in self.tasks if t.status == TaskStatus.PENDING]

    def done_tasks(self) -> List[Task]:
        return [t for t in self.tasks if t.status == TaskStatus.DONE]

    def failed_tasks(self) -> List[Task]:
        return [t for t in self.tasks if t.status == TaskStatus.FAILED]