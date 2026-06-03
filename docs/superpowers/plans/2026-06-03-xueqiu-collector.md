# Xueqiu Collector Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local CLI that collects posts from the user's followed Xueqiu dynamic timeline, stores them in SQLite, and exports them as JSONL or CSV.

**Architecture:** The package is a small Python CLI with isolated modules for parsing, error classification, SQLite storage, export, browser-backed fetching, and command orchestration. Offline unit tests cover all non-network behavior; live Xueqiu login and collection are verified manually after the Playwright dependency is installed and the user logs in through the dedicated browser profile.

**Tech Stack:** Python 3.8+, argparse, sqlite3, csv, json, dataclasses, pytest, Playwright for authenticated browser profile reuse.

---

## File Structure

- Create: `.gitignore` - excludes runtime data, exported files, local env files, caches, and browser profiles.
- Create: `pyproject.toml` - package metadata, console script, Playwright dependency, pytest extra.
- Create: `README.md` - local setup and command usage.
- Create: `src/xueqiu_collector/__init__.py` - package marker and version.
- Create: `src/xueqiu_collector/models.py` - `Post`, `RunSummary`, and `UpsertCounts` dataclasses.
- Create: `src/xueqiu_collector/text.py` - HTML-to-text normalization.
- Create: `src/xueqiu_collector/errors.py` - response classification and collector exceptions.
- Create: `src/xueqiu_collector/parser.py` - timeline JSON parsing into `Post` objects.
- Create: `src/xueqiu_collector/storage.py` - SQLite schema, post upsert, listing, and run recording.
- Create: `src/xueqiu_collector/exporter.py` - JSONL and CSV export.
- Create: `src/xueqiu_collector/client.py` - Playwright-backed auth and page fetching.
- Create: `src/xueqiu_collector/collector.py` - pagination orchestration, delays, and run summaries.
- Create: `src/xueqiu_collector/cli.py` - argparse command wiring.
- Create: `tests/conftest.py` - adds `src` to `sys.path` for tests without package install.
- Create: `tests/test_cli.py` - command parser and command behavior tests.
- Create: `tests/test_parser.py` - parser, text normalization, and response classification tests.
- Create: `tests/test_storage_exporter.py` - SQLite and export tests.
- Create: `tests/test_collector.py` - pagination and run-summary tests with a fake client.
- Create: `tests/test_client.py` - Playwright missing-dependency and request URL tests without live network.

## Task 1: Project Scaffold And CLI Parser

**Files:**
- Create: `.gitignore`
- Create: `pyproject.toml`
- Create: `src/xueqiu_collector/__init__.py`
- Create: `src/xueqiu_collector/cli.py`
- Create: `tests/conftest.py`
- Create: `tests/test_cli.py`

- [ ] **Step 1: Write the failing CLI parser tests**

Create `tests/conftest.py`:

```python
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))
```

Create `tests/test_cli.py`:

```python
from xueqiu_collector.cli import build_parser


def test_collect_defaults_match_spec():
    args = build_parser().parse_args(["collect"])

    assert args.command == "collect"
    assert args.pages == 3
    assert args.count == 20
    assert args.delay == 1.0
    assert args.database == "data/xueqiu.sqlite"


def test_export_requires_supported_format_and_output():
    args = build_parser().parse_args(
        ["export", "--format", "csv", "--output", "data/exports/posts.csv"]
    )

    assert args.command == "export"
    assert args.format == "csv"
    assert args.output == "data/exports/posts.csv"
```

- [ ] **Step 2: Run the tests and verify RED**

Run: `pytest tests/test_cli.py -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'xueqiu_collector'`.

- [ ] **Step 3: Add the minimal package scaffold and parser**

Create `.gitignore`:

```gitignore
__pycache__/
*.py[cod]
.pytest_cache/
.mypy_cache/
.venv/
venv/
.env
data/browser-profile/
data/*.sqlite
data/*.sqlite-*
data/exports/
```

Create `pyproject.toml`:

```toml
[build-system]
requires = ["setuptools>=61"]
build-backend = "setuptools.build_meta"

[project]
name = "xueqiu-collector"
version = "0.1.0"
description = "Collect followed Xueqiu timeline posts into a local SQLite database."
requires-python = ">=3.8"
dependencies = ["playwright>=1.40,<2"]

[project.optional-dependencies]
test = ["pytest>=6"]

[project.scripts]
xueqiu-collector = "xueqiu_collector.cli:main"

[tool.setuptools.packages.find]
where = ["src"]
```

Create `src/xueqiu_collector/__init__.py`:

