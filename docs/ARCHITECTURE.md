# Architecture

`collect_xueqiu` is a local CLI application. Its boundaries are intentionally
simple:

```text
Browser profile -> Xueqiu timeline client -> parser -> SQLite store
                                                   -> reports
                                                   -> notifications
```

## Modules

- `xueqiu_collector.client`
  - Uses Playwright with a persistent browser profile.
  - Fetches followed timeline pages through the logged-in session.
- `xueqiu_collector.collector`
  - Coordinates paging, response classification, parsing, storage, and run
    summaries.
- `xueqiu_collector.parser`
  - Converts Xueqiu timeline payloads into `Post` models.
  - Keeps the full raw JSON for future extraction.
- `xueqiu_collector.storage`
  - Owns SQLite schema creation, post upserts, author indexing, quote indexing,
    report records, notification records, and collection run records.
- `xueqiu_collector.periods`
  - Resolves the Beijing-time reporting windows.
- `xueqiu_collector.reporting`
  - Filters posts by period and renders Markdown reports.
- `xueqiu_collector.notifier`
  - Sends Markdown content through PushPlus, SMTP email, or a JSON webhook.
- `xueqiu_collector.cli`
  - Exposes `auth`, `collect`, `inspect`, `export`, `report`, and
    `collect-report`.

## Design Principles

- SQLite is the source of truth. Reports and exports are derived artifacts.
- Runtime data stays under `data/` and is ignored by Git.
- The collector stores raw JSON so new fields can be indexed later without
  recollecting old posts.
- Reporting is separated from collection so reports can be rebuilt without
  touching Xueqiu.
- Notification attempts are recorded separately from generated reports.

## Period Workflow

1. `collect-report` resolves a period such as `morning`.
2. The collector fetches recent timeline pages and upserts posts.
3. The report generator filters posts whose `created_at` falls inside the
   period window.
4. The report is written under `data/reports/YYYY/MM/DD/`.
5. The `reports` table records the generated report.
6. If `--notify` is passed, the notifier sends the Markdown and records the
   result in `notifications`.

## GitHub Safety

Do not commit runtime data:

- `data/db/xueqiu.sqlite`
- `data/browser-profile/`
- `data/reports/`
- `data/exports/`
- environment variables containing tokens or passwords

Those paths are ignored by `.gitignore`.
