import json
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

from xueqiu_collector.collector import collect_timeline, collect_user_timeline
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


def test_collect_timeline_indexes_home_source(tmp_path):
    store = Store(tmp_path / "xueqiu.sqlite")
    client = FakeClient([{"home_timeline": [item(1), item(2)]}])

    collect_timeline(store, client, pages=1, count=20, delay=0)

    assert [post.id for post in store.list_posts_for_source("home")] == ["1", "2"]
    with store.connect() as conn:
        run = conn.execute("SELECT source_key FROM collection_runs").fetchone()
        source = conn.execute(
            "SELECT source_type, label FROM collection_sources WHERE key = 'home'"
        ).fetchone()

    assert run["source_key"] == "home"
    assert tuple(source) == ("home", "followed timeline")


def test_collect_timeline_records_login_error(tmp_path):
    store = Store(tmp_path / "xueqiu.sqlite")

    class LoginExpiredClient:
        def fetch_timeline_page(self, page, count):
            return 401, "{\"error_description\":\"not logged in\"}"

    summary = collect_timeline(store, LoginExpiredClient(), pages=1, count=20, delay=0)

    assert summary.pages_fetched == 0
    assert summary.inserted_count == 0
    assert "xueqiu-collector auth" in summary.error


class FakeUserClient:
    def __init__(self, bodies):
        self.bodies = bodies
        self.calls = []

    def fetch_user_timeline_page(self, user_id, page, count):
        self.calls.append((user_id, page, count))
        return 200, json.dumps(self.bodies[page - 1])


def test_collect_user_timeline_filters_since_cutoff_and_stops_when_page_is_old(tmp_path):
    store = Store(tmp_path / "xueqiu.sqlite")
    cutoff = datetime(2025, 6, 4, tzinfo=timezone(timedelta(hours=8)))
    client = FakeUserClient(
        [
            {
                "statuses": [
                    {**item(3), "created_at": "2025-06-04T09:00:00+08:00"},
                    {**item(2), "created_at": "2025-06-04T00:00:00+08:00"},
                    {**item(1), "created_at": "2025-06-03T23:59:00+08:00"},
                ]
            },
            {"statuses": [{**item(4), "created_at": "2025-06-03T23:00:00+08:00"}]},
            {"statuses": [item(99)]},
        ]
    )

    summary = collect_user_timeline(
        store,
        client,
        user_id="2292705444",
        pages=3,
        count=20,
        delay=0,
        since=cutoff,
        start_page=1,
    )

    assert client.calls == [
        ("2292705444", 1, 20),
        ("2292705444", 2, 20),
    ]
    assert summary.pages_requested == 3
    assert summary.pages_fetched == 2
    assert summary.inserted_count == 2
    assert [post.id for post in store.list_posts_for_source("user:2292705444")] == [
        "2",
        "3",
    ]


def test_collect_user_timeline_honors_start_page(tmp_path):
    store = Store(tmp_path / "xueqiu.sqlite")
    cutoff = datetime(2024, 1, 1, tzinfo=timezone.utc)
    client = FakeUserClient(
        [
            {"statuses": [item(1)]},
            {"statuses": [item(2)]},
            {"statuses": []},
        ]
    )

    summary = collect_user_timeline(
        store,
        client,
        user_id="2292705444",
        pages=2,
        count=20,
        delay=0,
        since=cutoff,
        start_page=2,
    )

    assert client.calls == [("2292705444", 2, 20), ("2292705444", 3, 20)]
    assert summary.pages_fetched == 1
    assert [post.id for post in store.list_posts_for_source("user:2292705444")] == ["2"]


def test_collect_user_timeline_reuses_client_session_when_available(tmp_path):
    store = Store(tmp_path / "xueqiu.sqlite")
    cutoff = datetime(2024, 1, 1, tzinfo=timezone.utc)

    class SessionClient(FakeUserClient):
        def __init__(self, bodies):
            super().__init__(bodies)
            self.session_events = []

        @contextmanager
        def open_session(self):
            self.session_events.append("enter")
            try:
                yield self
            finally:
                self.session_events.append("exit")

    client = SessionClient([{"statuses": [item(1)]}])

    collect_user_timeline(
        store,
        client,
        user_id="2292705444",
        pages=1,
        count=20,
        delay=0,
        since=cutoff,
    )

    assert client.session_events == ["enter", "exit"]
