import pytest

from xueqiu_collector.client import PlaywrightTimelineClient, open_auth_browser


def test_fetch_timeline_page_uses_home_timeline_endpoint(monkeypatch, tmp_path):
    events = []

    class FakeResponse:
        status = 200

    class FakePage:
        def goto(self, url):
            events.append(("goto", url))
            return FakeResponse()

        def wait_for_load_state(self, state):
            events.append(("wait_for_load_state", state))

        def text_content(self, selector):
            events.append(("text_content", selector))
            return "{\"home_timeline\":[]}"

    class FakeContext:
        def new_page(self):
            events.append(("new_page", None))
            return FakePage()

        def close(self):
            events.append(("close", None))

    class FakeChromium:
        def launch_persistent_context(self, user_data_dir, headless):
            assert str(tmp_path / "profile") == user_data_dir
            assert headless is False
            return FakeContext()

    class FakePlaywright:
        chromium = FakeChromium()

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(
        "xueqiu_collector.client._sync_playwright",
        lambda: FakePlaywright(),
    )

    client = PlaywrightTimelineClient(tmp_path / "profile")
    status, body = client.fetch_timeline_page(page=2, count=30)

    assert status == 200
    assert body == "{\"home_timeline\":[]}"
    assert ("goto", "https://xueqiu.com/") in events
    assert (
        "goto",
        "https://xueqiu.com/v4/statuses/home_timeline.json?page=2&count=30",
    ) in events
    assert events[-1] == ("close", None)


def test_open_auth_browser_waits_for_browser_close(monkeypatch, tmp_path):
    events = []

    class FakePage:
        def goto(self, url):
            events.append(("goto", url))

    class FakeContext:
        def new_page(self):
            events.append(("new_page", None))
            return FakePage()

        def close(self):
            events.append(("close", None))

        def wait_for_event(self, event_name, timeout=None):
            events.append(("wait_for_event", event_name, timeout))

    class FakeChromium:
        def launch_persistent_context(self, user_data_dir, headless):
            events.append(("launch", user_data_dir, headless))
            return FakeContext()

    class FakePlaywright:
        chromium = FakeChromium()

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(
        "xueqiu_collector.client._sync_playwright",
        lambda: FakePlaywright(),
    )

    open_auth_browser(tmp_path / "profile")

    assert events[0] == ("launch", str(tmp_path / "profile"), False)
    assert ("goto", "https://xueqiu.com/") in events
    assert events[-1] == ("wait_for_event", "close", 0)


def test_missing_playwright_dependency_has_clear_message(monkeypatch, tmp_path):
    def missing_playwright():
        raise RuntimeError(
            "Playwright is not installed. Install dependencies with pip install -e . "
            "and install the browser with python -m playwright install chromium."
        )

    monkeypatch.setattr("xueqiu_collector.client._sync_playwright", missing_playwright)

    with pytest.raises(RuntimeError) as excinfo:
        open_auth_browser(tmp_path / "profile")

    assert "python -m playwright install chromium" in str(excinfo.value)
