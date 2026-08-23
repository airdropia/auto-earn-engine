#!/usr/bin/env python3
"""Daily digital product generator.

Stdlib only. Output is deterministic per UTC date: every scheduled run
produces a unique but reproducible product batch and appends it to the
catalog (idempotent - re-running the same date never duplicates products).
"""
from __future__ import annotations

import hashlib
import json
import math
import random
from datetime import datetime, timezone
from pathlib import Path

import listings
import pngio  # noqa: F401  (kept for future raster assets)
import svgkit

ROOT = Path(__file__).resolve().parents[1]
PRODUCTS_DIR = ROOT / "products"
CATALOG_DIR = ROOT / "catalog"

# Original short aphorisms written for this project (safe to sell).
QUOTES = [
    "Small daily steps beat rare heroic efforts.",
    "Focus is deciding what not to do today.",
    "Calm minds finish what busy minds start.",
    "Progress loves the person who shows up quietly.",
    "Done slowly is still done.",
    "Your future is built in ordinary hours.",
    "Consistency turns talent into results.",
    "Start small, start now, start again.",
    "A clear desk clears the mind.",
    "Energy follows attention, so aim it well.",
    "One good hour outranks a wasted day.",
    "Discipline is self respect in action.",
    "Rest is part of the work.",
    "Simplify first, speed comes later.",
    "The plan you finish beats the perfect plan.",
    "Grow a little every single day.",
    "Quiet work, loud results.",
    "Choose the harder right, easier wrong.",
    "Momentum starts with one motion.",
    "Make it exist, then make it better.",
    "Patience compounds like interest.",
    "Today's effort is tomorrow's luck.",
    "Order outside creates order inside.",
    "Finish something, anything, now.",
]

PALETTES = [
    ["#264653", "#2a9d8f", "#e9c46a", "#f4a261", "#e76f51"],
    ["#1d3557", "#457b9d", "#a8dadc", "#f1faee", "#e63946"],
    ["#606c38", "#283618", "#fefae0", "#dda15e", "#bc6c25"],
    ["#003049", "#d62828", "#f77f00", "#fcbf49", "#eae2b7"],
    ["#22223b", "#4a4e69", "#9a8c98", "#c9ada7", "#f2e9e4"],
    ["#0d1b2a", "#1b263b", "#415a77", "#778da9", "#e0e1dd"],
    ["#5f0f40", "#9a031e", "#fb8b24", "#e36414", "#0f4c5c"],
    ["#ef476f", "#ffd166", "#06d6a0", "#118ab2", "#073b4c"],
]


# --------------------------------------------------------------------------
# Product renderers
# --------------------------------------------------------------------------

def render_mandala(rng: random.Random) -> str:
    size = 1000
    cx = cy = size / 2
    palette = PALETTES[rng.randrange(len(PALETTES))]
    ink = palette[rng.randrange(len(palette))]
    accent = palette[rng.randrange(len(palette))]
    rings = rng.randint(5, 8)
    body = [f'<rect width="{size}" height="{size}" fill="#ffffff"/>']
    for ring in range(1, rings + 1):
        radius = ring * size / (2 * rings + 2)
        petals = rng.choice([8, 12, 16, 24])
        phase = math.pi / petals if ring % 2 == 0 else 0.0
        color = ink if ring % 2 == 0 else accent
        width = rng.choice([1.5, 2.5])
        for p in range(petals):
            angle = 2 * math.pi * p / petals + phase
            px = cx + radius * math.cos(angle)
            py = cy + radius * math.sin(angle)
            pr = radius * rng.uniform(0.25, 0.4)
            body.append(
                f'<circle cx="{px:.1f}" cy="{py:.1f}" r="{pr:.1f}" '
                f'fill="none" stroke="{color}" stroke-width="{width}"/>'
            )
            inner = radius * rng.uniform(0.55, 0.85)
            x1 = cx + inner * math.cos(angle + phase)
            y1 = cy + inner * math.sin(angle + phase)
            body.append(
                f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{px:.1f}" y2="{py:.1f}" '
                f'stroke="{color}" stroke-width="1.2"/>'
            )
    core = size / (2 * rings + 2) * 0.8
    body.append(
        f'<circle cx="{cx:.0f}" cy="{cy:.0f}" r="{core:.1f}" '
        f'fill="none" stroke="{ink}" stroke-width="2"/>'
    )
    return svgkit.svg_doc(size, size, "".join(body))


