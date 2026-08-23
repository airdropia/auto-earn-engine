#!/usr/bin/env python3
"""Static storefront builder.

Reads catalog/catalog.json + config.json and renders a self-contained
site/ folder ready for GitHub Pages deployment (stdlib only).
"""
from __future__ import annotations

import json
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import pngio
import svgkit

ROOT = Path(__file__).resolve().parents[1]
PRODUCTS_DIR = ROOT / "products"
CATALOG_PATH = ROOT / "catalog" / "catalog.json"
CONFIG_PATH = ROOT / "config.json"
SITE_DIR = ROOT / "site"

CSS = """
:root { color-scheme: dark; }
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: 'Segoe UI', system-ui, sans-serif; background: #0d1117; color: #e6edf3; }
a { color: inherit; text-decoration: none; }
header { padding: 48px 24px 32px; text-align: center; background: linear-gradient(180deg,#101826,#0d1117); }
header h1 { font-size: 2rem; letter-spacing: -0.02em; }
header p { color: #8b949e; margin-top: 8px; }
.badge { display:inline-block; margin-top:14px; font-size:.8rem; color:#58a6ff; border:1px solid #1f6feb55; border-radius:999px; padding:4px 12px; }
.stats { display:flex; gap:12px; justify-content:center; margin-top:16px; flex-wrap:wrap; }
.stats span { background:#161b22; border:1px solid #21262d; border-radius:8px; padding:6px 14px; font-size:.85rem; color:#c9d1d9; }
main { max-width: 1200px; margin: 0 auto; padding: 32px 20px 64px; }
.grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(270px,1fr)); gap:18px; }
.card { background:#161b22; border:1px solid #21262d; border-radius:14px; overflow:hidden; display:flex; flex-direction:column; transition:border-color .15s; }
.card:hover { border-color:#388bfd66; }
.thumb { background:#ffffff; aspect-ratio:1/1; display:flex; align-items:center; justify-content:center; overflow:hidden; }
.thumb img { width:100%; height:100%; object-fit:contain; }
.card-body { padding:14px 16px 16px; display:flex; flex-direction:column; gap:10px; flex:1; }
.card h2 { font-size:.95rem; line-height:1.35; }
.tags { display:flex; flex-wrap:wrap; gap:6px; }
.tags em { font-style:normal; font-size:.68rem; color:#8b949e; background:#0d1117; border:1px solid #21262d; border-radius:999px; padding:2px 8px; }
.actions { margin-top:auto; display:flex; gap:8px; }
.btn { flex:1; text-align:center; font-size:.82rem; font-weight:600; border-radius:8px; padding:9px 10px; }
.btn-primary { background:#238636; color:#fff; }
.btn-ghost { border:1px solid #30363d; color:#c9d1d9; }
.support { margin-top:44px; background:#101826; border:1px solid #1f2937; border-radius:14px; padding:22px; }
.support h3 { margin-bottom:8px; }
.support p { color:#9aa7b4; font-size:.92rem; line-height:1.5; }
.support a { color:#58a6ff; }
footer { text-align:center; color:#6e7681; font-size:.78rem; padding:28px 16px 40px; line-height:1.6; }
@media (max-width:520px){ header{padding:34px 16px 24px;} .grid{grid-template-columns:1fr;} }
"""


def rel(path: str) -> str:
    """Convert ROOT-relative product path to site-relative URL."""
    return path.replace("\\", "/")


def money_links(cfg: dict) -> str:
    parts: list[str] = []
    if cfg.get("patreon_url"):
        parts.append(
            f'<p>Support monthly on <a href="{svgkit.escape(cfg["patreon_url"])}" '
            'target="_blank" rel="noopener">Patreon</a> - every design here stays free.</p>'
        )
    if cfg.get("kofi_url"):
        parts.append(
            f'<p>Tip the machine\'s operator on <a href="{svgkit.escape(cfg["kofi_url"])}" '
            'target="_blank" rel="noopener">Ko-fi</a> - every file here is free.</p>'
        )
    if cfg.get("github_sponsors_url"):
        parts.append(
            f'<p>Sponsor the pipeline on <a href="{svgkit.escape(cfg["github_sponsors_url"])}" '
            'target="_blank" rel="noopener">GitHub Sponsors</a>.</p>'
        )
    if cfg.get("affiliate_html"):
        parts.append(str(cfg["affiliate_html"]))
    if not parts:
        parts.append(
            "<p>Monetization slots activate here automatically once store links "
            "are added to <code>config.json</code> (see docs/SETUP.md).</p>"
        )
    return "".join(parts)


