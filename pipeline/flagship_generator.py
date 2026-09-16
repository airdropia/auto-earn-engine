#!/usr/bin/env python3
"""
flagship_generator.py - Premium 3D layered mandala (flagship product).

Operator directive (2026-09-16): quality-over-quantity reset. This
produces ONE flagship-grade design per run - "would a crafter stop
scrolling?" is the bar, not volume.

Flagship-grade (evidence: AUDIT.md top-seller research):
- REAL depth: 7 physical layers, each a cardstock tier whose motif
  cutouts reveal lower layers (actual shadow-box structure)
- Motif vocabulary: pointed / rounded / scalloped / leaf (rib void)
  composed per-layer, so designs look distinct
- Cut-ready: bold shapes, minimum part width, no floating pieces

Output per design: combined SVG (preview) + one SVG per layer.
"""
from __future__ import annotations

import hashlib
import json
import math
import random
import re
from datetime import datetime, timezone
from pathlib import Path

import svgkit

ROOT = Path(__file__).resolve().parents[1]
PRODUCTS_DIR = ROOT / "products"
CATALOG_DIR = ROOT / "catalog"
CATALOG_PATH = CATALOG_DIR / "catalog.json"

SIZE = 1200
LAYERS = 7
MIN_PART = 14.0
MAX_ATTEMPTS = 12


def _p(cx, cy, r, a):
    return cx + r * math.cos(a), cy + r * math.sin(a)


def _fmt(x, y):
    return f"{x:.1f} {y:.1f}"


# --- Motif vocabulary -------------------------------------------------------
# Contract: each motif fn returns list[(d, is_hole)]. is_hole=True = VOID
# that reveals the layer below (filled with hole_fill).

def _petal_pointed(rng, inner, outer, half_w, cx, cy):
    tip = outer * rng.uniform(0.94, 1.0)
    base = inner * rng.uniform(0.95, 1.05)
    w = half_w * rng.uniform(0.55, 0.75)
    x1, y1 = _p(cx, cy, base, -math.pi / 2 - w)
    x2, y2 = _p(cx, cy, base, -math.pi / 2 + w)
    xt, yt = _p(cx, cy, tip, -math.pi / 2)
    cxm, cym = _p(cx, cy, (base + tip) / 2, -math.pi / 2)
    d = f"M {_fmt(x1, y1)} L {_fmt(xt, yt)} L {_fmt(x2, y2)} Q {_fmt(cxm, cym)} {_fmt(x1, y1)} Z"
    return [(d, False)]


def _petal_rounded(rng, inner, outer, half_w, cx, cy):
    tip = outer * rng.uniform(0.92, 1.0)
    base = inner * rng.uniform(0.92, 1.05)
    w = half_w * rng.uniform(0.6, 0.85)
    x1, y1 = _p(cx, cy, base, -math.pi / 2 - w)
    x2, y2 = _p(cx, cy, base, -math.pi / 2 + w)
    xt, yt = _p(cx, cy, tip, -math.pi / 2)
    c1 = _p(cx, cy, base + (tip - base) * 0.7, -math.pi / 2 - w * 1.35)
    c2 = _p(cx, cy, base + (tip - base) * 0.7, -math.pi / 2 + w * 1.35)
    d = (f"M {_fmt(x1, y1)} C {_fmt(*c1)} {_fmt(*c1)} {_fmt(xt, yt)} "
         f"C {_fmt(*c2)} {_fmt(*c2)} {_fmt(x2, y2)} Q {_fmt(x2, y2)} {_fmt(x1, y1)} Z")
    return [(d, False)]


def _petal_scalloped(rng, inner, outer, half_w, cx, cy):
    tip = outer * rng.uniform(0.9, 0.98)
    base = inner * rng.uniform(0.95, 1.02)
    span = 2 * half_w * 0.85
    d = [f"M {_fmt(*_p(cx, cy, base, -math.pi / 2 - half_w * 0.85))}"]
    for i in range(3):
        a1 = -math.pi / 2 - half_w * 0.85 + span * (i + 1) / 3
        am = -math.pi / 2 - half_w * 0.85 + span * (i + 0.5) / 3
        xm, ym = _p(cx, cy, tip * rng.uniform(0.85, 1.0), am)
        x1, y1 = _p(cx, cy, base * rng.uniform(0.98, 1.05), a1)
        d.append(f"Q {_fmt(xm, ym)} {_fmt(x1, y1)}")
    d.append("Z")
    return [(" ".join(d), False)]


