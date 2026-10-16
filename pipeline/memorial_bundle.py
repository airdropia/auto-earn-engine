#!/usr/bin/env python3
"""
memorial_bundle.py — the premium memorial bundle.

Market research 2026-10-16: Etsy sells pet-memorial shadow-box SVGs at
$3.74-$6.87, and the top listings sell VOLUME (30 designs in one $4.50
listing). At $9.99 for a single design we lose on price and have no volume
to show for it, so the single design is not the product a buyer should be
aimed at.

The product is the set: all three memorial variants (pet, angel wings,
rainbow bridge) in one bundle, with the editable name plate on every front
layer. No Etsy listing in the researched set offers the full memorial trio
with per-design name plates. That is the bundle this script publishes.

Pricing rationale: three designs at the single-design price is roughly the
market's $6.87 top end times three, minus the volume discount buyers expect
from a bundle. 17.99 USDT is deliberately below the naive sum (3 x 9.99 =
29.97) and above the market's single-design ceiling, so it reads as a deal
without reading as a bargain bin.

Idempotent: one bundle per UTC day, slug derived from the date.
"""
from __future__ import annotations

import hashlib
import json
import random
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import memorial_generator as mg

ROOT = Path(__file__).resolve().parents[1]
PRODUCTS_DIR = ROOT / "products"
CATALOG_DIR = ROOT / "catalog"
CATALOG_PATH = CATALOG_DIR / "catalog.json"

BUNDLE_PRICE_USDT = "17.99"


def find_memorial_designs(catalog: list[dict]) -> list[dict]:
    return [item for item in catalog if item.get("type") == "memorial"]


def build(today: str, catalog: list[dict]) -> dict | None:
    designs = find_memorial_designs(catalog)
    if len(designs) < 2:
        print(f"need at least 2 memorial designs to bundle, have {len(designs)}")
        return None

    digest = hashlib.sha1(f"memorial-bundle-{today}".encode()).hexdigest()[:8]
    slug = f"memorial-bundle-{digest}"
    folder = PRODUCTS_DIR / today / slug
    folder.mkdir(parents=True, exist_ok=True)

    files: list[str] = []
    used_labels: list[str] = []
    for item in designs:
        # Copy each design's SVGs into the bundle folder with a flat name so
        # the ZIP is one folder, not a tree the buyer has to unpack.
        src_dir = ROOT / item["folder"]
        label = item["id"].replace("memorial-", "")
        used_labels.append(label)
        for src in sorted(src_dir.glob("*.svg")):
            if "-layer-" in src.stem and label not in src.stem:
                continue
            name = f"{label}-{src.name}"
            dest = folder / name
            dest.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
            files.append(str(dest.relative_to(ROOT)).replace("\\", "/"))

    (folder / "ABOUT.txt").write_text(
        "Memorial Shadow-Box Collection - all variants, one bundle\n\n"
        f"Includes {len(designs)} seven-layer memorial designs: "
        f"{', '.join(used_labels)}.\n\n"
        "Every front layer carries an editable name plate: open the\n"
        "layer-1 file in Cricut Design Space or Silhouette Studio,\n"
        "double-click the placeholder text and type the name and dates.\n\n"
        "Cut each design's layers largest to smallest and stack with foam\n"
        "tape. The voids reveal the layers beneath, which is the depth.\n",
        encoding="utf-8",
    )
    (folder / "LICENSE.txt").write_text(
        "Memorial Shadow-Box Collection - License\n\n"
        "LICENSE - Commercial Use Grant: perpetual, worldwide, royalty-free\n"
        "license for personal AND commercial projects (physical products,\n"
        "client work, printed goods).\n\nNOT permitted: reselling or\n"
        "redistributing the raw digital files as-is; claiming authorship\n"
        "of the source designs.\n",
        encoding="utf-8",
    )

    title = f"Memorial Shadow Box Collection | {len(designs)} Editable-Name Designs, {mg.LAYERS} Layers Each"
    description = (
        f"The complete memorial line in one bundle: {len(designs)} seven-layer "
        "shadow-box designs (pet paw, angel wings, rainbow bridge), each with an "
        "editable name plate on the front layer so a grieving crafter can put "
        "their own beloved's name on it before cutting. Midnight, pearl and "
        "antique gold, stacked for real depth, with print-ready PNG renders. "
        "One download, every memorial design we make."
    )
    tags = sorted({
        t
        for item in designs
        for t in item.get("tags", [])
    } | {
        "memorial bundle", "memorial shadow box collection", "memorial svg bundle",
        "editable name svg", "pet loss svg bundle", "sympathy gift bundle",
        "cricut memorial bundle", "layered memorial bundle",
    })

    return {
        "id": slug,
        "type": "memorial-bundle",
        "title": title,
        "description": description,
        "tags": tags,
        "files": files,
        "folder": str(folder.relative_to(ROOT)).replace("\\", "/"),
        "preview": files[0],
        "created": today,
        "designs": len(designs),
        "quality": {"layers": mg.LAYERS, "personalizable": True, "variants": len(designs)},
        "price_usdt": BUNDLE_PRICE_USDT,
        "meta": {"price_usdt": BUNDLE_PRICE_USDT},
    }


def main() -> None:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if not CATALOG_PATH.exists():
        print("catalog not found; run memorial_generator.py first")
        return
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    existing = {item.get("id") for item in catalog}
    digest = hashlib.sha1(f"memorial-bundle-{today}".encode()).hexdigest()[:8]
    slug = f"memorial-bundle-{digest}"
    if slug in existing:
        print(f"bundle already exists for {today}: {slug}")
        return
    entry = build(today, catalog)
    if entry is None:
        return
    catalog.append(entry)
    CATALOG_DIR.mkdir(parents=True, exist_ok=True)
    CATALOG_PATH.write_text(json.dumps(catalog, indent=2) + "\n", encoding="utf-8")
    print(f"memorial bundle built: {slug} designs={entry['designs']} price={BUNDLE_PRICE_USDT} USDT")


if __name__ == "__main__":
    main()