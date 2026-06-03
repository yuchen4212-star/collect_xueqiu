from xueqiu_collector import cli
from xueqiu_collector.models import RunSummary


def test_collect_defaults_match_spec():
    args = cli.build_parser().parse_args(["collect"])

    assert args.command == "collect"
    assert args.pages == 3
    assert args.count == 20
    assert args.delay == 1.0
    assert args.database == "data/xueqiu.sqlite"


def test_export_requires_supported_format_and_output():
    args = cli.build_parser().parse_args(
        ["export", "--format", "csv", "--output", "data/exports/posts.csv"]
    )

    assert args.command == "export"
    assert args.format == "csv"
    assert args.output == "data/exports/posts.csv"


def test_main_auth_invokes_auth_browser(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(cli, "open_auth_browser", lambda profile: calls.append(profile))

    result = cli.main(["auth", "--profile-dir", str(tmp_path / "profile")])

    assert result == 0
    assert calls == [str(tmp_path / "profile")]


def test_main_collect_prints_summary(monkeypatch, tmp_path, capsys):
    summary = RunSummary(
        pages_requested=3,
        pages_fetched=2,
        inserted_count=4,
        updated_count=1,
        duplicate_count=2,
        error=None,
    )
    monkeypatch.setattr(
        cli,
        "collect_timeline",
        lambda store, client, pages, count, delay: summary,
    )

    result = cli.main(["--database", str(tmp_path / "db.sqlite"), "collect"])

    assert result == 0
    output = capsys.readouterr().out
    assert "inserted=4" in output
    assert "updated=1" in output
    assert "duplicate=2" in output


def test_main_export_jsonl_uses_store(monkeypatch, tmp_path):
    calls = []

    class FakeStore:
        def __init__(self, path):
            self.path = path

        def init_schema(self):
            calls.append(("init", self.path))

        def list_posts(self, limit=None):
            calls.append(("list", limit))
            return []

    monkeypatch.setattr(cli, "Store", FakeStore)
    monkeypatch.setattr(
        cli, "export_jsonl", lambda posts, output: calls.append(("jsonl", output))
    )

    result = cli.main(
        [
            "--database",
            str(tmp_path / "db.sqlite"),
            "export",
            "--format",
            "jsonl",
            "--output",
            str(tmp_path / "posts.jsonl"),
        ]
    )

    assert result == 0
    assert ("list", None) in calls
    assert ("jsonl", str(tmp_path / "posts.jsonl")) in calls
