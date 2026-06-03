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
        print(
            "{}\t{}\t{}\t{}\t{}".format(
                post.id,
                post.author_name or "",
                post.created_at or "",
                preview,
                post.url or "",
            )
        )


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
