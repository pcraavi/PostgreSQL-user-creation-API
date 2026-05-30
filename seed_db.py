#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
seed_db.py — Initialise the SQLite registry and insert sample records
======================================================================
Run this ONCE before starting the API for the first time.

Usage:
    python seed_db.py

What it does:
  1. Creates pg_registry.db (the SQLite file)
  2. Creates tables: db_registry, audit_log
  3. Inserts sample rows across dev / qa / uat / prod environments

Sample data uses generic, fictional hostnames — replace with your real
PostgreSQL hostnames before going live.

Columns in db_registry:
  env       — environment label:  dev | qa | uat | prod
  db_name   — PostgreSQL database name
  hostname  — FQDN or IP of the PostgreSQL host
  port      — PostgreSQL port (default 5432)
  active    — 1 = enabled, 0 = disabled (API will reject inactive entries)
  notes     — free-text description
"""

import sqlite3
from database import init_db, DB_PATH

# ──────────────────────────────────────────────────────────────────────────────
# Sample seed data
# Replace these with your real database inventory.
# ──────────────────────────────────────────────────────────────────────────────
SAMPLE_RECORDS = [
    # dev environment
    ("dev", "app_dev_main",    "pg-dev-01.internal.example.com",  5432, 1, "Main dev application database"),
    ("dev", "app_dev_reports", "pg-dev-01.internal.example.com",  5432, 1, "Dev reporting database"),
    ("dev", "app_dev_archive", "pg-dev-02.internal.example.com",  5432, 0, "Archived dev DB — inactive"),

    # qa environment
    ("qa",  "app_qa_reports",  "pg-qa-01.internal.example.com",   5432, 1, "QA reporting database"),
    ("qa",  "app_qa_inttest",  "pg-qa-02.internal.example.com",   5432, 1, "Integration test database"),

    # uat environment
    ("uat", "app_uat_main",    "pg-uat-01.internal.example.com",  5432, 1, "UAT main database"),
    ("uat", "app_uat_reports", "pg-uat-01.internal.example.com",  5432, 1, "UAT reporting database"),

    # prod environment
    ("prod", "app_prod_main",    "pg-prod-01.internal.example.com", 5432, 1, "Production main database"),
    ("prod", "app_prod_reports", "pg-prod-02.internal.example.com", 5432, 1, "Production read-replica for reports"),
    ("prod", "app_prod_archive", "pg-prod-03.internal.example.com", 5432, 0, "Production archive — inactive"),
]


def seed():
    # Step 1 — create tables
    init_db()
    print(f"[OK] Schema created/verified in {DB_PATH}")

    # Step 2 — insert sample records (skip duplicates with INSERT OR IGNORE)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    inserted = 0
    skipped  = 0

    for env, db_name, hostname, port, active, notes in SAMPLE_RECORDS:
        try:
            cursor.execute("""
                INSERT OR IGNORE INTO db_registry
                    (env, db_name, hostname, port, active, notes)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (env, db_name, hostname, port, active, notes))
            if cursor.rowcount > 0:
                inserted += 1
                print(f"  + inserted  [{env:4}]  {db_name}")
            else:
                skipped += 1
                print(f"  ~ skipped   [{env:4}]  {db_name}  (already exists)")
        except Exception as exc:
            print(f"  ! error     [{env:4}]  {db_name}: {exc}")

    conn.commit()
    conn.close()

    print(f"\n[DONE] {inserted} inserted, {skipped} skipped.")
    print(f"       Registry lives at: {DB_PATH}")
    print()
    print("Next steps:")
    print("  1. Edit SAMPLE_RECORDS in this file with your real hostnames.")
    print("  2. Set API_USERNAME / API_PASSWORD in app.py (or via env vars).")
    print("  3. Start the API:  python app.py")
    print()
    print("Quick test (replace credentials):")
    print("  curl -u pgadmin:Ch@ngeMe2024! http://localhost:5000/api/v1/registry")


if __name__ == "__main__":
    seed()
