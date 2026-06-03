import csv
import json
from dataclasses import asdict
from pathlib import Path
from typing import Iterable

from .models import Post


CSV_FIELDS = [
    "id",
    "author_id",
    "author_name",
    "created_at",
    "text",
    "html",
    "url",
    "reply_count",
    "retweet_count",
    "fav_count",
    "raw_json",
]


def export_jsonl(posts: Iterable[Post], output) -> None:
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    ordered = sorted(posts, key=lambda post: post.id)
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        for post in ordered:
            fh.write(json.dumps(asdict(post), ensure_ascii=False, sort_keys=True))
            fh.write("\n")


def export_csv(posts: Iterable[Post], output) -> None:
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    ordered = sorted(posts, key=lambda post: post.id)
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for post in ordered:
            row = asdict(post)
            writer.writerow({field: row[field] for field in CSV_FIELDS})