def build_mandala_bundle(rng: random.Random, out_dir: Path, slug: str) -> dict:
    folder = out_dir / slug
    folder.mkdir(parents=True, exist_ok=True)
    files: list[str] = []
    for i in range(5):
        name = f"{slug}-design-{i + 1}.svg"
        (folder / name).write_text(render_mandala(rng), encoding="utf-8")
        files.append(str((folder / name).relative_to(ROOT)).replace("\\", "/"))
    return {
        "files": files,
        "folder": str(folder.relative_to(ROOT)).replace("\\", "/"),
        "designs": 5,
        "preview": files[0],
    }


def _pattern_def(pid: str, kind: str, unit: int, fg: str, base: str) -> str:
    half = unit / 2
    if kind == "dots":
        r = half * 0.32
        content = (
            f'<circle cx="{half}" cy="{half}" r="{r:.1f}" fill="{fg}"/>'
            f'<circle cx="0" cy="0" r="{r:.1f}" fill="{fg}"/>'
            f'<circle cx="{unit}" cy="0" r="{r:.1f}" fill="{fg}"/>'
            f'<circle cx="0" cy="{unit}" r="{r:.1f}" fill="{fg}"/>'
            f'<circle cx="{unit}" cy="{unit}" r="{r:.1f}" fill="{fg}"/>'
        )
    elif kind == "triangles":
        content = f'<path d="M0,{unit} L{half},0 L{unit},{unit} Z" fill="{fg}"/>'
    elif kind == "lines":
        sw = max(2.0, unit * 0.08)
        content = (
            f'<line x1="0" y1="{half}" x2="{unit}" y2="{half}" '
            f'stroke="{fg}" stroke-width="{sw:.1f}"/>'
        )
    else:  # zigzag
        q = unit / 4
        sw = max(2.0, unit * 0.06)
        content = (
            f'<path d="M0,{3 * q:.1f} L{q:.1f},{q:.1f} L{2 * q:.1f},{3 * q:.1f} '
            f'L{3 * q:.1f},{q:.1f} L{unit},{3 * q:.1f}" fill="none" '
            f'stroke="{fg}" stroke-width="{sw:.1f}"/>'
        )
    return (
        f'<pattern id="{pid}" width="{unit}" height="{unit}" '
        f'patternUnits="userSpaceOnUse">'
        f'<rect width="{unit}" height="{unit}" fill="{base}"/>{content}</pattern>'
    )


def render_pattern_sheet(rng: random.Random) -> str:
    w, h = 1000, 1400
    unit = rng.choice([70, 90, 110])
    palette = PALETTES[rng.randrange(len(PALETTES))]
    kinds = ["dots", "triangles", "lines", "zigzag"]
    rng.shuffle(kinds)
    defs: list[str] = []
    rects: list[str] = []
    for i, kind in enumerate(kinds):
        fg = palette[i % len(palette)]
        base = palette[(i + 2) % len(palette)]
        defs.append(_pattern_def(f"pat{i}", kind, unit, fg, base))
        y = 40 + i * 330
        rects.append(
            f'<rect x="50" y="{y}" width="900" height="300" rx="16" '
            f'fill="url(#pat{i})" stroke="#dddddd" stroke-width="2"/>'
        )
    body = (
        "<defs>" + "".join(defs) + "</defs>"
        + f'<rect width="{w}" height="{h}" fill="#ffffff"/>'
        + "".join(rects)
    )
    return svgkit.svg_doc(w, h, body)


