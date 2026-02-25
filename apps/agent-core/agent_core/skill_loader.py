from __future__ import annotations

"""Skill loader for Markdown skills with YAML frontmatter metadata."""

import re
from pathlib import Path

import yaml

from .models import SkillDefinition


class SkillLoaderError(RuntimeError):
    pass


class SkillLoader:
    """Discovers and validates all `SKILL.md` files under a root folder."""

    def __init__(self, skills_root: Path) -> None:
        self.skills_root = skills_root

    def load_skills(self) -> dict[str, SkillDefinition]:
        """Load all skills and index them by unique skill name."""
        if not self.skills_root.exists():
            raise SkillLoaderError(f"Skills directory not found: {self.skills_root}")

        skills: dict[str, SkillDefinition] = {}
        for skill_file in sorted(self.skills_root.rglob("SKILL.md")):
            skill = self._load_single(skill_file)
            if skill.name in skills:
                raise SkillLoaderError(
                    f"Duplicate skill name '{skill.name}' in '{skill_file}' and '{skills[skill.name].path}'"
                )
            skills[skill.name] = skill

        if not skills:
            raise SkillLoaderError(f"No SKILL.md files found under: {self.skills_root}")
        return skills

    def _load_single(self, path: Path) -> SkillDefinition:
        """Parse one skill file and return normalized metadata + body instructions."""
        raw = path.read_text(encoding="utf-8")
        frontmatter, body = self._split_frontmatter(raw, path)
        metadata = yaml.safe_load(frontmatter) or {}

        name = metadata.get("name")
        description = metadata.get("description")
        if not isinstance(name, str) or not name.strip():
            raise SkillLoaderError(f"Missing non-empty 'name' frontmatter in: {path}")
        if not isinstance(description, str) or not description.strip():
            raise SkillLoaderError(f"Missing non-empty 'description' frontmatter in: {path}")
        if not body.strip():
            raise SkillLoaderError(f"Empty skill body in: {path}")

        return SkillDefinition(
            name=name.strip(),
            description=description.strip(),
            instructions=body.strip(),
            path=path,
        )

    @staticmethod
    def _split_frontmatter(markdown: str, path: Path) -> tuple[str, str]:
        """Split Markdown into (YAML frontmatter, body) using strict delimiters."""
        normalized = markdown.replace("\r\n", "\n")
        pattern = r"^---\n(.*?)\n---\n?(.*)$"
        match = re.match(pattern, normalized, flags=re.DOTALL)
        if not match:
            raise SkillLoaderError(f"Invalid frontmatter format in: {path}")
        return match.group(1), match.group(2)