```python
__version__ = "0.1.0"
```

Create `src/xueqiu_collector/cli.py`:

```python
import argparse
from typing import Optional, Sequence


DEFAULT_DATABASE = "data/xueqiu.sqlite"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="xueqiu-collector")
    parser.add_argument("--database", default=DEFAULT_DATABASE)

    subparsers = parser.add_subparsers(dest="command", required=True)

    auth = subparsers.add_parser("auth")
    auth.add_argument("--profile-dir", default="data/browser-profile")

    collect = subparsers.add_parser("collect")
    collect.add_argument("--profile-dir", default="data/browser-profile")
    collect.add_argument("--pages", type=int, default=3)
    collect.add_argument("--count", type=int, default=20)
    collect.add_argument("--delay", type=float, default=1.0)

    inspect = subparsers.add_parser("inspect")
    inspect.add_argument("--limit", type=int, default=20)

    export = subparsers.add_parser("export")
    export.add_argument("--format", choices=("jsonl", "csv"), required=True)
    export.add_argument("--output", required=True)

    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    parser.parse_args(argv)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run the tests and verify GREEN**

Run: `pytest tests/test_cli.py -v`

Expected: PASS with `2 passed`.

- [ ] **Step 5: Commit the scaffold**

```bash
git add .gitignore pyproject.toml src/xueqiu_collector/__init__.py src/xueqiu_collector/cli.py tests/conftest.py tests/test_cli.py
git commit -m "feat: scaffold xueqiu collector cli"
```

## Task 2: Parse Timeline Responses And Classify Errors

**Files:**
- Create: `src/xueqiu_collector/models.py`
- Create: `src/xueqiu_collector/text.py`
- Create: `src/xueqiu_collector/errors.py`
- Create: `src/xueqiu_collector/parser.py`
- Create: `tests/test_parser.py`

- [ ] **Step 1: Write failing parser and error tests**

Create `tests/test_parser.py`:

```python
import json

from xueqiu_collector.errors import ResponseKind, classify_response
from xueqiu_collector.parser import parse_timeline_payload
from xueqiu_collector.text import normalize_html_text


def test_normalize_html_text_strips_tags_and_entities():
    html = "<p>hello&nbsp;<a href='/S/SH000001'>$SH000001</a>&amp; more</p>"

    assert normalize_html_text(html) == "hello $SH000001 & more"


def test_parse_timeline_payload_accepts_home_timeline_items():
    payload = {
        "home_timeline": [
            {
                "id": 123,
                "created_at": 1710000000000,
                "text": "<p>first&nbsp;post</p>",
                "user": {"id": 456, "screen_name": "alice"},
                "reply_count": 2,
                "retweet_count": 3,
                "fav_count": 4,
            }
        ]
    }

    posts = parse_timeline_payload(payload)

    assert len(posts) == 1
    assert posts[0].id == "123"
    assert posts[0].author_id == "456"
    assert posts[0].author_name == "alice"
    assert posts[0].created_at == "2024-03-09T16:00:00+00:00"
    assert posts[0].text == "first post"
    assert posts[0].url == "https://xueqiu.com/456/123"
    assert posts[0].reply_count == 2
    assert json.loads(posts[0].raw_json)["id"] == 123


def test_classify_response_detects_login_error_from_status():
    result = classify_response(401, "{\"error_description\":\"not logged in\"}")

    assert result.kind == ResponseKind.UNAUTHORIZED
    assert "run xueqiu-collector auth" in result.message


def test_classify_response_detects_malformed_json():
    result = classify_response(200, "{broken")

    assert result.kind == ResponseKind.MALFORMED_JSON
    assert "malformed JSON" in result.message
```

- [ ] **Step 2: Run the tests and verify RED**

Run: `pytest tests/test_parser.py -v`

Expected: FAIL with `ModuleNotFoundError` for one of `xueqiu_collector.errors`, `xueqiu_collector.parser`, or `xueqiu_collector.text`.

- [ ] **Step 3: Add models, text normalization, error classification, and parsing**

Create `src/xueqiu_collector/models.py`:

```python
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Post:
    id: str
    author_id: Optional[str]
    author_name: Optional[str]
    created_at: Optional[str]
    text: str
    html: str
    url: Optional[str]
    reply_count: Optional[int]
    retweet_count: Optional[int]
    fav_count: Optional[int]
    raw_json: str


@dataclass(frozen=True)
class UpsertCounts:
    inserted: int
    updated: int
    duplicate: int


@dataclass(frozen=True)
class RunSummary:
    pages_requested: int
    pages_fetched: int
    inserted_count: int
    updated_count: int
    duplicate_count: int
    error: Optional[str] = None