def render_index(cfg: dict, catalog: list[dict]) -> str:
    newest = max(item["created"] for item in catalog)
    cards: list[str] = []
    for item in sorted(catalog, key=lambda x: x["created"], reverse=True):
        tag_html = "".join(f"<em>{svgkit.escape(t)}</em>" for t in item["tags"][:5])
        zip_href = f"downloads/{item['id']}.zip"
        preview_href = rel(item["preview"])
        files_list = "".join(
            f'<a class="btn btn-ghost" href="{rel(f)}" download>SVG {i + 1}</a>'
            for i, f in enumerate(item["files"][:2])
        )
        extra = (
            f'<span style="font-size:.72rem;color:#6e7681">+{len(item["files"]) - 2} more in zip</span>'
            if len(item["files"]) > 2
            else ""
        )
        cards.append(
            '<div class="card">'
            f'<div class="thumb"><img loading="lazy" src="{preview_href}" alt="{svgkit.escape(item["title"])}"/></div>'
            '<div class="card-body">'
            f"<h2>{svgkit.escape(item['title'])}</h2>"
            f'<div class="tags">{tag_html}</div>'
            f'{extra}'
            '<div class="actions">'
            f'<a class="btn btn-primary" href="{zip_href}" download>Download ZIP</a>'
            f"{files_list}"
            "</div></div></div>"
        )
    updated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return (
        "<!DOCTYPE html><html lang=\"en\"><head>"
        '<meta charset="utf-8"/>'
        '<meta name="viewport" content="width=device-width, initial-scale=1"/>'
        f"<title>{svgkit.escape(cfg['store_name'])} - Free SVG Bundles Daily</title>"
        '<meta name="description" content="New generative SVG design bundles published daily by automation. Free download."/>'
        '<meta property="og:title" content="' + svgkit.escape(cfg["store_name"]) + '"/>'
        '<meta property="og:description" content="Fresh SVG design bundles generated every day by automation."/>'
        '<meta property="og:image" content="og.png"/>'
        f"<style>{CSS}</style></head><body>"
        "<header>"
        f"<h1>{svgkit.escape(cfg['store_name'])}</h1>"
        f"<p>{svgkit.escape(cfg['tagline'])}</p>"
        '<span class="badge">&#9889; 100% automated &middot; free downloads</span>'
        '<div class="stats">'
        f"<span>{len(catalog)} products</span>"
        f"<span>updated {newest}</span>"
        "<span>SVG vector format</span>"
        "</div></header><main>"
        f'<div class="grid">{"".join(cards)}</div>'
        '<section class="support"><h3>Support this machine</h3>'
        f"{money_links(cfg)}"
        "</section></main>"
        f"<footer>Auto-generated by a GitHub Actions pipeline on {updated}.<br/>"
        "All assets original and generated in-house.</footer>"
        "</body></html>"
    )


def make_og_image(site_dir: Path, cfg: dict) -> None:
    seed = sum(ord(c) for c in cfg.get("store_name", "store"))
    c1 = [(seed * 7) % 256, (seed * 13) % 256, (seed * 29) % 256]
    c2 = [min(255, v + 70) for v in c1][::-1]

    def pixel(x: int, y: int):
        t = y / 630
        r = int(c1[0] + (c2[0] - c1[0]) * t)
        g = int(c1[1] + (c2[1] - c1[1]) * t)
        b = int(c1[2] + (c2[2] - c1[2]) * t)
        if (x + y) % 56 < 14:
            r, g, b = min(255, r + 18), min(255, g + 18), min(255, b + 18)
        return r, g, b

    pngio.write_png(site_dir / "og.png", 1200, 630, pixel)


def main() -> None:
    cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    catalog: list[dict] = []
    if CATALOG_PATH.exists():
        catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    if not catalog:
        print("catalog empty; run generate_products.py first")
        return

    if SITE_DIR.exists():
        shutil.rmtree(SITE_DIR)
    SITE_DIR.mkdir(parents=True)

    if PRODUCTS_DIR.exists():
        shutil.copytree(PRODUCTS_DIR, SITE_DIR / "products")

    downloads = SITE_DIR / "downloads"
    downloads.mkdir()
    zipped = 0
    for item in catalog:
        folder = ROOT / item.get("folder", "")
        if item.get("folder") and Path(folder).is_dir():
            with zipfile.ZipFile(downloads / f"{item['id']}.zip", "w", zipfile.ZIP_DEFLATED) as zf:
                for f in sorted(Path(folder).rglob("*")):
                    if f.is_file():
                        zf.write(f, f.relative_to(folder))
            zipped += 1

    make_og_image(SITE_DIR, cfg)
    (SITE_DIR / "index.html").write_text(render_index(cfg, catalog), encoding="utf-8")
    print(f"site built: products={len(catalog)} zips={zipped}")


if __name__ == "__main__":
    main()
