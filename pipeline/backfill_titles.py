#!/usr/bin/env python3
"""
backfill_titles.py — one-time repair of duplicate catalog titles.

Three flagship listings shipped with byte-identical titles ("Autumn 3D
Shadow-Box Mandala | 7 Layers") because the theme label alone drove the title.
Search engines treat near-identical titles as duplicates and index only one, so
those pages were effectively invisible.

This rewrites each existing entry's title deterministically from its own slug,
so the fix is stable and re-running changes nothing. Descriptions and tags are
left alone except that the theme-specific tag is preserved.

Usage: python3 pipeline/backfill_titles.py [--dry-run]
"""

import argparse
import hashlib
import json
import re
from datetime import date
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import themes  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "catalog" / "catalog.json"

# Substring seeds so "halloween mandala" and "thanksgiving svg" are caught,
# not just the bare words.
SEASONAL_TAG_WORDS = (
    "pumpkin", "thanksgiving", "harvest", "autumn", "fall ", "cozy",
    "halloween", "christmas", "valentine", "easter", "backtoschool", "leaves",
    "spring ", "summer ", "snow", "spooky", "advent",
)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not CATALOG.exists():
        print("catalog not found; nothing to do")
        return 0

    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    if not isinstance(catalog, list):
        print("unexpected catalog shape; refusing to touch it")
        return 1

    changed = 0
    seen_titles: dict[str, str] = {}

    for item in catalog:
        # memorial/memorial-bundle titles are written by memorial_generator.py and
        # memorial_bundle.py and carry the emotional wording ("In Loving Memory
        # Pet Shadow Box"). The generic seasonal title shapes would replace
        # them with "Stacked Autumn Mandala", which is both wrong for the buyer
        # and a duplicate of the generic line. The bundle was missed here once
        # and got published as "Autumn Mandala | 7-Layer 3D Shadow-Box" — the
        # 17.99 USDT product, carrying a mandala title, on the page a grieving
        # buyer is asked to pay for.
        if item.get("type") in ("memorial", "memorial-bundle"):
            seen_titles.setdefault(item.get("title", ""), item.get("id", ""))
            continue
        created = item.get("created") or date.today().isoformat()
        # Resolve the theme the same way the generator would have.
        try:
            theme = themes.get_today_theme(created)
        except ValueError:
            theme = themes.get_today_theme(date.today().isoformat())

        layers_m = re.search(r"(\d+)\s*layer", item.get("title", ""), re.I)
        layers = int(layers_m.group(1)) if layers_m else 7

        slug = item.get("id", created)
        disc = int(hashlib.sha1(slug.encode()).hexdigest(), 16) % 997

        # Guarantee uniqueness even if two slugs collide on the shape index.
        title = themes.unique_title(theme, layers, disc)
        if title in seen_titles:
            alt = themes.unique_title(theme, layers, disc + 1)
            title = alt if alt not in seen_titles else f"{title} ({created})"

        if title != item.get("title"):
            print(f"  {slug}: {item.get('title')!r} -> {title!r}")
            item["title"] = title
            changed += 1
        seen_titles[title] = slug

        # Keep tags fresh with the theme's own search terms — but never on the
        # memorial line. This merge was the original source of the seasonal
        # tag defects: it stamped pumpkin/thanksgiving onto grief designs, the
        # bundle then re-aggregated them, and the quality gate correctly
        # refused the build. The catalog was cleaned three times before the
        # merge itself was stopped here, so it cleans instead of adding.
        is_memorial = item.get("type") in ("memorial", "memorial-bundle")
        if is_memorial:
            kept = [t for t in (item.get("tags") or [])
                    if not any(s in t.lower() for s in SEASONAL_TAG_WORDS)]
            if kept != (item.get("tags") or []):
                item["tags"] = kept
            continue

        theme_tags = themes.theme_tags(theme)
        existing = item.get("tags") or []
        merged = sorted(set(existing) | set(theme_tags))
        if merged != existing:
            item["tags"] = merged

    dupes = len(catalog) - len(seen_titles)
    print(f"catalog entries: {len(catalog)}")
    print(f"titles changed : {changed}")
    print(f"duplicate titles remaining: {dupes}")

    if args.dry_run:
        print("dry run: nothing written")
        return 0

    if changed:
        CATALOG.write_text(json.dumps(catalog, indent=2), encoding="utf-8")
        print("catalog updated")
    else:
        print("catalog already unique; no write needed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
