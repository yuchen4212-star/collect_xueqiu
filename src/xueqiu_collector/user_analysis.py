from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple

from .models import Post
from .periods import CHINA_TZ
from .reporting import ReportResult


@dataclass(frozen=True)
class Theme:
    heading: str
    summary: str
    keywords: Sequence[str]


THEMES = (
    Theme(
        heading="Thought Signals / 思想线索",
        summary=(
            "He tends to reason from observable change, especially AI, labor, "
            "organization, efficiency, and market behavior."
        ),
        keywords=(
            "AI",
            "ai",
            "数据",
            "效率",
            "组织",
            "失业",
            "研究",
            "世界变化",
        ),
    ),
    Theme(
        heading="Investment Philosophy / 投资理念",
        summary=(
            "The investment language is trading-aware: valuation, expected "
            "difference, liquidity, position discipline, and avoiding crowded "
            "or stale narratives matter more than static labels."
        ),
        keywords=(
            "估值",
            "预期差",
            "交易",
            "赔率",
            "流动性",
            "市场",
            "买",
            "审慎",
            "ETF",
            "etf",
        ),
    ),
    Theme(
        heading="Economic Views / 经济观点",
        summary=(
            "The macro lens often connects consumption, aging, exports, RMB "
            "liquidity, industry cycles, and whether growth narratives can keep "
            "their pricing power."
        ),
        keywords=(
            "消费",
            "老龄化",
            "出海",
            "流动性",
            "增长",
            "经济",
            "新能源",
            "碳基",
            "内资",
            "永续",
        ),
    ),
)


def _parse_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=CHINA_TZ)
    return parsed


def _local_start(day: date) -> datetime:
    return datetime.combine(day, time(0, 0)).replace(tzinfo=CHINA_TZ)


def filter_posts_since_local_date(posts: Iterable[Post], since_date: date) -> List[Post]:
    cutoff = _local_start(since_date).astimezone(timezone.utc)
    selected = []
    for post in posts:
        created_at = _parse_datetime(post.created_at)
        if created_at and created_at.astimezone(timezone.utc) >= cutoff:
            selected.append(post)
    return sorted(
        selected,
        key=lambda post: (_parse_datetime(post.created_at) or datetime.min.replace(tzinfo=timezone.utc)),
        reverse=True,
    )


def user_analysis_path(output_dir, user_id: str, since_date: date) -> Path:
    return (
        Path(output_dir)
        / "users"
        / user_id
        / since_date.isoformat()
        / "user-{}-1y-analysis.md".format(user_id)
    )


def _trim(value: str, max_chars: int = 120) -> str:
    text = " ".join((value or "").split())
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3].rstrip() + "..."


def _local_time(value: Optional[str]) -> str:
    parsed = _parse_datetime(value)
    if not parsed:
        return "unknown time"
    return parsed.astimezone(CHINA_TZ).strftime("%Y-%m-%d %H:%M")


def _interaction_score(post: Post) -> int:
    return sum(value or 0 for value in (post.reply_count, post.retweet_count, post.fav_count))


def _theme_score(post: Post, keywords: Sequence[str]) -> int:
    haystack = post.text or ""
    return sum(1 for keyword in keywords if keyword and keyword in haystack)


def _evidence_posts(posts: Sequence[Post], keywords: Sequence[str], limit: int = 6) -> List[Post]:
    scored: List[Tuple[int, int, Post]] = []
    for post in posts:
        theme_score = _theme_score(post, keywords)
        if theme_score:
            scored.append((theme_score, _interaction_score(post), post))
    scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return [post for _, _, post in scored[:limit]]


def _render_evidence(post: Post) -> str:
    link = " [{}]({})".format("source", post.url) if post.url else ""
    return "- {}{}: {}".format(_local_time(post.created_at), link, _trim(post.text))


def render_user_analysis_report(
    posts: Iterable[Post],
    user_id: str,
    author_name: Optional[str],
    since_date: date,
) -> ReportResult:
    selected = filter_posts_since_local_date(posts, since_date)
    display_name = author_name or user_id
    title = "Xueqiu user {} one-year analysis".format(user_id)
    lines = [
        "# {}".format(title),
        "",
        "User: {} ({})".format(display_name, user_id),
        "Range: since {} 00:00 Beijing time".format(since_date.isoformat()),
        "Collected posts in range: {}".format(len(selected)),
        "",
        "This report is an evidence pack for human review. It groups short excerpts by recurring signals rather than claiming a full automated biography.",
        "",
    ]

    for theme in THEMES:
        lines.extend(["## {}".format(theme.heading), "", theme.summary, ""])
        evidence = _evidence_posts(selected, theme.keywords)
        if evidence:
            lines.append("Evidence:")
            lines.extend(_render_evidence(post) for post in evidence)
        else:
            lines.append("Evidence: no keyword matches in the collected range.")
        lines.append("")

    lines.extend(["## High-Interaction Samples / 高互动样本", ""])
    top_posts = sorted(selected, key=_interaction_score, reverse=True)[:10]
    if top_posts:
        lines.extend(_render_evidence(post) for post in top_posts)
    else:
        lines.append("No posts available.")
    lines.append("")

    return ReportResult(
        title=title,
        markdown="\n".join(lines).rstrip() + "\n",
        post_count=len(selected),
        author_count=1 if selected else 0,
    )


def write_user_analysis_report(
    report: ReportResult,
    output_dir,
    user_id: str,
    since_date: date,
) -> Path:
    path = user_analysis_path(output_dir, user_id, since_date)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(report.markdown, encoding="utf-8")
    return path
