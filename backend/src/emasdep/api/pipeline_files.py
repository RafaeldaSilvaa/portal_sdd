from __future__ import annotations

import io
import json
import zipfile
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import Session
    from .models.pipeline import PipelineRun


@dataclass
class FileEntry:
    name: str
    path: str
    type: str  # "file" or "directory"
    children: list[FileEntry] = field(default_factory=list)
    size: int = 0


def _build_file_tree(run: PipelineRun) -> list[FileEntry]:
    """ build file tree.

Args:
    run: Descrição do parâmetro run.

Retorna:
    Descrição do valor retornado."""
    files: list[FileEntry] = []

    if run.spec_json:
        try:
            spec = json.loads(run.spec_json)
            content = json.dumps(spec, indent=2)
            files.append(FileEntry(name="spec.json", path="spec.json", type="file", size=len(content)))
        except json.JSONDecodeError:
            files.append(FileEntry(name="spec.json", path="spec.json", type="file", size=len(run.spec_json)))

    if run.sdd_text:
        files.append(FileEntry(name="sdd.md", path="sdd.md", type="file", size=len(run.sdd_text)))

    children: list[FileEntry] = []

    if run.test_suite:
        children.append(FileEntry(name="test_suite.py", path="tests/test_suite.py", type="file", size=len(run.test_suite)))

    if run.code_artifacts:
        try:
            artifacts = json.loads(run.code_artifacts)
            for fname, code in artifacts.items():
                children.append(FileEntry(name=fname, path=f"src/{fname}", type="file", size=len(code)))
        except (json.JSONDecodeError, AttributeError):
            pass

    if children:
        files.append(FileEntry(name="tests", path="tests", type="directory", children=[c for c in children if c.path.startswith("tests/")]))
        files.append(FileEntry(name="src", path="src", type="directory", children=[c for c in children if c.path.startswith("src/")]))

    return files


def _find_file(run: PipelineRun, path: str) -> str | None:
    """ find file.

Args:
    run: Descrição do parâmetro run.
    path: Descrição do parâmetro path.

Retorna:
    Descrição do valor retornado."""
    if path == "spec.json" and run.spec_json:
        try:
            spec = json.loads(run.spec_json)
            return json.dumps(spec, indent=2)
        except json.JSONDecodeError:
            return run.spec_json
    if path == "sdd.md" and run.sdd_text:
        return run.sdd_text
    if path == "tests/test_suite.py" and run.test_suite:
        return run.test_suite
    if path.startswith("src/") and run.code_artifacts:
        try:
            artifacts = json.loads(run.code_artifacts)
            fname = path.split("/", 1)[1]
            return artifacts.get(fname)
        except (json.JSONDecodeError, ValueError):
            pass
    return None


def list_files(correlation_id: str, db: Session) -> list[FileEntry]:
    """list files.

Args:
    correlation_id: Descrição do parâmetro correlation_id.
    db: Descrição do parâmetro db.

Retorna:
    Descrição do valor retornado."""
    from .models.pipeline import PipelineRun
    run = db.query(PipelineRun).filter_by(correlation_id=correlation_id).first()
    if not run:
        return []
    return _build_file_tree(run)


def get_file_content(correlation_id: str, path: str, db: Session) -> str | None:
    """get file content.

Args:
    correlation_id: Descrição do parâmetro correlation_id.
    path: Descrição do parâmetro path.
    db: Descrição do parâmetro db.

Retorna:
    Descrição do valor retornado."""
    from .models.pipeline import PipelineRun
    run = db.query(PipelineRun).filter_by(correlation_id=correlation_id).first()
    if not run:
        return None
    return _find_file(run, path)


def build_zip(correlation_id: str, db: Session) -> bytes | None:
    """build zip.

Args:
    correlation_id: Descrição do parâmetro correlation_id.
    db: Descrição do parâmetro db.

Retorna:
    Descrição do valor retornado."""
    from .models.pipeline import PipelineRun
    run = db.query(PipelineRun).filter_by(correlation_id=correlation_id).first()
    if not run:
        return None

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        entries: list[tuple[str, str | None]] = [
            ("spec.json", run.spec_json),
            ("sdd.md", run.sdd_text),
            ("tests/test_suite.py", run.test_suite),
        ]
        if run.code_artifacts:
            try:
                artifacts = json.loads(run.code_artifacts)
                for fname, code in artifacts.items():
                    entries.append((f"src/{fname}", code))
            except (json.JSONDecodeError, AttributeError):
                pass
        for path, content in entries:
            if content:
                zf.writestr(path, content)
    buf.seek(0)
    return buf.getvalue()
