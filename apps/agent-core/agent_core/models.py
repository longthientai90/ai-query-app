from __future__ import annotations

"""Data models shared across skill loading and runtime orchestration."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class SkillDefinition:
    """Immutable representation of one discovered skill."""

    name: str
    description: str
    instructions: str
    path: Path
