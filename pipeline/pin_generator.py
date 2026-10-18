#!/usr/bin/env python3
"""Pinterest/Instagram-ready pin images, generated from the products.

Traffic to a design asset is won on images, not on text, so every pin is
built from a real product render instead of a stock photo: the design fills
the top of the frame and the words underneath say what the free maker does.

Each pin is emitted as SVG (so rsvg-convert in CI rasterises the text with a
real font) rather than being composited pixel by pixel here.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "catalog" / "catalog.json"
PINS = ROOT / "pins"

PIN_W, PIN_H = 1000, 1500

HEADLINES = {
    "memorial-pet-50b75d91": ("PET MEMORIAL SHADOW BOX", "Paw print, editable name plate"),
    "memorial-angel-55b91710": ("IN LOVING MEMORY", "Angel wings, editable name plate"),
    "memorial-rainbow-5c35a80d": ("RAINBOW BRIDGE", "For the one you are waiting for"),
    "memorial-sunset-70e940e6": ("A HEART IN MEMORY", "Purple keepsake, editable name"),
    "memorial-forest-b14fa0d6": ("ROOTED IN MEMORY", "Leaf motif, editable name plate"),
    "memorial-ocean-577f9da2": ("FOREVER IN THE TIDE", "Wave motif, editable name plate"),
    "memorial-bundle-5fb903ca": ("ALL 3 MEMORIAL DESIGNS", "One download, 3 name plates"),
}

MAKER_URL = "airdropia.github.io/auto-earn-engine/maker"


def _inner_svg(path: Path) -> str:
    """Body of a generated design SVG, with its header and <svg> tag removed.

    Bare ampersands are escaped on the way in: inlining the design into a
    larger document exposes any unescaped "&" in the source, which rsvg then
    rejects as a parse error and takes the whole pin step down with it.
    """
    text = path.read_text(encoding="utf-8")
    body = re.sub(r"^.*?<svg[^>]*>", "", text, flags=re.S)
    body = re.sub(r"</svg>\s*$", "", body, flags=re.S)
    body = re.sub(r"&(?!(?:#\d+|#x[0-9a-fA-F]+|[A-Za-z][A-Za-z0-9]*);)", "&amp;", body)
    return body.strip()


def _xml_safe(value: str) -> str:
    return (value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def pin_svg(design_path: Path, headline: str, subline: str) -> str:
    inner = _inner_svg(design_path)
    # The design is authored at 1200x1200; scale it to the top 1000px of the pin.
    scale = PIN_W / 1200.0
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{PIN_W}" height="{PIN_H}" viewBox="0 0 {PIN_W} {PIN_H}">
  <rect width="{PIN_W}" height="{PIN_H}" fill="#0d1117"/>
  <g transform="translate(0,0) scale({scale:.4f})">{inner}</g>
  <rect x="0" y="{PIN_W - 6}" width="{PIN_W}" height="6" fill="#c9a227"/>
  <text x="{PIN_W // 2}" y="1085" text-anchor="middle" font-family="Georgia, 'Times New Roman', serif"
        font-size="66" font-weight="bold" fill="#f2ede3" letter-spacing="2">{headline}</text>
  <text x="{PIN_W // 2}" y="1165" text-anchor="middle" font-family="Georgia, serif"
        font-size="38" fill="#9db4d0" font-style="italic">{subline}</text>
  <rect x="150" y="1215" width="700" height="132" rx="16" fill="#16202c" stroke="#26313f" stroke-width="2"/>
  <text x="{PIN_W // 2}" y="1272" text-anchor="middle" font-family="Georgia, serif"
        font-size="40" font-weight="bold" fill="#c9a227">FREE MEMORIAL MAKER</text>
  <text x="{PIN_W // 2}" y="1322" text-anchor="middle" font-family="Georgia, serif"
        font-size="30" fill="#8b949e">Type their name. No signup.</text>
  <text x="{PIN_W // 2}" y="1425" text-anchor="middle" font-family="Georgia, serif"
        font-size="26" fill="#6e7681">{MAKER_URL}</text>
</svg>
"""


def main() -> int:
    if not CATALOG.exists():
        print("no catalog; nothing to pin")
        return 0
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    PINS.mkdir(parents=True, exist_ok=True)

    written = 0
    for item in catalog:
        pid = str(item.get("id", ""))
        if not pid.startswith("memorial"):
            continue
        design = ROOT / str(item.get("folder", "")) / f"{pid}-design-1.svg"
        if not design.exists():
            continue
        headline, subline = HEADLINES.get(
            pid, (str(item.get("title", "Memorial shadow box"))[:26].upper(),
                  "Editable name plate, 7 layers")
        )
        headline = _xml_safe(headline)
        subline = _xml_safe(subline)
        out = PINS / f"{pid}-pin.svg"
        out.write_text(pin_svg(design, headline, subline), encoding="utf-8")
        written += 1

    print(f"pin svgs written: {written}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())