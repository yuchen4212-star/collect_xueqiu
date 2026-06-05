# Operations

This document covers day-to-day use, scheduling, and recovery.

## Initial Setup

Windows PowerShell:

```powershell
pip install .[test]
python -m playwright install chromium
xueqiu-collector auth
```

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install '.[test]'
python -m playwright install chromium
xueqiu-collector auth
```

After `auth`, log in to Xueqiu in the browser and close the browser window.

## Manual Collection

```powershell
xueqiu-collector collect --pages 3 --count 20
```

Collect one user's timeline since a Beijing local date:

```powershell
xueqiu-collector collect-user --user-id 2292705444 --since-date 2025-06-04 --pages 500
```

For very active users, long runs can be resumed by page segment:

```powershell
xueqiu-collector collect-user --user-id 2292705444 --since-date 2025-06-04 --start-page 101 --pages 100
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

Generate a one-user analysis evidence pack:

```powershell
xueqiu-collector user-report --user-id 2292705444 --since-date 2025-06-04
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

Configure PushPlus with user-level environment variables on Windows:

```powershell
[Environment]::SetEnvironmentVariable('XUEQIU_NOTIFY','pushplus','User')
[Environment]::SetEnvironmentVariable('XUEQIU_PUSHPLUS_TOKEN','your-token','User')
```

On macOS/Linux, export the variables in the shell or scheduler environment:

```bash
export XUEQIU_NOTIFY=pushplus
export XUEQIU_PUSHPLUS_TOKEN='your-token'
```

Open a new shell or reload your shell profile so the environment variables are
visible, then test:

```powershell
xueqiu-collector report --period morning --date 2026-06-04 --notify
```

Do not commit tokens to Git.

## Data Backup

Back up the SQLite database:

```powershell
Copy-Item data/db/xueqiu.sqlite data/db/xueqiu.backup.sqlite
```

For a Mac migration, keep this backup private and restore it to
`data/db/xueqiu.sqlite` after cloning the repository. Re-run
`xueqiu-collector auth` on the Mac instead of copying `data/browser-profile/`
across operating systems.

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
