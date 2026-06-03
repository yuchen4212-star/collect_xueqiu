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
