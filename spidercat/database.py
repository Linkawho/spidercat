"""SQLite persistence layer.

Every discovered site, crawl attempt, and categorization decision is written to
SQLite immediately so progress is never lost, even if the process is killed.
"""

from __future__ import annotations

import sqlite3
import threading
from datetime import datetime, timezone
from typing import Optional

SCHEMA = """
CREATE TABLE IF NOT EXISTS sites (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    url           TEXT UNIQUE NOT NULL,
    domain        TEXT NOT NULL,
    title         TEXT,
    description   TEXT,
    category      TEXT,
    category_source TEXT,          -- 'seed' | 'ai' | 'heuristic'
    popularity    INTEGER DEFAULT 0,
    domain_age_years REAL,
    is_auto_added INTEGER DEFAULT 0,
    status        TEXT DEFAULT 'pending',  -- pending | crawled | rejected | error
    reject_reason TEXT,
    notes         TEXT,
    created_at    TEXT NOT NULL,
    updated_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS crawl_queue (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    url        TEXT UNIQUE NOT NULL,
    depth      INTEGER DEFAULT 0,
    status     TEXT DEFAULT 'queued',  -- queued | done | failed
    added_at   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS crawl_log (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    url        TEXT NOT NULL,
    event      TEXT NOT NULL,
    detail     TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_sites_category ON sites(category);
CREATE INDEX IF NOT EXISTS idx_sites_status ON sites(status);
CREATE INDEX IF NOT EXISTS idx_queue_status ON crawl_queue(status);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Database:
    """Thread-safe wrapper around a single SQLite connection."""

    def __init__(self, path: str) -> None:
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(SCHEMA)
        self._conn.commit()

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    # -- sites -------------------------------------------------------------
    def upsert_site(
        self,
        url: str,
        domain: str,
        *,
        title: Optional[str] = None,
        description: Optional[str] = None,
        category: Optional[str] = None,
        category_source: Optional[str] = None,
        popularity: int = 0,
        domain_age_years: Optional[float] = None,
        is_auto_added: int = 0,
        status: str = "pending",
        reject_reason: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> None:
        now = _now()
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO sites (
                    url, domain, title, description, category, category_source,
                    popularity, domain_age_years, is_auto_added, status,
                    reject_reason, notes, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(url) DO UPDATE SET
                    title = COALESCE(excluded.title, sites.title),
                    description = COALESCE(excluded.description, sites.description),
                    category = COALESCE(excluded.category, sites.category),
                    category_source = COALESCE(excluded.category_source, sites.category_source),
                    popularity = MAX(sites.popularity, excluded.popularity),
                    domain_age_years = COALESCE(excluded.domain_age_years, sites.domain_age_years),
                    is_auto_added = MAX(sites.is_auto_added, excluded.is_auto_added),
                    status = excluded.status,
                    reject_reason = COALESCE(excluded.reject_reason, sites.reject_reason),
                    notes = COALESCE(excluded.notes, sites.notes),
                    updated_at = excluded.updated_at
                """,
                (
                    url, domain, title, description, category, category_source,
                    popularity, domain_age_years, is_auto_added, status,
                    reject_reason, notes, now, now,
                ),
            )
            self._conn.commit()

    def get_site(self, url: str) -> Optional[sqlite3.Row]:
        with self._lock:
            return self._conn.execute(
                "SELECT * FROM sites WHERE url = ?", (url,)
            ).fetchone()

    def all_sites(self) -> list[sqlite3.Row]:
        with self._lock:
            return self._conn.execute(
                "SELECT * FROM sites ORDER BY category, title"
            ).fetchall()

    def sites_in_category(self, category: str) -> list[sqlite3.Row]:
        with self._lock:
            return self._conn.execute(
                "SELECT * FROM sites WHERE category = ? ORDER BY title",
                (category,),
            ).fetchall()

    # -- crawl queue -------------------------------------------------------
    def enqueue(self, url: str, depth: int = 0) -> None:
        now = _now()
        with self._lock:
            self._conn.execute(
                """
                INSERT OR IGNORE INTO crawl_queue (url, depth, status, added_at)
                VALUES (?, ?, 'queued', ?)
                """,
                (url, depth, now),
            )
            self._conn.commit()

    def next_queued(self) -> Optional[sqlite3.Row]:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM crawl_queue WHERE status = 'queued' ORDER BY id LIMIT 1"
            ).fetchone()
            if row:
                self._conn.execute(
                    "UPDATE crawl_queue SET status = 'done' WHERE id = ?", (row["id"],)
                )
                self._conn.commit()
            return row

    def queue_size(self) -> int:
        with self._lock:
            return self._conn.execute(
                "SELECT COUNT(*) AS c FROM crawl_queue WHERE status = 'queued'"
            ).fetchone()["c"]

    # -- log ---------------------------------------------------------------
    def log(self, url: str, event: str, detail: Optional[str] = None) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO crawl_log (url, event, detail, created_at) VALUES (?, ?, ?, ?)",
                (url, event, detail, _now()),
            )
            self._conn.commit()
