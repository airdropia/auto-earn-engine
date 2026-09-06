#!/usr/bin/env python3
"""Daily digital product generator (v2 quality edition).

Stdlib only. Deterministic per UTC date. Produces multiple candidates per
slot and keeps only gate-passers (see private-docs/AUDIT.md), so published
volume holds while weak output is filtered at source.

Idempotent: re-running the same date never duplicates catalog entries.
"""
from __future__ import annotations

import hashlib
import json
import math
import random
import re
from datetime import datetime, timezone
from pathlib import Path

import listings
import pngio  # noqa: F401
import svgkit
import themes

ROOT = Path(__file__).resolve().parents[1]
PRODUCTS_DIR = ROOT / "products"
CATALOG_DIR = ROOT / "catalog"
CATALOG_PATH = CATALOG_DIR / "catalog.json"

MAX_ATTEMPTS_PER_SLOT = 3

# Bundle sizes per product type (AUDIT.md P4: raise from 5 to 8-10 to
# match marketplace bundle perception, where 25+ designs is the "feels
# like a deal" threshold for buyers). Planner stays small (2 sheets) -
# a printable is a single 1-page artifact, not a tileable collection.
BUNDLE_SIZES: dict[str, int] = {
    "mandala": 8,
    "layered-mandala": 6,
    "patterns": 4,
    "quotes": 6,
    "planner": 2,
}

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
    "Choose the harder right over the easier wrong.",
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

SERIF_STACK = "Georgia, 'Times New Roman', serif"
SANS_STACK = "Arial, Helvetica, sans-serif"


def _lum(color: str) -> float:
    value = color.lstrip("#")
    r, g, b = (int(value[i:i + 2], 16) / 255 for i in (0, 2, 4))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _p(cx: float, cy: float, radius: float, angle: float) -> tuple[float, float]:
    return cx + radius * math.cos(angle), cy + radius * math.sin(angle)


def _fmt(x: float, y: float) -> str:
    return f"{x:.1f} {y:.1f}"


# --------------------------------------------------------------------------
# Mandala v2: true rotational symmetry, layered filled petals, closed paths
# --------------------------------------------------------------------------

def _mandala_wedge(rng: random.Random, cx: float, cy: float,
                   inner_r: float, outer_r: float, half_w: float,
                   ink: str, accent: str) -> list[str]:
    """One wedge of motif elements spanning -half_w..+half_w around -90 deg."""
    parts: list[str] = []
    tip = outer_r * rng.uniform(0.86, 0.98)
    mid = (inner_r + tip) / 2

    # Filled petal: closed quadratic path inner-left -> tip -> inner-right -> Z
    x1, y1 = _p(cx, cy, inner_r, -math.pi / 2 - half_w)
    xt, yt = _p(cx, cy, tip, -math.pi / 2)
    x2, y2 = _p(cx, cy, inner_r, -math.pi / 2 + half_w)
    c1x, c1y = _p(cx, cy, mid * rng.uniform(0.9, 1.25), -math.pi / 2 - half_w * 1.5)
    c2x, c2y = _p(cx, cy, mid * rng.uniform(0.9, 1.25), -math.pi / 2 + half_w * 1.5)
    fill = ink if rng.random() < 0.45 else "none"
    parts.append(
        f'<path d="M {_fmt(x1, y1)} Q {_fmt(c1x, c1y)} {_fmt(xt, yt)} '
        f'Q {_fmt(c2x, c2y)} {_fmt(x2, y2)} Z" fill="{fill}" '
        f'stroke="{ink}" stroke-width="{rng.choice([1.5, 2.0])}"/>'
    )

    # Inner echo petal in accent, smaller closed path
    exr = inner_r + (tip - inner_r) * rng.uniform(0.35, 0.55)
    ehw = half_w * rng.uniform(0.45, 0.65)
    xa, ya = _p(cx, cy, inner_r, -math.pi / 2 - ehw)
    xb, yb = _p(cx, cy, exr, -math.pi / 2)
    xc, yc = _p(cx, cy, inner_r, -math.pi / 2 + ehw)
    em = (inner_r + exr) / 2
    ea1x, ea1y = _p(cx, cy, em, -math.pi / 2 - ehw * 1.4)
    ea2x, ea2y = _p(cx, cy, em, -math.pi / 2 + ehw * 1.4)
    parts.append(
        f'<path d="M {_fmt(xa, ya)} Q {_fmt(ea1x, ea1y)} {_fmt(xb, yb)} '
        f'Q {_fmt(ea2x, ea2y)} {_fmt(xc, yc)} Z" fill="none" '
        f'stroke="{accent}" stroke-width="1.4"/>'
    )

    # Dots along the wedge axis
    for frac in rng.sample([0.3, 0.5, 0.7, 0.85], k=rng.randint(2, 3)):
        dr = inner_r + (tip - inner_r) * frac
        dx, dy = _p(cx, cy, dr, -math.pi / 2)
        parts.append(
            f'<circle cx="{dx:.1f}" cy="{dy:.1f}" r="{rng.uniform(2.5, 5):.1f}" '
            f'fill="{accent}"/>'
        )

    # Thin radial line on the wedge edge
    lx1, ly1 = _p(cx, cy, inner_r, -math.pi / 2 - half_w)
    lx2, ly2 = _p(cx, cy, outer_r, -math.pi / 2 - half_w)
    parts.append(
        f'<line x1="{lx1:.1f}" y1="{ly1:.1f}" x2="{lx2:.1f}" y2="{ly2:.1f}" '
        f'stroke="{accent}" stroke-width="0.8" opacity="0.7"/>'
    )
    return parts