def _petal_leaf(rng, inner, outer, half_w, cx, cy):
    tip = outer * rng.uniform(0.95, 1.0)
    base = inner * rng.uniform(0.95, 1.03)
    w = half_w * rng.uniform(0.5, 0.7)
    x1, y1 = _p(cx, cy, base, -math.pi / 2 - w)
    x2, y2 = _p(cx, cy, base, -math.pi / 2 + w)
    xt, yt = _p(cx, cy, tip, -math.pi / 2)
    main = (f"M {_fmt(x1, y1)} "
            f"Q {_fmt(*_p(cx, cy, (base + tip) * 0.55, -math.pi / 2 - w * 1.2))} {_fmt(xt, yt)} "
            f"Q {_fmt(*_p(cx, cy, (base + tip) * 0.55, -math.pi / 2 + w * 1.2))} {_fmt(x2, y2)} "
            f"Q {_fmt(x2, y2)} {_fmt(x1, y1)} Z")
    rw = w * rng.uniform(0.22, 0.34)
    ra = (base + tip) * rng.uniform(0.42, 0.6)
    rb = tip * rng.uniform(0.75, 0.9)
    xa, ya = _p(cx, cy, ra, -math.pi / 2)
    xb, yb = _p(cx, cy, rb, -math.pi / 2)
    rib = (f"M {_fmt(xa, ya)} "
           f"Q {_fmt(*_p(cx, cy, (ra + rb) / 2, -math.pi / 2 - rw))} {_fmt(xb, yb)} "
           f"Q {_fmt(*_p(cx, cy, (ra + rb) / 2, -math.pi / 2 + rw))} {_fmt(xa, ya)} Z")
    return [(main, False), (rib, True)]


MOTIFS = [_petal_pointed, _petal_rounded, _petal_scalloped, _petal_leaf]


# --- Layer composition ------------------------------------------------------

def _motif_group(rng, inner, outer, half_w, cx, cy, motif_fn, fill, hole_fill):
    out = []
    for d, is_hole in motif_fn(rng, inner, outer, half_w, cx, cy):
        f = hole_fill if is_hole else fill
        out.append(f'<path d="{d}" fill="{f}"/>')
    return "".join(out)


def _ring(cx, cy, inner, outer, symmetry, motif_fn, rng, fill, hole_fill):
    half_w = (2 * math.pi / symmetry) * rng.uniform(0.30, 0.44)
    wedge = _motif_group(rng, inner, outer, half_w, cx, cy, motif_fn, fill, hole_fill)
    rot = 360 / symmetry
    return "".join(
        f'<g transform="rotate({rot * i:.2f} {cx:.0f} {cy:.0f})">{wedge}</g>'
        for i in range(symmetry)
    )


def _annulus_base(cx, cy, inner, outer, fill):
    """Solid donut ring (outer circle + inner hole)."""
    return (f'<path d="M {_fmt(cx + outer, cy)} A {outer:.1f} {outer:.1f} 0 1 0 '
            f'{_fmt(cx - outer, cy)} A {outer:.1f} {outer:.1f} 0 1 0 {_fmt(cx + outer, cy)} Z '
            f'M {_fmt(cx + inner, cy)} A {inner:.1f} {inner:.1f} 0 1 0 '
            f'{_fmt(cx - inner, cy)} A {inner:.1f} {inner:.1f} 0 1 0 {_fmt(cx + inner, cy)} Z" '
            f'fill="{fill}" fill-rule="evenodd"/>')


def render_flagship(rng) -> tuple[str, list[str]]:
    """Return (combined_svg, [layer_svgs]) for one flagship design."""
    cx = cy = SIZE / 2
    palette = ["#1d3557", "#457b9d", "#a8dadc", "#f1faee", "#e63946"]
    hole_fill = "#ffffff"
    max_r = SIZE / 2 - 30

    band_tops = [1.0, 0.88, 0.76, 0.64, 0.52, 0.40, 0.28]
    band_bottoms = [0.86, 0.74, 0.62, 0.50, 0.38, 0.26, 0.0]
    picks = rng.sample(range(len(MOTIFS)), len(MOTIFS))
    motifs = [MOTIFS[picks[i % len(picks)]] for i in range(LAYERS - 1)]
    motifs.append(MOTIFS[0])
    symmetry = rng.choice([10, 12, 14, 16])

    layer_svgs: list[str] = []
    combined_parts: list[str] = []
    for li in range(LAYERS):
        inner = max_r * band_bottoms[li]
        outer = max_r * band_tops[li]
        fill = palette[li % len(palette)]
        parts = []
        if li == LAYERS - 1:
            parts.append(f'<circle cx="{cx:.0f}" cy="{cy:.0f}" r="{outer:.1f}" fill="{fill}"/>')
            parts.append(_ring(cx, cy, outer * 0.35, outer * 0.92, max(8, symmetry - 4),
                               motifs[li], rng, palette[(li + 2) % len(palette)], hole_fill))
        else:
            parts.append(_annulus_base(cx, cy, inner, outer, fill))
            parts.append(_ring(cx, cy, inner + 4, outer - 3, symmetry,
                               motifs[li], rng, palette[(li + 2) % len(palette)], hole_fill))
        bg = f'<rect width="{SIZE}" height="{SIZE}" fill="#ffffff"/>'
        layer_svgs.append(svgkit.svg_doc(SIZE, SIZE, bg + "".join(parts)))
        combined_parts.extend(parts)

    combined = svgkit.svg_doc(
        SIZE, SIZE,
        f'<rect width="{SIZE}" height="{SIZE}" fill="#ffffff"/>' + "".join(combined_parts),
    )
    return combined, layer_svgs


