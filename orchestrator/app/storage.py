from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Optional

# LangGraph checkpointers (names vary by version). We try imports in a safe order.
SqliteSaver = None
PostgresSaver = None

try:
    from langgraph.checkpoint.sqlite import SqliteSaver as _SqliteSaver  # type: ignore
    SqliteSaver = _SqliteSaver
except Exception:
    SqliteSaver = None

try:
    from langgraph.checkpoint.postgres import PostgresSaver as _PostgresSaver  # type: ignore
    PostgresSaver = _PostgresSaver
except Exception:
    PostgresSaver = None

@contextmanager
def build_checkpointer():
    """Return a LangGraph-compatible checkpointer.

    Priority:
      1) Postgres if DATABASE_URL is set and PostgresSaver is available
      2) SQLite file otherwise (requires SqliteSaver)

    Notes:
      - This is written defensively across LangGraph versions.
      - If neither saver is available, yields None (graph will run without persistence).
    """
    db_url = os.getenv("DATABASE_URL", "").strip()
    if db_url and PostgresSaver is not None:
        # PostgresSaver typically needs a psycopg connection string
        saver = PostgresSaver.from_conn_string(db_url)  # type: ignore[attr-defined]
        try:
            yield saver
        finally:
            try:
                saver.close()  # type: ignore[attr-defined]
            except Exception:
                pass
        return

    # Default to sqlite
    sqlite_path = os.getenv("SQLITE_CHECKPOINT_PATH", "/app/out/checkpoints.sqlite")
    if SqliteSaver is not None:
        saver = SqliteSaver.from_conn_string(f"sqlite:///{sqlite_path}")  # type: ignore[attr-defined]
        try:
            yield saver
        finally:
            try:
                saver.close()  # type: ignore[attr-defined]
            except Exception:
                pass
        return

    yield None