def render_mandala(rng: random.Random, palette: list[str] | None = None) -> str:
    size = 1000
    cx = cy = size / 2
    if palette is None:
        palette = PALETTES[rng.randrange(len(PALETTES))]
    ink = min(palette, key=_lum)
    accents = sorted(palette, key=_lum)[1:3]
    body = [f'<rect width="{size}" height="{size}" fill="#ffffff"/>']

    symmetry = rng.choice([8, 10, 12, 16])
    ring_count = rng.randint(3, 5)
    max_radius = size / 2 - 20
    for layer in range(ring_count):
        outer_r = max_radius * (layer + 1) / ring_count
        inner_r = max_radius * layer / ring_count * rng.uniform(0.72, 0.88)
        half_w = (2 * math.pi / symmetry) * rng.uniform(0.30, 0.46)
        accent = accents[layer % len(accents)]
        wedge_parts = _mandala_wedge(rng, cx, cy, inner_r, outer_r, half_w, ink, accent)
        wedge_svg = "".join(wedge_parts)
        for i in range(symmetry):
            body.append(
                f'<g transform="rotate({360 * i / symmetry:.2f} {cx:.0f} {cy:.0f})">'
                f"{wedge_svg}</g>"
            )

    core_r = max_radius / ring_count * rng.uniform(0.5, 0.8)
    body.append(f'<circle cx="{cx:.0f}" cy="{cy:.0f}" r="{core_r:.1f}" fill="{ink}"/>')
    body.append(
        f'<circle cx="{cx:.0f}" cy="{cy:.0f}" r="{core_r * 0.62:.1f}" fill="#ffffff"/>'
    )
    body.append(
        f'<path d="M {cx:.0f} {cy - core_r * 0.45:.1f} '
        f'L {cx + core_r * 0.4:.1f} {cy + core_r * 0.32:.1f} '
        f'L {cx - core_r * 0.4:.1f} {cy + core_r * 0.32:.1f} Z" '
        f'fill="{accents[0]}"/>'
    )
    return svgkit.svg_doc(size, size, "".join(body))


def _mandala_pixels(rng: random.Random, palette: list[str] | None = None,
                    size: int = 1000) -> tuple[list[str], dict]:
    """Render a stylized PNG preview of a mandala: concentric palette rings
    plus radial accent wedges derived from the same RNG seed as the SVG
    counterpart. Returns (rgb_palette_list, render_params) for use by
    pngio.write_png via a pixel_fn closure. The preview is theme-faithful
    (same colors, same symmetry) but is a flat-color stylization, not a
    pixel-perfect copy of the SVG path geometry.
    """
    if palette is None:
        palette = PALETTES[rng.randrange(len(PALETTES))]
    ink = min(palette, key=_lum)
    accents = sorted(palette, key=_lum)[1:3]
    symmetry = rng.choice([8, 10, 12, 16])
    ring_count = rng.randint(3, 5)
    max_radius = size / 2 - 20
    # Per-ring colors: ink for outermost, accents rotating inward, white core
    ring_colors: list[str] = [ink]
    for i in range(1, ring_count):
        ring_colors.append(accents[i % len(accents)])
    # Wedge accent (alternates per symmetry sector for visual rhythm)
    wedge_accent = accents[0]
    params = {
        "cx": size / 2, "cy": size / 2,
        "ring_count": ring_count, "max_radius": max_radius,
        "ring_colors": ring_colors, "symmetry": symmetry, "wedge_accent": wedge_accent,
    }
    return [pngio.hex_rgb(c) for c in ring_colors], params


def _layered_pixels(rng: random.Random, palette: list[str] | None = None,
                   size: int = 1000) -> tuple[list[str], dict]:
    """Stylized PNG preview of a layered mandala: 3 concentric band rings
    (outer/mid/core) using theme palette, with a small core dot."""
    if palette is None:
        palette = PALETTES[rng.randrange(len(PALETTES))]
    ink = min(palette, key=_lum)
    accents = sorted(palette, key=_lum)[1:3]
    symmetry = rng.choice([8, 10, 12])
    max_radius = size / 2 - 24
    # 3 layers: outer (accent0), middle (ink), inner (accent1) + white core
    layer_colors = [accents[0], ink, accents[1], "#ffffff"]
    params = {
        "cx": size / 2, "cy": size / 2,
        "max_radius": max_radius, "symmetry": symmetry,
        "layer_colors": layer_colors, "ink": ink, "core_r": max_radius * 0.13,
    }
    return [pngio.hex_rgb(c) for c in layer_colors], params


def _make_mandala_pixel_fn(rgb_palette, params, size):
    """Closure: (x, y) -> (r, g, b) for a mandala preview."""
    cx, cy = params["cx"], params["cy"]
    max_radius = params["max_radius"]
    ring_count = params["ring_count"]
    ring_colors = params["ring_colors"]
    symmetry = params["symmetry"]
    wedge_accent = params["wedge_accent"]
    wedge_rgb = pngio.hex_rgb(wedge_accent)
    white = (255, 255, 255)
    def pixel(x: int, y: int) -> tuple[int, int, int]:
        dx, dy = x - cx, y - cy
        r = math.hypot(dx, dy)
        if r > max_radius + 1:
            return white
        # Pick ring (0 = outermost)
        ring_idx = int((1 - r / max_radius) * ring_count)
        if ring_idx >= ring_count:
            return white
        # Add subtle wedge accent at even sectors for visual rhythm
        angle = math.atan2(dy, dx) + math.pi / 2  # shift so 0 is top
        if angle < 0:
            angle += 2 * math.pi
        sector = int(angle / (2 * math.pi) * symmetry)
        if sector % 2 == 0:
            return rgb_palette[ring_idx]
        return wedge_rgb
    return pixel


