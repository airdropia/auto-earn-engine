"""Render product SVGs to Pinterest-ready 1000x1000 PNG pins (stdlib only).

Supports the shape set emitted by our own generators: rect, circle, line.
Stroked circles are drawn as ring outlines; lines are drawn with thickness.
"""
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "pipeline"))
from pngio import write_png

ROOT = Path(__file__).parent
OUT_DIR = ROOT / "pins"
OUT_DIR.mkdir(exist_ok=True)

BASE = "https://airdropia.github.io/auto-earn-engine/"

PIN_TITLES = {
    "mandala": ("Free Mandala SVG Bundle - Cricut & Laser Cut Files",
                "Download 5 free mandala SVG designs, perfect for Cricut, laser cutting and crafts. New bundle daily!"),
    "patterns": ("Free Seamless Pattern SVG - Repeat Tile Designs",
                 "Free seamless vector pattern for fabric printing, wallpapers and surface design. New patterns daily!"),
    "quotes": ("Free Quote Card Templates - Instagram & Print",
               "4 free motivational quote card SVG templates for Instagram posts and printing. Grab the daily set!"),
    "planner": ("Free Habit Tracker Printable - A4 Planner Insert",
                "Free printable habit tracker SVG, A4 planner insert for goal tracking. New designs daily!"),
}


def parse_color(val):
    val = (val or "").strip()
    if not val or val == "none":
        return None
    if val.startswith("#"):
        if len(val) == 7:
            return (int(val[1:3], 16), int(val[3:5], 16), int(val[5:7], 16))
        if len(val) == 4:
            return tuple(int(c * 2, 16) for c in val[1:])
    m = re.match(r"rgb\((\d+),\s*(\d+),\s*(\d+)\)", val)
    if m:
        return (int(m.group(1)), int(m.group(2)), int(m.group(3)))
    return None


class Canvas:
    def __init__(self, size, bg):
        self.size = size
        self.px = [[bg] * size for _ in range(size)]

    def blend(self, x, y, color):
        if 0 <= x < self.size and 0 <= y < self.size:
            self.px[y][x] = color

    def fill_circle(self, cx, cy, r, color):
        if color is None:
            return
        r2 = r * r
        x_lo = max(0, int(cx - r) - 1)
        x_hi = min(self.size - 1, int(cx + r) + 1)
        y_lo = max(0, int(cy - r) - 1)
        y_hi = min(self.size - 1, int(cy + r) + 1)
        for y in range(y_lo, y_hi + 1):
            dy2 = (y - cy) ** 2
            for x in range(x_lo, x_hi + 1):
                if (x - cx) ** 2 + dy2 <= r2:
                    self.blend(x, y, color)

    def ring(self, cx, cy, r, width, color):
        if color is None:
            return
        ro = r + width / 2
        ri = r - width / 2
        x_lo = max(0, int(cx - ro) - 1)
        x_hi = min(self.size - 1, int(cx + ro) + 1)
        y_lo = max(0, int(cy - ro) - 1)
        y_hi = min(self.size - 1, int(cy + ro) + 1)
        for y in range(y_lo, y_hi + 1):
            dy2 = (y - cy) ** 2
            for x in range(x_lo, x_hi + 1):
                d2 = (x - cx) ** 2 + dy2
                if ri**2 <= d2 <= ro**2:
                    self.blend(x, y, color)

    def line(self, x1, y1, x2, y2, width, color):
        if color is None:
            return
        steps = int(max(abs(x2 - x1), abs(y2 - y1)) * 2) + 1
        half = width / 2
        for i in range(steps + 1):
            t = i / steps
            x = x1 + (x2 - x1) * t
            y = y1 + (y2 - y1) * t
            self.fill_circle(x, y, half, color)

    def write(self, path):
        px = self.px
        size = self.size

        def pixel_fn(x, y):
            return px[y][x]

        write_png(path, size, size, pixel_fn)


