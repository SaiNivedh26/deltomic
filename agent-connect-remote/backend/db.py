from __future__ import annotations

import logging
from contextlib import contextmanager
from pathlib import Path

import psycopg2
from psycopg2.extras import RealDictCursor

from backend.config import COCKROACH_CONNECTION_STRING

logger = logging.getLogger(__name__)


def get_connection():
    return psycopg2.connect(COCKROACH_CONNECTION_STRING)


@contextmanager
def get_cursor():
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def run_migrations():
    migration_dir = Path(__file__).parent.parent / "migrations"
    migration_files = sorted(migration_dir.glob("*.sql"))

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            for migration_file in migration_files:
                sql = migration_file.read_text()
                cur.execute(sql)
                logger.info(f"Applied migration: {migration_file.name}")
        conn.commit()
        logger.info("All migrations applied successfully")
    except Exception as e:
        conn.rollback()
        logger.error(f"Migration failed: {e}")
        raise
    finally:
        conn.close()