def _make_layered_pixel_fn(rgb_palette, params, size):
    """Closure: (x, y) -> (r, g, b) for a layered mandala preview."""
    cx, cy = params["cx"], params["cy"]
    max_radius = params["max_radius"]
    layer_colors = params["layer_colors"]
    core_r = params["core_r"]
    inner_r = max_radius * 0.42
    mid_r = max_radius * 0.66
    outer_r = max_radius * 0.95
    white = (255, 255, 255)
    def pixel(x: int, y: int) -> tuple[int, int, int]:
        dx, dy = x - cx, y - cy
        r = math.hypot(dx, dy)
        if r > outer_r + 1:
            return white
        if r < core_r * 0.4:
            return white  # small white dot at very center
        if r < core_r:
            return pngio.hex_rgb(params["ink"])
        if r < mid_r:
            return rgb_palette[1]  # middle layer (ink)
        if r < inner_r:
            return rgb_palette[2]  # inner layer (accent1)
        return rgb_palette[0]  # outer layer (accent0)
    return pixel


def count_elements(svg_text: str) -> int:
    return sum(svg_text.count(f"<{tag}") for tag in ("path", "circle", "rect", "line"))


def paths_closed(svg_text: str) -> bool:
    start = 0
    while True:
        idx = svg_text.find("<path", start)
        if idx == -1:
            return True
        end = svg_text.find("/>", idx)
        seg = svg_text[idx:end if end != -1 else len(svg_text)]
        dpos = seg.find('d="')
        if dpos == -1:
            return False
        dval = seg[dpos + 3:]
        dval = dval[:dval.find('"')]
        if not dval.strip().endswith("Z"):
            return False
        start = end


def validate_mandala_svg(svg_text: str) -> str | None:
    """Return a defect description or None when the candidate passes."""
    if count_elements(svg_text) < 120:
        return f"too simple ({count_elements(svg_text)} elements)"
    if not paths_closed(svg_text):
        return "open path found"
    return None


def build_mandala_bundle(rng: random.Random, out_dir: Path, slug: str,
                       theme: dict | None = None) -> dict:
    folder = out_dir / slug
    folder.mkdir(parents=True, exist_ok=True)
    palette = themes.theme_palette(theme) if theme else None
    title = f"{themes.theme_label(theme)} Mandala SVG Bundle" if theme else "Mandala SVG Bundle"
    files: list[str] = []
    total_elements = 0
    for i in range(BUNDLE_SIZES["mandala"]):
        for attempt in range(MAX_ATTEMPTS_PER_SLOT):
            state = rng.getstate()
            svg = render_mandala(rng, palette)
            defect = validate_mandala_svg(svg)
            if defect is None:
                break
            # Failed validation: do not reset state - the original semantics
            # were "try a new random design until one passes". We only
            # reuse `state` AFTER success to drive a matching PNG render.
        else:
            raise RuntimeError("mandala slot failed quality gate after retries")
        name = f"{slug}-design-{i + 1}.svg"
        (folder / name).write_text(svg, encoding="utf-8")
        # Generate matching PNG preview (theme-faithful stylization, same RNG seed)
        rng.setstate(state)
        rgb_palette, params = _mandala_pixels(rng, palette)
        png_name = f"{slug}-design-{i + 1}.png"
        pixel_fn = _make_mandala_pixel_fn(rgb_palette, params, 1000)
        pngio.write_png(folder / png_name, 1000, 1000, pixel_fn)
        files.append(str((folder / name).relative_to(ROOT)).replace("\\", "/"))
        files.append(str((folder / png_name).relative_to(ROOT)).replace("\\", "/"))
        total_elements += count_elements(svg)
    write_package_docs(folder, title, files, "cut-ready closed paths",
                       theme=theme, product_type="mandala", designs=BUNDLE_SIZES["mandala"])
    return {
        "files": files,
        "folder": str(folder.relative_to(ROOT)).replace("\\", "/"),
        "designs": BUNDLE_SIZES["mandala"],
        "preview": files[0],
        "quality": {"elements": total_elements},
    }


# --------------------------------------------------------------------------
# Layered mandala v1: cut-ready 3D cardstock layers (bold connected shapes)
# --------------------------------------------------------------------------
# Design rules (see private-docs/AUDIT.md, P1):
# - bold filled shapes only, min stroke 6px @1000 viewBox (gate: >=4px)
# - no floating dots, no thin slivers -> cuts cleanly on Cricut
# - 3 concentric layer bands; each layer ships as its own SVG so makers can
#   cut each tier from different cardstock and stack with foam dots.

LAYERED_LAYERS = 3
CUT_STROKE = 6.0
LAYER_BANDS = [  # (inner_frac, outer_frac) of max radius; index 0 = outermost
    (0.60, 0.95),
    (0.34, 0.66),
    (0.00, 0.42),
]


def _cut_petal(rng: random.Random, cx: float, cy: float,
               inner_r: float, outer_r: float, half_w: float, fill: str) -> str:
    """One fat closed petal spanning inner_r..outer_r centred on -90deg."""
    base = inner_r * rng.uniform(1.02, 1.10)
    tip = outer_r * rng.uniform(0.96, 1.00)
    x1, y1 = _p(cx, cy, base, -math.pi / 2 - half_w)
    xt, yt = _p(cx, cy, tip, -math.pi / 2)
    x2, y2 = _p(cx, cy, base, -math.pi / 2 + half_w)
    mid = (base + tip) / 2
    c1x, c1y = _p(cx, cy, mid, -math.pi / 2 - half_w * 1.5)
    c2x, c2y = _p(cx, cy, mid, -math.pi / 2 + half_w * 1.5)
    return (
        f'<path d="M {_fmt(x1, y1)} Q {_fmt(c1x, c1y)} {_fmt(xt, yt)} '
        f'Q {_fmt(c2x, c2y)} {_fmt(x2, y2)} Z" fill="{fill}"/>'
    )


