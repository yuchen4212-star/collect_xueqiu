import json
from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Optional

from .models import Post, RunSummary
from .periods import CHINA_TZ, PeriodWindow
from .text import normalize_html_text


@dataclass(frozen=True)
class QuotedStatus:
    author_name: str
    text: str
    url: str


@dataclass(frozen=True)
class ReportResult:
    title: str
    markdown: str
    post_count: int
    author_count: int


@dataclass(frozen=True)
class MessageParts:
    label: str
    body: str
    contexts: List[str]


@dataclass(frozen=True)
class ReplyText:
    target: Optional[str]
    body: str


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


def filter_posts_by_window(posts: Iterable[Post], window: PeriodWindow) -> List[Post]:
    selected = []
    for post in posts:
        created_at = _parse_datetime(post.created_at)
        created_utc = created_at.astimezone(timezone.utc) if created_at else None
        if created_utc and window.start_utc <= created_utc < window.end_utc:
            selected.append(post)
    return selected


def _quoted_status(post: Post) -> Optional[QuotedStatus]:
    try:
        raw = json.loads(post.raw_json)
    except (TypeError, ValueError):
        return None
    quoted = raw.get("retweeted_status") if isinstance(raw, dict) else None
    if not isinstance(quoted, dict):
        return None

    user = quoted.get("user") if isinstance(quoted.get("user"), dict) else {}
    author_name = str(user.get("screen_name") or user.get("name") or "未知作者")
    text = normalize_html_text(str(quoted.get("text") or quoted.get("description") or ""))
    target = quoted.get("target")
    if isinstance(target, str) and target.startswith("/"):
        url = "https://xueqiu.com{}".format(target)
    else:
        quoted_id = quoted.get("id")
        user_id = quoted.get("user_id") or user.get("id")
        if quoted_id and user_id:
            url = "https://xueqiu.com/{}/{}".format(user_id, quoted_id)
        else:
            url = ""
    return QuotedStatus(author_name=author_name, text=text, url=url)


def _trim(value: str, max_chars: int) -> str:
    text = (value or "").strip()
    if max_chars <= 0 or len(text) <= max_chars:
        return text
    return text[: max_chars - 3].rstrip() + "..."


def _format_local_time(value: Optional[str]) -> str:
    parsed = _parse_datetime(value)
    if not parsed:
        return "未知时间"
    return parsed.astimezone(CHINA_TZ).strftime("%H:%M")


def _group_by_author(posts: Iterable[Post], sort_by_activity: bool = False) -> OrderedDict:
    grouped = OrderedDict()
    ordered = sorted(
        posts,
        key=lambda post: (post.author_name or "", post.created_at or "", post.id),
    )
    for post in ordered:
        author = post.author_name or "未知作者"
        grouped.setdefault(author, []).append(post)
    if sort_by_activity:
        return OrderedDict(
            sorted(
                grouped.items(),
                key=lambda item: (-len(item[1]), item[0]),
            )
        )
    return grouped


def _interaction_text(post: Post, include_zero: bool, separator: str) -> str:
    counts = []
    for label, value in (
        ("评论", post.reply_count),
        ("转发", post.retweet_count),
        ("赞", post.fav_count),
    ):
        if value is None:
            continue
        if include_zero or value:
            counts.append("{} {}".format(label, value))
    return separator.join(counts)


def _report_title(window: PeriodWindow, posts: List[Post], grouped: OrderedDict) -> str:
    return "雪球关注动态｜{}｜{}条｜{}人".format(
        window.label,
        len(posts),
        len(grouped),
    )


def _message_parts(text: str) -> MessageParts:
    parts = [part.strip() for part in (text or "").split("//") if part.strip()]
    body = parts[0] if parts else ""
    label = "回复" if body.startswith("回复 @") else "正文"
    return MessageParts(label=label, body=body, contexts=parts[1:])


