import pytest
from emasdep.healing.engine import HealingEngine
from emasdep.healing.snapshot import SnapshotManager
from emasdep.core.types import CodePatchSnapshot


class TestSnapshotManager:
    @pytest.fixture
    def manager(self, tmp_path):
        return SnapshotManager(str(tmp_path / "snapshots"))

    def test_save_and_restore_snapshot(self, manager):
        snapshot = CodePatchSnapshot.create(
            filepath="test.py",
            contents="print('hello')",
            crash_log="test error",
        )

        saved_path = manager.save(snapshot)
        assert saved_path.exists()

        restored = manager.restore(snapshot)
        assert restored == "print('hello')"

    def test_list_snapshots_returns_saved_ones(self, manager):
        s1 = CodePatchSnapshot.create(filepath="a.py", contents="a", crash_log="")
        s2 = CodePatchSnapshot.create(filepath="b.py", contents="b", crash_log="")

        manager.save(s1)
        manager.save(s2)

        snapshots = manager.list_snapshots()
        assert len(snapshots) >= 2

    def test_purge_removes_snapshot(self, manager):
        snapshot = CodePatchSnapshot.create(filepath="x.py", contents="x", crash_log="")
        manager.save(snapshot)
        assert manager.purge(snapshot.state_id) is True
        assert manager.purge("nonexistent") is False


class TestHealingEngine:
    @pytest.fixture
    def engine(self, tmp_path):
        snap_mgr = SnapshotManager(str(tmp_path / "snapshots"))
        return HealingEngine(max_attempts=2, snapshot_manager=snap_mgr)

    def test_rollback_returns_original_content(self, engine):
        snapshot = CodePatchSnapshot.create(
            filepath="test.py",
            contents="original code",
            crash_log="error",
        )
        restored = engine.rollback(snapshot)
        assert restored == "original code"
