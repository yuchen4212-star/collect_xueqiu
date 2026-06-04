import json

from xueqiu_collector.models import Post
from xueqiu_collector.periods import resolve_period_window
from xueqiu_collector.reporting import ReportResult, report_path
from xueqiu_collector.storage import Store


def make_post(post_id="1", raw=None):
    return Post(
        id=post_id,
        author_id="42",
        author_name="alice",
        created_at="2026-06-04T02:00:00+00:00",
        text="hello",
        html="<p>hello</p>",
        url="https://xueqiu.com/42/{}".format(post_id),
        reply_count=1,
        retweet_count=0,
        fav_count=2,
        raw_json=json.dumps(raw or {"id": post_id, "text": "hello"}, ensure_ascii=False),
    )


def test_report_path_archives_by_local_date_and_style():
    window = resolve_period_window("morning", report_date="2026-06-04")

    path = report_path("data/reports", window, style="digest")

    assert str(path).replace("\\", "/") == (
        "data/reports/2026/06/04/0930-1230-morning.digest.md"
    )


def test_store_schema_has_layered_metadata_tables(tmp_path):
    store = Store(tmp_path / "db" / "xueqiu.sqlite")
    store.init_schema()

    with store.connect() as conn:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }

    assert {"posts", "authors", "post_quotes", "collection_runs", "reports", "notifications"} <= tables


def test_upsert_posts_indexes_author_and_quoted_original(tmp_path):
    raw = {
        "id": 1,
        "text": "转发",
        "retweeted_status": {
            "id": 99,
            "user_id": 77,
            "target": "/77/99",
            "text": "quoted text",
            "user": {"id": 77, "screen_name": "quoted-author"},
        },
    }
    store = Store(tmp_path / "db" / "xueqiu.sqlite")
    store.init_schema()

    store.upsert_posts([make_post(raw=raw)])

    with store.connect() as conn:
        author = conn.execute("SELECT name FROM authors WHERE id = '42'").fetchone()
        quote = conn.execute(
            "SELECT quoted_post_id, quoted_author_id, quoted_author_name, quoted_url "
            "FROM post_quotes WHERE post_id = '1'"
        ).fetchone()

    assert author["name"] == "alice"
    assert tuple(quote) == ("99", "77", "quoted-author", "https://xueqiu.com/77/99")


def test_store_records_reports_and_notifications(tmp_path):
    store = Store(tmp_path / "db" / "xueqiu.sqlite")
    store.init_schema()
    window = resolve_period_window("morning", report_date="2026-06-04")
    report = ReportResult("title", "# title\n", post_count=2, author_count=1)

    report_id = store.record_report(
        window=window,
        report=report,
        output_path="data/reports/2026/06/04/0930-1230-morning.digest.md",
        style="digest",
    )
    store.record_notification(
        report_id=report_id,
        channel="pushplus",
        sent=True,
        message="ok",
    )

    with store.connect() as conn:
        stored_report = conn.execute("SELECT * FROM reports").fetchone()
        stored_notification = conn.execute("SELECT * FROM notifications").fetchone()

    assert stored_report["period_key"] == "morning"
    assert stored_report["style"] == "digest"
    assert stored_notification["report_id"] == report_id
    assert stored_notification["channel"] == "pushplus"
    assert stored_notification["sent"] == 1


def test_init_schema_backfills_metadata_from_legacy_posts(tmp_path):
    store = Store(tmp_path / "db" / "xueqiu.sqlite")
    raw = {
        "id": 1,
        "text": "转发",
        "retweeted_status": {
            "id": 99,
            "user_id": 77,
            "target": "/77/99",
            "text": "quoted text",
            "user": {"id": 77, "screen_name": "quoted-author"},
        },
    }
    with store.connect() as conn:
        conn.execute(
            """
            CREATE TABLE posts (
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
            INSERT INTO posts (
                id, author_id, author_name, created_at, text, html, url,
                reply_count, retweet_count, fav_count, raw_json, collected_at, updated_at
            )
            VALUES ('1', '42', 'alice', '2026-06-04T02:00:00+00:00',
                    'hello', '<p>hello</p>', 'https://xueqiu.com/42/1',
                    1, 0, 2, ?, 'now', 'now')
            """,
            (json.dumps(raw, ensure_ascii=False),),
        )

    store.init_schema()

    with store.connect() as conn:
        author = conn.execute("SELECT name FROM authors WHERE id = '42'").fetchone()
        quote = conn.execute("SELECT quoted_text FROM post_quotes WHERE post_id = '1'").fetchone()

    assert author["name"] == "alice"
    assert quote["quoted_text"] == "quoted text"