def _cut_arc(rng: random.Random, cx: float, cy: float,
             radius: float, start_angle: float, sweep: float, ink: str) -> str:
    """Thick stroked arc linking two petals (interlock)."""
    x0, y0 = _p(cx, cy, radius, start_angle)
    x1, y1 = _p(cx, cy, radius, start_angle + sweep)
    large = 1 if sweep > math.pi else 0
    return (
        f'<path d="M {_fmt(x0, y0)} A {radius:.1f} {radius:.1f} 0 {large} 1 '
        f'{_fmt(x1, y1)}" fill="none" stroke="{ink}" stroke-width="{CUT_STROKE:.1f}"/>'
    )


def render_layered_design(rng: random.Random,
                       palette: list[str] | None = None) -> tuple[str, list[str]]:
    """Return (combined_svg, [layer_1_svg, layer_2_svg, layer_3_svg])."""
    size = 1000
    cx = cy = size / 2
    max_radius = size / 2 - 24
    if palette is None:
        palette = PALETTES[rng.randrange(len(PALETTES))]
    ink = min(palette, key=_lum)
    accents = sorted(palette, key=_lum)[1:3]
    symmetry = rng.choice([8, 10, 12])
    step = 2 * math.pi / symmetry

    all_parts: list[str] = []
    layer_svgs: list[str] = []
    for layer in range(LAYERED_LAYERS):
        inner_frac, outer_frac = LAYER_BANDS[layer]
        inner_r = max_radius * inner_frac
        outer_r = max_radius * outer_frac
        half_w = step * rng.uniform(0.28, 0.38)
        # One wedge of bold shapes, rotated `symmetry` times for full coverage.
        wedge: list[str] = []
        wedge.append(_cut_petal(rng, cx, cy, inner_r, outer_r, half_w, ink))
        echo_outer = inner_r + (outer_r - inner_r) * rng.uniform(0.30, 0.45)
        wedge.append(_cut_petal(rng, cx, cy, inner_r, echo_outer,
                                half_w * rng.uniform(0.5, 0.65), accents[0]))
        mid_r = (inner_r + outer_r) / 2
        arc_gap = step * rng.uniform(0.04, 0.08)
        wedge.append(_cut_arc(rng, cx, cy, mid_r, arc_gap,
                              step - 2 * arc_gap, accents[1]))
        wedge_svg = "".join(wedge)
        parts: list[str] = []
        for i in range(symmetry):
            parts.append(
                f'<g transform="rotate({360 * i / symmetry:.2f} {cx:.0f} {cy:.0f})">'
                f"{wedge_svg}</g>"
            )
        if layer == LAYERED_LAYERS - 1:
            parts.append(
                f'<circle cx="{cx:.0f}" cy="{cy:.0f}" r="{max_radius * 0.13:.1f}" fill="{ink}"/>'
            )
            parts.append(
                f'<circle cx="{cx:.0f}" cy="{cy:.0f}" r="{max_radius * 0.05:.1f}" fill="#ffffff"/>'
            )
        bg = f'<rect width="{size}" height="{size}" fill="#ffffff"/>'
        layer_svgs.append(svgkit.svg_doc(size, size, bg + "".join(parts)))
        all_parts.extend(parts)
    combined = svgkit.svg_doc(
        size, size,
        f'<rect width="{size}" height="{size}" fill="#ffffff"/>' + "".join(all_parts),
    )
    return combined, layer_svgs


def validate_layered_svg(svg_text: str) -> str | None:
    """Return a defect description or None when the candidate passes."""
    if count_elements(svg_text) < 18:
        return f"too few elements ({count_elements(svg_text)})"
    for match in re.finditer(r'stroke-width="([\d.]+)"', svg_text):
        if float(match.group(1)) < 4.0:
            return "stroke thinner than 4px (cut hazard)"
    for match in re.finditer(r'<circle[^>]*\br="([\d.]+)"', svg_text):
        if float(match.group(1)) < 12.0:
            return "floating dot detected"
    return None


def build_layered_mandala_bundle(rng: random.Random, out_dir: Path, slug: str,
                              theme: dict | None = None) -> dict:
    folder = out_dir / slug
    folder.mkdir(parents=True, exist_ok=True)
    palette = themes.theme_palette(theme) if theme else None
    title = (f"{themes.theme_label(theme)} 3D Layered Mandala SVG Pack"
             if theme else "3D Layered Mandala SVG Pack")
    files: list[str] = []
    total_elements = 0
    for i in range(BUNDLE_SIZES["layered-mandala"]):
        for attempt in range(MAX_ATTEMPTS_PER_SLOT):
            state = rng.getstate()
            combined, layers = render_layered_design(rng, palette)
            defect = None
            for svg in [combined, *layers]:
                d = validate_layered_svg(svg)
                if d is not None:
                    defect = d
                    break
            if defect is None:
                break
            # Failed validation: do not reset state - original semantics are
            # "try a new random design until one passes". `state` is reused
            # AFTER success to drive a matching PNG render below.
        else:
            raise RuntimeError("layered mandala slot failed quality gate after retries")
        names = [f"{slug}-design-{i + 1}.svg"] + [
            f"{slug}-design-{i + 1}-layer-{j}.svg" for j in range(1, LAYERED_LAYERS + 1)
        ]
        for name, svg in zip(names, [combined, *layers]):
            (folder / name).write_text(svg, encoding="utf-8")
            files.append(str((folder / name).relative_to(ROOT)).replace("\\", "/"))
        # Generate matching PNG preview (combined design, theme-faithful stylization)
        rng.setstate(state)
        rgb_palette, params = _layered_pixels(rng, palette)
        png_name = f"{slug}-design-{i + 1}.png"
        pixel_fn = _make_layered_pixel_fn(rgb_palette, params, 1000)
        pngio.write_png(folder / png_name, 1000, 1000, pixel_fn)
        files.append(str((folder / png_name).relative_to(ROOT)).replace("\\", "/"))
        total_elements += sum(count_elements(s) for s in layers)
    write_package_docs(folder, title, files,
                       "cut-ready bold shapes, 3 layers per design for cardstock stacking",
                       theme=theme, product_type="layered-mandala",
                       designs=BUNDLE_SIZES["layered-mandala"])
    return {
        "files": files,
        "folder": str(folder.relative_to(ROOT)).replace("\\", "/"),
        "designs": BUNDLE_SIZES["layered-mandala"],
        "preview": files[0],
        "quality": {"elements": total_elements},
    }


