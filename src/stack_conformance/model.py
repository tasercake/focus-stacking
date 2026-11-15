"""Target-independent conformance records."""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable


@dataclass(frozen=True)
class Case:
    id: str
    suite: str
    run: Callable
    description: str = ""


@dataclass
class ProcessResult:
    command: list[str]
    returncode: int
    stdout: str
    stderr: str
    duration: float
    timed_out: bool = False
    output: Path | None = None
    diagnostics: dict = field(default_factory=dict)


RunResult = ProcessResult


@dataclass
class CaseResult:
    id: str
    suite: str
    status: str
    duration: float
    error: str = ""
    notes: dict = field(default_factory=dict)
