#!/usr/bin/env python3
"""
weekly_compilation.py - Build the weekly mega-bundle (AUDIT.md P4).

Runs on Monday (separate cron, NOT part of daily generate_products.py).
Pulls the past 7 days of catalog items, copies all files into a single
weekly-compilation folder, writes an enhanced README, and registers a
single "weekly-compilation" item in catalog.json.

Why weekly compilations:
- "Weekly best-of" mega-bundles are a real Etsy/CF pattern (e.g. "Best
  of September Vol 1") - buyers grab one, get 30+ designs at one price
- Long-tail SEO: each weekly bundle becomes a new indexed page with
  the week's theme + all sub-products' tags aggregated
- Compounding catalog: weekly + daily = 5 items/day * 7 + 1 weekly = 36
  items/week instead of 35, plus the weekly acts as a "hub" page

Output:
  products/YYYY-Wnn/weekly-compilation-<hash>/
      <copies of all source SVGs/PNGs from past 7 days>
      LICENSE.txt
      ABOUT.txt (enhanced with week summary, theme, top tags)
  catalog.json: one new entry with type="weekly-compilation"

Idempotent: same week -> same id, no duplicate (catalog in-place replace).
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

import themes

ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / "catalog" / "catalog.json"
PRODUCTS_DIR = ROOT / "products"


def iso_week_id(today: datetime) -> str:
    """YYYY-Www (ISO week of year). e.g. 2026-W36."""
    iso = today.isocalendar()
    return f"{iso[0]}-W{iso[1]:02d}"


def get_week_window(today: datetime) -> tuple[str, str]:
    """Return (start_date_str, end_date_str) for the past 7 days inclusive
    of today. e.g. on Monday 2026-09-07, returns 2026-09-01..2026-09-07."""
    end = today.date()
    start = end - timedelta(days=6)
    return start.isoformat(), end.isoformat()


def collect_week_items(catalog: list[dict], start: str, end: str) -> list[dict]:
    """Filter catalog items whose created date is in [start, end]."""
    out = []
    for item in catalog:
        d = item.get("created", "")
        if start <= d <= end:
            out.append(item)
    return out


def aggregate_week_metadata(items: list[dict]) -> dict:
    """Compute summary metadata for the weekly bundle:
    - design count (sum of all items' designs)
    - file count (sum of all items' files)
    - top tags (5 most common)
    - themes seen (deduped)
    - types included (mandala/layered/patterns/quotes/planner)
    """
    designs = sum(i.get("designs", 0) for i in items)
    files = sum(len(i.get("files", [])) for i in items)
    tag_counter: Counter[str] = Counter()
    labels: list[str] = []
    types: Counter[str] = Counter()
    for i in items:
        for t in i.get("tags", []):
            tag_counter[t] += 1
        # Pull theme label from title prefix
        title = i.get("title", "")
        # titles look like "Back to School Mandala SVG Bundle #348"
        words = title.split()
        if len(words) > 1 and words[-1].startswith("#"):
            labels.append(" ".join(words[:-2]))  # drop trailing "#N"
        types[i.get("type", "")] += 1
    return {
        "designs": designs,
        "files": files,
        "top_tags": [t for t, _ in tag_counter.most_common(5)],
        "themes": list(dict.fromkeys(labels))[:5],
        "types": dict(types),
        "items_count": len(items),
    }


def build_weekly_compilation(today: datetime | None = None) -> dict:
    """Build the weekly mega-bundle for the week containing `today`
    (default: now). Returns the catalog entry to be added/updated."""
    if today is None:
        today = datetime.now(timezone.utc)

    start_str, end_str = get_week_window(today)
    week_id = iso_week_id(today)

    catalog: list[dict] = []
    if CATALOG_PATH.exists():
        catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))

    items = collect_week_items(catalog, start_str, end_str)
    if not items:
        print(f"weekly_compilation: no items found in {start_str}..{end_str}, skipping")
        return None

    summary = aggregate_week_metadata(items)

    # Deterministic id so re-runs of the same week are idempotent
    digest = hashlib.sha1(f"{week_id}-weekly".encode()).hexdigest()[:8]
    slug = f"weekly-compilation-{digest}"
    folder = PRODUCTS_DIR / week_id / slug
    folder.mkdir(parents=True, exist_ok=True)

    # Copy all source files into the weekly folder, named with source-date prefix
    all_files: list[str] = []
    for item in items:
        src_folder = ROOT / item.get("folder", "")
        if not src_folder.is_dir():
            continue
        for f in item.get("files", []):
            src = ROOT / f
            if not src.exists():
                continue
            # Prefix filename with the source date to avoid collisions
            src_date = item.get("created", "")
            dest_name = f"{src_date}_{Path(f).name}"
            dest = folder / dest_name
            if not dest.exists():
                shutil.copy2(src, dest)
            all_files.append(str(dest.relative_to(ROOT)).replace("\\", "/"))

    # Theme of the week = today's theme (since weekly is built today, themed today)
    week_theme = themes.get_today_theme(today.strftime("%Y-%m-%d"))

    # Write enhanced ABOUT + LICENSE
    about = (
        f"Weekly Compilation Bundle ({week_id})\n"
        f"\n"
        f"Week of: {start_str} to {end_str}\n"
        f"Theme: {week_theme['label']}\n"
        f"\n"
        f"What's inside:\n"
        f"- {summary['items_count']} curated products\n"
        f"- {summary['designs']} total designs\n"
        f"- {summary['files']} total files (SVG + PNG where available)\n"
        f"\n"
        f"Types included: {', '.join(summary['types'].keys())}\n"
        f"Top search tags: {', '.join(summary['top_tags'])}\n"
        f"\n"
        f"File naming: each file starts with its source date (YYYY-MM-DD)\n"
        f"so you can identify which daily batch it came from. e.g.\n"
        f"'2026-09-06_back-to-school-mandala-design-1.svg' is design 1\n"
        f"from the Back to School Mandala pack generated on 2026-09-06.\n"
        f"\n"
        f"Licensing: same as the source bundles - perpetual commercial-use\n"
        f"grant, no reselling of the raw files, attribution appreciated.\n"
        f"\n"
        f"Generated on {today.strftime('%Y-%m-%d')}.\n"
    )
    (folder / "ABOUT.txt").write_text(about, encoding="utf-8")
    license_text = (
        f"Weekly Compilation Bundle ({week_id})\n"
        f"Generated by VectorForge Daily automation pipeline.\n"
        f"\n"
        f"LICENSE - Commercial Use Grant (same as source bundles).\n"
        f"NOT permitted: reselling or redistributing the raw digital files\n"
        f"as-is, or claiming authorship of the source designs.\n"
    )
    (folder / "LICENSE.txt").write_text(license_text, encoding="utf-8")

    title = f"Weekly Compilation Bundle {week_id} | {summary['designs']} designs"

    return {
        "id": slug,
        "type": "weekly-compilation",
        "title": title,
        "description": (
            f"Best-of-week mega-bundle for {week_id} ({start_str} to {end_str}). "
            f"Curated compilation of {summary['items_count']} products, "
            f"{summary['designs']} total designs across "
            f"{', '.join(summary['types'].keys())}. "
            f"Theme: {week_theme['label']}. "
            f"Every file is a fully usable SVG/PNG from the week's daily batches."
        ),
        "tags": summary["top_tags"] + ["weekly compilation", "best of week", "mega bundle",
                                         week_theme["label"].lower() + " bundle"],
        "files": all_files,
        "folder": str(folder.relative_to(ROOT)).replace("\\", "/"),
        "preview": all_files[0] if all_files else "",
        "created": today.strftime("%Y-%m-%d"),
        "designs": summary["designs"],
        "week_id": week_id,
    }


def main() -> int:
    entry = build_weekly_compilation()
    if entry is None:
        return 0

    catalog: list[dict] = []
    if CATALOG_PATH.exists():
        catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))

    # Idempotent: replace if same id, else append
    existing_idx = next(
        (i for i, e in enumerate(catalog) if e.get("id") == entry["id"]), -1
    )
    modified = False
    if existing_idx >= 0:
        if (catalog[existing_idx].get("files") != entry["files"]
                or catalog[existing_idx].get("title") != entry["title"]):
            catalog[existing_idx] = entry
            modified = True
    else:
        catalog.append(entry)
        modified = True

    if modified:
        CATALOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        CATALOG_PATH.write_text(json.dumps(catalog, indent=2), encoding="utf-8")

    print(f"weekly_compilation: {entry['id']} "
          f"({entry['designs']} designs, {len(entry['files'])} files, "
          f"week={entry['week_id']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
