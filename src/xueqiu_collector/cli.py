import argparse
from typing import Optional, Sequence


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


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    parser.parse_args(argv)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
