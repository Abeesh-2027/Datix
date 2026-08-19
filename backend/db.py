
import os
import pickle
import logging

from sqlalchemy import create_engine, text

logger = logging.getLogger(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = None
if DATABASE_URL:
    try:
        engine = create_engine(
            DATABASE_URL,
            pool_pre_ping=True,  
            pool_size=5,
            max_overflow=5,
        )
    except Exception:
        logger.exception("Could not create database engine; persistence disabled.")
        engine = None


def init_db():
    """Create the sessions table if it doesn't exist yet. Safe to call on every boot."""
    if engine is None:
        logger.warning("DATABASE_URL not set - session data will NOT survive restarts/worker switches.")
        return
    try:
        with engine.begin() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS sessions (
                    sid TEXT PRIMARY KEY,
                    raw BYTEA,
                    clean BYTEA,
                    filtered BYTEA,
                    log JSONB,
                    chat JSONB,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
            """))
        logger.info("Database ready.")
    except Exception:
        logger.exception("Failed to initialize database table.")


def _df_to_bytes(df):
    if df is None:
        return None
    return pickle.dumps(df, protocol=pickle.HIGHEST_PROTOCOL)


def _bytes_to_df(b):
    if b is None:
        return None
    return pickle.loads(bytes(b))


def load_session(sid: str):
    """Return a state dict for this session id, or None if not found / DB unavailable."""
    if engine is None:
        return None
    try:
        with engine.begin() as conn:
            row = conn.execute(
                text("SELECT raw, clean, filtered, log, chat FROM sessions WHERE sid = :sid"),
                {"sid": sid},
            ).fetchone()
        if row is None:
            return None
        raw_b, clean_b, filtered_b, log, chat = row
        return {
            "raw": _bytes_to_df(raw_b),
            "clean": _bytes_to_df(clean_b),
            "filtered": _bytes_to_df(filtered_b),
            "log": log,
            "chat": chat or [],
        }
    except Exception:
        logger.exception("Failed to load session %s from database.", sid)
        return None


def save_session(sid: str, state: dict):
    """Upsert the given session state. Silently no-ops if the DB is unavailable."""
    if engine is None:
        return
    try:
        payload = {
            "sid": sid,
            "raw": _df_to_bytes(state.get("raw")),
            "clean": _df_to_bytes(state.get("clean")),
            "filtered": _df_to_bytes(state.get("filtered")),
            "log": _json_or_none(state.get("log")),
            "chat": _json_or_none(state.get("chat") or []),
        }
        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO sessions (sid, raw, clean, filtered, log, chat, updated_at)
                VALUES (:sid, :raw, :clean, :filtered, CAST(:log AS JSONB), CAST(:chat AS JSONB), now())
                ON CONFLICT (sid) DO UPDATE SET
                    raw = EXCLUDED.raw,
                    clean = EXCLUDED.clean,
                    filtered = EXCLUDED.filtered,
                    log = EXCLUDED.log,
                    chat = EXCLUDED.chat,
                    updated_at = now()
            """), payload)
    except Exception:
        logger.exception("Failed to save session %s to database.", sid)


def _json_or_none(value):
    import json
    if value is None:
        return None
    return json.dumps(value)


def delete_session(sid: str):
    if engine is None:
        return
    try:
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM sessions WHERE sid = :sid"), {"sid": sid})
    except Exception:
        logger.exception("Failed to delete session %s from database.", sid)
