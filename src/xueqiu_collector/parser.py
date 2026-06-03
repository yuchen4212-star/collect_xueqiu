import json
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

from .models import Post
from .text import normalize_html_text


def _timeline_items(payload: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
    for key in ("home_timeline", "list", "statuses"):
        items = payload.get(key)
        if isinstance(items, list):
            return [item for item in items if isinstance(item, dict)]
    return []


def _created_at(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        seconds = float(value) / 1000 if value > 10_000_000_000 else float(value)
        return datetime.fromtimestamp(seconds, timezone.utc).isoformat()
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _count(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _first_present(item: Dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in item and item[key] is not None:
            return item[key]
    return None


def _url(author_id: Optional[str], post_id: str) -> Optional[str]:
    if author_id:
        return "https://xueqiu.com/{}/{}".format(author_id, post_id)
    return "https://xueqiu.com/statuses/{}".format(post_id)


def parse_timeline_payload(payload: Dict[str, Any]) -> List[Post]:
    posts: List[Post] = []
    for item in _timeline_items(payload):
        raw_id = item.get("id") or item.get("status_id")
        if raw_id is None:
            continue
        post_id = str(raw_id)
        user = item.get("user") if isinstance(item.get("user"), dict) else {}
        author_id = str(user["id"]) if user.get("id") is not None else None
        author_name = user.get("screen_name") or user.get("name")
        html = str(item.get("text") or item.get("description") or "")
        posts.append(
            Post(
                id=post_id,
                author_id=author_id,
                author_name=str(author_name) if author_name is not None else None,
                created_at=_created_at(item.get("created_at")),
                text=normalize_html_text(html),
                html=html,
                url=_url(author_id, post_id),
                reply_count=_count(_first_present(item, "reply_count", "comments_count")),
                retweet_count=_count(
                    _first_present(item, "retweet_count", "retweets_count")
                ),
                fav_count=_count(_first_present(item, "fav_count", "like_count")),
                raw_json=json.dumps(item, ensure_ascii=False, separators=(",", ":")),
            )
        )
    return posts
