# 24 November 2026 — One Image

make.fun bounty entry for the competition **"Sum up 24 November's world news in one image"**.

## Description

`main.py` condenses the world news of **Tuesday, 24 November 2026** into a single image. It gathers the day's headlines, ranks them by significance, and renders them onto one canvas as a compact visual summary.

## How to run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt   # if the entry ships one
python main.py
```

Output: `out/2026-11-24.png`.

Optional:

```bash
python main.py --date 2026-11-24 --out out/2026-11-24.png
```

## What it does