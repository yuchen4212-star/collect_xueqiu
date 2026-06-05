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
