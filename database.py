# -*- coding: utf-8 -*-
"""
database.py — SQLite metadata registry for pg_user_api
=======================================================
Stores the database inventory (env / dbname / hostname / port / active)
and an operations audit log.

Schema
------
  db_registry   — known PostgreSQL databases per environment
  audit_log     — timestamped record of every API action taken

Compatible with Python 3.8+
"""

import sqlite3
import logging

DB_PATH = "pg_registry.db"   # path to the SQLite file

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# Initialise schema
# ──────────────────────────────────────────────────────────────────────────────

def init_db():
    """
    Create tables if they do not already exist.
    Call once at startup via seed_db.py.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS db_registry (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            env         TEXT    NOT NULL,
            db_name     TEXT    NOT NULL,
            hostname    TEXT    NOT NULL,
            port        INTEGER NOT NULL DEFAULT 5432,
            active      INTEGER NOT NULL DEFAULT 1,
            notes       TEXT,
            created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
            UNIQUE(env, db_name)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            env          TEXT,
            db_name      TEXT,
            pg_username  TEXT,
            operation    TEXT,
            status       TEXT,
            performed_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)

    conn.commit()
    conn.close()
    logger.info("SQLite schema initialised at %s", DB_PATH)


# ──────────────────────────────────────────────────────────────────────────────
# Registry queries
# ──────────────────────────────────────────────────────────────────────────────

def get_db_registry(env, db_name):
    """
    Return the registry row for (env, db_name) if it is active.
    Returns a dict with keys: env, db_name, hostname, port, active, notes
    or None if not found / inactive.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT env, db_name, hostname, port, active, notes
        FROM   db_registry
        WHERE  env = ?
          AND  db_name = ?
          AND  active = 1
    """, (env, db_name))
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None


def list_all_registry():
    """Return all rows in the registry (active and inactive)."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, env, db_name, hostname, port, active, notes, created_at
        FROM   db_registry
        ORDER  BY env, db_name
    """)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


# ──────────────────────────────────────────────────────────────────────────────
# Audit log
# ──────────────────────────────────────────────────────────────────────────────

def log_operation(env, db_name, pg_username, operation, status):
    """Insert a row into the audit_log table."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO audit_log (env, db_name, pg_username, operation, status)
            VALUES (?, ?, ?, ?, ?)
        """, (env, db_name, pg_username, operation, status))
        conn.commit()
        conn.close()
    except Exception as exc:
        logger.warning("audit_log insert failed: %s", exc)
