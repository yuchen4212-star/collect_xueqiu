from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Post:
    id: str
    author_id: Optional[str]
    author_name: Optional[str]
    created_at: Optional[str]
    text: str
    html: str
    url: Optional[str]
    reply_count: Optional[int]
    retweet_count: Optional[int]
    fav_count: Optional[int]
    raw_json: str


@dataclass(frozen=True)
class UpsertCounts:
    inserted: int
    updated: int
    duplicate: int


@dataclass(frozen=True)
class RunSummary:
    pages_requested: int
    pages_fetched: int
    inserted_count: int
    updated_count: int
    duplicate_count: int
    error: Optional[str] = None
