# Data Model

The database lives at:

```text
data/db/xueqiu.sqlite
```

## Tables

### `posts`

Primary fact table for collected Xueqiu posts.

Important columns:

- `id`: Xueqiu status id, primary key.
- `author_id`, `author_name`: author identity at collection time.
- `created_at`: post time.
- `text`: normalized readable text.
- `html`: original HTML-ish text field.
- `url`: Xueqiu post URL.
- `reply_count`, `retweet_count`, `fav_count`: interaction counters.
- `raw_json`: full Xueqiu status JSON.
- `collected_at`, `updated_at`: local collection metadata.

### `authors`

Author index extracted from collected posts.

- `id`: author id.
- `name`: most recent seen screen name.
- `last_seen_at`: last local time this author appeared in collection.

### `post_quotes`

Quoted or reposted originals extracted from `raw_json.retweeted_status`.

- `post_id`: collected post that contains the quote.
- `quoted_post_id`: quoted/original status id.
- `quoted_author_id`, `quoted_author_name`: quoted/original author.
- `quoted_text`: normalized quoted/original text.
- `quoted_url`: URL for the quoted/original post.
- `raw_json`: quoted/original raw JSON.
- `updated_at`: local extraction time.

### `collection_runs`

One row per collection run.

- requested and fetched page counts
- inserted, updated, duplicate counts
- error text if the run stopped early

### `reports`

One row per generated report.

- period key and label
- local and UTC window boundaries
- report style
- output path
- post and author counts

### `notifications`

One row per notification attempt.

- `report_id`: related report if available.
- `channel`: `pushplus`, `email`, `webhook`, or `none`.
- `sent`: `1` for sent, `0` for skipped or failed.
- `message`: provider response or local skip/failure reason.

## Why Keep Raw JSON?

Xueqiu response fields can change, and useful fields may be discovered later.
Keeping `raw_json` makes it possible to add new indexes without recollecting old
posts.

## Derived Artifacts

Reports and exports are not source-of-truth data. They can be regenerated from
SQLite when needed.