def validate(svg_text: str) -> str | None:
    n = sum(svg_text.count(f"<{t}") for t in ("path", "circle", "rect", "line"))
    if n < 60:
        return f"too simple ({n} elements)"
    for m in re.finditer(r'<circle[^>]*\br="([\d.]+)"', svg_text):
        if float(m.group(1)) < MIN_PART:
            return f"floating dot r={m.group(1)}"
    return None


def build(rng, out_dir: Path, slug: str, theme: dict) -> dict:
    folder = out_dir / slug
    folder.mkdir(parents=True, exist_ok=True)
    for attempt in range(MAX_ATTEMPTS):
        combined, layers = render_flagship(rng)
        defects = [d for d in (validate(s) for s in [combined, *layers]) if d]
        if not defects:
            break
    else:
        raise RuntimeError("flagship failed quality gate after retries")

    files = []
    names = [f"{slug}-design-1.svg"] + [
        f"{slug}-design-1-layer-{j}.svg" for j in range(1, LAYERS + 1)
    ]
    for name, svg in zip(names, [combined, *layers]):
        (folder / name).write_text(svg, encoding="utf-8")
        files.append(str((folder / name).relative_to(ROOT)).replace("\\", "/"))

    (folder / "ABOUT.txt").write_text(
        f"{theme['label']} 3D Shadow-Box Mandala - Flagship\n\n"
        f"{LAYERS} physical layers for shadow-box assembly.\n"
        "Cut each layer from cardstock, stack largest to smallest with foam dots.\n"
        "Voids in upper layers reveal lower layers - that is the 3D depth.\n",
        encoding="utf-8",
    )
    return {
        "files": files,
        "folder": str(folder.relative_to(ROOT)).replace("\\", "/"),
        "designs": 1,
        "preview": files[0],
        "quality": {"layers": LAYERS},
    }


def main() -> None:
    import themes
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    rng = random.Random(f"flagship:{today}")
    theme = themes.get_today_theme(today)
    slug_seed = hashlib.sha1(f"flagship-{today}".encode()).hexdigest()[:8]
    slug = f"flagship-{slug_seed}"
    catalog: list[dict] = []
    if CATALOG_PATH.exists():
        catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    existing = {i.get("id") for i in catalog}
    if slug in existing:
        print(f"flagship already exists for {today}: {slug}")
        return
    item = build(rng, PRODUCTS_DIR / today, slug, theme)
    entry = {
        "id": slug,
        "type": "flagship",
        "title": f"{theme['label']} 3D Shadow-Box Mandala | {LAYERS} Layers",
        "description": (
            f"Premium {LAYERS}-layer 3D shadow-box mandala. Cut each layer from "
            f"cardstock and stack for real depth - voids in upper layers reveal "
            f"lower layers. Theme: {theme['label']}."
        ),
        "tags": [f"{theme['label'].lower()} mandala", "3d layered mandala",
                 "shadow box svg", "cricut mandala", "layered svg", "flagship"],
        "files": item["files"],
        "folder": item["folder"],
        "preview": item["preview"],
        "created": today,
        "designs": 1,
        "quality": item["quality"],
    }
    catalog.append(entry)
    CATALOG_DIR.mkdir(parents=True, exist_ok=True)
    CATALOG_PATH.write_text(json.dumps(catalog, indent=2), encoding="utf-8")
    print(f"flagship built: {slug} layers={LAYERS}")


if __name__ == "__main__":
    main()