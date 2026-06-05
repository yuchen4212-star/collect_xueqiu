import time
from datetime import datetime, timezone

from .errors import ResponseKind, classify_response
from .models import RunSummary
from .parser import parse_timeline_payload


def collect_timeline(store, client, pages: int, count: int, delay: float) -> RunSummary:
    store.init_schema()
    inserted = updated = duplicate = pages_fetched = 0
    error = None

    for page in range(1, pages + 1):
        status_code, body = client.fetch_timeline_page(page=page, count=count)
        classified = classify_response(status_code, body)
        if classified.kind != ResponseKind.SUCCESS:
            error = "Page {}: {}".format(page, classified.message)
            break

        posts = parse_timeline_payload(classified.data)
        if not posts:
            break

        counts = store.upsert_posts(
            posts,
            source_key="home",
            source_type="home",
            source_id=None,
            source_label="followed timeline",
        )
        inserted += counts.inserted
        updated += counts.updated
        duplicate += counts.duplicate
        pages_fetched += 1

        if delay > 0 and page < pages:
            time.sleep(delay)

    summary = RunSummary(
        pages_requested=pages,
        pages_fetched=pages_fetched,
        inserted_count=inserted,
        updated_count=updated,
        duplicate_count=duplicate,
        error=error,
    )
    store.record_run(summary, source_key="home")
    return summary


def _parse_datetime(value):
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def _is_since(post, since: datetime) -> bool:
    created_at = _parse_datetime(post.created_at)
    if created_at is None:
        return False
    return created_at.astimezone(timezone.utc) >= since.astimezone(timezone.utc)


def _all_dated_posts_are_old(posts, since: datetime) -> bool:
    dated = [_parse_datetime(post.created_at) for post in posts]
    dated = [value for value in dated if value is not None]
    if not dated:
        return False
    cutoff = since.astimezone(timezone.utc)
    return all(value.astimezone(timezone.utc) < cutoff for value in dated)


def collect_user_timeline(
    store,
    client,
    user_id: str,
    pages: int,
    count: int,
    delay: float,
    since: datetime,
    start_page: int = 1,
) -> RunSummary:
    open_session = getattr(client, "open_session", None)
    if callable(open_session):
        with open_session():
            return _collect_user_timeline_pages(
                store,
                client,
                user_id=user_id,
                pages=pages,
                count=count,
                delay=delay,
                since=since,
                start_page=start_page,
            )
    return _collect_user_timeline_pages(
        store,
        client,
        user_id=user_id,
        pages=pages,
        count=count,
        delay=delay,
        since=since,
        start_page=start_page,
    )


def _collect_user_timeline_pages(
    store,
    client,
    user_id: str,
    pages: int,
    count: int,
    delay: float,
    since: datetime,
    start_page: int,
) -> RunSummary:
    store.init_schema()
    inserted = updated = duplicate = pages_fetched = 0
    error = None
    source_key = "user:{}".format(user_id)

    for offset in range(pages):
        page_number = start_page + offset
        status_code, body = client.fetch_user_timeline_page(
            user_id=user_id, page=page_number, count=count
        )
        classified = classify_response(status_code, body)
        if classified.kind != ResponseKind.SUCCESS:
            error = "Page {}: {}".format(page_number, classified.message)
            break

        posts = parse_timeline_payload(classified.data)
        if not posts:
            break

        selected = [post for post in posts if _is_since(post, since)]
        if selected:
            counts = store.upsert_posts(
                selected,
                source_key=source_key,
                source_type="user",
                source_id=user_id,
                source_label="Xueqiu user {}".format(user_id),
            )
            inserted += counts.inserted
            updated += counts.updated
            duplicate += counts.duplicate
        pages_fetched += 1

        if _all_dated_posts_are_old(posts, since):
            break

        if delay > 0 and offset < pages - 1:
            time.sleep(delay)

    summary = RunSummary(
        pages_requested=pages,
        pages_fetched=pages_fetched,
        inserted_count=inserted,
        updated_count=updated,
        duplicate_count=duplicate,
        error=error,
    )
    store.record_run(summary, source_key=source_key)
    return summary
