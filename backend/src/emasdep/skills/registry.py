"""SkillOps Engine: JIT compiler of best practices."""

from __future__ import annotations

from pathlib import Path
from typing import NamedTuple


class Skill(NamedTuple):
    name: str
    content: str
    filepath: Path


class SkillRegistry:
    def __init__(self, skills_path: str = "./skills"):
        self._path = Path(skills_path)
        self._cache: dict[str, Skill] = {}

    def discover(self) -> list[Skill]:
        if not self._path.exists():
            return []
        skills: list[Skill] = []
        for f in self._path.glob("*.md"):
            content = f.read_text(encoding="utf-8")
            skill = Skill(name=f.stem, content=content, filepath=f)
            self._cache[f.stem] = skill
            skills.append(skill)
        return skills

    def find_by_tags(self, tags: list[str]) -> list[Skill]:
        results: list[Skill] = []
        for skill in self._cache.values():
            if any(tag.lower() in skill.name.lower() for tag in tags):
                results.append(skill)
        if not results:
            results = self.discover()
            results = [
                s for s in results
                if any(tag.lower() in s.name.lower() for tag in tags)
            ]
        return results

    def get(self, name: str) -> Skill | None:
        if name in self._cache:
            return self._cache[name]
        filepath = self._path / f"{name}.md"
        if filepath.exists():
            skill = Skill(name=name, content=filepath.read_text(), filepath=filepath)
            self._cache[name] = skill
            return skill
        return None

    def register(self, name: str, content: str) -> Skill:
        filepath = self._path / f"{name}.md"
        filepath.write_text(content, encoding="utf-8")
        skill = Skill(name=name, content=content, filepath=filepath)
        self._cache[name] = skill
        return skill