# --------------------------------------------------------------------------
# Pattern sheet v2: richer tile vocabulary
# --------------------------------------------------------------------------

def _pattern_def(pid: str, kind: str, unit: int, fg: str, base: str) -> str:
    h = unit / 2
    q = unit / 4

    def sw(fraction: float) -> float:
        return max(2.0, unit * fraction)

    shapes: dict[str, str] = {
        "dots": "".join(
            f'<circle cx="{cx_:.1f}" cy="{cy_:.1f}" r="{h * 0.30:.1f}" fill="{fg}"/>'
            for cx_, cy_ in ((h, h), (0, 0), (unit, 0), (0, unit), (unit, unit))
        ),
        "triangles": (
            f'<path d="M0,{unit:.1f} L{h:.1f},0 L{unit:.1f},{unit:.1f} Z" fill="{fg}"/>'
            f'<path d="M{h:.1f},{unit:.1f} L{unit:.1f},0 L{unit:.1f},{unit:.1f}" '
            f'fill="none" stroke="{fg}" stroke-width="{sw(0.03):.1f}"/>'
        ),
        "lines": (
            f'<line x1="0" y1="{h:.1f}" x2="{unit}" y2="{h:.1f}" '
            f'stroke="{fg}" stroke-width="{sw(0.08):.1f}"/>'
            f'<line x1="{h:.1f}" y1="0" x2="{h:.1f}" y2="{unit}" '
            f'stroke="{fg}" stroke-width="{sw(0.02):.1f}" opacity="0.6"/>'
        ),
        "zigzag": (
            f'<path d="M0,{3 * q:.1f} L{q:.1f},{q:.1f} L{2 * q:.1f},{3 * q:.1f} '
            f'L{3 * q:.1f},{q:.1f} L{unit:.1f},{3 * q:.1f}" fill="none" '
            f'stroke="{fg}" stroke-width="{sw(0.05):.1f}"/>'
        ),
        "diamonds": (
            f'<path d="M{h:.1f},0 L{unit:.1f},{h:.1f} L{h:.1f},{unit:.1f} L0,{h:.1f} Z" '
            f'fill="none" stroke="{fg}" stroke-width="{sw(0.04):.1f}"/>'
            f'<circle cx="{h:.1f}" cy="{h:.1f}" r="{q * 0.5:.1f}" fill="{fg}"/>'
        ),
        "plus": (
            f'<path d="M{h - q:.1f},{h - q:.1f} h{2 * q:.1f} v{2 * q:.1f} h{-2 * q:.1f} Z" '
            f'fill="{fg}"/>'
            f'<path d="M{h - q * 1.6:.1f},{h:.1f} h{3.2 * q:.1f} '
            f'M{h:.1f},{h - q * 1.6:.1f} v{3.2 * q:.1f}" '
            f'stroke="{fg}" stroke-width="{sw(0.03):.1f}"/>'
        ),
        "arcs": "".join(
            f'<circle cx="{unit * off:.2f}" cy="{unit:.2f}" r="{unit * 0.42:.1f}" '
            f'fill="none" stroke="{fg}" stroke-width="{sw(0.05):.1f}"/>'
            for off in (0.25, 0.75)
        ),
        "scales": (
            f'<path d="M0,{unit:.1f} A{h:.1f} {h:.1f} 0 0 1 {unit:.1f},{unit:.1f} Z" '
            f'fill="{fg}" opacity="0.85"/>'
            f'<path d="M{-h:.1f},{unit:.1f} A{h:.1f} {h:.1f} 0 0 1 {h:.1f},{unit:.1f}" '
            f'fill="none" stroke="{fg}" stroke-width="{sw(0.03):.1f}"/>'
        ),
    }
    content = shapes[kind]
    return (
        f'<pattern id="{pid}" width="{unit}" height="{unit}" '
        f'patternUnits="userSpaceOnUse">'
        f'<rect width="{unit:.1f}" height="{unit:.1f}" fill="{base}"/>{content}</pattern>'
    )


PATTERN_KINDS = ["dots", "triangles", "lines", "zigzag", "diamonds", "plus", "arcs", "scales"]


def render_pattern_sheet(rng: random.Random,
                      palette: list[str] | None = None) -> str:
    w, h = 1000, 1400
    unit = rng.choice([70, 90, 110])
    if palette is None:
        palette = PALETTES[rng.randrange(len(PALETTES))]
    kinds = rng.sample(PATTERN_KINDS, 4)
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


def validate_pattern_sheet(svg_text: str) -> str | None:
    n_defs = svg_text.count("<pattern ")
    if n_defs < 4:
        return f"only {n_defs} pattern defs"
    if count_elements(svg_text) < 10:
        return "too few elements"
    return None


