"""Point-in-time state snapshots for rollback capability."""

from __future__ import annotations

from pathlib import Path

from ..core.types import CodePatchSnapshot


class SnapshotManager:
    def __init__(self, storage_path: str = "./.emasdep_snapshots") -> None:
        """  init  .

Args:
    storage_path: Descrição do parâmetro storage_path.

Retorna:
    Descrição do valor retornado."""
        self._path = Path(storage_path)
        self._path.mkdir(parents=True, exist_ok=True)

    def save(self, snapshot: CodePatchSnapshot) -> Path:
        """save.

Args:
    snapshot: Descrição do parâmetro snapshot.

Retorna:
    Descrição do valor retornado."""
        snap_dir = self._path / snapshot.state_id
        snap_dir.mkdir(parents=True, exist_ok=True)

        content_path = snap_dir / "original_content.txt"
        content_path.write_text(snapshot.original_contents, encoding="utf-8")

        log_path = snap_dir / "crash_log.txt"
        log_path.write_text(snapshot.crash_log, encoding="utf-8")

        meta_path = snap_dir / "metadata.txt"
        meta_path.write_text(
            f"state_id: {snapshot.state_id}\n"
            f"target_file: {snapshot.target_filepath}\n"
            f"created_at: {snapshot.created_at.isoformat()}\n",
            encoding="utf-8",
        )

        return snap_dir

    def restore(self, snapshot: CodePatchSnapshot) -> str:
        return snapshot.original_contents

    def list_snapshots(self) -> list[CodePatchSnapshot]:
        """list snapshots.

Retorna:
    Descrição do valor retornado."""
        if not self._path.exists():
            return []
        snapshots: list[CodePatchSnapshot] = []
        for snap_dir in self._path.iterdir():
            if not snap_dir.is_dir():
                continue
            content_file = snap_dir / "original_content.txt"
            log_file = snap_dir / "crash_log.txt"
            if content_file.exists():
                snapshots.append(
                    CodePatchSnapshot(
                        state_id=snap_dir.name,
                        target_filepath=Path(snap_dir.name),
                        original_contents=content_file.read_text(encoding="utf-8"),
                        crash_log=log_file.read_text(encoding="utf-8") if log_file.exists() else "",
                    )
                )
        return snapshots

    def purge(self, state_id: str) -> bool:
        """purge.

Args:
    state_id: Descrição do parâmetro state_id.

Retorna:
    Descrição do valor retornado."""
        snap_dir = self._path / state_id
        if snap_dir.exists():
            import shutil
            shutil.rmtree(snap_dir)
            return True
        return False
