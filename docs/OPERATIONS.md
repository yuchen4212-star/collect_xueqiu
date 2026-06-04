# Operations

This document covers day-to-day use, scheduling, and recovery.

## Initial Setup

```powershell
pip install .[test]
python -m playwright install chromium
xueqiu-collector auth
```

After `auth`, log in to Xueqiu in the browser and close the browser window.

## Manual Collection

```powershell
xueqiu-collector collect --pages 3 --count 20
```

Inspect the latest local rows:

```powershell
xueqiu-collector inspect --limit 20
```

## Manual Report

```powershell
xueqiu-collector report --period auto
```

Rebuild a specific period:

```powershell
xueqiu-collector report --period morning --date 2026-06-04
```

Collect and report together:

```powershell
xueqiu-collector collect-report --period auto --notify
```

## Daily Periods

All windows use Beijing time.

```text
overnight  00:00 -> 09:30
morning    09:30 -> 12:30
midday     12:30 -> 14:50
evening    14:50 -> 24:00
```

Recommended run points:

```text
00:00  collect-report --period evening --notify
09:30  collect-report --period overnight --notify
12:30  collect-report --period morning --notify
14:50  collect-report --period midday --notify
```

## PushPlus

Configure PushPlus with user-level environment variables:

```powershell
[Environment]::SetEnvironmentVariable('XUEQIU_NOTIFY','pushplus','User')
[Environment]::SetEnvironmentVariable('XUEQIU_PUSHPLUS_TOKEN','your-token','User')
```

Open a new shell so the environment variables are visible, then test:

```powershell
xueqiu-collector report --period morning --date 2026-06-04 --notify
```

Do not commit tokens to Git.

## Data Backup

Back up the SQLite database:

```powershell
Copy-Item data/db/xueqiu.sqlite data/db/xueqiu.backup.sqlite
```

Reports and exports can be regenerated, but they are safe to back up if you want
an archive.

## Troubleshooting

### Login expired

Run:

```powershell
xueqiu-collector auth
```

Then log in again and close the browser.

### PushPlus sends nothing

Check:

- `XUEQIU_NOTIFY=pushplus`
- `XUEQIU_PUSHPLUS_TOKEN` is set in the current shell
- PushPlus account can receive messages
- PushPlus token has not been rotated

### Tests

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest -v
```
