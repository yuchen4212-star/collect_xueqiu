import html
import re


TAG_RE = re.compile(r"<[^>]+>")
SPACE_RE = re.compile(r"\s+")


def normalize_html_text(value: str) -> str:
    unescaped = html.unescape(value or "")
    without_tags = TAG_RE.sub(" ", unescaped)
    return SPACE_RE.sub(" ", without_tags).strip()
