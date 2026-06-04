import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Optional

from .models import Post, RunSummary, UpsertCounts
from .text import normalize_html_text


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
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS authors (
                    id TEXT PRIMARY KEY,
                    name TEXT,
                    last_seen_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS post_quotes (
                    post_id TEXT PRIMARY KEY,
                    quoted_post_id TEXT,
                    quoted_author_id TEXT,
                    quoted_author_name TEXT,
                    quoted_text TEXT NOT NULL,
                    quoted_url TEXT,
                    raw_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    period_key TEXT NOT NULL,
                    period_label TEXT NOT NULL,
                    start_local TEXT NOT NULL,
                    end_local TEXT NOT NULL,
                    start_utc TEXT NOT NULL,
                    end_utc TEXT NOT NULL,
                    style TEXT NOT NULL,
                    output_path TEXT NOT NULL,
                    post_count INTEGER NOT NULL,
                    author_count INTEGER NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS notifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    report_id INTEGER,
                    channel TEXT NOT NULL,
                    sent INTEGER NOT NULL,
                    message TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            self._backfill_metadata(conn)

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
                self._upsert_author(conn, post, now)
                self._upsert_quote(conn, post, now)
        return UpsertCounts(inserted, updated, duplicate)

    def _upsert_author(self, conn, post: Post, now: str) -> None:
        if not post.author_id:
            return
        conn.execute(
            """
            INSERT INTO authors (id, name, last_seen_at)
            VALUES (?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name = excluded.name,
                last_seen_at = excluded.last_seen_at
            """,
            (post.author_id, post.author_name, now),
        )

    def _upsert_quote(self, conn, post: Post, now: str) -> None:
        quoted = _quoted_status_from_raw(post.raw_json)
        if quoted is None:
            conn.execute("DELETE FROM post_quotes WHERE post_id = ?", (post.id,))
            return
        conn.execute(
            """
            INSERT INTO post_quotes (
                post_id, quoted_post_id, quoted_author_id, quoted_author_name,
                quoted_text, quoted_url, raw_json, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(post_id) DO UPDATE SET
                quoted_post_id = excluded.quoted_post_id,
                quoted_author_id = excluded.quoted_author_id,
                quoted_author_name = excluded.quoted_author_name,
                quoted_text = excluded.quoted_text,
                quoted_url = excluded.quoted_url,
                raw_json = excluded.raw_json,
                updated_at = excluded.updated_at
            """,
            (
                post.id,
                quoted["id"],
                quoted["author_id"],
                quoted["author_name"],
                quoted["text"],
                quoted["url"],
                quoted["raw_json"],
                now,
            ),
        )

    def _backfill_metadata(self, conn) -> None:
        now = datetime.now(timezone.utc).isoformat()
        rows = conn.execute("SELECT * FROM posts").fetchall()
        for row in rows:
            post = Post(
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
            self._upsert_author(conn, post, now)
            self._upsert_quote(conn, post, now)

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

    def record_report(self, window, report, output_path, style: str) -> int:
        now = datetime.now(timezone.utc).isoformat()
        with self.connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO reports (
                    period_key, period_label, start_local, end_local, start_utc,
                    end_utc, style, output_path, post_count, author_count, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    window.key,
                    window.label,
                    window.start_local.isoformat(),
                    window.end_local.isoformat(),
                    window.start_utc.isoformat(),
                    window.end_utc.isoformat(),
                    style,
                    str(output_path),
                    report.post_count,
                    report.author_count,
                    now,
                ),
            )
            return int(cursor.lastrowid)

    def record_notification(
        self,
        report_id: Optional[int],
        channel: str,
        sent: bool,
        message: str,
    ) -> int:
        now = datetime.now(timezone.utc).isoformat()
        with self.connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO notifications (report_id, channel, sent, message, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (report_id, channel, 1 if sent else 0, message, now),
            )
            return int(cursor.lastrowid)


def _quoted_status_from_raw(raw_json: str):
    try:
        raw = json.loads(raw_json)
    except (TypeError, ValueError):
        return None
    quoted = raw.get("retweeted_status") if isinstance(raw, dict) else None
    if not isinstance(quoted, dict):
        return None
    user = quoted.get("user") if isinstance(quoted.get("user"), dict) else {}
    quoted_id = quoted.get("id")
    author_id = quoted.get("user_id") or user.get("id")
    target = quoted.get("target")
    if isinstance(target, str) and target.startswith("/"):
        url = "https://xueqiu.com{}".format(target)
    elif quoted_id and author_id:
        url = "https://xueqiu.com/{}/{}".format(author_id, quoted_id)
    else:
        url = None
    return {
        "id": str(quoted_id) if quoted_id is not None else None,
        "author_id": str(author_id) if author_id is not None else None,
        "author_name": user.get("screen_name") or user.get("name"),
        "text": normalize_html_text(
            str(quoted.get("text") or quoted.get("description") or "")
        ),
        "url": url,
        "raw_json": json.dumps(quoted, ensure_ascii=False, separators=(",", ":")),
    }