def render_quote_card(rng: random.Random, quote: str) -> str:
    w, h = 1080, 1350
    palette = PALETTES[rng.randrange(len(PALETTES))]
    background = palette[rng.randrange(len(palette))]
    foreground_candidates = ["#ffffff", "#f5f1e8"]
    foreground = foreground_candidates[rng.randrange(2)]
    accent = palette[rng.randrange(len(palette))]
    if accent.lower() == background.lower():
        accent = "#ffffff"
    font_size = 92
    line_height = int(font_size * 1.35)
    lines = svgkit.wrap_text(quote, 16)
    total = len(lines) * line_height
    y0 = (h - total) / 2 + font_size
    tspans = "".join(
        f'<tspan x="{w / 2}" y="{y0 + i * line_height:.0f}">{svgkit.escape(line)}</tspan>'
        for i, line in enumerate(lines)
    )
    deco = (
        f'<circle cx="{rng.randint(80, 200)}" cy="{rng.randint(80, 200)}" '
        f'r="{rng.randint(30, 90)}" fill="none" stroke="{accent}" stroke-width="3" opacity="0.6"/>'
        f'<circle cx="{w - rng.randint(80, 200)}" cy="{h - rng.randint(80, 200)}" '
        f'r="{rng.randint(30, 90)}" fill="none" stroke="{accent}" stroke-width="3" opacity="0.6"/>'
        f'<rect x="60" y="60" width="{w - 120}" height="{h - 120}" fill="none" '
        f'stroke="{foreground}" stroke-width="2" opacity="0.35"/>'
    )
    text = (
        f'<text font-family="Georgia, serif" font-size="{font_size}" '
        f'fill="{foreground}" text-anchor="middle">{tspans}</text>'
    )
    body = (
        f'<rect width="{w}" height="{h}" fill="{background}"/>'
        + deco + text
    )
    return svgkit.svg_doc(w, h, body)


def build_quote_set(rng: random.Random, out_dir: Path, slug: str) -> dict:
    folder = out_dir / slug
    folder.mkdir(parents=True, exist_ok=True)
    picks = rng.sample(QUOTES, 4)
    files: list[str] = []
    for i, quote in enumerate(picks):
        name = f"{slug}-card-{i + 1}.svg"
        (folder / name).write_text(render_quote_card(rng, quote), encoding="utf-8")
        files.append(str((folder / name).relative_to(ROOT)).replace("\\", "/"))
    return {
        "files": files,
        "folder": str(folder.relative_to(ROOT)).replace("\\", "/"),
        "designs": 4,
        "preview": files[0],
    }


def render_planner(rng: random.Random) -> str:
    w, h = 1123, 794
    palette = PALETTES[rng.randrange(len(PALETTES))]
    header_color = palette[rng.randrange(3)]
    margin, top = 40, 150
    rows, cols = 8, 31
    cw = (w - margin * 2) / cols
    rh = (h - top - 50) / rows
    parts = [f'<rect width="{w}" height="{h}" fill="#ffffff"/>']
    parts.append(f'<rect x="0" y="0" width="{w}" height="90" fill="{header_color}"/>')
    parts.append(
        '<text x="40" y="58" font-family="Helvetica, Arial, sans-serif" '
        'font-size="34" font-weight="bold" fill="#ffffff">Habit Tracker</text>'
    )
    parts.append(
        f'<text x="{w - margin}" y="56" text-anchor="end" '
        'font-family="Helvetica, Arial, sans-serif" font-size="22" '
        'fill="#ffffff">Month: __________</text>'
    )
    for c in range(cols):
        x = margin + c * cw
        parts.append(
            f'<text x="{x + cw / 2:.1f}" y="{top - 10:.1f}" text-anchor="middle" '
            f'font-size="11" fill="#666666">{c + 1}</text>'
        )
    for r in range(rows + 1):
        y = top + r * rh
        parts.append(
            f'<line x1="{margin}" y1="{y:.1f}" x2="{w - margin}" y2="{y:.1f}" '
            'stroke="#e4e4e4" stroke-width="1"/>'
        )
    for c in range(cols + 1):
        x = margin + c * cw
        parts.append(
            f'<line x1="{x:.1f}" y1="{top:.1f}" x2="{x:.1f}" '
            f'y2="{top + rows * rh:.1f}" stroke="#e4e4e4" stroke-width="1"/>'
        )
    label_w = cw * 2
    for r in range(rows):
        y_mid = top + r * rh + rh / 2
        parts.append(
            f'<line x1="{margin + label_w:.1f}" y1="{top + r * rh:.1f}" '
            f'x2="{margin + label_w:.1f}" y2="{top + (r + 1) * rh:.1f}" '
            'stroke="#e4e4e4" stroke-width="1"/>'
        )
        parts.append(
            f'<text x="{margin + 12:.1f}" y="{y_mid + 5:.1f}" font-size="13" '
            'fill="#888888">Habit _______</text>'
        )
    return svgkit.svg_doc(w, h, "".join(parts))


