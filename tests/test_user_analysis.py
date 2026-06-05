import json
from datetime import date

from xueqiu_collector.models import Post
from xueqiu_collector.user_analysis import (
    filter_posts_since_local_date,
    render_user_analysis_report,
    user_analysis_path,
)


def make_post(post_id, created_at, text):
    return Post(
        id=post_id,
        author_id="2292705444",
        author_name="metalslime",
        created_at=created_at,
        text=text,
        html="<p>{}</p>".format(text),
        url="https://xueqiu.com/2292705444/{}".format(post_id),
        reply_count=1,
        retweet_count=2,
        fav_count=3,
        raw_json=json.dumps({"id": post_id, "description": text}, ensure_ascii=False),
    )


def test_filter_posts_since_local_date_uses_beijing_boundary():
    posts = [
        make_post("old", "2025-06-03T15:59:59+00:00", "old"),
        make_post("new", "2025-06-03T16:00:00+00:00", "new"),
    ]

    filtered = filter_posts_since_local_date(posts, date(2025, 6, 4))

    assert [post.id for post in filtered] == ["new"]


def test_user_analysis_path_is_layered_by_author_and_date():
    path = user_analysis_path("data/analysis", "2292705444", date(2025, 6, 4))

    assert str(path).replace("\\", "/") == (
        "data/analysis/users/2292705444/2025-06-04/user-2292705444-1y-analysis.md"
    )


def test_render_user_analysis_report_includes_themes_and_evidence():
    posts = [
        make_post("1", "2026-06-04T08:00:00+00:00", "AI changes efficiency and jobs"),
        make_post("2", "2026-06-03T08:00:00+00:00", "valuation and expected return"),
        make_post("3", "2026-06-02T08:00:00+00:00", "consumption and liquidity"),
    ]

    report = render_user_analysis_report(
        posts,
        user_id="2292705444",
        author_name="metalslime",
        since_date=date(2025, 6, 4),
    )

    assert "2292705444" in report.title
    assert "## Thought Signals" in report.markdown
    assert "## Investment Philosophy" in report.markdown
    assert "## Economic Views" in report.markdown
    assert "https://xueqiu.com/2292705444/1" in report.markdown