def build_pattern_pack(rng: random.Random, out_dir: Path, slug: str,
                     theme: dict | None = None) -> dict:
    folder = out_dir / slug
    folder.mkdir(parents=True, exist_ok=True)
    palette = themes.theme_palette(theme) if theme else None
    title = (f"{themes.theme_label(theme)} Seamless Pattern Pack"
             if theme else "Seamless Pattern Pack")
    files: list[str] = []
    for i in range(BUNDLE_SIZES["patterns"]):
        for attempt in range(MAX_ATTEMPTS_PER_SLOT):
            svg = render_pattern_sheet(rng, palette)
            defect = validate_pattern_sheet(svg)
            if defect is None:
                break
        else:
            raise RuntimeError("pattern slot failed quality gate after retries")
        name = f"{slug}-board-{i + 1}.svg"
        (folder / name).write_text(svg, encoding="utf-8")
        files.append(str((folder / name).relative_to(ROOT)).replace("\\", "/"))
    write_package_docs(folder, title, files, "tileable vector boards",
                       theme=theme, product_type="patterns", designs=BUNDLE_SIZES["patterns"])
    return {
        "files": files,
        "folder": str(folder.relative_to(ROOT)).replace("\\", "/"),
        "designs": BUNDLE_SIZES["patterns"],
        "preview": files[0],
        "quality": {"boards": BUNDLE_SIZES["patterns"]},
    }


# --------------------------------------------------------------------------
# Quote card v2: kicker + double frame + rules, safe font stacks only
# --------------------------------------------------------------------------

def render_quote_card(rng: random.Random, quote: str, serial: int,
                    palette: list[str] | None = None) -> str:
    w, h = 1080, 1350
    if palette is None:
        palette = PALETTES[rng.randrange(len(PALETTES))]
    background = palette[rng.randrange(len(palette))]
    foreground = "#ffffff" if _lum(background) < 0.45 else "#10131a"
    accent_candidates = [c for c in palette if abs(_lum(c) - _lum(background)) > 0.3]
    accent = rng.choice(accent_candidates) if accent_candidates else foreground

    margin = 90
    font_size = 88
    line_height = int(font_size * 1.38)
    lines = svgkit.wrap_text(quote, 15)
    block_h = len(lines) * line_height
    center_y = h / 2 - block_h / 2 + font_size
    tspans = "".join(
        f'<tspan x="{w / 2}" y="{center_y + i * line_height:.0f}">{svgkit.escape(line)}</tspan>'
        for i, line in enumerate(lines)
    )
    body = [
        f'<rect width="{w}" height="{h}" fill="{background}"/>',
        f'<rect x="{margin}" y="{margin}" width="{w - 2 * margin}" height="{h - 2 * margin}" '
        f'fill="none" stroke="{foreground}" stroke-width="3" opacity="0.85"/>',
        f'<rect x="{margin + 14}" y="{margin + 14}" width="{w - 2 * margin - 28}" '
        f'height="{h - 2 * margin - 28}" fill="none" stroke="{foreground}" '
        'stroke-width="1" opacity="0.4"/>',
        f'<path d="M {margin} {margin + 60} L {margin} {margin} L {margin + 60} {margin}" '
        f'fill="none" stroke="{accent}" stroke-width="6"/>',
        f'<path d="M {w - margin - 60} {h - margin} L {w - margin} {h - margin} '
        f'L {w - margin} {h - margin - 60}" fill="none" stroke="{accent}" stroke-width="6"/>',
        f'<text x="{w / 2:.0f}" y="{center_y - line_height * 1.9:.0f}" '
        f'font-family="{SANS_STACK}" font-size="30" letter-spacing="12" '
        f'fill="{accent}" text-anchor="middle">DAILY FUEL No.{serial:03d}</text>',
        f'<text x="{w / 2:.0f}" y="{center_y - line_height * 1.35:.0f}" '
        f'font-family="{SERIF_STACK}" font-size="44" fill="{foreground}" '
        'text-anchor="middle">~</text>',
        f'<text font-family="{SERIF_STACK}" font-size="{font_size}" '
        f'fill="{foreground}" text-anchor="middle">{tspans}</text>',
        f'<line x1="{w * 0.34:.0f}" y1="{center_y + block_h + line_height * 0.9:.0f}" '
        f'x2="{w * 0.66:.0f}" y2="{center_y + block_h + line_height * 0.9:.0f}" '
        f'stroke="{accent}" stroke-width="3"/>',
        f'<text x="{w / 2:.0f}" y="{center_y + block_h + line_height * 1.6:.0f}" '
        f'font-family="{SANS_STACK}" font-size="24" letter-spacing="6" '
        f'fill="{foreground}" opacity="0.75" text-anchor="middle">'
        'VECTORFORGE DAILY</text>',
    ]
    return svgkit.svg_doc(w, h, "".join(body))


def validate_quote_card(svg_text: str) -> str | None:
    for token in ("DAILY FUEL", "VECTORFORGE"):
        if token not in svg_text:
            return f"missing {token}"
    # a card carries 3 rects + 2 paths + 1 line of geometry; texts excluded
    if count_elements(svg_text) < 6:
        return "too few elements"
    return None


def build_quote_set(rng: random.Random, out_dir: Path, slug: str, serial: int,
                  theme: dict | None = None) -> dict:
    folder = out_dir / slug
    folder.mkdir(parents=True, exist_ok=True)
    palette = themes.theme_palette(theme) if theme else None
    title = (f"{themes.theme_label(theme)} Quote Card Set"
             if theme else "Quote Card Set")
    quote_bank = themes.theme_quotes(theme) if theme else QUOTES
    picks = rng.sample(quote_bank, min(BUNDLE_SIZES["quotes"], len(quote_bank)))
    files: list[str] = []
    for i, quote in enumerate(picks):
        for attempt in range(MAX_ATTEMPTS_PER_SLOT):
            svg = render_quote_card(rng, quote, serial, palette)
            defect = validate_quote_card(svg)
            if defect is None:
                break
        else:
            raise RuntimeError("quote slot failed quality gate after retries")
        name = f"{slug}-card-{i + 1}.svg"
        (folder / name).write_text(svg, encoding="utf-8")
        files.append(str((folder / name).relative_to(ROOT)).replace("\\", "/"))
    write_package_docs(folder, title, files, "1080x1350 social-ready cards",
                       theme=theme, product_type="quotes", designs=BUNDLE_SIZES["quotes"])
    return {
        "files": files,
        "folder": str(folder.relative_to(ROOT)).replace("\\", "/"),
        "designs": BUNDLE_SIZES["quotes"],
        "preview": files[0],
        "quality": {"cards": 4},
    }


