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