def svg_to_png(svg_path: Path, out_path: Path, size: int = 1000) -> None:
    text = svg_path.read_text(encoding="utf-8")

    vb = re.search(r'viewBox="([\d\.\- ]+)"', text)
    if vb:
        x0, y0, w, h = (float(v) for v in vb.group(1).split())
    else:
        x0, y0, w, h = 0.0, 0.0, float(size), float(size)

    scale = size / max(w, h)
    off_x = (size - w * scale) / 2 - x0 * scale
    off_y = (size - h * scale) / 2 - y0 * scale

    bg = (255, 255, 255)
    bg_m = re.search(r'<rect[^>]*fill="(#[0-9a-fA-F]+)"[^>]*/>', text)
    if bg_m:
        c = parse_color(bg_m.group(1))
        if c:
            bg = c
    cv = Canvas(size, bg)

    for m in re.finditer(r"<circle([^/>]*)/>", text):
        a = dict(re.findall(r'([\w:-]+)="([^"]*)"', m.group(1)))
        cx = float(a.get("cx", "0")) * scale + off_x
        cy = float(a.get("cy", "0")) * scale + off_y
        r = float(a.get("r", "0")) * scale
        stroke_w = float(a.get("stroke-width", "1")) * scale
        if a.get("fill", "none") != "none":
            cv.fill_circle(cx, cy, r, parse_color(a["fill"]))
        if a.get("stroke", "none") != "none":
            cv.ring(cx, cy, r, stroke_w, parse_color(a["stroke"]))

    for m in re.finditer(r"<line([^/>]*)/>", text):
        a = dict(re.findall(r'([\w:-]+)="([^"]*)"', m.group(1)))
        x1 = float(a.get("x1", "0")) * scale + off_x
        y1 = float(a.get("y1", "0")) * scale + off_y
        x2 = float(a.get("x2", "0")) * scale + off_x
        y2 = float(a.get("y2", "0")) * scale + off_y
        sw = float(a.get("stroke-width", "1")) * scale
        cv.line(x1, y1, x2, y2, sw, parse_color(a.get("stroke")))

    for m in re.finditer(r"<rect([^/>]*)/>", text):
        a = dict(re.findall(r'([\w:-]+)="([^"]*)"', m.group(1)))
        if "x" not in a and "y" not in a and a.get("width") in ("100%", None):
            continue  # background already applied
        rx = float(a.get("x", "0")) * scale + off_x
        ry = float(a.get("y", "0")) * scale + off_y
        rw = float(a.get("width", "0")) * scale
        rh = float(a.get("height", "0")) * scale
        col = parse_color(a.get("fill"))
        if col:
            for y in range(max(0, int(ry)), min(size, int(ry + rh))):
                for x in range(max(0, int(rx)), min(size, int(rx + rw))):
                    cv.blend(x, y, col)

    cv.write(out_path)


def main() -> None:
    products_dir = ROOT / "products"
    made = 0
    for day_dir in sorted(products_dir.iterdir()):
        if not day_dir.is_dir():
            continue
        for prod_dir in sorted(day_dir.iterdir()):
            kind = prod_dir.name.split("-")[0]
            svgs = sorted(prod_dir.glob("*.svg"))
            if not svgs:
                continue
            out = OUT_DIR / f"{prod_dir.name}.png"
            try:
                svg_to_png(svgs[0], out)
                made += 1
            except Exception as exc:
                print(f"skip {prod_dir.name}: {exc}")
    print(f"pins made: {made}")

    lines = []
    for day_dir in sorted(products_dir.iterdir()):
        for prod_dir in sorted(day_dir.iterdir()):
            kind = prod_dir.name.split("-")[0]
            title, desc = PIN_TITLES.get(kind, ("Free SVG Design Bundle", "Free daily SVG downloads."))
            lines.append(f"## pins/{prod_dir.name}.png")
            lines.append(f"Title: {title}")
            lines.append(
                f"Description: {desc} Get it free: {BASE} "
                f"#{kind}svg #freebies #cricut #lasercut #silhouettecameo #printable"
            )
            lines.append("")
    (OUT_DIR / "captions.md").write_text("\n".join(lines), encoding="utf-8")
    print("captions written")


if __name__ == "__main__":
    main()