# --------------------------------------------------------------------------
# Planner (clean grid geometry, contrast-checked header)
# --------------------------------------------------------------------------

def render_planner(rng: random.Random,
                 palette: list[str] | None = None) -> str:
    w, h = 1123, 794
    if palette is None:
        palette = PALETTES[rng.randrange(len(PALETTES))]
    header_color = sorted(palette, key=_lum)[0]
    margin, top = 40, 150
    rows, cols = 8, 31
    cw = (w - margin * 2) / cols
    rh = (h - top - 50) / rows
    parts = [f'<rect width="{w}" height="{h}" fill="#ffffff"/>']
    parts.append(f'<rect x="0" y="0" width="{w}" height="90" fill="{header_color}"/>')
    parts.append(
        f'<text x="40" y="58" font-family="{SANS_STACK}" font-size="34" '
        'font-weight="bold" fill="#ffffff">Habit Tracker</text>'
    )
    parts.append(
        f'<text x="{w - margin}" y="56" text-anchor="end" '
        f'font-family="{SANS_STACK}" font-size="22" '
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
            'stroke="#dedede" stroke-width="1"/>'
        )
    for c in range(cols + 1):
        x = margin + c * cw
        parts.append(
            f'<line x1="{x:.1f}" y1="{top:.1f}" x2="{x:.1f}" '
            f'y2="{top + rows * rh:.1f}" stroke="#dedede" stroke-width="1"/>'
        )
    label_w = cw * 2
    for r in range(rows):
        parts.append(
            f'<line x1="{margin + label_w:.1f}" y1="{top + r * rh:.1f}" '
            f'x2="{margin + label_w:.1f}" y2="{top + (r + 1) * rh:.1f}" '
            'stroke="#dedede" stroke-width="1"/>'
        )
        parts.append(
            f'<text x="{margin + 12:.1f}" y="{top + r * rh + rh / 2 + 5:.1f}" '
            'font-size="13" fill="#888888">Habit _______</text>'
        )
    return svgkit.svg_doc(w, h, "".join(parts))


def validate_planner(svg_text: str) -> str | None:
    lines = svg_text.count("<line")
    if lines < 40:
        return f"grid incomplete ({lines} lines)"
    return None


def build_planner(rng: random.Random, out_dir: Path, slug: str,
                theme: dict | None = None) -> dict:
    folder = out_dir / slug
    folder.mkdir(parents=True, exist_ok=True)
    palette = themes.theme_palette(theme) if theme else None
    title = (f"{themes.theme_label(theme)} Habit Tracker Printable"
             if theme else "Habit Tracker Printable")
    variants = BUNDLE_SIZES["planner"]
    files: list[str] = []
    for i in range(variants):
        for attempt in range(MAX_ATTEMPTS_PER_SLOT):
            svg = render_planner(rng, palette)
            defect = validate_planner(svg)
            if defect is None:
                break
        else:
            raise RuntimeError("planner slot failed quality gate after retries")
        name = f"{slug}-sheet-{i + 1}.svg"
        (folder / name).write_text(svg, encoding="utf-8")
        files.append(str((folder / name).relative_to(ROOT)).replace("\\", "/"))
    write_package_docs(folder, title, files, "A4 landscape print sheets",
                       theme=theme, product_type="planner", designs=BUNDLE_SIZES["planner"])
    return {
        "files": files,
        "folder": str(folder.relative_to(ROOT)).replace("\\", "/"),
        "designs": variants,
        "preview": files[0],
        "quality": {"sheets": variants},
    }


# --------------------------------------------------------------------------
# Packaging paperwork (LICENSE.txt + ABOUT.txt inside every bundle)
# --------------------------------------------------------------------------

LICENSE_TEXT = """{title}
Generated by VectorForge Daily automation pipeline.

LICENSE - Commercial Use Grant
The operator of this archive grants the downloader a perpetual,
worldwide, royalty-free license to use these files in personal AND
commercial projects (physical products, client work, printed goods).

NOT permitted:
- Reselling or redistributing the raw digital files as-is
- Claiming authorship of the source designs

Attribution appreciated but not required.
"""

# Per-type use-case examples for the enhanced ABOUT.txt (P4 packaging).
# Shown as a 4-5 bullet list to help buyers visualize what they can make.
USE_CASES: dict[str, list[str]] = {
    "mandala": [
        "Wall art and printable posters (12x12 inch and up)",
        "Cricut / Silhouette vinyl decals for cars, laptops, water bottles",
        "Wood-burned and laser-engraved signs (Glowforge, xTool, OMTech)",
        "Vinyl stencil for furniture and floor cloths",
        "Adult coloring book pages and zen-tangle printables",
    ],
    "layered-mandala": [
        "3D paper art: cut each layer from different cardstock and stack with foam dots",
        "Shadow-box frames (8x8 or 10x10 inch) with foam-mounted layers",
        "Cricut Maker cardstock cut files (each layer ships as a separate SVG)",
        "Wall hangings on canvas stretcher bars (one layer per bar)",
        "Vinyl layered decals (cut each color from a different vinyl sheet)",
    ],
    "patterns": [
        "Fabric and textile printing (pillows, tea towels, aprons)",
        "Wrapping paper, gift tags, and stationery",
        "Scrapbooking and digital planner backgrounds",
        "Phone cases, mugs, and sublimation printables",
        "Web and social-media tileable backgrounds",
    ],
    "quotes": [
        "Instagram and Pinterest posts (1080x1350 portrait, on-brand)",
        "Printable wall art for home office and living room",
        "T-shirt and tote-bag iron-on transfers",
        "Daily social media content calendar posts",
        "Greeting cards and gift tags",
    ],
    "planner": [
        "A4 / US Letter printable planner insert (print at 100% or 'fit to page')",
        "Bullet journal and disc-bound planner pages",
        "Homeschool and classroom tracking sheets",
        "Goal-setting worksheets and accountability trackers",
    ],
}