def _split_reply_text(text: str) -> ReplyText:
    has_reply_prefix = text.startswith("回复 @")
    has_user_prefix = text.startswith("@")
    if not has_reply_prefix and not has_user_prefix:
        return ReplyText(target=None, body=text)
    marker = " : "
    marker_at = text.find(marker)
    if marker_at < 0:
        marker = ":"
        marker_at = text.find(marker)
    if marker_at < 0:
        return ReplyText(target=None, body=text)
    prefix_length = len("回复 ") if has_reply_prefix else 0
    target = text[prefix_length:marker_at].strip()
    body = text[marker_at + len(marker) :].strip()
    return ReplyText(target=target, body=body)


def _post_links(post: Post, quoted: Optional[QuotedStatus]) -> str:
    links = []
    if post.url:
        links.append("[原帖]({})".format(post.url))
    if quoted and quoted.url:
        links.append("[引用]({})".format(quoted.url))
    return "｜".join(links)


def _render_digest_post(post: Post, max_chars: int) -> List[str]:
    interactions = _interaction_text(post, include_zero=False, separator="｜")
    header = _format_local_time(post.created_at)
    if interactions:
        header = "{}｜{}".format(header, interactions)
    lines = ["- {}".format(header)]
    parts = _message_parts(post.text)
    if parts.body:
        reply = _split_reply_text(parts.body)
        if reply.target:
            lines.append("  回复 {}：".format(reply.target))
            lines.append("  {}".format(_trim(reply.body, max_chars)))
        else:
            lines.append("  {}：".format(parts.label))
            lines.append("  {}".format(_trim(reply.body, max_chars)))
    if parts.contexts:
        for context in parts.contexts:
            reply = _split_reply_text(context)
            if reply.target:
                lines.append("  ↳ 上文 {}：".format(reply.target))
                lines.append("  {}".format(_trim(reply.body, max_chars)))
            else:
                lines.append("  ↳ 上文：")
                lines.append("  {}".format(_trim(reply.body, max_chars)))
    quoted = _quoted_status(post)
    if quoted:
        lines.append("  引用 @{}：".format(quoted.author_name))
        lines.append("  {}".format(_trim(quoted.text, max_chars)))
    links = _post_links(post, quoted)
    if links:
        lines.append("  {}".format(links))
    lines.append("")
    return lines


def _render_digest_report(
    posts: Iterable[Post],
    window: PeriodWindow,
    summary: Optional[RunSummary] = None,
    max_chars: int = 300,
    author_limit: int = 3,
) -> ReportResult:
    posts = list(posts)
    grouped = _group_by_author(posts, sort_by_activity=True)
    title = _report_title(window, posts, grouped)
    active_authors = "｜".join(
        "{} {}".format(author, len(author_posts))
        for author, author_posts in list(grouped.items())[:8]
    )
    lines = [
        "# {}".format(title),
        "",
        "时间段：{} 到 {}（北京时间）".format(
            window.start_local.strftime("%Y-%m-%d %H:%M"),
            window.end_local.strftime("%Y-%m-%d %H:%M"),
        ),
        "活跃作者：{}".format(active_authors or "无"),
    ]
    if summary is not None:
        lines.append(
            "采集：抓取 {}/{} 页，新增 {}，更新 {}，重复 {}{}".format(
                summary.pages_fetched,
                summary.pages_requested,
                summary.inserted_count,
                summary.updated_count,
                summary.duplicate_count,
                "，错误：{}".format(summary.error) if summary.error else "",
            )
        )
    lines.append("")

    if not posts:
        lines.append("本时间段没有新的发言。")
    for author, author_posts in grouped.items():
        visible_posts = author_posts[: max(author_limit, 0)]
        hidden_posts = author_posts[len(visible_posts) :]
        lines.extend(["## {} · {}条".format(author, len(author_posts)), ""])
        for post in visible_posts:
            lines.extend(_render_digest_post(post, max_chars))
        if hidden_posts:
            lines.extend(
                [
                    "<details>",
                    "<summary>还有 {} 条，点击展开</summary>".format(len(hidden_posts)),
                    "",
                ]
            )
            for post in hidden_posts:
                lines.extend(_render_digest_post(post, max_chars))
            lines.extend(["</details>", ""])

    return ReportResult(
        title=title,
        markdown="\n".join(lines).rstrip() + "\n",
        post_count=len(posts),
        author_count=len(grouped),
    )


