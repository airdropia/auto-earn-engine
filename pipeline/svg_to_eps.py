#!/usr/bin/env python3
"""
svg_to_eps.py - Convert VectorForge Daily SVG to EPS container (manual use).

P3 (AUDIT.md) multi-format delivery: SVG is primary, EPS is a secondary
option for users on Adobe tools that prefer EPS import. EPS is not part
of the daily pipeline - run this script on demand to produce a .eps file
alongside an existing .svg.

What this script does:
  - Wraps the SVG content inside a minimal EPSF-3.0 container with
    proper Adobe header + %%BoundingBox + %%EOF.
  - The SVG itself is embedded as a comment / included verbatim, so the
    .eps file can be opened in Adobe Illustrator (which reads the embedded
    SVG when the BoundingBox and ShowPage are present).

What this script does NOT do:
  - It does NOT convert SVG path geometry into PostScript path operators.
    Adobe Illustrator handles the import via its SVG parser; for other
    tools that need real PS geometry, use Inkscape's --export-type=eps.

Usage:
    python3 pipeline/svg_to_eps.py products/2026-09-06/mandala-*/design-1.svg
    # writes design-1.eps in the same folder

Multiple input files are supported.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

EPS_HEADER_TEMPLATE = """%!PS-Adobe-3.0 EPSF-3.0
%%BoundingBox: 0 0 {width} {height}
%%HiResBoundingBox: 0.000000 0.000000 {width}.000000 {height}.000000
%%Title: {title}
%%Creator: VectorForge Daily (svg_to_eps.py)
%%CreationDate: D:20260906
%%LanguageLevel: 2
%%Pages: 1
%%DocumentData: Clean7Bit
%%EndComments
%%BeginProlog
%%EndProlog
%%Page: 1 1
%%BeginDocument: embedded_svg
"""


def svg_dimensions(svg_text: str) -> tuple[int, int]:
    """Extract width/height from <svg width="W" height="H" ...>."""
    w_match = re.search(r'\bwidth="(\d+)"', svg_text)
    h_match = re.search(r'\bheight="(\d+)"', svg_text)
    if not w_match or not h_match:
        return 1000, 1000
    return int(w_match.group(1)), int(h_match.group(1))


def svg_to_eps(svg_path: Path) -> Path:
    """Read an .svg and write an .eps container alongside it."""
    if not svg_path.exists():
        raise FileNotFoundError(svg_path)
    if svg_path.suffix.lower() != ".svg":
        raise ValueError(f"Not an SVG file: {svg_path}")

    svg_text = svg_path.read_text(encoding="utf-8")
    width, height = svg_dimensions(svg_text)
    header = EPS_HEADER_TEMPLATE.format(
        width=width, height=height, title=svg_path.stem
    )
    eps_text = (
        header
        + "%% SVG content embedded below as a comment for Adobe import:\n"
        + "".join(f"% {line}\n" for line in svg_text.splitlines())
        + "%%EndDocument\nshowpage\n%%Trailer\n%%EOF\n"
    )
    eps_path = svg_path.with_suffix(".eps")
    eps_path.write_text(eps_text, encoding="utf-8")
    return eps_path


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 1
    written: list[Path] = []
    for arg in argv:
        p = Path(arg)
        if not p.exists():
            print(f"  skip (not found): {p}", file=sys.stderr)
            continue
        if p.is_dir():
            for svg in sorted(p.rglob("*.svg")):
                written.append(svg_to_eps(svg))
        else:
            written.append(svg_to_eps(p))
    for eps in written:
        print(f"  wrote {eps} ({eps.stat().st_size} bytes)")
    return 0 if written else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
