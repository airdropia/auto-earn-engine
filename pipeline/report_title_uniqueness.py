#!/usr/bin/env python3
"""
report_title_uniqueness.py — count duplicate titles in the catalog.

Search engines index one of a set of duplicate titles and drop the rest, so a
duplicate title is a page that will never be found. This reports the state and
writes it into metrics/ so the trend is visible over time.

Always exits 0: a duplicate is a finding to publish, not a reason to fail the
job that publishes the finding.
"""

import collections
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "catalog" / "catalog.json"
OUT = ROOT / "metrics" / "seo-health.md"


def main() -> int:
    if not CATALOG.exists():
        print("catalog missing")
        return 0

    items = json.loads(CATALOG.read_text(encoding="utf-8"))
    if not isinstance(items, list):
        print("unexpected catalog shape")
        return 0

    titles = [i.get("title", "") for i in items]
    counts = collections.Counter(titles)
    dupes = {t: n for t, n in counts.items() if n > 1}
    empty = [i.get("id") for i in items if not i.get("title")]

    lines = [
        "# SEO HEALTH (auto-generated)",
        "",
        f"_Auto-updated {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')} "
        "by `pipeline/report_title_uniqueness.py`_",
        "",
        "| Check | Value |",
        "|---|---|",
        f"| Catalog entries | {len(items)} |",
        f"| Distinct titles | {len(counts)} |",
        f"| Duplicate titles | {len(dupes)} |",
        f"| Entries missing a title | {len(empty)} |",
        "",
    ]

    if dupes:
        lines.append("## Duplicates")
        lines.append("")
        for t, n in sorted(dupes.items(), key=lambda kv: -kv[1]):
            lines.append(f"- ({n}x) {t}")
        lines.append("")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines), encoding="utf-8")

    print(f"entries={len(items)} distinct_titles={len(counts)} duplicates={len(dupes)}")
    if dupes:
        print("::warning::duplicate titles present:", list(dupes)[:3])
    else:
        print("::notice::all catalog titles are unique")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
