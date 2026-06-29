from xueqiu_collector.notifier import notify


def test_notify_skips_when_channel_is_not_configured():
    result = notify("title", "content", env={})

    assert result.sent is False
    assert result.channel == "none"


def test_notify_pushplus_posts_markdown_payload(monkeypatch):
    calls = []

    def fake_post(url, payload, timeout):
        calls.append((url, payload, timeout))
        return '{"code":200}'

    monkeypatch.setattr("xueqiu_collector.notifier._post_json", fake_post)

    result = notify(
        "标题",
        "# 内容",
        env={"XUEQIU_NOTIFY": "pushplus", "XUEQIU_PUSHPLUS_TOKEN": "token"},
    )

    assert result.sent is True
    assert calls[0][0] == "https://www.pushplus.plus/send"
    assert calls[0][1]["token"] == "token"
    assert calls[0][1]["template"] == "markdown"


def test_notify_pushplus_reports_api_error_as_unsent(monkeypatch):
    def fake_post(url, payload, timeout):
        return '{"code":999,"msg":"too large"}'

    monkeypatch.setattr("xueqiu_collector.notifier._post_json", fake_post)

    result = notify(
        "title",
        "content",
        env={"XUEQIU_NOTIFY": "pushplus", "XUEQIU_PUSHPLUS_TOKEN": "token"},
    )

    assert result.sent is False
    assert result.channel == "pushplus"
    assert "too large" in result.message


def test_notify_pushplus_truncates_content_before_posting(monkeypatch):
    calls = []

    def fake_post(url, payload, timeout):
        calls.append(payload)
        return '{"code":200,"msg":"ok"}'

    monkeypatch.setattr("xueqiu_collector.notifier._post_json", fake_post)

    result = notify(
        "title",
        "0123456789" * 20,
        env={
            "XUEQIU_NOTIFY": "pushplus",
            "XUEQIU_PUSHPLUS_TOKEN": "token",
            "XUEQIU_PUSHPLUS_MAX_CHARS": "80",
        },
    )

    assert result.sent is True
    assert len(calls[0]["content"]) <= 80
    assert "truncated" in calls[0]["content"]


def test_notify_pushplus_truncates_content_by_utf8_bytes(monkeypatch):
    calls = []

    def fake_post(url, payload, timeout):
        calls.append(payload)
        return '{"code":200,"msg":"ok"}'

    monkeypatch.setattr("xueqiu_collector.notifier._post_json", fake_post)

    result = notify(
        "title",
        "雪球报告" * 40,
        env={
            "XUEQIU_NOTIFY": "pushplus",
            "XUEQIU_PUSHPLUS_TOKEN": "token",
            "XUEQIU_PUSHPLUS_MAX_BYTES": "120",
        },
    )

    assert result.sent is True
    assert len(calls[0]["content"].encode("utf-8")) <= 120
    assert "truncated" in calls[0]["content"]


def test_notify_reads_persistent_windows_environment_when_process_env_is_stale(monkeypatch):
    calls = []

    def fake_post(url, payload, timeout):
        calls.append((url, payload, timeout))
        return '{"code":200}'

    monkeypatch.setattr("xueqiu_collector.notifier.os.environ", {})
    monkeypatch.setattr(
        "xueqiu_collector.notifier._get_persistent_environment",
        lambda: {
            "XUEQIU_NOTIFY": "pushplus",
            "XUEQIU_PUSHPLUS_TOKEN": "persisted-token",
        },
        raising=False,
    )
    monkeypatch.setattr("xueqiu_collector.notifier._post_json", fake_post)

    result = notify("title", "content")

    assert result.sent is True
    assert result.channel == "pushplus"
    assert calls[0][1]["token"] == "persisted-token"
