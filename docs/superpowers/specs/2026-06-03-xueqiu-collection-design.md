# Xueqiu Followed Posts Collection Design

## Goal

Build a local tool that collects posts from the people the user follows on Xueqiu, stores them locally, and exports them for later reading or analysis.

## Context

The repository is currently empty except for Git metadata. Xueqiu's FAQ says that after following a user, their posts appear in the user's "dynamic" page: https://xueqiu.com/about/faq/3/2. The first version should therefore collect from the authenticated dynamic timeline instead of trying to infer every followed user manually.

The tool must not store the user's Xueqiu password. It should keep data local to this repository and make login expiration visible instead of silently skipping data.

## Recommended Approach

Use a Python command-line tool with an isolated browser login profile. The user logs into Xueqiu once in that dedicated browser profile. The collector then reuses that profile to request the authenticated dynamic timeline, parse returned timeline items, and persist normalized rows in SQLite.

This approach is preferred over reading the user's everyday Chrome cookies because it avoids touching unrelated browser data. It is also preferred over manually pasting cookies because it is easier to refresh when the login expires.

## Alternatives Considered

1. Read the user's existing browser cookies.

   This is convenient when the user is already logged in, but it requires access to a broader browser profile and can be brittle across browser encryption, profile naming, and locked database files.

2. Store a manually pasted Cookie header in an `.env` file.

   This is simple to implement and can work as a fallback, but it is annoying when cookies expire and increases the chance of accidentally leaving session data in project files.

3. Crawl each followed user's profile page.

   This can become useful later for completeness checks, but the first version would need a separate way to discover the followed-user list and would not necessarily match what the user's dynamic page shows.

## Scope

The first version will include:

- `auth`: open or reuse a dedicated Xueqiu browser profile so the user can log in.
- `collect`: fetch one or more pages of the authenticated dynamic timeline.
- `inspect`: show recent stored posts and basic collection statistics.
- `export`: write stored posts to JSONL or CSV.
- SQLite storage under a local data directory.
- Duplicate handling by stable post ID.
- Error reporting for missing login, expired login, HTTP failures, parsing failures, and empty pages.
- Tests for parsing, storage, duplicate handling, pagination stop rules, export formatting, and login/error classification.

The first version will not include:

- Automatic username/password login.
- Cloud sync.
- A scheduled background daemon.
- A graphical dashboard.
- Guaranteed archival of every historical post before the first collection run.

## Command-Line Interface

The executable command will be `xueqiu-collector`.

`xueqiu-collector auth`

Opens the dedicated browser profile at the Xueqiu site. The command succeeds when the browser profile exists and the user has had a chance to log in. It does not need to prove login by collecting posts, because the user may run it solely to refresh the session.

`xueqiu-collector collect --pages 3 --count 20`

Collects timeline pages from the authenticated dynamic feed. Defaults should be conservative: a small page count, a short delay between requests, and clear output showing inserted rows, updated rows, duplicate rows, and failures.

`xueqiu-collector inspect --limit 20`

Prints recent stored posts with ID, author, created time, text preview, and URL.

`xueqiu-collector export --format jsonl --output data/exports/xueqiu-posts.jsonl`

Exports all stored posts in a deterministic order. CSV output uses UTF-8 with a BOM so common Windows spreadsheet tools can open Chinese text cleanly.

## Data Model

SQLite table `posts`:

- `id`: stable Xueqiu post ID, primary key.
- `author_id`: Xueqiu author ID when present.
- `author_name`: display name when present.
- `created_at`: post creation time as an ISO 8601 string when parseable.
- `text`: normalized text with HTML stripped.
- `html`: original HTML body when present.
- `url`: canonical post URL when derivable.
- `reply_count`: integer count when present.
- `retweet_count`: integer count when present.
- `fav_count`: integer count when present.
- `raw_json`: compact JSON for the original item.
- `collected_at`: ISO 8601 timestamp for this collection attempt.
- `updated_at`: ISO 8601 timestamp for the last upsert.

SQLite table `collection_runs`:

- `id`: integer primary key.
- `started_at`: ISO 8601 timestamp.
- `finished_at`: ISO 8601 timestamp when completed.
- `pages_requested`: requested page count.
- `pages_fetched`: successful page count.
- `inserted_count`: inserted post rows.
- `updated_count`: updated post rows.
- `duplicate_count`: unchanged existing post rows.
- `error`: final error message when the run fails.

## Data Flow

1. `auth` creates a dedicated browser profile directory under `data/browser-profile` and opens Xueqiu for manual login.
2. `collect` loads the same profile and requests authenticated dynamic timeline pages.
3. Each response is classified before parsing: success, unauthorized or expired login, HTTP failure, empty response, or malformed JSON.
4. Successful responses are parsed into normalized `Post` records.
5. The storage layer upserts records by `id`.
6. The run summary is written to `collection_runs`.
7. `inspect` and `export` read only from SQLite, so they work offline after collection.

## Error Handling

Login errors must be explicit. If the timeline request indicates the user is not logged in or the server returns an authentication-related error, the CLI prints a message telling the user to run `xueqiu-collector auth` again.

HTTP failures should include status code and requested page. Parsing failures should include the page number and enough context to debug without printing sensitive cookies. Empty pages stop pagination after recording that no more data was found.

The collector should use conservative delays between page requests and should not attempt to bypass access controls, captchas, or rate limits.

## Testing Strategy

Unit tests will drive implementation:

- Timeline parser converts representative Xueqiu-like JSON items into normalized `Post` objects.
- HTML text normalization strips tags and decodes common entities.
- Storage inserts new posts and updates existing posts by ID without duplicating rows.
- Pagination stops on empty pages and records run counts correctly.
- Exporter produces deterministic JSONL and CSV output.
- Error classifier maps unauthorized, HTTP failure, malformed JSON, and empty response cases to clear user-facing errors.

Network access and live Xueqiu login will be tested manually after the offline test suite passes.

## Privacy And Safety

The repository should ignore local runtime data such as `data/browser-profile`, SQLite databases, exported files, and `.env` files. The code should never print Cookie headers, passwords, or browser profile internals. Raw post JSON is stored because it is useful for later parsing improvements, but it remains local.

## Completion Criteria

The implementation is complete when:

1. The CLI can create or reuse a dedicated login profile.
2. The CLI can collect authenticated dynamic timeline posts from Xueqiu into SQLite.
3. Re-running collection deduplicates by post ID.
4. The CLI can inspect stored posts.
5. The CLI can export stored posts to JSONL and CSV.
6. Tests cover parser, storage, pagination, export, and error classification.
7. A manual run proves either successful live collection or, if login/network access is unavailable in the current environment, an explicit and accurate login/network error path.