def build_planner(rng: random.Random, out_dir: Path, slug: str) -> dict:
    folder = out_dir / slug
    folder.mkdir(parents=True, exist_ok=True)
    variants = rng.choice([1, 2])
    files: list[str] = []
    for i in range(variants):
        name = f"{slug}-sheet-{i + 1}.svg"
        (folder / name).write_text(render_planner(rng), encoding="utf-8")
        files.append(str((folder / name).relative_to(ROOT)).replace("\\", "/"))
    return {
        "files": files,
        "folder": str(folder.relative_to(ROOT)).replace("\\", "/"),
        "designs": variants,
        "preview": files[0],
    }


def build_pattern_pack(rng: random.Random, out_dir: Path, slug: str) -> dict:
    folder = out_dir / slug
    folder.mkdir(parents=True, exist_ok=True)
    variants = rng.choice([1, 2])
    files: list[str] = []
    for i in range(variants):
        name = f"{slug}-board-{i + 1}.svg"
        (folder / name).write_text(render_pattern_sheet(rng), encoding="utf-8")
        files.append(str((folder / name).relative_to(ROOT)).replace("\\", "/"))
    return {
        "files": files,
        "folder": str(folder.relative_to(ROOT)).replace("\\", "/"),
        "designs": variants,
        "preview": files[0],
    }


BUILDERS = {
    "mandala": build_mandala_bundle,
    "patterns": build_pattern_pack,
    "quotes": build_quote_set,
    "planner": build_planner,
}


# --------------------------------------------------------------------------
# Catalog assembly
# --------------------------------------------------------------------------

def build_product(product_type: str, rng: random.Random, batch_dir: Path, today: str) -> dict:
    digest = hashlib.sha1(f"{today}-{product_type}".encode()).hexdigest()[:8]
    slug = f"{product_type}-{digest}"
    serial = 100 + datetime.strptime(today, "%Y-%m-%d").timetuple().tm_yday
    built = BUILDERS[product_type](rng, batch_dir, slug)
    meta = {"serial": serial, "designs": built["designs"]}
    return {
        "id": slug,
        "type": product_type,
        "title": listings.title_for(product_type, meta),
        "description": listings.description_for(product_type, meta),
        "tags": listings.tags_for(product_type),
        "files": built["files"],
        "folder": built["folder"],
        "preview": built["preview"],
        "created": today,
    }


def main() -> None:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    rng = random.Random(f"auto-earn-engine:{today}")
    batch_dir = PRODUCTS_DIR / today
    batch_dir.mkdir(parents=True, exist_ok=True)

    catalog_path = CATALOG_DIR / "catalog.json"
    catalog: list[dict] = []
    if catalog_path.exists():
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    existing_ids = {item.get("id") for item in catalog}

    new_items = []
    for product_type in ("mandala", "patterns", "quotes", "planner"):
        item = build_product(product_type, rng, batch_dir, today)
        if item["id"] not in existing_ids:
            new_items.append(item)

    if new_items:
        catalog.extend(new_items)
        CATALOG_DIR.mkdir(parents=True, exist_ok=True)
        catalog_path.write_text(json.dumps(catalog, indent=2), encoding="utf-8")

    print(f"date={today} generated={len(new_items)} catalog_total={len(catalog)}")


if __name__ == "__main__":
    main()
