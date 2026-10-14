#!/usr/bin/env python3
"""
verify_theme_rotation.py — assert that a season does not collapse to one theme.

When every listing in a month resolved to the same theme label, every title in
that month was identical and search engines indexed only one of them. This is
the regression test for that failure.

Exits non-zero if any season resolves to fewer than MIN_DISTINCT themes.
"""

import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import themes  # noqa: E402

MIN_DISTINCT = 3


def distinct_in_year(year: int = 2026) -> dict:
    out: dict[int, set] = {}
    d = date(year, 1, 1)
    end = date(year + 1, 1, 1)
    while d < end:
        label = themes.get_today_theme(d.isoformat())["label"]
        out.setdefault(d.month, set()).add(label)
        d += timedelta(days=1)
    return out


def main() -> int:
    per_month = distinct_in_year()
    failures = []

    print("distinct themes per month (2026):")
    for month in sorted(per_month):
        labels = sorted(per_month[month])
        status = "ok" if len(labels) >= MIN_DISTINCT else "TOO FEW"
        print(f"  {month:02d}: {len(labels)}  {status}  {labels}")
        if len(labels) < MIN_DISTINCT:
            failures.append(month)

    # Titles must also be unique enough: sample a fortnight and count shapes.
    d = date(2026, 10, 1)
    titles = []
    for _ in range(14):
        theme = themes.get_today_theme(d.isoformat())
        titles.append(themes.unique_title(theme, 7, d.timetuple().tm_yday))
        d += timedelta(days=1)
    uniq = len(set(titles))
    print(f"sample fortnight: {uniq}/{len(titles)} distinct titles")
    if uniq < MIN_DISTINCT:
        failures.append("title-shapes")

    if failures:
        print(f"FAIL: {failures}")
        return 1
    print("PASS: seasonal rotation and title variety are healthy")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
