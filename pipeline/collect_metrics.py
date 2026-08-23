#!/usr/bin/env python3
"""Weekly metrics collector.

Records catalog size plus GitHub repository traffic (views/clones, 14-day
window) into metrics/metrics.json. Traffic API failures degrade to zero so
the job stays green on brand-new repositories.
"""
from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
METRICS_DIR = ROOT / "metrics"


def gh_api(endpoint: str) -> dict:
    env = os.environ.copy()
    try:
        result = subprocess.run(
            ["gh", "api", endpoint],
            capture_output=True,
            text=True,
            check=True,
            env=env,
        )
        return json.loads(result.stdout)
    except (subprocess.CalledProcessError, json.JSONDecodeError):
        return {}


def main() -> None:
    catalog_path = ROOT / "catalog" / "catalog.json"
    catalog_size = 0
    if catalog_path.exists():
        catalog_size = len(json.loads(catalog_path.read_text(encoding="utf-8")))

    repo = os.environ.get("GITHUB_REPOSITORY", "")
    views = gh_api(f"repos/{repo}/traffic/views").get("count", 0)
    clones = gh_api(f"repos/{repo}/traffic/clones").get("count", 0)

    METRICS_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "catalog_products": catalog_size,
        "repo_views_14d": views,
        "repo_clones_14d": clones,
    }
    (METRICS_DIR / "metrics.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8"
    )
    print(json.dumps(payload))


if __name__ == "__main__":
    main()
