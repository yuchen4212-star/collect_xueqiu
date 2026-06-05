# Mac Migration

Use GitHub for source code and documentation only. Keep local runtime state out
of GitHub:

- `data/db/xueqiu.sqlite`: local SQLite history
- `data/browser-profile/`: Xueqiu login cookies
- `data/reports/`, `data/exports/`, `data/analysis/`: derived local files
- notification tokens and email passwords

## Before Pushing From Windows

Check the working tree:

```powershell
git status --short
git ls-files data .env
```

Expected: no `data/` files and no `.env` files are tracked.

Back up the SQLite database so the Mac can keep the same historical timeline:

```powershell
New-Item -ItemType Directory -Force data\db\backups
Compress-Archive -Path data\db\xueqiu.sqlite -DestinationPath data\db\backups\xueqiu.sqlite.backup.zip
```

Copy `data\db\backups\xueqiu.sqlite.backup.zip` to a private location such as an
external drive, iCloud Drive, OneDrive, or another private backup tool.

Do not rely on copying `data/browser-profile/` across operating systems. Run
`xueqiu-collector auth` again on the Mac.

## Clone And Install On Mac

```bash
git clone https://github.com/yuchen4212-star/collect_xueqiu.git
cd collect_xueqiu

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install '.[test]'
python -m playwright install chromium
```

Run the tests:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q
```

## Restore Local State On Mac

Restore the SQLite database backup:

```bash
mkdir -p data/db
unzip xueqiu.sqlite.backup.zip -d /tmp/xueqiu-db-restore
cp /tmp/xueqiu-db-restore/data/db/xueqiu.sqlite data/db/xueqiu.sqlite
```

Create a fresh Xueqiu browser login:

```bash
xueqiu-collector auth
```

Log in in the opened browser, then close the browser window.

## Configure Notifications On Mac

For an interactive shell, add these to `~/.zshrc`:

```bash
export XUEQIU_NOTIFY=pushplus
export XUEQIU_PUSHPLUS_TOKEN='your-token'
```

Reload the shell:

```bash
source ~/.zshrc
```

For scheduled jobs, set the same variables in the scheduler environment. Do not
assume a cron or launchd job can read `~/.zshrc`.

Test notification delivery:

```bash
xueqiu-collector report --period auto --notify
```

Expected: `notify=pushplus sent=True`.

## Daily Use

```bash
xueqiu-collector collect-report --period overnight --notify
```

Reports are still written under `data/reports/YYYY/MM/DD/`; those files remain
local and ignored by Git.
