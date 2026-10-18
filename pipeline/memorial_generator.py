#!/usr/bin/env python3
"""
memorial_generator.py — the emotional memorial line (VectorForge Daily).

Owner directive (2026-10-15): the market is a mind game. Generic mandalas are
a commodity; grief is not. This line sells to people who are ACTIVELY
searching for a way to honour someone they lost, and the pull is emotional,
never technical. Every memorial design therefore carries:

  - a name-plate FRONT layer with editable placeholder text. The buyer types
    their beloved's name and dates in Cricut Design Space or Silhouette
    Studio; that single personalisation step is what turns a cut file into a
    keepsake, and it is what the listing copy leads with.
  - a motif layer whose central icon (paw / angel wings + halo / rainbow
    bridge) is chosen per variant, so the emotion is visible at a glance.
  - seven physical layers for real shadow-box depth.
  - soft memorial palettes: midnight, pearl, ivory, antique gold.

Variants (one per UTC day, rotated; `--all` emits one of each, used for a
launch run):

  pet      paw print + hearts, "Forever in our hearts"
  angel    angel wings + halo + stars, "Gone from sight, never from heart"
  rainbow  rainbow bridge + paws + stars, "Waiting at the rainbow bridge"

Priced at 9.99 USDT: a memorial buyer is not price-comparing in the moment,
they are looking for the one that feels right.

Idempotent: the slug derives from (variant, date), so re-running a day is a
no-op, matching the flagship generator's contract.
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
from flagship_generator import MOTIFS as PETAL_MOTIFS, _annulus_base, _ring

ROOT = Path(__file__).resolve().parents[1]
PRODUCTS_DIR = ROOT / "products"
CATALOG_DIR = ROOT / "catalog"
CATALOG_PATH = CATALOG_DIR / "catalog.json"

SIZE = 1200
LAYERS = 7
MIN_PART = 14.0
MAX_ATTEMPTS = 12
PRICE_USDT = "9.99"

# --- Variants ---------------------------------------------------------------

VARIANTS: dict[str, dict] = {
    "pet": {
        "label": "Pet Memorial",
        "icon": "paw",
        # midnight -> slate -> pearl -> ivory, with antique gold and a soft rose
        "palette": ["#1b2a4a", "#4a6fa5", "#9db4d0", "#f2ede3", "#c9a227"],
        "accent": "#b76e79",
        "plate_line": "Forever in our hearts",
        "titles": [
            "In Loving Memory Pet Shadow Box | {layers}-Layer Dog Memorial SVG",
            "Pet Memorial Shadow Box | {layers} Layers of Remembrance SVG",
            "Dog & Cat Memorial Shadow Box | {layers}-Layer Pet Keepsake SVG",
        ],
        "description": (
            "For the one who is waiting at the rainbow bridge. Seven soft layers "
            "of midnight blue, pearl and antique gold stack into a keepsake "
            "shadow box with a paw print at its heart. The front layer carries "
            "an editable name plate: type your beloved's name and dates in "
            "Cricut Design Space and it becomes yours in minutes."
        ),
        "tags": [
            "pet memorial svg", "dog memorial shadow box", "cat memorial svg",
            "in loving memory svg", "rainbow bridge svg", "pet loss keepsake",
            "sympathy gift svg", "layered memorial svg", "cricut memorial",
        ],
    },
    "angel": {
        "label": "In Loving Memory",
        "icon": "angel",
        "palette": ["#1b2a4a", "#4a6fa5", "#b9c9de", "#f7f4ec", "#c9a227"],
        "accent": "#e8e4d8",
        "plate_line": "Gone from sight, never from heart",
        "titles": [
            "Angel Wings Memorial Shadow Box | In Loving Memory SVG",
            "In Loving Memory Shadow Box | {layers}-Layer Angel Memorial SVG",
            "Memorial Angel Wings Cut File | {layers} Layer Shadow Box SVG",
        ],
        "description": (
            "Seven layers of soft midnight and ivory stack into an angel-winged "
            "memorial shadow box for someone you will never stop missing. The "
            "front name plate is editable: add their name and the years that "
            "bracket a whole life, in Cricut Design Space or Silhouette Studio, "
            "and the keepsake is ready to cut."
        ),
        "tags": [
            "in loving memory svg", "angel wings svg", "memorial shadow box",
            "sympathy gift svg", "memorial keepsake svg", "cricut memorial",
            "layered memorial svg", "bereavement gift", "remembrance svg",
        ],
    },
    "rainbow": {
        "label": "Rainbow Bridge",
        "icon": "rainbow",
        "palette": ["#1b2a4a", "#5a7fae", "#a8c0dc", "#f7f4ec", "#c9a227"],
        "accent": "#d9a5b3",
        "plate_line": "Waiting at the rainbow bridge",
        "titles": [
            "Rainbow Bridge Pet Memorial Shadow Box | {layers}-Layer SVG",
            "Pet Memorial Rainbow Bridge Shadow Box | {layers} Layers SVG",
            "Rainbow Bridge Memorial Cut File | {layers}-Layer Keepsake SVG",
        ],
        "description": (
            "A rainbow bridge arcs through seven soft layers, with paw prints "
            "resting at its heart. Cut it from cardstock and stack it into a "
            "memorial keepsake for the pet who is waiting on the other side. "
            "The front name plate is editable, so their name and years belong "
            "on it before you cut a single sheet."
        ),
        "tags": [
            "rainbow bridge svg", "pet memorial svg", "dog memorial shadow box",
            "in loving memory svg", "pet loss gift", "sympathy svg",
            "layered memorial svg", "cricut pet memorial", "keepsake shadow box",
        ],
    },
    "sunset": {
        "label": "Sunset Memorial",
        "icon": "heart",
        "palette": ["#2a1b3d", "#5a2d82", "#8e44ad", "#f4e1d2", "#c9a227"],
        "accent": "#b76e79",
        "plate_line": "Forever in the sunset",
        "titles": [
            "Sunset Memorial Shadow Box | {layers}-Layer SVG",
            "Sunset Memorial Cut File | {layers} Layer Shadow Box SVG",
            "Sunset Remembrance Shadow Box | {layers}-Layer Keepsake SVG",
        ],
        "description": (
            "Seven layers of deep purple, plum, and ivory stack into a sunset "
            "memorial shadow box with a heart motif at its heart. The front "
            "name plate is editable: type your beloved's name and dates in "
            "Cricut Design Space and it becomes yours in minutes."
        ),
        "tags": [
            "sunset memorial svg", "memorial shadow box svg", "in loving memory svg",
            "sympathy gift svg", "memorial keepsake svg", "cricut memorial",
            "layered memorial svg", "remembrance svg", "sunset shadow box",
        ],
    },
    "forest": {
        "label": "Forest Memorial",
        "icon": "leaf",
        "palette": ["#1b3a2a", "#2d5a3d", "#5a8a5d", "#f4efe1", "#c9a227"],
        "accent": "#8a9b7d",
        "plate_line": "Rooted in memory",
        "titles": [
            "Forest Memorial Shadow Box | {layers}-Layer SVG",
            "Forest Memorial Cut File | {layers} Layer Shadow Box SVG",
            "Forest Remembrance Shadow Box | {layers}-Layer Keepsake SVG",
        ],
        "description": (
            "Seven layers of deep forest green, moss, and ivory stack into a "
            "forest memorial shadow box with a leaf motif at its heart. The "
            "front name plate is editable: type your beloved's name and dates "
            "in Cricut Design Space and it becomes yours in minutes."
        ),
        "tags": [
            "forest memorial svg", "memorial shadow box svg", "in loving memory svg",
            "sympathy gift svg", "memorial keepsake svg", "cricut memorial",
            "layered memorial svg", "remembrance svg", "forest shadow box",
        ],
    },
    "ocean": {
        "label": "Ocean Memorial",
        "icon": "wave",
        "palette": ["#0a2a3a", "#1d4a5d", "#3d6a7d", "#e8f4f8", "#c9a227"],
        "accent": "#7da0b3",
        "plate_line": "Forever in the tide",
        "titles": [
            "Ocean Memorial Shadow Box | {layers}-Layer SVG",
            "Ocean Memorial Cut File | {layers} Layer Shadow Box SVG",
            "Ocean Remembrance Shadow Box | {layers}-Layer Keepsake SVG",
        ],
        "description": (
            "Seven layers of deep ocean blue, teal, and ivory stack into an "
            "ocean memorial shadow box with a wave motif at its heart. The "
            "front name plate is editable: type your beloved's name and dates "
            "in Cricut Design Space and it becomes yours in minutes."
        ),
        "tags": [
            "ocean memorial svg", "memorial shadow box svg", "in loving memory svg",
            "sympathy gift svg", "memorial keepsake svg", "cricut memorial",
            "layered memorial svg", "remembrance svg", "ocean shadow box",
        ],
    },
    "candle": {
        "label": "Candle Memorial",
        "icon": "heart",
        "palette": ["#3d2b1f", "#6a4c93", "#9b59b6", "#f4e9e2", "#c9a227"],
        "accent": "#d4a5a5",
        "plate_line": "Your light remains",
        "titles": [
            "Candle Memorial Shadow Box | {layers}-Layer SVG",
            "Candle Memorial Cut File | {layers} Layer Shadow Box SVG",
            "Candle Remembrance Shadow Box | {layers}-Layer Keepsake SVG",
        ],
        "description": (
            "Seven layers of deep amber, plum, and ivory stack into a candle "
            "memorial shadow box with a heart motif at its heart. The front "
            "name plate is editable: type your beloved's name and dates in "
            "Cricut Design Space and it becomes yours in minutes."
        ),
        "tags": [
            "candle memorial svg", "memorial shadow box svg", "in loving memory svg",
            "sympathy gift svg", "memorial keepsake svg", "cricut memorial",
            "layered memorial svg", "remembrance svg", "candle shadow box",
        ],
    },
    "star": {
        "label": "Star Memorial",
        "icon": "star",
        "palette": ["#1a2a3a", "#3d5a7d", "#5a7da0", "#e8f0f8", "#c9a227"],
        "accent": "#f0d9b5",
        "plate_line": "A star in our sky",
        "titles": [
            "Star Memorial Shadow Box | {layers}-Layer SVG",
            "Star Memorial Cut File | {layers} Layer Shadow Box SVG",
            "Star Remembrance Shadow Box | {layers}-Layer Keepsake SVG",
        ],
        "description": (
            "Seven layers of deep night blue, teal, and ivory stack into a "
            "star memorial shadow box with a star motif at its heart. The "
            "front name plate is editable: type your beloved's name and dates "
            "in Cricut Design Space and it becomes yours in minutes."
        ),
        "tags": [
            "star memorial svg", "memorial shadow box svg", "in loving memory svg",
            "sympathy gift svg", "memorial keepsake svg", "cricut memorial",
            "layered memorial svg", "remembrance svg", "star shadow box",
        ],
    },
    "cross": {
        "label": "Cross Memorial",
        "icon": "star",
        "palette": ["#2a2a3a", "#4a4a5d", "#6a6a8d", "#f4f4f8", "#c9a227"],
        "accent": "#b0b0c0",
        "plate_line": "Forever in our hearts",
        "titles": [
            "Cross Memorial Shadow Box | {layers}-Layer SVG",
            "Cross Memorial Cut File | {layers} Layer Shadow Box SVG",
            "Cross Remembrance Shadow Box | {layers}-Layer Keepsake SVG",
        ],
        "description": (
            "Seven layers of deep charcoal, slate, and ivory stack into a "
            "cross memorial shadow box with a star motif at its heart. The "
            "front name plate is editable: type your beloved's name and dates "
            "in Cricut Design Space and it becomes yours in minutes."
        ),
        "tags": [
            "cross memorial svg", "memorial shadow box svg", "in loving memory svg",
            "sympathy gift svg", "memorial keepsake svg", "cricut memorial",
            "layered memorial svg", "remembrance svg", "cross shadow box",
        ],
    },
}

_FONT = "Georgia, 'Times New Roman', serif"


# --- helpers ----------------------------------------------------------------

def _p(cx, cy, r, a):
    return cx + r * math.cos(a), cy + r * math.sin(a)


def _fmt(x, y):
    return f"{x:.1f} {y:.1f}"


def _star(cx, cy, r, fill, points=5):
    pts = []
    for i in range(points * 2):
        rr = r if i % 2 == 0 else r * 0.42
        a = -math.pi / 2 + i * math.pi / points
        x, y = _p(cx, cy, rr, a)
        pts.append(_fmt(x, y))
    poly = " ".join(pts)
    return '<polygon points="%s" fill="%s"/>' % (poly, fill)


def _icon_paw(cx, cy, r, fill):
    """Paw print: a pad blob plus four toes."""
    parts = []
    pad = (
        f"M {_fmt(cx - 0.62 * r, cy + 0.42 * r)} "
        f"C {_fmt(cx - 0.62 * r, cy + 0.05 * r)} {_fmt(cx - 0.38 * r, cy - 0.22 * r)} {_fmt(cx, cy - 0.22 * r)} "
        f"C {_fmt(cx + 0.38 * r, cy - 0.22 * r)} {_fmt(cx + 0.62 * r, cy + 0.05 * r)} {_fmt(cx + 0.62 * r, cy + 0.42 * r)} "
        f"C {_fmt(cx + 0.62 * r, cy + 0.74 * r)} {_fmt(cx + 0.3 * r, cy + 0.86 * r)} {_fmt(cx, cy + 0.86 * r)} "
        f"C {_fmt(cx - 0.3 * r, cy + 0.86 * r)} {_fmt(cx - 0.62 * r, cy + 0.74 * r)} {_fmt(cx - 0.62 * r, cy + 0.42 * r)} Z"
    )
    parts.append(f'<path d="{pad}" fill="{fill}"/>')
    # Toes must clear MIN_PART as well: a paw print is drawn as one pad plus
    # four toe islands, and undersized islands tear out on the mat.
    toe_r = max(0.19 * r, MIN_PART + 1.5)
    for deg in (-62, -21, 21, 62):
        a = math.radians(deg)
        # toes sit above the pad
        tx = cx + math.sin(a) * 0.55 * r
        ty = cy - 0.42 * r + math.sin(a) * 0.3 * r
        parts.append(f'<circle cx="{tx:.1f}" cy="{ty:.1f}" r="{toe_r:.1f}" fill="{fill}"/>')
    return "".join(parts)


def _icon_heart(cx, cy, r, fill):
    d = (
        f"M {_fmt(cx, cy + 0.78 * r)} "
        f"C {_fmt(cx - 1.05 * r, cy + 0.05 * r)} {_fmt(cx - 0.6 * r, cy - 0.62 * r)} {_fmt(cx - 0.28 * r, cy - 0.55 * r)} "
        f"C {_fmt(cx - 0.06 * r, cy - 0.5 * r)} {_fmt(cx, cy - 0.25 * r)} {_fmt(cx, cy - 0.2 * r)} "
        f"C {_fmt(cx, cy - 0.25 * r)} {_fmt(cx + 0.06 * r, cy - 0.5 * r)} {_fmt(cx + 0.28 * r, cy - 0.55 * r)} "
        f"C {_fmt(cx + 0.6 * r, cy - 0.62 * r)} {_fmt(cx + 1.05 * r, cy + 0.05 * r)} {_fmt(cx, cy + 0.78 * r)} Z"
    )
    return f'<path d="{d}" fill="{fill}"/>'


def _icon_wings(cx, cy, r, fill):
    """One mirrored wing per side: three scalloped feathers."""
    def feather(dx):
        # a single curved blade from the shoulder outward
        x0, y0 = cx + dx * 0.1 * r, cy + 0.05 * r
        x1, y1 = cx + dx * 1.15 * r, cy - 0.35 * r
        x2, y2 = cx + dx * 1.55 * r, cy + 0.05 * r
        x3, y3 = cx + dx * 1.1 * r, cy + 0.5 * r
        return (
            f"M {_fmt(x0, y0)} "
            f"Q {_fmt(x1, y1)} {_fmt(x2, y2)} "
            f"Q {_fmt(x3, y3)} {_fmt(x0, y0 + 0.28 * r)} Z"
        )

    parts = [f'<path d="{feather(1)}" fill="{fill}"/>',
             f'<path d="{feather(-1)}" fill="{fill}"/>']
    # second, smaller feather pair above
    def feather2(dx):
        x0, y0 = cx + dx * 0.05 * r, cy - 0.1 * r
        x1, y1 = cx + dx * 0.9 * r, cy - 0.72 * r
        x2, y2 = cx + dx * 1.2 * r, cy - 0.35 * r
        x3, y3 = cx + dx * 0.75 * r, cy - 0.05 * r
        return (
            f"M {_fmt(x0, y0)} "
            f"Q {_fmt(x1, y1)} {_fmt(x2, y2)} "
            f"Q {_fmt(x3, y3)} {_fmt(x0, y0 + 0.2 * r)} Z"
        )
    parts.append(f'<path d="{feather2(1)}" fill="{fill}"/>')
    parts.append(f'<path d="{feather2(-1)}" fill="{fill}"/>')
    # halo above
    hr = 0.42 * r
    hy = cy - 1.25 * r
    halo = (
        f"M {_fmt(cx - hr, hy)} A {hr:.1f} {hr * 0.32:.1f} 0 1 0 {_fmt(cx + hr, hy)} "
        f"A {hr:.1f} {hr * 0.32:.1f} 0 1 0 {_fmt(cx - hr, hy)} Z"
    )
    parts.append(
        f'<path d="{halo}" fill="none" stroke="{fill}" stroke-width="{0.09 * r:.1f}"/>'
    )
    return "".join(parts)


def _icon_rainbow(cx, cy, r, fill):
    """Three concentric bridge arcs plus a small star under each end."""
    parts = []
    for i, (rr, col) in enumerate([(1.0 * r, fill), (0.78 * r, fill), (0.56 * r, fill)]):
        d = (
            f"M {_fmt(cx - rr, cy + 0.2 * r)} "
            f"A {rr:.1f} {rr:.1f} 0 0 1 {_fmt(cx + rr, cy + 0.2 * r)}"
        )
        parts.append(
            f'<path d="{d}" fill="none" stroke="{col}" '
            f'stroke-width="{0.16 * r:.1f}" stroke-linecap="round"/>'
        )
    # Foot dots must clear MIN_PART: a sub-14px island is a choking hazard on
    # a Cricut blade, not a decorative detail.
    dot_r = max(0.14 * r, MIN_PART + 1.5)
    parts.append(f'<circle cx="{cx - 0.72 * r:.1f}" cy="{cy + 0.52 * r:.1f}" r="{dot_r:.1f}" fill="{fill}"/>')
    parts.append(f'<circle cx="{cx + 0.72 * r:.1f}" cy="{cy + 0.52 * r:.1f}" r="{dot_r:.1f}" fill="{fill}"/>')
    return "".join(parts)


def _icon_leaf(cx, cy, r, fill):
    """A single leaf motif: stem plus leaf blade."""
    parts = []
    # Stem
    stem = (
        f"M {_fmt(cx, cy + 0.4 * r)} "
        f"Q {_fmt(cx, cy + 0.05 * r)} {_fmt(cx, cy - 0.3 * r)} Z"
    )
    parts.append(f'<path d="{stem}" fill="{fill}"/>')
    # Leaf blade - curved teardrop shape
    blade = (
        f"M {_fmt(cx - 0.35 * r, cy - 0.25 * r)} "
        f"Q {_fmt(cx - 0.6 * r, cy - 0.55 * r)} {_fmt(cx - 0.4 * r, cy - 0.8 * r)} "
        f"Q {_fmt(cx, cy - 0.7 * r)} {_fmt(cx + 0.4 * r, cy - 0.8 * r)} "
        f"Q {_fmt(cx + 0.6 * r, cy - 0.55 * r)} {_fmt(cx + 0.35 * r, cy - 0.25 * r)} "
        f"Q {_fmt(cx + 0.15 * r, cy - 0.15 * r)} {_fmt(cx, cy + 0.05 * r)} Z"
    )
    parts.append(f'<path d="{blade}" fill="{fill}"/>')
    # Vein
    vein = (
        f"M {_fmt(cx, cy - 0.3 * r)} "
        f"Q {_fmt(cx, cy - 0.5 * r)} {_fmt(cx, cy - 0.7 * r)} Z"
    )
    parts.append(f'<path d="{vein}" fill="none" stroke="{fill}" stroke-width="{0.05 * r:.1f}"/>')
    return "".join(parts)


def _icon_wave(cx, cy, r, fill):
    """A wave motif: three overlapping arcs."""
    parts = []
    for i, offset in enumerate([-0.3, 0.0, 0.3]):
        d = (
            f"M {_fmt(cx - r, cy + offset * r)} "
            f"Q {_fmt(cx - r * 0.5, cy + (offset + 0.15) * r)} {_fmt(cx, cy + offset * r)} "
            f"Q {_fmt(cx + r * 0.5, cy + (offset - 0.15) * r)} {_fmt(cx + r, cy + offset * r)}"
        )
        parts.append(f'<path d="{d}" fill="none" stroke="{fill}" stroke-width="{0.1 * r:.1f}"/>')
    return "".join(parts)


def _icon_candle(cx, cy, r, fill):
    """A candle motif: flame on top of a rectangular body."""
    parts = []
    # Candle body
    body = (
        f"M {_fmt(cx - 0.2 * r, cy + 0.3 * r)} "
        f"L {_fmt(cx + 0.2 * r, cy + 0.3 * r)} "
        f"L {_fmt(cx + 0.2 * r, cy - 0.2 * r)} "
        f"L {_fmt(cx - 0.2 * r, cy - 0.2 * r)} Z"
    )
    parts.append(f'<path d="{body}" fill="{fill}"/>')
    # Flame
    flame = (
        f"M {_fmt(cx, cy - 0.2 * r)} "
        f"Q {_fmt(cx - 0.1 * r, cy - 0.35 * r)} {_fmt(cx, cy - 0.45 * r)} "
        f"Q {_fmt(cx + 0.1 * r, cy - 0.35 * r)} {_fmt(cx, cy - 0.2 * r)} Z"
    )
    parts.append(f'<path d="{flame}" fill="#f0d9b5"/>')
    # Wick
    wick = (
        f"M {_fmt(cx, cy - 0.2 * r)} "
        f"L {_fmt(cx, cy - 0.1 * r)} Z"
    )
    parts.append(f'<path d="{wick}" fill="none" stroke="#8a7a6a" stroke-width="{0.05 * r:.1f}"/>')
    return "".join(parts)


def _icon_star(cx, cy, r, fill):
    """A five-pointed star motif."""
    pts = []
    for i in range(10):
        rr = r if i % 2 == 0 else r * 0.4
        a = -math.pi / 2 + i * math.pi / 5
        x, y = _p(cx, cy, rr, a)
        pts.append(_fmt(x, y))
    poly = " ".join(pts)
    return f'<polygon points="{poly}" fill="{fill}"/>'


def _icon_cross(cx, cy, r, fill):
    """A cross motif: vertical and horizontal bars."""
    parts = []
    bar_w = 0.18 * r
    bar_h = 0.7 * r
    # Vertical bar
    vbar = (
        f"M {_fmt(cx - bar_w / 2, cy - bar_h / 2)} "
        f"L {_fmt(cx + bar_w / 2, cy - bar_h / 2)} "
        f"L {_fmt(cx + bar_w / 2, cy + bar_h / 2)} "
        f"L {_fmt(cx - bar_w / 2, cy + bar_h / 2)} Z"
    )
    parts.append(f'<path d="{vbar}" fill="{fill}"/>')
    # Horizontal bar
    hbar = (
        f"M {_fmt(cx - bar_h / 2, cy - bar_w / 2)} "
        f"L {_fmt(cx + bar_h / 2, cy - bar_w / 2)} "
        f"L {_fmt(cx + bar_h / 2, cy + bar_w / 2)} "
        f"L {_fmt(cx - bar_h / 2, cy + bar_w / 2)} Z"
    )
    parts.append(f'<path d="{hbar}" fill="{fill}"/>')
    return "".join(parts)


def _big_icon(kind, cx, cy, r, fill):
    if kind == "paw":
        return _icon_paw(cx, cy, r, fill)
    if kind == "angel":
        return _icon_wings(cx, cy, r, fill)
    if kind == "rainbow":
        return _icon_rainbow(cx, cy, r, fill)
    if kind == "leaf":
        return _icon_leaf(cx, cy, r, fill)
    if kind == "wave":
        return _icon_wave(cx, cy, r, fill)
    if kind == "heart":
        return _icon_heart(cx, cy, r, fill)
    if kind == "candle":
        return _icon_candle(cx, cy, r, fill)
    if kind == "star":
        return _icon_star(cx, cy, r, fill)
    if kind == "cross":
        return _icon_cross(cx, cy, r, fill)
    return _icon_rainbow(cx, cy, r, fill)


def _small_icon(kind, cx, cy, r, fill):
    if kind == "paw":
        return _icon_heart(cx, cy, r, fill)
    if kind == "leaf":
        return _icon_heart(cx, cy, r, fill)
    if kind == "wave":
        return _icon_heart(cx, cy, r, fill)
    if kind == "candle":
        return _icon_star(cx, cy, r, fill)
    if kind == "star":
        return _icon_star(cx, cy, r, fill)
    if kind == "cross":
        return _icon_star(cx, cy, r, fill)
    return _star(cx, cy, r, fill)


def _text(cx, cy, content, size, fill, weight="normal", style="normal", spacing=None):
    sp = f' letter-spacing="{spacing}"' if spacing else ""
    return (
        f'<text x="{cx:.0f}" y="{cy:.0f}" font-family="{_FONT}" font-size="{size}" '
        f'font-weight="{weight}" font-style="{style}" text-anchor="middle" '
        f'fill="{fill}"{sp}>{svgkit.escape(content)}</text>'
    )


# --- Layer construction -----------------------------------------------------

def _front_layer(variant, cx, cy, max_r, palette):
    """The name plate: ivory disc, gold ring, editable placeholder text."""
    fill_front = palette[3]
    gold = palette[4]
    ink = palette[0]
    parts = [
        f'<circle cx="{cx:.0f}" cy="{cy:.0f}" r="{max_r:.1f}" fill="{fill_front}"/>',
        _annulus_base(cx, cy, max_r - 26, max_r - 8, gold),
    ]
    # a quiet ring of small gold dots
    for i in range(12):
        a = i * math.pi / 6
        x, y = _p(cx, cy, max_r * 0.845, a)
        parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{MIN_PART + 1.5:.1f}" fill="{gold}"/>')
    # medallion
    med = max_r * 0.46
    parts.append(f'<circle cx="{cx:.0f}" cy="{cy:.0f}" r="{med:.1f}" fill="#ffffff"/>')
    parts.append(
        f'<circle cx="{cx:.0f}" cy="{cy:.0f}" r="{med + 10:.1f}" fill="none" '
        f'stroke="{gold}" stroke-width="4"/>'
    )
    # the emotional copy, all editable text
    parts.append(_text(cx, cy - med * 0.52, "IN LOVING", 30, ink, spacing="7"))
    parts.append(_text(cx, cy - med * 0.30, "MEMORY", 30, ink, spacing="7"))
    parts.append(_text(cx, cy + med * 0.16, "Your Beloved's Name", 56, ink, weight="bold"))
    parts.append(_text(cx, cy + med * 0.52, "2010 \u2014 2026", 34, palette[1]))
    parts.append(
        _text(cx, cy + med * 0.78, variant["plate_line"], 26, palette[1], style="italic")
    )
    parts.append(_icon_heart(cx, cy + med * 1.02, 18, gold))
    return "".join(parts)


def _motif_layer(variant, cx, cy, max_r, palette, rng):
    """Deep layer: solid disc, central icon, small icon ring."""
    fill = palette[0]
    icon_fill = palette[4]
    parts = [f'<circle cx="{cx:.0f}" cy="{cy:.0f}" r="{max_r * 0.30:.1f}" fill="{fill}"/>']
    parts.append(_big_icon(variant["icon"], cx, cy, max_r * 0.155, icon_fill))
    ring_r = max_r * 0.245
    small = max(max_r * 0.028, MIN_PART + 1.5)
    for i in range(10):
        a = i * 2 * math.pi / 10 - math.pi / 2
        x, y = _p(cx, cy, ring_r, a)
        parts.append(_small_icon(variant["icon"], x, y, small, palette[2]))
    return "".join(parts)


def _back_layer(cx, cy, max_r, palette):
    fill = palette[0]
    gold = palette[4]
    parts = [f'<circle cx="{cx:.0f}" cy="{cy:.0f}" r="{max_r * 0.28:.1f}" fill="{fill}"/>']
    for i in range(12):
        a0 = i * math.pi / 6
        a1 = a0 + math.pi / 18
        x0, y0 = _p(cx, cy, max_r * 0.06, a0)
        x1, y1 = _p(cx, cy, max_r * 0.26, a0)
        x2, y2 = _p(cx, cy, max_r * 0.26, a1)
        x3, y3 = _p(cx, cy, max_r * 0.06, a1)
        parts.append(
            f'<path d="M {_fmt(x0, y0)} L {_fmt(x1, y1)} L {_fmt(x2, y2)} L {_fmt(x3, y3)} Z" fill="{gold}"/>'
        )
    return "".join(parts)


def _ring_layers(vng, cx, cy, max_r, palette, rng):
    """The four middle mandala rings, each a different petal motif."""
    bands = [(0.82, 0.70), (0.68, 0.56), (0.54, 0.42), (0.40, 0.30)]
    symmetry = rng.choice([10, 12, 14, 16])
    picks = rng.sample(range(len(PETAL_MOTIFS)), len(PETAL_MOTIFS))
    out = []
    for li, (top, bottom) in enumerate(bands):
        outer = max_r * top
        inner = max_r * bottom
        fill = palette[li % 3]
        motif = PETAL_MOTIFS[picks[li % len(picks)]]
        parts = [_annulus_base(cx, cy, inner, outer, fill)]
        parts.append(_ring(cx, cy, inner + 4, outer - 3, symmetry,
                           motif, rng, palette[(li + 1) % 3], "#ffffff"))
        out.append("".join(parts))
    return out


def render_memorial(variant, rng) -> tuple[str, list[str]]:
    """Return (combined_svg, [layer_svgs]) for one memorial design."""
    cx = cy = SIZE / 2
    max_r = SIZE / 2 - 30
    palette = variant["palette"]

    layer_bodies: list[str] = []
    layer_bodies.append(_front_layer(variant, cx, cy, max_r, palette))
    layer_bodies.extend(_ring_layers(variant, cx, cy, max_r, palette, rng))
    layer_bodies.append(_motif_layer(variant, cx, cy, max_r, palette, rng))
    layer_bodies.append(_back_layer(cx, cy, max_r, palette))

    bg = f'<rect width="{SIZE}" height="{SIZE}" fill="#ffffff"/>'
    layer_svgs = [svgkit.svg_doc(SIZE, SIZE, bg + body) for body in layer_bodies]
    combined = svgkit.svg_doc(SIZE, SIZE, bg + "".join(layer_bodies))
    return combined, layer_svgs


def validate(svg_text: str, is_combined: bool = False) -> str | None:
    n = sum(svg_text.count(f"<{t}") for t in ("path", "circle", "rect", "line", "polygon"))
    floor = 60 if is_combined else 8
    if n < floor:
        return f"too simple ({n} elements, floor {floor})"
    for m in re.finditer(r'<circle[^>]*\br="([\d.]+)"', svg_text):
        if float(m.group(1)) < MIN_PART:
            return f"floating dot r={m.group(1)}"
    return None


def build(rng, out_dir: Path, slug: str, variant: dict) -> dict:
    folder = out_dir / slug
    folder.mkdir(parents=True, exist_ok=True)
    for attempt in range(MAX_ATTEMPTS):
        combined, layers = render_memorial(variant, rng)
        defects = [d for d in (validate(combined, True), *(validate(s) for s in layers)) if d]
        if not defects:
            break
        print(f"attempt {attempt + 1}: {defects[:2]}")
    else:
        raise RuntimeError(f"memorial failed quality gate: {'; '.join(defects[:3])}")

    files = []
    names = [f"{slug}-design-1.svg"] + [
        f"{slug}-design-1-layer-{j}.svg" for j in range(1, LAYERS + 1)
    ]
    for name, svg in zip(names, [combined, *layers]):
        (folder / name).write_text(svg, encoding="utf-8")
        files.append(str((folder / name).relative_to(ROOT)).replace("\\", "/"))

    label = variant["label"]
    (folder / "LICENSE.txt").write_text(
        f"{label} 3D Shadow-Box Memorial - {LAYERS} Layers\n\n"
        "LICENSE - Commercial Use Grant: perpetual, worldwide, royalty-free\n"
        "license for personal AND commercial projects (physical products,\n"
        "client work, printed goods).\n\nNOT permitted: reselling or\n"
        "redistributing the raw digital files as-is; claiming authorship\n"
        "of the source designs.\n",
        encoding="utf-8",
    )
    (folder / "ABOUT.txt").write_text(
        f"{label} 3D Shadow-Box Memorial - {LAYERS} Layers\n\n"
        "A keepsake shadow box for someone you will never stop missing.\n\n"
        "PERSONALISE THE NAME PLATE (the front layer):\n"
        f"  1. Open {slug}-design-1-layer-1.svg in Cricut Design Space or\n"
        "     Silhouette Studio.\n"
        "  2. Double-click the placeholder text and type your beloved's name\n"
        "     and dates. Everything else cuts as-is.\n\n"
        "ASSEMBLE: cut each layer from cardstock, stack largest to smallest\n"
        "with foam dots. Voids in the upper layers reveal the layers beneath\n"
        "- that is the depth of the keepsake.\n",
        encoding="utf-8",
    )
    return {
        "files": files,
        "folder": str(folder.relative_to(ROOT)).replace("\\", "/"),
        "designs": 1,
        "preview": files[0],
        "quality": {"layers": LAYERS, "personalizable": True},
    }


def main() -> None:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true",
                    help="emit one design per variant (used on launch runs)")
    ap.add_argument("--variant", choices=sorted(VARIANTS), default=None)
    args = ap.parse_args()

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    yday = datetime.now(timezone.utc).timetuple().tm_yday

    catalog: list[dict] = []
    if CATALOG_PATH.exists():
        catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    existing = {item.get("id") for item in catalog}

    if args.all:
        names = list(VARIANTS)
    elif args.variant:
        names = [args.variant]
    else:
        names = [list(VARIANTS)[yday % len(VARIANTS)]]

    made = 0
    for vname in names:
        variant = VARIANTS[vname]
        digest = hashlib.sha1(f"memorial-{vname}-{today}".encode()).hexdigest()[:8]
        slug = f"memorial-{vname}-{digest}"
        # One listing per design, forever. The slug used to be minted from the
        # date, so every daily run created a *new* product id for a variant
        # that already existed: the storefront ended up selling the same paw
        # print three times, and the same collection bundle three times at
        # 17.99 USDT. Duplicate listings confuse a grieving buyer and make
        # three pages compete with each other in search. Reuse the id that is
        # already published for this variant and refresh its files in place.
        reused = next(
            (item.get("id") for item in catalog
             if str(item.get("id", "")).startswith(f"memorial-{vname}-")),
            None,
        )
        if reused:
            slug = reused
        elif slug in existing:
            print(f"memorial already exists for {today}: {slug}")
            continue
        rng = random.Random(f"memorial:{vname}:{today}")
        if reused:
            prev = next(item for item in catalog if item.get("id") == slug)
            prev_folder = prev.get("folder", "")
            built = build(rng, (ROOT / prev_folder).parent, slug, variant)
            prev.update({
                "title": variant["titles"][int(digest, 16) % len(variant["titles"])]
                         .format(layers=LAYERS),
                "description": variant["description"],
                "tags": variant["tags"],
                "files": built["files"],
                "folder": built["folder"],
                "preview": built["preview"],
            })
            made += 1
            print(f"memorial refreshed in place: {slug}")
            continue
        item = build(rng, PRODUCTS_DIR / today, slug, variant)
        discriminator = int(digest, 16) % len(variant["titles"])
        title = variant["titles"][discriminator].format(layers=LAYERS)
        catalog.append({
            "id": slug,
            "type": "memorial",
            "title": title,
            "description": variant["description"],
            "tags": variant["tags"],
            "files": item["files"],
            "folder": item["folder"],
            "preview": item["preview"],
            "created": today,
            "designs": item["designs"],
            "quality": item["quality"],
            "price_usdt": PRICE_USDT,
            "meta": {"price_usdt": PRICE_USDT},
        })
        made += 1
        print(f"memorial built: {slug} variant={vname} layers={LAYERS}")

    if made:
        CATALOG_DIR.mkdir(parents=True, exist_ok=True)
        CATALOG_PATH.write_text(json.dumps(catalog, indent=2) + "\n", encoding="utf-8")
        print(f"catalog updated: {made} memorial design(s)")


if __name__ == "__main__":
    main()