def _render_full_report(
    posts: Iterable[Post],
    window: PeriodWindow,
    summary: Optional[RunSummary] = None,
    max_chars: int = 1200,
) -> ReportResult:
    posts = list(posts)
    grouped = _group_by_author(posts)
    title = "雪球关注动态 {} {}".format(
        window.start_local.strftime("%Y-%m-%d"),
        window.label,
    )
    lines = [
        "# {}".format(title),
        "",
        "时间段：{} 到 {}（北京时间）".format(
            window.start_local.strftime("%Y-%m-%d %H:%M"),
            window.end_local.strftime("%Y-%m-%d %H:%M"),
        ),
        "本段发言：{} 条，作者：{} 位".format(len(posts), len(grouped)),
    ]
    if summary is not None:
        lines.append(
            "采集结果：抓取 {}/{} 页，新增 {}，更新 {}，重复 {}{}".format(
                summary.pages_fetched,
                summary.pages_requested,
                summary.inserted_count,
                summary.updated_count,
                summary.duplicate_count,
                "，错误：{}".format(summary.error) if summary.error else "",
            )
        )
    lines.append("")

    if not posts:
        lines.append("本时间段没有新的发言。")
    for author, author_posts in grouped.items():
        lines.extend(["## {} ({})".format(author, len(author_posts)), ""])
        for post in author_posts:
            link = "[原帖]({})".format(post.url) if post.url else "原帖"
            lines.append("### {} {}".format(_format_local_time(post.created_at), link))
            lines.extend(["", _trim(post.text, max_chars), ""])
            quoted = _quoted_status(post)
            if quoted:
                quoted_link = " [{}]({})".format("链接", quoted.url) if quoted.url else ""
                lines.append("> 引用原文：{}{}".format(quoted.author_name, quoted_link))
                lines.append("> {}".format(_trim(quoted.text, max_chars)))
                lines.append("")
            interactions = _interaction_text(post, include_zero=True, separator=" / ")
            if interactions:
                lines.extend(["互动：{}".format(interactions), ""])

    return ReportResult(
        title=title,
        markdown="\n".join(lines).rstrip() + "\n",
        post_count=len(posts),
        author_count=len(grouped),
    )


def render_author_report(
    posts: Iterable[Post],
    window: PeriodWindow,
    summary: Optional[RunSummary] = None,
    max_chars: int = 300,
    style: str = "digest",
    author_limit: int = 3,
) -> ReportResult:
    if style == "full":
        return _render_full_report(posts, window, summary=summary, max_chars=max_chars)
    if style == "digest":
        return _render_digest_report(
            posts,
            window,
            summary=summary,
            max_chars=max_chars,
            author_limit=author_limit,
        )
    raise ValueError("unsupported report style {}".format(style))


def report_path(output_dir, window: PeriodWindow, style: str = "digest") -> Path:
    day_dir = Path(output_dir) / window.start_local.strftime("%Y") / window.start_local.strftime("%m") / window.start_local.strftime("%d")
    filename = "{}-{}-{}.{}.md".format(
        window.start_local.strftime("%H%M"),
        window.end_local.strftime("%H%M"),
        window.key,
        style,
    )
    return day_dir / filename


def write_report(
    report: ReportResult,
    output_dir,
    window: PeriodWindow,
    style: str = "digest",
) -> Path:
    path = report_path(output_dir, window, style=style)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(report.markdown, encoding="utf-8")
    return path
