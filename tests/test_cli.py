from xueqiu_collector.cli import build_parser


def test_collect_defaults_match_spec():
    args = build_parser().parse_args(["collect"])

    assert args.command == "collect"
    assert args.pages == 3
    assert args.count == 20
    assert args.delay == 1.0
    assert args.database == "data/xueqiu.sqlite"


def test_export_requires_supported_format_and_output():
    args = build_parser().parse_args(
        ["export", "--format", "csv", "--output", "data/exports/posts.csv"]
    )

    assert args.command == "export"
    assert args.format == "csv"
    assert args.output == "data/exports/posts.csv"
