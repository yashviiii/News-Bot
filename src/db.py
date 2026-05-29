"""SQLite connection helpers and schema initialization.

Run `python -m src.db init` to (re)create the DB from `schema.sql`. Other
modules call `connect()` to get a configured connection with foreign keys
enabled and Row factory set.
"""

from __future__ import annotations

import argparse
import logging
import sqlite3
import sys
from pathlib import Path
from typing import Iterator

from . import config


logger = logging.getLogger(__name__)


def connect(db_path: str | None = None) -> sqlite3.Connection:
    """Open a SQLite connection with the project-standard settings."""
    path = db_path or config.DB_PATH
    conn = sqlite3.connect(path, timeout=30.0, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def init_db(db_path: str | None = None, *, schema_path: Path | None = None) -> None:
    """Create tables, indexes, FTS5 table, and triggers if they do not exist."""
    schema = (schema_path or config.SCHEMA_PATH).read_text(encoding="utf-8")
    with connect(db_path) as conn:
        conn.executescript(schema)
    logger.info("Initialized DB at %s", db_path or config.DB_PATH)


def reset_db(db_path: str | None = None) -> None:
    """Delete the SQLite file (if present) and recreate the schema."""
    path = Path(db_path or config.DB_PATH)
    if path.exists():
        path.unlink()
    # WAL/SHM sidecars
    for sfx in ("-wal", "-shm"):
        sidecar = path.with_name(path.name + sfx)
        if sidecar.exists():
            sidecar.unlink()
    init_db(str(path))


def iter_rows(cursor: sqlite3.Cursor) -> Iterator[sqlite3.Row]:
    """Yield Row objects from a cursor; trivial helper for readability."""
    for row in cursor:
        yield row


def _main(argv: list[str]) -> int:
    config.configure_logging()
    parser = argparse.ArgumentParser(prog="python -m src.db")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init", help="Create the schema if not already present")
    sub.add_parser("reset", help="Delete DB file and recreate from schema.sql")

    args = parser.parse_args(argv)
    if args.cmd == "init":
        init_db()
    elif args.cmd == "reset":
        reset_db()
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))
