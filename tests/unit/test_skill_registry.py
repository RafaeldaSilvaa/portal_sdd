import pytest
from emasdep.skills.registry import SkillRegistry


class TestSkillRegistry:
    @pytest.fixture
    def registry(self, tmp_path):
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        (skills_dir / "python-protocols.md").write_text(
            "# Python Protocols\nContent here"
        )
        return SkillRegistry(str(skills_dir))

    def test_discover_finds_all_skills(self, registry):
        skills = registry.discover()
        assert len(skills) == 1
        assert skills[0].name == "python-protocols"

    def test_get_by_name_returns_skill(self, registry):
        skill = registry.get("python-protocols")
        assert skill is not None
        assert "Python Protocols" in skill.content

    def test_get_nonexistent_returns_none(self, registry):
        skill = registry.get("nonexistent")
        assert skill is None

    def test_register_creates_new_skill(self, registry):
        skill = registry.register("new-skill", "# New Skill\nContent")
        assert skill.name == "new-skill"
        assert (registry._path / "new-skill.md").exists()

    def test_find_by_tags_returns_matching_skills(self, registry):
        registry.register("mutation-testing", "# Mutation Testing")
        matches = registry.find_by_tags(["mutation"])
        assert len(matches) >= 1
        assert any(m.name == "mutation-testing" for m in matches)

    def test_empty_registry_returns_empty(self, tmp_path):
        registry = SkillRegistry(str(tmp_path / "empty"))
        assert registry.discover() == []