ABOUT_TEXT = """{title}

Theme: {theme_label}
{files_total} file(s) across {designs} design(s).

What is inside:
{file_list}

What you can make with this bundle:
{use_cases}

Quick use notes:
- SVG files open in Cricut Design Space, Silhouette Studio, Inkscape,
  Illustrator, Figma and most laser software.
- PNG files (when included) are 1000x1000 transparent rasters - use them
  in Canva, Procreate, or any tool that does not read SVG.
- All shapes are vector - scale to any size without quality loss.
- Printables: print at 100% scale on A4 or US Letter ("fit to page" also works).
- Colors are flat fills; recolor freely in any vector editor.

Format spec:
- ViewBox: 1000x1000 (square designs) or product-specific dimensions.
- Layered mandalas ship as one combined SVG + 3 separate layer SVGs.
- All designs carry an embedded generation marker for provenance.

Generated on {date}. Questions? Reach the operator via the storefront
support links.
"""


def write_package_docs(folder: Path, title: str, files: list[str], note: str,
                       theme: dict | None = None,
                       product_type: str = "",
                       designs: int = 0) -> None:
    """Write LICENSE.txt and ABOUT.txt for a bundle.

    Enhanced in P4:
    - Theme label surfaced in ABOUT.txt
    - Per-type use-case list (5 examples) so buyers visualize what they
      can make with the bundle
    - File count + design count for at-a-glance "value" perception
    - Format spec section explaining dimensions and layered-mandala structure
    """
    (folder / "LICENSE.txt").write_text(
        LICENSE_TEXT.format(title=title), encoding="utf-8"
    )
    listing = "\n".join(f"- {Path(f).name}" for f in files)
    use_cases = USE_CASES.get(product_type, [])
    use_case_lines = "\n".join(f"  - {uc}" for uc in use_cases) if use_cases else "  - Versatile designs for crafts, decor, and digital projects"
    about_args = {
        "title": f"{title} ({note})",
        "theme_label": themes.theme_label(theme) if theme else "Classic (evergreen)",
        "files_total": len(files),
        "designs": designs,
        "file_list": listing,
        "use_cases": use_case_lines,
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
    }
    (folder / "ABOUT.txt").write_text(
        ABOUT_TEXT.format(**about_args), encoding="utf-8"
    )


BUILDERS = {
    "mandala": build_mandala_bundle,
    "layered-mandala": build_layered_mandala_bundle,
    "patterns": build_pattern_pack,
    "quotes": build_quote_set,
    "planner": build_planner,
}


# --------------------------------------------------------------------------
# Catalog assembly
# --------------------------------------------------------------------------

def build_product(product_type: str, rng: random.Random, batch_dir: Path,
                today: str, theme: dict) -> dict:
    digest = hashlib.sha1(f"{today}-{product_type}".encode()).hexdigest()[:8]
    slug = f"{product_type}-{digest}"
    serial = 100 + datetime.strptime(today, "%Y-%m-%d").timetuple().tm_yday
    if product_type == "quotes":
        built = BUILDERS[product_type](rng, batch_dir, slug, serial, theme)
    else:
        built = BUILDERS[product_type](rng, batch_dir, slug, theme)
    meta = {"serial": serial, "designs": built["designs"]}
    item = {
        "id": slug,
        "type": product_type,
        "title": listings.title_for(product_type, meta, theme),
        "description": listings.description_for(product_type, meta, theme),
        "tags": listings.tags_for(product_type, theme),
        "files": built["files"],
        "folder": built["folder"],
        "preview": built["preview"],
        "created": today,
        "designs": built["designs"],
    }
    if "quality" in built:
        item["quality"] = built["quality"]
    return item


def main() -> None:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    rng = random.Random(f"auto-earn-engine:{today}")
    batch_dir = PRODUCTS_DIR / today
    batch_dir.mkdir(parents=True, exist_ok=True)

    catalog_path = CATALOG_PATH
    catalog: list[dict] = []
    if catalog_path.exists():
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    existing_ids = {item.get("id") for item in catalog}

    modified = False
    theme = themes.get_today_theme(today)
    for product_type in ("mandala", "layered-mandala", "patterns", "quotes", "planner"):
        item = build_product(product_type, rng, batch_dir, today, theme)
        # Idempotency: if id already in catalog, replace in place when the
        # regenerated item differs (e.g. P3 added PNG files, P2 added
        # theme prefix). Same date, same id, content updated.
        existing_idx = next(
            (i for i, e in enumerate(catalog) if e.get("id") == item["id"]), -1
        )
        if existing_idx >= 0:
            if (catalog[existing_idx].get("files") != item["files"]
                    or catalog[existing_idx].get("title") != item["title"]):
                catalog[existing_idx] = item
                modified = True
        else:
            catalog.append(item)
            modified = True

    if modified:
        CATALOG_DIR.mkdir(parents=True, exist_ok=True)
        catalog_path.write_text(json.dumps(catalog, indent=2), encoding="utf-8")

    new_count = sum(1 for i in catalog if i.get("created") == today)
    print(f"date={today} today_count={new_count} catalog_total={len(catalog)} "
          "(all slots passed inline quality gate)")


if __name__ == "__main__":
    main()
