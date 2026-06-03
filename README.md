# Xueqiu Collector

Local CLI for collecting posts from the Xueqiu users you follow.

## Setup

```powershell
pip install -e .[test]
python -m playwright install chromium
```

## Login

```powershell
xueqiu-collector auth
```

Log in to Xueqiu in the opened browser, then return to the terminal and press Enter.

## Collect

```powershell
xueqiu-collector collect --pages 3 --count 20
```

Collected posts are stored in `data/xueqiu.sqlite`.

## Inspect

```powershell
xueqiu-collector inspect --limit 20
```

## Export

```powershell
xueqiu-collector export --format jsonl --output data/exports/xueqiu-posts.jsonl
xueqiu-collector export --format csv --output data/exports/xueqiu-posts.csv
```

Runtime files under `data/` are ignored by Git.
