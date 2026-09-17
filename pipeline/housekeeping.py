#!/usr/bin/env python3
"""Autonomous housekeeping / cleanup for the product catalog.

Idempotent. Safe-by-default (no hard deletes unless --purge given):

  - ARCHIVE: products older than KEEP_DAYS are moved to _archive/<date>/ and
    their catalog entries flagged `"archived": true` (kept for history, out
    of the storefront grid).
  - REPORT: lists unreferenced folders (on disk but not in catalog) and
    junk files (temp/thumbnail/cache patterns) — printed, not deleted.
  - PURGE (--purge): delete unreferenced/junk files for real (irreversible,
    only when explicitly requested).

Run in CI via .github/workflows/housekeeping.yml. No deps beyond stdlib.

Usage:  python3 pipeline/housekeeping.py [--purge] [--keep N]
Env:    KEEP_DAYS=N  (default 90)
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRODUCTS_DIR = ROOT / "products"
CATALOG_PATH = ROOT / "catalog" / "catalog.json"
ARCHIVE_DIR = ROOT / "_archive" / "products"

JUNK_PATTERNS = ("*.tmp", "*.bak", "Thumbs.db", ".DS_Store", "*.pyc", "__pycache__")


def parse_date(p: Path) -> datetime | None:
    """Extract YYYY-MM-DD from a folder name like '2026-09-16' (also WNN weeks skipped)."""
    name = p.name
    if len(name) == 10 and name[4] == "-" and name[7] == "-":
        try:
            return datetime.strptime(name, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            return None
    return None  # non-date (weekly compilations, etc.) -> never auto-archived


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--purge", action="store_true", help="really delete unreferenced/junk")
    ap.add_argument("--keep", type=int, default=int(os.environ.get("KEEP_DAYS", "90")))
    args = ap.parse_args()

    catalog: list[dict] = []
    if CATALOG_PATH.exists():
        catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))

    in_catalog = {Path(c.get("folder", "")).name for c in catalog if c.get("folder")}
    now = datetime.now(timezone.utc)
    archived = []
    junk_found = []

    # 1) Archive stale dated product folders (keep KEEP_DAYS)
    if PRODUCTS_DIR.is_dir():
        for p in sorted(PRODUCTS_DIR.iterdir()):
            if not p.is_dir():
                continue
            d = parse_date(p)
            if d is None:
                continue  # weeks/undated -> skip
            age_days = (now - d).days
            if age_days > args.keep:
                target = ARCHIVE_DIR / p.name
                shutil.move(str(p), str(target))
                archived.append(p.name)
                # flag catalog entries for this date as archived
                for c in catalog:
                    if c.get("folder") and Path(c.get("folder", "")).name == p.name:
                        c["archived"] = True

    # 2) Find unreferenced folders + junk files
    unreferenced = []
    if PRODUCTS_DIR.is_dir():
        for p in sorted(PRODUCTS_DIR.iterdir()):
            if p.is_dir() and p.name not in in_catalog:
                unreferenced.append(str(p))

    for base in (ROOT, PRODUCTS_DIR):
        if not base.is_dir():
            continue
        for pat in JUNK_PATTERNS:
            for f in base.rglob(pat):
                junk_found.append(str(f))

    # 3) Apply purge if requested
    if args.purge:
        for f in junk_found:
            Path(f).unlink(missing_ok=True)
        # remove now-empty product dirs that are unreferenced
        for d in unreferenced:
            dp = Path(d)
            if not any(dp.iterdir()):
                dp.rmdir()
        unreferenced = [d for d in unreferenced if Path(d).exists()]

    # 4) Write catalog back only if we changed it
    if archived:
        CATALOG_PATH.write_text(json.dumps(catalog, indent=2), encoding="utf-8")

    print(f"archived={len(archived)} unreferenced={len(unreferenced)} junk={len(junk_found)}")
    for a in archived:
        print(f"  archived: {a}")
    for u in unreferenced:
        print(f"  unreferenced: {u}")
    for j in junk_found:
        print(f"  junk: {j}")
    if not archived and not unreferenced and not junk_found:
        print("clean: nothing to do")


if __name__ == "__main__":
    main()
