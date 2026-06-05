# collect_xueqiu

Collect posts from the Xueqiu users you follow, store them locally, generate
readable period reports, and optionally push those reports through PushPlus,
email, or a webhook.

This project is designed for personal use: it keeps your login cookies and
collected data on your own machine, while Git tracks only the source code and
documentation.

## Features

- Collect followed Xueqiu timeline posts with a logged-in browser profile.
- Collect a specific user's timeline for a date range with `collect-user`.
- Store posts in SQLite with author, quote, collection, report, and notification
  metadata tables.
- Keep source membership indexes so followed-feed posts and single-user posts
  can share one database without getting mixed together.
- Generate Beijing-time period reports:
  - `overnight`: 00:00 to 09:30
  - `morning`: 09:30 to 12:30
  - `midday`: 12:30 to 14:50
  - `evening`: 14:50 to 24:00
- Render digest reports grouped by author, with expandable overflow sections.
- Split replies, reply context, and quoted originals into readable conversation
  blocks.
- Send reports through PushPlus, SMTP email, or a generic JSON webhook.
- Generate a local one-user evidence pack with `user-report`.
- Keep runtime files under layered `data/` directories that are ignored by Git.

## Install

```powershell
pip install .[test]
python -m playwright install chromium
```

## Login

```powershell
xueqiu-collector auth
```

Log in to Xueqiu in the opened browser, then close the browser window. The
browser profile is stored under `data/browser-profile/`.

## Collect

```powershell
xueqiu-collector collect --pages 3 --count 20
```

Collected posts are stored in `data/db/xueqiu.sqlite`.

Collect a specific user's timeline since a Beijing local date:

```powershell
xueqiu-collector collect-user --user-id 2292705444 --since-date 2025-06-04 --pages 500
```

The command stops when it reaches a page whose dated posts are all older than
the cutoff date. Xueqiu currently accepts `count` values up to `20` for this
endpoint.

## Report

Generate a report for the most recently completed period:

```powershell
xueqiu-collector report --period auto
```

Collect first, then generate and optionally push the report:

```powershell
xueqiu-collector collect-report --period auto --notify
```

Rebuild a specific local-date window:

```powershell
xueqiu-collector report --period morning --date 2026-06-04
```

Reports are written under `data/reports/YYYY/MM/DD/`, for example:

```text
data/reports/2026/06/04/0930-1230-morning.digest.md
```

Generate a one-user analysis evidence pack from already collected user posts:

```powershell
xueqiu-collector user-report --user-id 2292705444 --since-date 2025-06-04
```

User analysis files are written under `data/analysis/users/<user-id>/<since-date>/`.

## Report Styles

The default style is `digest`:

- Up to 3 posts per author are shown first.
- Extra posts are collapsed into expandable `<details>` blocks.
- Reply text, prior context, and quoted originals are separated.
- Links are shown as compact `[原帖]` and `[引用]` references.

Render every post without collapsing:

```powershell
xueqiu-collector report --period morning --style full
```

Change how many posts are visible per author:

```powershell
xueqiu-collector report --period morning --author-limit 5
```

## Notifications

Set `XUEQIU_NOTIFY` to choose a channel. If it is unset, reports are only written
locally.

PushPlus:

```powershell
[Environment]::SetEnvironmentVariable('XUEQIU_NOTIFY','pushplus','User')
[Environment]::SetEnvironmentVariable('XUEQIU_PUSHPLUS_TOKEN','your-token','User')
```

SMTP email:

```powershell
[Environment]::SetEnvironmentVariable('XUEQIU_NOTIFY','email','User')
[Environment]::SetEnvironmentVariable('XUEQIU_EMAIL_HOST','smtp.example.com','User')
[Environment]::SetEnvironmentVariable('XUEQIU_EMAIL_PORT','587','User')
[Environment]::SetEnvironmentVariable('XUEQIU_EMAIL_USER','you@example.com','User')
[Environment]::SetEnvironmentVariable('XUEQIU_EMAIL_PASSWORD','your-password','User')
[Environment]::SetEnvironmentVariable('XUEQIU_EMAIL_TO','you@example.com','User')
```

Generic JSON webhook:

```powershell
[Environment]::SetEnvironmentVariable('XUEQIU_NOTIFY','webhook','User')
[Environment]::SetEnvironmentVariable('XUEQIU_WEBHOOK_URL','https://example.com/webhook','User')
```

## Export

Exports are manual snapshots. Keep them date-scoped:

```powershell
xueqiu-collector export --format jsonl --output data/exports/2026/06/04/posts.jsonl
xueqiu-collector export --format csv --output data/exports/2026/06/04/posts.csv
```

## Runtime Layout

```text
data/
  db/
    xueqiu.sqlite          # SQLite source of truth
  browser-profile/         # Xueqiu login cookies
  reports/YYYY/MM/DD/      # generated Markdown reports
  analysis/users/...       # generated single-user analysis reports
  exports/YYYY/MM/DD/      # manual CSV/JSONL exports
```

Runtime files under `data/` are ignored by Git.

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Data Model](docs/DATA_MODEL.md)
- [Operations](docs/OPERATIONS.md)

## Tests

On this Windows Anaconda environment, disable third-party pytest plugin
autoloading:

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest -v
```
