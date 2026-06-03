import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Optional

from .models import Post, RunSummary, UpsertCounts


class Store:
    def __init__(self, path):
        self.path = Path(path)

    def connect(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.path))
        conn.row_factory = sqlite3.Row
        return conn

    def init_schema(self) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS posts (
                    id TEXT PRIMARY KEY,
                    author_id TEXT,
                    author_name TEXT,
                    created_at TEXT,
                    text TEXT NOT NULL,
                    html TEXT NOT NULL,
                    url TEXT,
                    reply_count INTEGER,
                    retweet_count INTEGER,
                    fav_count INTEGER,
                    raw_json TEXT NOT NULL,
                    collected_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS collection_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    started_at TEXT NOT NULL,
                    finished_at TEXT,
                    pages_requested INTEGER NOT NULL,
                    pages_fetched INTEGER NOT NULL,
                    inserted_count INTEGER NOT NULL,
                    updated_count INTEGER NOT NULL,
                    duplicate_count INTEGER NOT NULL,
                    error TEXT
                )
                """
            )

    def upsert_posts(self, posts: Iterable[Post]) -> UpsertCounts:
        inserted = updated = duplicate = 0
        now = datetime.now(timezone.utc).isoformat()
        with self.connect() as conn:
            for post in posts:
                existing = conn.execute(
                    "SELECT raw_json FROM posts WHERE id = ?", (post.id,)
                ).fetchone()
                if existing is None:
                    conn.execute(
                        """
                        INSERT INTO posts (
                            id, author_id, author_name, created_at, text, html, url,
                            reply_count, retweet_count, fav_count, raw_json,
                            collected_at, updated_at
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            post.id,
                            post.author_id,
                            post.author_name,
                            post.created_at,
                            post.text,
                            post.html,
                            post.url,
                            post.reply_count,
                            post.retweet_count,
                            post.fav_count,
                            post.raw_json,
                            now,
                            now,
                        ),
                    )
                    inserted += 1
                elif existing["raw_json"] == post.raw_json:
                    duplicate += 1
                else:
                    conn.execute(
                        """
                        UPDATE posts
                        SET author_id = ?, author_name = ?, created_at = ?, text = ?,
                            html = ?, url = ?, reply_count = ?, retweet_count = ?,
                            fav_count = ?, raw_json = ?, updated_at = ?
                        WHERE id = ?
                        """,
                        (
                            post.author_id,
                            post.author_name,
                            post.created_at,
                            post.text,
                            post.html,
                            post.url,
                            post.reply_count,
                            post.retweet_count,
                            post.fav_count,
                            post.raw_json,
                            now,
                            post.id,
                        ),
                    )
                    updated += 1
        return UpsertCounts(inserted, updated, duplicate)

    def list_posts(self, limit: Optional[int] = None) -> List[Post]:
        sql = "SELECT * FROM posts ORDER BY id ASC"
        params = ()
        if limit is not None:
            sql += " LIMIT ?"
            params = (limit,)
        with self.connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [
            Post(
                id=row["id"],
                author_id=row["author_id"],
                author_name=row["author_name"],
                created_at=row["created_at"],
                text=row["text"],
                html=row["html"],
                url=row["url"],
                reply_count=row["reply_count"],
                retweet_count=row["retweet_count"],
                fav_count=row["fav_count"],
                raw_json=row["raw_json"],
            )
            for row in rows
        ]

    def record_run(self, summary: RunSummary) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO collection_runs (
                    started_at, finished_at, pages_requested, pages_fetched,
                    inserted_count, updated_count, duplicate_count, error
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    now,
                    now,
                    summary.pages_requested,
                    summary.pages_fetched,
                    summary.inserted_count,
                    summary.updated_count,
                    summary.duplicate_count,
                    summary.error,
                ),
            )
