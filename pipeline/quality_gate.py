#!/usr/bin/env python3
"""Standalone CI quality gate (see docs/QUALITY-BAR.md).

Validates every SVG under products/ plus catalog/package consistency.
Exits non-zero on any violation so the batch never deploys.
"""
from __future__ import annotations

import json
import re
import sys
import xml.dom.minidom
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRODUCTS_DIR = ROOT / "products"
CATALOG_PATH = ROOT / "catalog" / "catalog.json"

MIN_ELEMENTS = {
    "mandala": 120,
    "layered-mandala": 18,
    "patterns": 10,
    "quotes": 5,
    "planner": 40,
}


def svg_type_of(path: Path) -> str:
    for product_type in MIN_ELEMENTS:
        if path.name.startswith(product_type):
            return product_type
    return "other"


def count_elements(text: str) -> int:
    return sum(text.count(f"<{tag}") for tag in ("path", "circle", "rect", "line"))


def check_svg(path: Path) -> list[str]:
    defects: list[str] = []
    text = path.read_text(encoding="utf-8", errors="replace")

    try:
        xml.dom.minidom.parseString(text)
    except Exception as error:  # noqa: BLE001
        return [f"invalid XML: {error}"]

    ptype = svg_type_of(path)
    minimum = MIN_ELEMENTS.get(ptype)
    if minimum is not None and count_elements(text) < minimum:
        defects.append(f"{count_elements(text)} elements < {minimum} for {ptype}")

    if ptype == "mandala":
        start = 0
        while True:
            idx = text.find("<path", start)
            if idx == -1:
                break
            end = text.find("/>", idx)
            seg = text[idx:end if end != -1 else len(text)]
            dpos = seg.find('d="')
            if dpos == -1:
                defects.append("path without d attribute")
                break
            dval = seg[dpos + 3:]
            dval = dval[:dval.find('"')]
            if not dval.strip().endswith("Z"):
                defects.append(f"open path in {path.name}")
                break
            start = end

    if ptype == "layered-mandala":
        # Cut-readiness invariants (AUDIT.md P1): thick strokes only,
        # no floating dots - otherwise the design shreds on a Cricut.
        for match in re.finditer(r'stroke-width="([\d.]+)"', text):
            if float(match.group(1)) < 4.0:
                defects.append(f"stroke {match.group(1)}px < 4px in {path.name}")
                break
        for match in re.finditer(r'<circle[^>]*\br="([\d.]+)"', text):
            if float(match.group(1)) < 12.0:
                defects.append(f"floating dot r={match.group(1)}px in {path.name}")
                break

    return defects


def check_package_paperwork() -> list[str]:
    defects: list[str] = []
    if not CATALOG_PATH.exists():
        return ["catalog.json missing"]
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    for item in catalog:
        folder = ROOT / item.get("folder", "")
        if not item.get("folder") or not folder.is_dir():
            defects.append(f"{item['id']}: bundle folder missing")
            continue
        for required in ("LICENSE.txt", "ABOUT.txt"):
            if not (folder / required).exists():
                defects.append(f"{item['id']}: {required} missing")
    return defects


def check_pngs_for_mandala_products() -> list[str]:
    """P3 multi-format: mandala and layered-mandala must ship a PNG preview
    alongside each SVG (per-design PNG download, see AUDIT.md P3).

    Only items generated on or after the P3 deploy date (2026-09-06) are
    required to have a matching PNG. Older items are grandfathered (their
    files list predates P3, regenerating them would change buyer-facing
    slugs - not worth it for retired storefront positions).
    """
    defects: list[str] = []
    if not PRODUCTS_DIR.exists():
        return defects
    p3_deploy_date = "2026-09-06"
    png_signature = b"\x89PNG\r\n\x1a\n"
    for svg_path in sorted(PRODUCTS_DIR.rglob("*.svg")):
        ptype = svg_type_of(svg_path)
        if ptype not in ("mandala", "layered-mandala"):
            continue
        # Only require PNG for the combined design SVGs (not per-layer
        # _layer-1/2/3/ files) - those are auxiliary cut files.
        if "-layer-" in svg_path.stem:
            continue
        # Grandfather: items generated before P3 deploy are exempt.
        try:
            date_part = svg_path.parts[svg_path.parts.index("products") + 1]
        except (ValueError, IndexError):
            continue
        if date_part < p3_deploy_date:
            continue
        png_path = svg_path.with_suffix(".png")
        if not png_path.exists():
            defects.append(f"{png_path.relative_to(ROOT)}: PNG preview missing for {svg_path.name}")
            continue
        head = png_path.read_bytes()[:8]
        if head != png_signature:
            defects.append(f"{png_path.relative_to(ROOT)}: not a valid PNG")
            continue
        if png_path.stat().st_size < 1024:
            defects.append(f"{png_path.relative_to(ROOT)}: PNG too small ({png_path.stat().st_size}B)")
    return defects


def main() -> int:
    all_defects: list[str] = []
    checked = 0

    if PRODUCTS_DIR.exists():
        for path in sorted(PRODUCTS_DIR.rglob("*.svg")):
            checked += 1
            for defect in check_svg(path):
                all_defects.append(f"{path.relative_to(ROOT)}: {defect}")

    for defect in check_pngs_for_mandala_products():
        all_defects.append(defect)

    for defect in check_package_paperwork():
        all_defects.append(defect)

    print(f"quality gate: checked={checked} svgs, defects={len(all_defects)}")
    for defect in all_defects[:20]:
        print(f"  DEFECT {defect}")

    return 1 if all_defects else 0


if __name__ == "__main__":
    sys.exit(main())
