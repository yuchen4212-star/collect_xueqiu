import time

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

        counts = store.upsert_posts(posts)
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
    store.record_run(summary)
    return summary
