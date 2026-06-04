import argparse
import sys
from datetime import datetime
from typing import Optional, Sequence

from .client import PlaywrightTimelineClient, open_auth_browser
from .collector import collect_timeline
from .exporter import export_csv, export_jsonl
from .notifier import notify
from .periods import CHINA_TZ, PERIOD_CHOICES, resolve_period_window
from .reporting import filter_posts_by_window, render_author_report, write_report
from .storage import Store


DEFAULT_DATABASE = "data/db/xueqiu.sqlite"
DEFAULT_REPORT_DIR = "data/reports"


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

    report = subparsers.add_parser("report")
    _add_report_args(report)

    collect_report = subparsers.add_parser("collect-report")
    collect_report.add_argument("--profile-dir", default="data/browser-profile")
    collect_report.add_argument("--pages", type=int, default=3)
    collect_report.add_argument("--count", type=int, default=20)
    collect_report.add_argument("--delay", type=float, default=1.0)
    _add_report_args(collect_report)

    return parser


def _add_report_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--period", choices=PERIOD_CHOICES, default="auto")
    parser.add_argument("--date", help="Local report date in YYYY-MM-DD")
    parser.add_argument("--output-dir", default=DEFAULT_REPORT_DIR)
    parser.add_argument("--max-chars", type=int, default=300)
    parser.add_argument("--style", choices=("digest", "full"), default="digest")
    parser.add_argument("--author-limit", type=int, default=3)
    parser.add_argument("--notify", action="store_true")


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


def _safe_console_text(text: str, encoding: Optional[str] = None) -> str:
    target_encoding = encoding or getattr(sys.stdout, "encoding", None) or "utf-8"
    return text.encode(target_encoding, errors="replace").decode(
        target_encoding, errors="replace"
    )


def _print_posts(posts) -> None:
    for post in posts:
        preview = post.text[:80].replace("\n", " ")
        line = "{}\t{}\t{}\t{}\t{}".format(
            post.id,
            post.author_name or "",
            post.created_at or "",
            preview,
            post.url or "",
        )
        print(_safe_console_text(line))


def _build_report(store, args, summary=None):
    window = resolve_period_window(
        args.period, now=datetime.now(CHINA_TZ), report_date=args.date
    )
    posts = filter_posts_by_window(store.list_posts(limit=None), window)
    report = render_author_report(
        posts,
        window,
        summary=summary,
        max_chars=args.max_chars,
        style=args.style,
        author_limit=args.author_limit,
    )
    path = write_report(report, args.output_dir, window, style=args.style)
    report_id = store.record_report(
        window=window,
        report=report,
        output_path=path,
        style=args.style,
    )
    print(
        _safe_console_text(
            "report={} report_id={} posts={} authors={}".format(
                path, report_id, report.post_count, report.author_count
            )
        )
    )
    if args.notify:
        result = notify(report.title, report.markdown)
        store.record_notification(
            report_id=report_id,
            channel=result.channel,
            sent=result.sent,
            message=result.message,
        )
        print(
            _safe_console_text(
                "notify={} sent={} {}".format(
                    result.channel, result.sent, result.message
                )
            )
        )
    return path


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

    if args.command == "report":
        _build_report(store, args)
        return 0

    if args.command == "collect-report":
        client = PlaywrightTimelineClient(args.profile_dir)
        summary = collect_timeline(
            store,
            client,
            pages=args.pages,
            count=args.count,
            delay=args.delay,
        )
        _print_summary(summary)
        _build_report(store, args, summary=summary)
        return 1 if summary.error else 0

    parser.error("unknown command {}".format(args.command))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
