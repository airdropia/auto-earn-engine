#!/usr/bin/env python3
"""Autonomous LIVE HEALTH reporter (runs in CI).

Writes metrics/live-health.md with ground-truth facts fetched live:
  - storefront HTTP status (urllib)
  - catalog product count (local catalog.json)
  - repo traffic (gh api, optional)
  - latest CI run status (gh api, optional)

Driven by .github/workflows/state-sync.yml (daily cron + on-demand).
The generated file is committed to the repo so any session/agent can read
the freshest live facts at any time. Idempotent (overwrites in place).

No deps beyond Python stdlib. Network calls are best-effort.

Usage:  python3 pipeline/sync_state.py   (from repo root)
Env:    SKIP_NETWORK=1  -> only local facts, no network
        GH_TOKEN=...    -> authenticated gh calls (optional)
"""
from __future__ import annotations

import json
import os
import subprocess
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "metrics" / "live-health.md"
BASE = "https://airdropia.github.io/auto-earn-engine"
SKIP_NETWORK = os.environ.get("SKIP_NETWORK") == "1"


def sh(cmd: list[str], timeout: int = 20) -> str:
    try:
        return subprocess.run(cmd, capture_output=True, text=True,
                              timeout=timeout).stdout.strip()
    except Exception:
        return ""


def http_status(url: str) -> str:
    if SKIP_NETWORK:
        return "n/a"
    try:
        req = urllib.request.Request(url, method="HEAD",
                                     headers={"User-Agent": "sync_state"})
        with urllib.request.urlopen(req, timeout=15) as r:
            return str(r.status)
    except Exception as e:
        return f"ERR {getattr(e, 'code', '')}"


def main() -> None:
    # ---- collect facts ----
    home = http_status(f"{BASE}/")
    buyer = ""
    for pid in ("flagship-22acf7b3",):
        u = f"{BASE}/p/{pid}/"
        if http_status(u) == "200":
            buyer = u
            break

    catalog_count = "n/a"
    cat = ROOT / "catalog" / "catalog.json"
    if cat.exists():
        try:
            catalog_count = str(len(json.loads(cat.read_text(encoding="utf-8"))))
        except Exception:
            pass

    latest_run = "n/a"
    if not SKIP_NETWORK:
        r = sh(["gh", "run", "list", "--workflow=flagship-test.yml",
                "--limit=1", "--json=conclusion,createdAt", "--jq=.[0]"])
        if r:
            try:
                d = json.loads(r)
                latest_run = f"{d.get('conclusion','?')} @ {d.get('createdAt','?')}"
            except Exception:
                latest_run = r

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    lines = [
        "# LIVE HEALTH (auto-generated)",
        "",
        f"_Auto-updated {now} by `pipeline/sync_state.py` (CI: state-sync workflow). ",
        "Do not hand-edit; next run overwrites._",
        "",
        "| Check | Value |",
        "|---|---|",
        f"| Storefront `/` | {home} |",
        f"| Buyer page | {buyer or 'none 200'} |",
        f"| Catalog products | {catalog_count} |",
        f"| Latest flagship CI run | {latest_run} |",
        "",
    ]

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"live-health updated: {now} home={home} catalog={catalog_count} run={latest_run}")


if __name__ == "__main__":
    main()