```

Create `src/xueqiu_collector/text.py`:

```python
import html
import re


TAG_RE = re.compile(r"<[^>]+>")
SPACE_RE = re.compile(r"\s+")


def normalize_html_text(value: str) -> str:
    unescaped = html.unescape(value or "")
    without_tags = TAG_RE.sub(" ", unescaped)
    return SPACE_RE.sub(" ", without_tags).strip()
```

Create `src/xueqiu_collector/errors.py`:

```python
import json
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional


class ResponseKind(str, Enum):
    SUCCESS = "success"
    UNAUTHORIZED = "unauthorized"
    HTTP_FAILURE = "http_failure"
    EMPTY = "empty"
    MALFORMED_JSON = "malformed_json"


@dataclass(frozen=True)
class ClassifiedResponse:
    kind: ResponseKind
    message: str
    data: Optional[Any] = None


def _looks_like_login_error(data: Any) -> bool:
    if not isinstance(data, dict):
        return False
    error_code = str(data.get("error_code", ""))
    description = str(data.get("error_description", ""))
    login_words = ("login", "logged in", "登录", "重新登录")
    return error_code in {"400016", "401", "403"} or any(
        word in description.lower() for word in login_words
    )


def classify_response(status_code: int, body: str) -> ClassifiedResponse:
    if status_code in (401, 403):
        return ClassifiedResponse(
            ResponseKind.UNAUTHORIZED,
            "Xueqiu login is missing or expired; run xueqiu-collector auth again.",
        )
    if status_code < 200 or status_code >= 300:
        return ClassifiedResponse(
            ResponseKind.HTTP_FAILURE,
            "HTTP failure from Xueqiu: status {}".format(status_code),
        )
    if not body:
        return ClassifiedResponse(ResponseKind.EMPTY, "Empty response from Xueqiu.")
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        return ClassifiedResponse(
            ResponseKind.MALFORMED_JSON,
            "Received malformed JSON from Xueqiu.",
        )
    if _looks_like_login_error(data):
        return ClassifiedResponse(
            ResponseKind.UNAUTHORIZED,
            "Xueqiu login is missing or expired; run xueqiu-collector auth again.",
            data,
        )
    return ClassifiedResponse(ResponseKind.SUCCESS, "OK", data)
```

Create `src/xueqiu_collector/parser.py`:

```python
import json
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

from .models import Post
from .text import normalize_html_text


