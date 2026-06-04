import json

from xueqiu_collector.models import Post
from xueqiu_collector.periods import resolve_period_window
from xueqiu_collector.reporting import filter_posts_by_window, render_author_report


def make_post(
    post_id,
    author,
    created_at,
    text,
    raw=None,
):
    return Post(
        id=post_id,
        author_id="42",
        author_name=author,
        created_at=created_at,
        text=text,
        html="<p>{}</p>".format(text),
        url="https://xueqiu.com/42/{}".format(post_id),
        reply_count=1,
        retweet_count=2,
        fav_count=3,
        raw_json=json.dumps(raw or {"id": post_id, "text": text}, ensure_ascii=False),
    )


def test_filter_posts_by_local_period_window():
    window = resolve_period_window("morning", report_date="2026-06-04")
    inside = make_post("1", "alice", "2026-06-04T02:00:00+00:00", "inside")
    outside = make_post("2", "bob", "2026-06-04T06:51:00+00:00", "outside")

    assert filter_posts_by_window([inside, outside], window) == [inside]


def test_render_author_report_groups_posts_and_expands_quoted_original():
    raw = {
        "id": 1,
        "text": "转发",
        "retweeted_status": {
            "id": 99,
            "target": "/99/99",
            "text": "<p>原文<br/>第二行</p>",
            "user": {"screen_name": "原作者"},
        },
    }
    posts = [
        make_post("2", "bob", "2026-06-04T02:00:00+00:00", "B"),
        make_post("1", "alice", "2026-06-04T02:01:00+00:00", "A", raw=raw),
    ]
    window = resolve_period_window("morning", report_date="2026-06-04")

    report = render_author_report(posts, window, max_chars=120, style="full")

    assert "# 雪球关注动态" in report.markdown
    assert "本段发言：2 条，作者：2 位" in report.markdown
    assert "## alice (1)" in report.markdown
    assert "## bob (1)" in report.markdown
    assert "引用原文：原作者" in report.markdown
    assert "原文 第二行" in report.markdown
    assert "https://xueqiu.com/99/99" in report.markdown


def test_render_digest_report_collapses_extra_author_posts():
    posts = [
        make_post(str(index), "alice", "2026-06-04T02:0{}:00+00:00".format(index), "post {}".format(index))
        for index in range(1, 6)
    ]
    window = resolve_period_window("morning", report_date="2026-06-04")

    report = render_author_report(
        posts,
        window,
        max_chars=80,
        style="digest",
        author_limit=3,
    )

    assert "# 雪球关注动态｜09:30-12:30｜5条｜1人" in report.markdown
    assert "活跃作者：alice 5" in report.markdown
    assert "## alice · 5条" in report.markdown
    assert "<details>" in report.markdown
    assert "<summary>还有 2 条，点击展开</summary>" in report.markdown
    assert report.markdown.index("post 3") < report.markdown.index("<details>")
    assert report.markdown.index("<details>") < report.markdown.index("post 4")


def test_render_digest_post_splits_reply_context_and_quote_blocks():
    raw = {
        "id": 1,
        "text": "回复 @bob : 我自己的回复// @bob :上文问题",
        "retweeted_status": {
            "id": 99,
            "target": "/99/99",
            "text": "被引用的原文",
            "user": {"screen_name": "原作者"},
        },
    }
    posts = [
        make_post(
            "1",
            "alice",
            "2026-06-04T02:00:00+00:00",
            "回复 @bob : 我自己的回复// @bob :上文问题",
            raw=raw,
        )
    ]
    window = resolve_period_window("morning", report_date="2026-06-04")

    report = render_author_report(posts, window, style="digest", max_chars=80)

    assert "- 10:00" in report.markdown
    assert "  回复 @bob：" in report.markdown
    assert "  我自己的回复" in report.markdown
    assert "  ↳ 上文 @bob：" in report.markdown
    assert "  上文问题" in report.markdown
    assert "  引用 @原作者：" in report.markdown
    assert "  被引用的原文" in report.markdown
    assert "我自己的回复//" not in report.markdown


def test_render_digest_post_uses_conversation_card_links():
    raw = {
        "id": 1,
        "text": "回复 @bob : 我自己的回复// @bob :上文问题",
        "retweeted_status": {
            "id": 99,
            "target": "/99/99",
            "text": "被引用的原文",
            "user": {"screen_name": "原作者"},
        },
    }
    posts = [
        make_post(
            "1",
            "alice",
            "2026-06-04T02:00:00+00:00",
            "回复 @bob : 我自己的回复// @bob :上文问题",
            raw=raw,
        )
    ]
    window = resolve_period_window("morning", report_date="2026-06-04")

    report = render_author_report(posts, window, style="digest", max_chars=80)

    assert "- 10:00｜评论 1｜转发 2｜赞 3" in report.markdown
    assert "  回复 @bob：" in report.markdown
    assert "  我自己的回复" in report.markdown
    assert "  ↳ 上文 @bob：" in report.markdown
    assert "  上文问题" in report.markdown
    assert "  引用 @原作者：" in report.markdown
    assert "  被引用的原文" in report.markdown
    assert "  [原帖](https://xueqiu.com/42/1)｜[引用](https://xueqiu.com/99/99)" in report.markdown
    assert "原帖：https://xueqiu.com/42/1" not in report.markdown
    assert "  > https://xueqiu.com/99/99" not in report.markdown
