from contextlib import contextmanager
from pathlib import Path


HOME_TIMELINE_URL = (
    "https://xueqiu.com/v4/statuses/home_timeline.json?page={page}&count={count}"
)
USER_TIMELINE_URL = (
    "https://xueqiu.com/statuses/user_timeline.json?"
    "user_id={user_id}&page={page}&count={count}"
)
PAGE_TIMEOUT_MS = 30000


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
        self._session_page = None

    def fetch_timeline_page(self, page: int, count: int):
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        url = HOME_TIMELINE_URL.format(page=page, count=count)
        return self._fetch_url(url)

    def fetch_user_timeline_page(self, user_id: str, page: int, count: int):
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        url = USER_TIMELINE_URL.format(user_id=user_id, page=page, count=count)
        return self._fetch_url(url)

    def _fetch_url(self, url: str):
        if self._session_page is not None:
            return self._fetch_with_page(self._session_page, url)

        self.profile_dir.mkdir(parents=True, exist_ok=True)
        with _sync_playwright() as playwright:
            context = playwright.chromium.launch_persistent_context(
                user_data_dir=str(self.profile_dir),
                headless=False,
            )
            try:
                page_obj = self._new_ready_page(context)
                return self._fetch_with_page(page_obj, url)
            finally:
                close = getattr(context, "close", None)
                if close is not None:
                    close()

    @contextmanager
    def open_session(self):
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        with _sync_playwright() as playwright:
            context = playwright.chromium.launch_persistent_context(
                user_data_dir=str(self.profile_dir),
                headless=False,
            )
            try:
                self._session_page = self._new_ready_page(context)
                yield self
            finally:
                self._session_page = None
                close = getattr(context, "close", None)
                if close is not None:
                    close()

    def _new_ready_page(self, context):
        page_obj = context.new_page()
        page_obj.set_default_timeout(PAGE_TIMEOUT_MS)
        page_obj.goto(
            "https://xueqiu.com/",
            wait_until="domcontentloaded",
            timeout=PAGE_TIMEOUT_MS,
        )
        return page_obj

    def _fetch_with_page(self, page_obj, url: str):
        response = page_obj.goto(
            url,
            wait_until="domcontentloaded",
            timeout=PAGE_TIMEOUT_MS,
        )
        page_obj.wait_for_load_state("domcontentloaded")
        body = page_obj.text_content("body") or ""
        status = response.status if response is not None else 0
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