def _timeline_items(payload: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
    for key in ("home_timeline", "list", "statuses"):
        items = payload.get(key)
        if isinstance(items, list):
            return [item for item in items if isinstance(item, dict)]
    return []


def _created_at(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        seconds = float(value) / 1000 if value > 10_000_000_000 else float(value)
        return datetime.fromtimestamp(seconds, timezone.utc).isoformat()
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _count(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _first_present(item: Dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in item and item[key] is not None:
            return item[key]
    return None


def _url(author_id: Optional[str], post_id: str) -> Optional[str]:
    if author_id:
        return "https://xueqiu.com/{}/{}".format(author_id, post_id)
    return "https://xueqiu.com/statuses/{}".format(post_id)


def parse_timeline_payload(payload: Dict[str, Any]) -> List[Post]:
    posts: List[Post] = []
    for item in _timeline_items(payload):
        raw_id = item.get("id") or item.get("status_id")
        if raw_id is None:
            continue
        post_id = str(raw_id)
        user = item.get("user") if isinstance(item.get("user"), dict) else {}
        author_id = str(user["id"]) if user.get("id") is not None else None
        author_name = user.get("screen_name") or user.get("name")
        html = str(item.get("text") or item.get("description") or "")
        posts.append(
            Post(
                id=post_id,
                author_id=author_id,
                author_name=str(author_name) if author_name is not None else None,
                created_at=_created_at(item.get("created_at")),
                text=normalize_html_text(html),
                html=html,
                url=_url(author_id, post_id),
                reply_count=_count(_first_present(item, "reply_count", "comments_count")),
                retweet_count=_count(_first_present(item, "retweet_count", "retweets_count")),
                fav_count=_count(_first_present(item, "fav_count", "like_count")),
                raw_json=json.dumps(item, ensure_ascii=False, separators=(",", ":")),
            )
        )
    return posts
```

- [ ] **Step 4: Run the tests and verify GREEN**

Run: `pytest tests/test_parser.py -v`

Expected: PASS with `4 passed`.

- [ ] **Step 5: Commit parser work**

```bash
git add src/xueqiu_collector/models.py src/xueqiu_collector/text.py src/xueqiu_collector/errors.py src/xueqiu_collector/parser.py tests/test_parser.py
git commit -m "feat: parse xueqiu timeline payloads"
```

## Task 3: SQLite Storage And Export

**Files:**
- Create: `src/xueqiu_collector/storage.py`
- Create: `src/xueqiu_collector/exporter.py`
- Create: `tests/test_storage_exporter.py`

- [ ] **Step 1: Write failing storage and export tests**

Create `tests/test_storage_exporter.py`:

```python
import csv
import json

from xueqiu_collector.exporter import export_csv, export_jsonl
from xueqiu_collector.models import Post
from xueqiu_collector.storage import Store


def make_post(post_id="1", text="hello"):
    return Post(
        id=post_id,
        author_id="42",
        author_name="alice",
        created_at="2024-03-09T16:00:00+00:00",
        text=text,
        html="<p>{}</p>".format(text),
        url="https://xueqiu.com/42/{}".format(post_id),
        reply_count=1,
        retweet_count=2,
        fav_count=3,
        raw_json=json.dumps({"id": post_id, "text": text}, ensure_ascii=False),
    )


def test_store_upserts_posts_without_duplicates(tmp_path):
    store = Store(tmp_path / "xueqiu.sqlite")
    store.init_schema()

    first = store.upsert_posts([make_post()])
    second = store.upsert_posts([make_post()])
    third = store.upsert_posts([make_post(text="changed")])

    assert first.inserted == 1
    assert second.duplicate == 1
    assert third.updated == 1
    assert len(store.list_posts(limit=10)) == 1
    assert store.list_posts(limit=10)[0].text == "changed"


def test_export_jsonl_writes_deterministic_rows(tmp_path):
    store = Store(tmp_path / "xueqiu.sqlite")
    store.init_schema()
    store.upsert_posts([make_post("2", "second"), make_post("1", "first")])

    output = tmp_path / "posts.jsonl"
    export_jsonl(store.list_posts(limit=100), output)

    lines = output.read_text(encoding="utf-8").splitlines()
    assert json.loads(lines[0])["id"] == "1"
    assert json.loads(lines[1])["id"] == "2"


def test_export_csv_writes_utf8_sig(tmp_path):
    store = Store(tmp_path / "xueqiu.sqlite")
    store.init_schema()
    store.upsert_posts([make_post("1", "中文")])

    output = tmp_path / "posts.csv"
    export_csv(store.list_posts(limit=100), output)

    raw = output.read_bytes()
    assert raw.startswith(b"\xef\xbb\xbf")
    rows = list(csv.DictReader(output.read_text(encoding="utf-8-sig").splitlines()))
    assert rows[0]["text"] == "中文"
```

- [ ] **Step 2: Run the tests and verify RED**

Run: `pytest tests/test_storage_exporter.py -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'xueqiu_collector.storage'`.

- [ ] **Step 3: Add SQLite storage and exporters**

Create `src/xueqiu_collector/storage.py`:

```python
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
```

Create `src/xueqiu_collector/exporter.py`:

```python
import csv
import json
from dataclasses import asdict
from pathlib import Path
from typing import Iterable

from .models import Post


CSV_FIELDS = [
    "id",
    "author_id",
    "author_name",
    "created_at",
    "text",
    "html",
    "url",
    "reply_count",
    "retweet_count",
    "fav_count",
    "raw_json",
]


def export_jsonl(posts: Iterable[Post], output) -> None:
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    ordered = sorted(posts, key=lambda post: post.id)
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        for post in ordered:
            fh.write(json.dumps(asdict(post), ensure_ascii=False, sort_keys=True))
            fh.write("\n")


def export_csv(posts: Iterable[Post], output) -> None:
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    ordered = sorted(posts, key=lambda post: post.id)
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for post in ordered:
            row = asdict(post)
            writer.writerow({field: row[field] for field in CSV_FIELDS})
```

- [ ] **Step 4: Run the tests and verify GREEN**

Run: `pytest tests/test_storage_exporter.py -v`

Expected: PASS with `3 passed`.

- [ ] **Step 5: Commit storage and export**

```bash
git add src/xueqiu_collector/storage.py src/xueqiu_collector/exporter.py tests/test_storage_exporter.py
git commit -m "feat: store and export collected posts"
```

## Task 4: Collection Orchestration Without Live Network

**Files:**
- Create: `src/xueqiu_collector/collector.py`
- Create: `tests/test_collector.py`

- [ ] **Step 1: Write failing collector tests with a fake client**

Create `tests/test_collector.py`:

```python
import json

from xueqiu_collector.collector import collect_timeline
from xueqiu_collector.storage import Store


class FakeClient:
    def __init__(self, bodies):
        self.bodies = bodies
        self.calls = []

    def fetch_timeline_page(self, page, count):
        self.calls.append((page, count))
        return 200, json.dumps(self.bodies[page - 1])


def item(post_id):
    return {
        "id": post_id,
        "created_at": 1710000000000,
        "text": "<p>post {}</p>".format(post_id),
        "user": {"id": 456, "screen_name": "alice"},
    }


def test_collect_timeline_stops_on_empty_page(tmp_path):
    store = Store(tmp_path / "xueqiu.sqlite")
    client = FakeClient(
        [
            {"home_timeline": [item(1), item(2)]},
            {"home_timeline": []},
            {"home_timeline": [item(3)]},
        ]
    )

    summary = collect_timeline(store, client, pages=3, count=20, delay=0)

    assert client.calls == [(1, 20), (2, 20)]
    assert summary.pages_requested == 3
    assert summary.pages_fetched == 1
    assert summary.inserted_count == 2
    assert summary.error is None
    assert [post.id for post in store.list_posts()] == ["1", "2"]


def test_collect_timeline_records_login_error(tmp_path):
    store = Store(tmp_path / "xueqiu.sqlite")

    class LoginExpiredClient:
        def fetch_timeline_page(self, page, count):
            return 401, "{\"error_description\":\"not logged in\"}"

    summary = collect_timeline(store, LoginExpiredClient(), pages=1, count=20, delay=0)

    assert summary.pages_fetched == 0
    assert summary.inserted_count == 0
    assert "xueqiu-collector auth" in summary.error
```

- [ ] **Step 2: Run the tests and verify RED**

Run: `pytest tests/test_collector.py -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'xueqiu_collector.collector'`.

- [ ] **Step 3: Implement collection orchestration**

Create `src/xueqiu_collector/collector.py`:

```python
import time

from .errors import ResponseKind, classify_response
from .models import RunSummary
from .parser import parse_timeline_payload


def collect_timeline(store, client, pages: int, count: int, delay: float) -> RunSummary:
    store.init_schema()
    inserted = updated = duplicate = pages_fetched = 0
    error = None

    for page in range(1, pages + 1):
        status_code, body = client.fetch_timeline_page(page=page, count=count)
        classified = classify_response(status_code, body)
        if classified.kind != ResponseKind.SUCCESS:
            error = "Page {}: {}".format(page, classified.message)
            break

        posts = parse_timeline_payload(classified.data)
        if not posts:
            break

        counts = store.upsert_posts(posts)
        inserted += counts.inserted
        updated += counts.updated
        duplicate += counts.duplicate
        pages_fetched += 1

        if delay > 0 and page < pages:
            time.sleep(delay)

    summary = RunSummary(
        pages_requested=pages,
        pages_fetched=pages_fetched,
        inserted_count=inserted,
        updated_count=updated,
        duplicate_count=duplicate,
        error=error,
    )
    store.record_run(summary)
    return summary
```

- [ ] **Step 4: Run the tests and verify GREEN**

Run: `pytest tests/test_collector.py -v`

Expected: PASS with `2 passed`.

- [ ] **Step 5: Commit collector orchestration**

```bash
git add src/xueqiu_collector/collector.py tests/test_collector.py
git commit -m "feat: orchestrate xueqiu collection runs"
```

## Task 5: Playwright Client And Auth Flow

**Files:**
- Create: `src/xueqiu_collector/client.py`
- Create: `tests/test_client.py`

- [ ] **Step 1: Write failing client tests**

Create `tests/test_client.py`:

```python
import builtins

import pytest

from xueqiu_collector.client import PlaywrightTimelineClient, open_auth_browser


def test_fetch_timeline_page_uses_home_timeline_endpoint(monkeypatch, tmp_path):
    calls = []

    class FakeResponse:
        status = 200

        def text(self):
            return "{\"home_timeline\":[]}"

    class FakeRequest:
        def get(self, url):
            calls.append(url)
            return FakeResponse()

    class FakeContext:
        request = FakeRequest()

    class FakeChromium:
        def launch_persistent_context(self, user_data_dir, headless):
            assert str(tmp_path / "profile") == user_data_dir
            assert headless is True
            return FakeContext()

    class FakePlaywright:
        chromium = FakeChromium()

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(
        "xueqiu_collector.client._sync_playwright",
        lambda: FakePlaywright(),
    )

    client = PlaywrightTimelineClient(tmp_path / "profile")
    status, body = client.fetch_timeline_page(page=2, count=30)

    assert status == 200
    assert body == "{\"home_timeline\":[]}"
    assert calls == [
        "https://xueqiu.com/v4/statuses/home_timeline.json?page=2&count=30"
    ]


def test_open_auth_browser_waits_for_user_before_closing(monkeypatch, tmp_path):
    events = []

    class FakePage:
        def goto(self, url):
            events.append(("goto", url))

    class FakeContext:
        def new_page(self):
            events.append(("new_page", None))
            return FakePage()

        def close(self):
            events.append(("close", None))

    class FakeChromium:
        def launch_persistent_context(self, user_data_dir, headless):
            events.append(("launch", user_data_dir, headless))
            return FakeContext()

    class FakePlaywright:
        chromium = FakeChromium()

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(
        "xueqiu_collector.client._sync_playwright",
        lambda: FakePlaywright(),
    )
    monkeypatch.setattr(builtins, "input", lambda prompt: events.append(("input", prompt)))

    open_auth_browser(tmp_path / "profile")

    assert events[0] == ("launch", str(tmp_path / "profile"), False)
    assert ("goto", "https://xueqiu.com/") in events
    assert events[-1] == ("close", None)


def test_missing_playwright_dependency_has_clear_message(monkeypatch, tmp_path):
    def missing_playwright():
        raise RuntimeError(
            "Playwright is not installed. Install dependencies with pip install -e . "
            "and install the browser with python -m playwright install chromium."
        )

    monkeypatch.setattr("xueqiu_collector.client._sync_playwright", missing_playwright)

    with pytest.raises(RuntimeError) as excinfo:
        open_auth_browser(tmp_path / "profile")

    assert "python -m playwright install chromium" in str(excinfo.value)
```

- [ ] **Step 2: Run the tests and verify RED**

Run: `pytest tests/test_client.py -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'xueqiu_collector.client'`.

- [ ] **Step 3: Implement lazy Playwright client**

Create `src/xueqiu_collector/client.py`:

```python
from pathlib import Path


HOME_TIMELINE_URL = (
    "https://xueqiu.com/v4/statuses/home_timeline.json?page={page}&count={count}"
)


def _sync_playwright():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError(
            "Playwright is not installed. Install dependencies with "
            "pip install -e . and install the browser with "
            "python -m playwright install chromium."
        ) from exc
    return sync_playwright()


class PlaywrightTimelineClient:
    def __init__(self, profile_dir):
        self.profile_dir = Path(profile_dir)

    def fetch_timeline_page(self, page: int, count: int):
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        url = HOME_TIMELINE_URL.format(page=page, count=count)
        with _sync_playwright() as playwright:
            context = playwright.chromium.launch_persistent_context(
                user_data_dir=str(self.profile_dir),
                headless=True,
            )
            response = context.request.get(url)
            status = response.status
            body = response.text()
            close = getattr(context, "close", None)
            if close is not None:
                close()
            return status, body


def open_auth_browser(profile_dir) -> None:
    path = Path(profile_dir)
    path.mkdir(parents=True, exist_ok=True)
    with _sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(
            user_data_dir=str(path),
            headless=False,
        )
        page = context.new_page()
        page.goto("https://xueqiu.com/")
        input("Log in to Xueqiu in the opened browser, then press Enter here.")
        context.close()
```

- [ ] **Step 4: Run the tests and verify GREEN**

Run: `pytest tests/test_client.py -v`

Expected: PASS with `3 passed`.

- [ ] **Step 5: Commit client work**

```bash
git add src/xueqiu_collector/client.py tests/test_client.py
git commit -m "feat: add playwright xueqiu client"
```

## Task 6: Wire CLI Commands And Usage Docs

**Files:**
- Modify: `src/xueqiu_collector/cli.py`
- Create: `README.md`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Add failing CLI command behavior tests**

Replace `tests/test_cli.py` with:

```python
from xueqiu_collector import cli
from xueqiu_collector.models import RunSummary


def test_collect_defaults_match_spec():
    args = cli.build_parser().parse_args(["collect"])

    assert args.command == "collect"
    assert args.pages == 3
    assert args.count == 20
    assert args.delay == 1.0
    assert args.database == "data/xueqiu.sqlite"


def test_export_requires_supported_format_and_output():
    args = cli.build_parser().parse_args(
        ["export", "--format", "csv", "--output", "data/exports/posts.csv"]
    )

    assert args.command == "export"
    assert args.format == "csv"
    assert args.output == "data/exports/posts.csv"


def test_main_auth_invokes_auth_browser(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(cli, "open_auth_browser", lambda profile: calls.append(profile))

    result = cli.main(["auth", "--profile-dir", str(tmp_path / "profile")])

    assert result == 0
    assert calls == [str(tmp_path / "profile")]


def test_main_collect_prints_summary(monkeypatch, tmp_path, capsys):
    summary = RunSummary(
        pages_requested=3,
        pages_fetched=2,
        inserted_count=4,
        updated_count=1,
        duplicate_count=2,
        error=None,
    )
    monkeypatch.setattr(cli, "collect_timeline", lambda store, client, pages, count, delay: summary)

    result = cli.main(["--database", str(tmp_path / "db.sqlite"), "collect"])

    assert result == 0
    output = capsys.readouterr().out
    assert "inserted=4" in output
    assert "updated=1" in output
    assert "duplicate=2" in output


def test_main_export_jsonl_uses_store(monkeypatch, tmp_path):
    calls = []

    class FakeStore:
        def __init__(self, path):
            self.path = path

        def init_schema(self):
            calls.append(("init", self.path))

        def list_posts(self, limit=None):
            calls.append(("list", limit))
            return []

    monkeypatch.setattr(cli, "Store", FakeStore)
    monkeypatch.setattr(cli, "export_jsonl", lambda posts, output: calls.append(("jsonl", output)))

    result = cli.main(
        [
            "--database",
            str(tmp_path / "db.sqlite"),
            "export",
            "--format",
            "jsonl",
            "--output",
            str(tmp_path / "posts.jsonl"),
        ]
    )

    assert result == 0
    assert ("list", None) in calls
    assert ("jsonl", str(tmp_path / "posts.jsonl")) in calls
```

- [ ] **Step 2: Run the tests and verify RED**

Run: `pytest tests/test_cli.py -v`

Expected: FAIL because `cli.open_auth_browser`, `cli.collect_timeline`, or command dispatch is missing.

- [ ] **Step 3: Implement CLI command dispatch**

Replace `src/xueqiu_collector/cli.py` with:

```python
import argparse
from typing import Optional, Sequence

from .client import PlaywrightTimelineClient, open_auth_browser
from .collector import collect_timeline
from .exporter import export_csv, export_jsonl
from .storage import Store


DEFAULT_DATABASE = "data/xueqiu.sqlite"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="xueqiu-collector")
    parser.add_argument("--database", default=DEFAULT_DATABASE)

    subparsers = parser.add_subparsers(dest="command", required=True)

    auth = subparsers.add_parser("auth")
    auth.add_argument("--profile-dir", default="data/browser-profile")

    collect = subparsers.add_parser("collect")
    collect.add_argument("--profile-dir", default="data/browser-profile")
    collect.add_argument("--pages", type=int, default=3)
    collect.add_argument("--count", type=int, default=20)
    collect.add_argument("--delay", type=float, default=1.0)

    inspect = subparsers.add_parser("inspect")
    inspect.add_argument("--limit", type=int, default=20)

    export = subparsers.add_parser("export")
    export.add_argument("--format", choices=("jsonl", "csv"), required=True)
    export.add_argument("--output", required=True)

    return parser


def _print_summary(summary) -> None:
    print(
        "pages={}/{} inserted={} updated={} duplicate={} error={}".format(
            summary.pages_fetched,
            summary.pages_requested,
            summary.inserted_count,
            summary.updated_count,
            summary.duplicate_count,
            summary.error or "",
        )
    )


def _print_posts(posts) -> None:
    for post in posts:
        preview = post.text[:80].replace("\n", " ")
        print("{}\t{}\t{}\t{}\t{}".format(
            post.id,
            post.author_name or "",
            post.created_at or "",
            preview,
            post.url or "",
        ))


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "auth":
        open_auth_browser(args.profile_dir)
        return 0

    store = Store(args.database)
    store.init_schema()

    if args.command == "collect":
        client = PlaywrightTimelineClient(args.profile_dir)
        summary = collect_timeline(
            store,
            client,
            pages=args.pages,
            count=args.count,
            delay=args.delay,
        )
        _print_summary(summary)
        return 1 if summary.error else 0

    if args.command == "inspect":
        _print_posts(store.list_posts(limit=args.limit))
        return 0

    if args.command == "export":
        posts = store.list_posts(limit=None)
        if args.format == "jsonl":
            export_jsonl(posts, args.output)
        else:
            export_csv(posts, args.output)
        print("exported {} posts to {}".format(len(posts), args.output))
        return 0

    parser.error("unknown command {}".format(args.command))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Add README usage**

Create `README.md`:

````markdown
# Xueqiu Collector

Local CLI for collecting posts from the Xueqiu users you follow.

## Setup

```powershell
pip install -e .[test]
python -m playwright install chromium
```

## Login

```powershell
xueqiu-collector auth
```

Log in to Xueqiu in the opened browser, then return to the terminal and press Enter.

## Collect

```powershell
xueqiu-collector collect --pages 3 --count 20
```

Collected posts are stored in `data/xueqiu.sqlite`.

## Inspect

```powershell
xueqiu-collector inspect --limit 20
```

## Export

```powershell
xueqiu-collector export --format jsonl --output data/exports/xueqiu-posts.jsonl
xueqiu-collector export --format csv --output data/exports/xueqiu-posts.csv
```

Runtime files under `data/` are ignored by Git.
````

- [ ] **Step 5: Run the full offline suite**

Run: `pytest -v`

Expected: PASS with all tests passing. The exact count should equal the tests created in Tasks 1 through 6.

- [ ] **Step 6: Commit CLI wiring and docs**

```bash
git add src/xueqiu_collector/cli.py tests/test_cli.py README.md
git commit -m "feat: wire xueqiu collector commands"
```

## Task 7: Manual Live Verification

**Files:**
- No source file changes expected.
- Runtime output will be under ignored `data/` paths.

- [ ] **Step 1: Install package and browser dependency**

Run: `pip install -e .[test]`

Expected: package installs successfully. If the command fails with network access disabled, rerun with the required sandbox escalation.

Run: `python -m playwright install chromium`

Expected: Chromium browser installation completes. If the command fails with network access disabled, rerun with the required sandbox escalation.

- [ ] **Step 2: Open the dedicated Xueqiu login profile**

Run: `xueqiu-collector auth`

Expected: a Chromium window opens at `https://xueqiu.com/`. The user logs in, returns to the terminal, and presses Enter.

- [ ] **Step 3: Run a small live collection**

Run: `xueqiu-collector collect --pages 1 --count 5 --delay 0`

Expected: either a summary with collected rows, such as `pages=1/1 inserted=...`, or an explicit login/network error that tells the user what to refresh. It must not print cookies.

- [ ] **Step 4: Verify inspect and export against the live database**

Run: `xueqiu-collector inspect --limit 5`

Expected: prints up to five stored posts with ID, author, time, preview, and URL.

Run: `xueqiu-collector export --format jsonl --output data/exports/xueqiu-posts.jsonl`

Expected: writes `data/exports/xueqiu-posts.jsonl`.

Run: `xueqiu-collector export --format csv --output data/exports/xueqiu-posts.csv`

Expected: writes `data/exports/xueqiu-posts.csv` with UTF-8 BOM.

- [ ] **Step 5: Commit any verification-only doc correction**

If manual verification reveals that a README command needs correction, edit only `README.md`, run `pytest -v`, then commit:

```bash
git add README.md
git commit -m "docs: clarify xueqiu collector usage"
```

## Self-Review

Spec coverage:

- Dedicated login profile: Task 5 implements `open_auth_browser`; Task 7 verifies it manually.
- Authenticated dynamic timeline collection: Task 5 implements the timeline endpoint client; Task 4 orchestrates collection; Task 7 verifies live behavior.
- SQLite storage and duplicate handling: Task 3 covers schema and upsert counts.
- `auth`, `collect`, `inspect`, and `export`: Task 1 defines parser shape; Task 6 wires command behavior.
- JSONL and CSV export: Task 3 covers exporters; Task 6 wires CLI; Task 7 verifies runtime files.
- Error reporting: Task 2 classifies unauthorized, HTTP failure, empty, and malformed JSON; Task 4 records login errors in run summaries.
- Tests: Tasks 1 through 6 create offline pytest coverage for parser, storage, pagination, export, error classification, client behavior, and CLI wiring.
- Privacy and local data ignores: Task 1 creates `.gitignore`; Task 5 keeps Playwright imports lazy and does not print cookies.

Placeholder scan:

- This plan contains no open-ended implementation markers.
- Each source-changing step includes exact tests, exact code, commands, and expected outcomes.

Type consistency:

- `Post`, `RunSummary`, and `UpsertCounts` are defined once in `models.py` and used consistently by parser, storage, exporter, collector, and CLI.
- Store methods are consistently named `init_schema`, `upsert_posts`, `list_posts`, and `record_run`.
- Client method is consistently named `fetch_timeline_page`.
