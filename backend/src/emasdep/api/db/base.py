import logging
import os
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

logger = logging.getLogger("emasdep.db")


class Base(DeclarativeBase):
    pass


def get_database_url() -> str:
    """get database url.

Retorna:
    Descrição do valor retornado."""
    url = os.getenv("EMASDEP_DATABASE_URL")
    if url:
        return url
    raise RuntimeError(
        "EMASDEP_DATABASE_URL environment variable required. "
        "In Docker: postgresql://emasdep:emasdep@db:5432/emasdep"
    )


def _make_engine(url: str | None = None) -> Engine:
    """ make engine.

Args:
    url: Descrição do parâmetro url.

Retorna:
    Descrição do valor retornado."""
    url = url or get_database_url()
    return create_engine(
        url,
        echo=os.getenv("EMASDEP_DB_ECHO", "false").lower() == "true",
        connect_args=(
            {"check_same_thread": False}
            if url.startswith("sqlite")
            else {}
        ),
        pool_pre_ping=True,
    )


def _make_session(engine: Engine | None = None) -> sessionmaker:
    """ make session.

Args:
    engine: Descrição do parâmetro engine.

Retorna:
    Descrição do valor retornado."""
    return sessionmaker(
        bind=engine or _make_engine(),
        autocommit=False,
        autoflush=False,
    )


engine = None
SessionLocal = None


def ensure_engine() -> Engine:
    """ensure engine.

Retorna:
    Descrição do valor retornado."""
    global engine, SessionLocal
    if engine is None:
        engine = _make_engine()
        SessionLocal = _make_session(engine)
    return engine


def migrate_schema() -> None:
    """migrate schema.

Retorna:
    Descrição do valor retornado."""
    url = get_database_url()
    is_sqlite = url.startswith("sqlite")
    eng = ensure_engine()

    if is_sqlite:
        migrations = [
            "ALTER TABLE pipeline_runs ADD COLUMN is_cancelled INTEGER DEFAULT 0",
            "ALTER TABLE pipeline_runs ADD COLUMN interaction_pending TEXT",
            "ALTER TABLE pipeline_runs ADD COLUMN code_artifacts TEXT",
        ]
    else:
        migrations = [
            "ALTER TABLE pipeline_runs ADD COLUMN IF NOT EXISTS is_cancelled BOOLEAN DEFAULT FALSE",
            "ALTER TABLE pipeline_runs ADD COLUMN IF NOT EXISTS interaction_pending TEXT",
            "ALTER TABLE pipeline_runs ADD COLUMN IF NOT EXISTS code_artifacts TEXT",
            "ALTER TABLE pipeline_runs ALTER COLUMN is_converged TYPE BOOLEAN USING is_converged::BOOLEAN",
            "ALTER TABLE pipeline_runs ALTER COLUMN is_cancelled TYPE BOOLEAN USING is_cancelled::BOOLEAN",
        ]

    for stmt in migrations:
        try:
            with eng.connect() as conn:
                conn.execute(text(stmt))
                conn.commit()
            col = stmt.split("ADD COLUMN")[1].split()[0] if "ADD COLUMN" in stmt else stmt[:40]
            logger.info("Migration applied: %s", col)
        except Exception:
            pass


def get_db():
    """get db.

Retorna:
    None"""
    db = SessionLocal() if SessionLocal else _make_session(ensure_engine())()
    try:
        yield db
    finally:
        db.close()
