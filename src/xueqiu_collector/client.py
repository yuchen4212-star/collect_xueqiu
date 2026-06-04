from pathlib import Path


HOME_TIMELINE_URL = (
    "https://xueqiu.com/v4/statuses/home_timeline.json?page={page}&count={count}"
)


def _sync_playwright():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError(
            "Playwright is not installed. Install dependencies with "
            "pip install -e . and install the browser with "
            "python -m playwright install chromium."
        ) from exc
    return sync_playwright()


class PlaywrightTimelineClient:
    def __init__(self, profile_dir):
        self.profile_dir = Path(profile_dir)

    def fetch_timeline_page(self, page: int, count: int):
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        url = HOME_TIMELINE_URL.format(page=page, count=count)
        with _sync_playwright() as playwright:
            context = playwright.chromium.launch_persistent_context(
                user_data_dir=str(self.profile_dir),
                headless=True,
            )
            response = context.request.get(url)
            status = response.status
            body = response.text()
            close = getattr(context, "close", None)
            if close is not None:
                close()
            return status, body


def open_auth_browser(profile_dir) -> None:
    path = Path(profile_dir)
    path.mkdir(parents=True, exist_ok=True)
    with _sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(
            user_data_dir=str(path),
            headless=False,
        )
        page = context.new_page()
        page.goto("https://xueqiu.com/")
        print("Log in to Xueqiu in the opened browser, then close the browser window.")
        context.wait_for_event("close", timeout=0)
