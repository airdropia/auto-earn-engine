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
.support code { background:#0d1117; border:1px solid #21262d; border-radius:6px; padding:5px 9px; word-break:break-all; color:#7ee787; font-size:.82rem; }
.copy-btn { background:#21262d; border:1px solid #30363d; color:#c9d1d9; border-radius:6px; padding:5px 12px; font-size:.75rem; cursor:pointer; margin-left:8px; vertical-align:middle; }
.copy-btn:hover { border-color:#58a6ff; color:#fff; }
.warn { display:block; font-size:.72rem; color:#d29922; margin-top:4px; }
.actions.big { margin:22px 0 8px; }
.actions.big .btn { flex:0 0 auto; padding:12px 18px; }
.info { background:#101826; border:1px solid #1f2937; border-radius:14px; padding:22px; margin-top:26px; line-height:1.6; }
.info p { color:#9aa7b4; font-size:.92rem; margin:10px 0; }
.buy { background:#11161d; border:1px solid #2b3644; border-radius:14px; padding:18px; margin:22px 0; }
.buy h3 { margin:0 0 8px; font-size:1.1rem; }
.buy p { color:#9aa7b4; font-size:.92rem; margin:8px 0; }
.buy .price { font-size:1.25rem; color:#e6edf3; margin:12px 0 4px; }
.buy .price strong { color:#7ee787; }
.buy code { word-break:break-all; background:#0d1117; border:1px solid #21262d; border-radius:6px; padding:8px 10px; display:inline-block; font-size:.82rem; color:#7ee787; }
.buycta { margin-top:14px; }
table.price-table { width:100%; border-collapse:collapse; margin-top:10px; font-size:.9rem; }
table.price-table th, table.price-table td { text-align:left; padding:9px 10px; border-bottom:1px solid #21262d; }
table.price-table th { color:#8b949e; font-weight:600; font-size:.78rem; text-transform:uppercase; letter-spacing:.04em; }
table.price-table td.amt { color:#7ee787; font-family:ui-monospace,monospace; white-space:nowrap; }
.card-price { color:#7ee787; font-size:.82rem; font-family:ui-monospace,monospace; margin:2px 0 8px; }
.info h3 { margin-top:20px; font-size:1.05rem; }
.info h3:first-of-type { margin-top:0; }
.hero { background:#ffffff; border-radius:14px; border:1px solid #21262d; padding:18px; display:flex; align-items:center; justify-content:center; }
.hero img { max-width:min(560px,100%); height:auto; border-radius:10px; }
.related { display:grid; grid-template-columns:repeat(auto-fill,minmax(210px,1fr)); gap:12px; margin-top:14px; }
.rel { background:#161b22; border:1px solid #21262d; border-radius:10px; padding:10px; display:flex; align-items:center; gap:10px; transition:border-color .15s; }
.rel:hover { border-color:#388bfd66; }
.rel img { width:52px; height:52px; object-fit:contain; background:#fff; border-radius:6px; }
.rel span { font-size:.8rem; line-height:1.3; color:#c9d1d9; }
footer { text-align:center; color:#6e7681; font-size:.78rem; padding:28px 16px 40px; line-height:1.6; }
@media (max-width:520px){ header{padding:34px 16px 24px;} .grid{grid-template-columns:1fr;} }
"""


def contact_link(cfg: dict) -> str:
    """Footer contact line, only when an email is configured."""
    email = cfg.get("contact_email") or ""
    if not email:
        return ""
    return f' &middot; <a href="mailto:{svgkit.escape(email)}">{svgkit.escape(email)}</a>'

def rel(path: str) -> str:
    """Convert ROOT-relative product path to site-relative URL."""
    return path.replace("\\", "/")


def money_links(cfg: dict) -> str:
    parts: list[str] = []
    if cfg.get("patreon_url"):
        parts.append(
            f'<p>Support monthly on <a href="{svgkit.escape(cfg["patreon_url"])}" '
            'target="_blank" rel="noopener">Patreon</a> - new designs every week.</p>'
        )
    if cfg.get("kofi_url"):
        parts.append(
            f'<p>Tip the machine\'s operator on <a href="{svgkit.escape(cfg["kofi_url"])}" '
            'target="_blank" rel="noopener">Ko-fi</a>.</p>'
        )
    if cfg.get("github_sponsors_url"):
        parts.append(
            f'<p>Sponsor the pipeline on <a href="{svgkit.escape(cfg["github_sponsors_url"])}" '
            'target="_blank" rel="noopener">GitHub Sponsors</a>.</p>'
        )
    if cfg.get("crypto_address"):
        network = cfg.get("crypto_network") or "crypto"
        parts.append(
            '<p>Crypto tip - '
            f'{svgkit.escape(network)} only:</p>'
            f'<p><code id="tip-address">{svgkit.escape(cfg["crypto_address"])}</code>'
            '<button class="copy-btn" type="button" '
            'onclick="navigator.clipboard.writeText(document.getElementById(\'tip-address\').textContent)">Copy</button>'
            f'<span class="warn">Send only {svgkit.escape(network)} to this address - other assets will be lost.</span></p>'
        )
    if cfg.get("affiliate_html"):
        parts.append(str(cfg["affiliate_html"]))
    if not parts:
        parts.append(
            "<p>Monetization slots activate here automatically once store links "
            "are added to <code>config.json</code> (see README).</p>"
        )
    return "".join(parts)


def canonical_url(cfg: dict) -> str:
    """Public base URL of the storefront, no trailing slash."""
    return (cfg.get("site_base_url") or "https://airdropia.github.io/auto-earn-engine").rstrip("/")

def product_page_url(cfg: dict, item: dict) -> str:
    """Canonical URL of a single product's landing page."""
    return f"{canonical_url(cfg)}/p/{item['id']}/"

def file_buttons(item: dict) -> str:
    """Download buttons for a product: one per format (SVG, PNG, MOCKUP),
    falling back to the first two files when no preferred format exists."""
    def fmt_of(path_str: str) -> str:
        name = Path(path_str).name
        if "-mockup" in name:
            return "MOCKUP"
        ext = Path(path_str).suffix.upper().lstrip(".")
        return ext or "FILE"

    by_fmt: dict[str, list[str]] = {}
    for f in item.get("files", []):
        by_fmt.setdefault(fmt_of(f), []).append(f)
    displayed: list[tuple[str, str]] = []
    per_fmt: dict[str, int] = {}
    for fmt in ("SVG", "PNG", "MOCKUP"):
        if by_fmt.get(fmt):
            per_fmt[fmt] = per_fmt.get(fmt, 0) + 1
            displayed.append((by_fmt[fmt][0], f"{fmt} {per_fmt[fmt]}"))
    if not displayed:
        for f in item.get("files", [])[:2]:
            fmt = fmt_of(f)
            per_fmt[fmt] = per_fmt.get(fmt, 0) + 1
            displayed.append((f, f"{fmt} {per_fmt[fmt]}"))
    return "".join(
        f'<a class="btn btn-ghost" href="{rel(f)}" download>{label}</a>'
        for f, label in displayed
    )

def product_jsonld(cfg: dict, item: dict) -> str:
    """schema.org Product markup. Rich results need price/availability, and
    marking the item honestly is what lets it qualify for product rich results."""
    import json as _json
    base = canonical_url(cfg)
    payload = {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": item["title"],
        "description": " ".join((item.get("description") or "").split())[:300],
        "sku": item["id"],
        "category": item.get("type") or "Digital Design",
        "brand": {"@type": "Brand", "name": cfg.get("store_name", "VectorForge Daily")},
        "image": [f"{base}/{rel(item.get('preview', ''))}"],
        "offers": {
            "@type": "Offer",
            "price": checkout_price(cfg, item),
            "priceCurrency": "USDT",
            "availability": "https://schema.org/InStock",
            "url": product_page_url(cfg, item),
            "seller": {"@type": "Organization", "name": cfg.get("store_name", "VectorForge Daily")},
        },
    }
    return _json.dumps(payload, indent=None)


def checkout_price(cfg: dict, item: dict) -> str:
    """Price in USDT for the paid bundle. Quality-first pricing: a single
    considered flagship is worth more than a cheap bundle nobody trusts."""
    override = (item.get("meta") or {}).get("price_usdt") or cfg.get("price_usdt", "7.00")
    return str(override)


def checkout_block(cfg: dict, item: dict) -> str:
    """Crypto checkout panel. No gateway account, no KYC: the buyer sends
    USDT BEP20 to the published address and payment is confirmed on-chain
    by pipeline/checkout.py. Full file list stays public as the free tier."""
    address = cfg.get("crypto_address", "")
    network = cfg.get("crypto_network") or "USDT (BEP20)"
    price = checkout_price(cfg, item)
    if not address:
        return ""
    return (
        '<section class="buy" id="buy">'
        f'<h3>Get the full {svgkit.escape(item.get("type", "bundle"))} bundle</h3>'
        '<p>Every layer file, the combined SVG, and the 6500px print-ready PNG '
        'render. Delivered instantly as a ZIP - you receive a download link '
        'the moment the payment is confirmed on-chain.</p>'
        f'<p class="price"><strong>{svgkit.escape(price)} {svgkit.escape(network)}</strong></p>'
        '<p class="payaddr">Send exactly <strong>the amount shown on the checkout '
        'page</strong> to:</p>'
        f'<p><code id="pay-address">{svgkit.escape(address)}</code>'
        '<button class="copy-btn" type="button" '
        'onclick="navigator.clipboard.writeText(document.getElementById(\'pay-address\').textContent)">Copy</button></p>'
        '<p class="warn">Only ' + svgkit.escape(network) + ' on the BEP20 network '
        '(BSC). Send anything else and the funds are unrecoverable. '
        'Payment is verified automatically on-chain; no account needed.</p>'
        '<p class="buycta"><a class="btn btn-primary" href="../checkout/">Open checkout</a></p>'
        '</section>'
    )


def render_product_page(cfg: dict, item: dict, catalog: list[dict]) -> str:
    """One indexable landing page per product (long-tail SEO).

    Each page has a unique title/description, the product image, download
    buttons, the full listing copy, license note, and links to related
    products (internal links help crawlers discover the whole catalog).
    """
    base = canonical_url(cfg)
    title = item["title"]
    desc = " ".join((item.get("description") or "").split())[:155]
    preview = rel(item.get("preview", ""))
    tag_html = "".join(f"<em>{svgkit.escape(t)}</em>" for t in item.get("tags", [])[:8])
    zip_href = f"{base}/downloads/{item['id']}.zip"
    # Description paragraphs (split on blank lines to keep the bullet list)
    desc_html = "".join(
        f"<p>{svgkit.escape(block)}</p>"
        for block in (item.get("description") or "").split("\n\n") if block.strip()
    )
    # Related products: same type, newest 6 excluding self
    related = [
        i for i in sorted(catalog, key=lambda x: x.get("created", ""), reverse=True)
        if i.get("type") == item.get("type") and i.get("id") != item.get("id")
    ][:6]
    related_html = "".join(
        f'<a class="rel" href="{product_page_url(cfg, r)}">'
        f'<img loading="lazy" src="/auto-earn-engine/{rel(r.get("preview", "")) if not rel(r.get("preview", "")).startswith("http") else r.get("preview", "")}" alt=""/>'
        f'<span>{svgkit.escape(r.get("title", "")[:52])}</span></a>'
        for r in related
    )
    updated = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    contact_line = contact_link(cfg)
    return (
        '<!DOCTYPE html><html lang="en"><head>'
        '<meta charset="utf-8"/>'
        '<meta name="viewport" content="width=device-width, initial-scale=1"/>'
        f"<title>{svgkit.escape(title)} | {svgkit.escape(cfg['store_name'])}</title>"
        f'<meta name="description" content="{svgkit.escape(desc)}"/>'
        f'<link rel="canonical" href="{product_page_url(cfg, item)}"/>'
        f'<meta property="og:title" content="{svgkit.escape(title)}"/>'
        f'<meta property="og:description" content="{svgkit.escape(desc)}"/>'
        f'<meta property="og:image" content="{base}/{svgkit.escape(preview)}"/>'
        '<meta name="twitter:card" content="summary_large_image"/>'
        '<meta name="robots" content="index,follow,max-image-preview:large"/>'
        f'<script type="application/ld+json">{product_jsonld(cfg, item)}</script>'
        f"<style>{CSS}</style></head><body>"
        '<header><p><a href="./../..">&larr; Back to all bundles</a></p>'
        f'<h1>{svgkit.escape(title)}</h1>'
        f'<div class="tags">{tag_html}</div>'
        f'<span class="badge">{svgkit.escape(cfg.get("store_name", "VectorForge Daily"))} '
        f'&middot; layered SVG cut files &middot; commercial use allowed</span>'
        '</header><main>'
        f'<div class="hero"><img src="{base}/{svgkit.escape(preview)}" alt="{svgkit.escape(title)}"/></div>'
        '<div class="actions big">'
        f'<a class="btn btn-primary" href="{base}/downloads/{item["id"]}.zip" download>Download full bundle (ZIP)</a>'
        f"{file_buttons(item)}"
        '</div>'
        + checkout_block(cfg, item)
        + f'<section class="info">{desc_html}'
        '<h3>License</h3>'
        '<p>Free for personal and commercial use. You may use these designs in physical '
        'products, client work and printed goods. Please do not resell or redistribute '
        'the raw digital files as-is.</p>'
        '<h3>How to use</h3>'
        '<p>SVG opens in Cricut Design Space, Silhouette Studio, Inkscape, Illustrator and '
        'most laser software. PNG files (where included) are 1000&times;1000 transparent '
        'rasters for Canva, Procreate and any tool that does not read SVG. All shapes are '
        'vector - scale to any size with no quality loss.</p>'
        '</section>'        + (f'<section class="info"><h3>More {svgkit.escape(item.get("type", ""))} bundles</h3>'
           f'<div class="related">{related_html}</div></section>' if related_html else "")
        + '<section class="support"><h3>Support this machine</h3>'
        + money_links(cfg)
        + '</section></main>'
        '<footer>Generated by the VectorForge Daily pipeline on ' + updated + '.<br/>'
        '<a href="./../..">All free SVG bundles</a> &middot; '
        '<a href="./../../privacy.html">Privacy Policy</a>' + contact_line + '</footer>'
        '</body></html>'
    )

def render_checkout(cfg: dict, catalog: list[dict]) -> str:
    """The checkout page. No account, no KYC, no gateway: buyer sends USDT
    BEP20 to the published address; payment is confirmed on-chain by
    pipeline/checkout.py, which assigns each product a unique amount."""
    base = canonical_url(cfg)
    address = cfg.get("crypto_address", "")
    network = cfg.get("crypto_network") or "USDT (BEP20)"
    price = checkout_price(cfg, {"meta": {}})
    rows = []
    for item in sorted(catalog, key=lambda x: x.get("created", ""), reverse=True):
        rows.append(
            f'<tr><td>{svgkit.escape(item.get("title", "")[:60])}</td>'
            f'<td class="amt">{svgkit.escape(checkout_price(cfg, item))} {svgkit.escape(network)}</td>'
            f'<td><a class="btn btn-ghost" href="{rel(item.get("preview", ""))}">preview</a></td></tr>'
        )
    return (
        '<!DOCTYPE html><html lang="en"><head>'
        '<meta charset="utf-8"/>'
        '<meta name="viewport" content="width=device-width, initial-scale=1"/>'
        f"<title>Crypto checkout | {svgkit.escape(cfg.get('store_name', 'VectorForge Daily'))}</title>"
        '<meta name="description" content="Buy layered SVG cut files with USDT. No account, no KYC - payment confirmed on-chain."/>'
        f'<link rel="canonical" href="{base}/checkout/"/>'
        '<meta name="robots" content="index,follow"/>'
        f"<style>{CSS}</style></head><body>"
        '<header><p><a href="./../..">&larr; Back to all bundles</a></p>'
        '<h1>Checkout</h1>'
        f'<span class="badge">{svgkit.escape(network)} &middot; no account needed &middot; on-chain verified</span>'
        '</header><main>'
        '<section class="info"><h3>How it works</h3>'
        '<ol><li>Pick a bundle below and note its exact amount.</li>'
        '<li>Send that amount of ' + svgkit.escape(network) + ' to the address shown.</li>'
        '<li>Payment is detected automatically on-chain and your download link '
        'is issued. No account, no login, no KYC - nothing to sign up for.</li></ol>'
        f'<p class="payaddr">Send only <strong>{svgkit.escape(network)}</strong> on the '
        'BEP20 network (BSC). Other assets sent here are unrecoverable.</p>'
        f'<p><code id="pay-address">{svgkit.escape(address)}</code>'
        '<button class="copy-btn" type="button" '
        'onclick="navigator.clipboard.writeText(document.getElementById(\'pay-address\').textContent)">Copy</button></p>'
        '</section>'
        '<section class="info"><h3>Available bundles</h3>'
        '<table class="price-table"><thead><tr><th>Bundle</th><th>Price</th><th></th></tr></thead>'
        '<tbody>' + "".join(rows) + '</tbody></table>'
        '</section>'
        + (f'<section class="support">{money_links(cfg)}</section>' if money_links(cfg) else "")
        + '</main><footer>Payments verified on-chain &middot; '
        f'<a href="./../..">All bundles</a> &middot; <a href="./../privacy.html">Privacy</a>'
        + contact_link(cfg) + '</footer></body></html>'
    )


# SEO keyword clusters. Each entry becomes an indexable /c/<slug>/ page
# targeting one search intent. Craft-cutting buyers search by machine + format
# + style, not by our product names, so these clusters are how the catalog
# becomes findable. Kept explicit (not auto-generated from tags) because each
# one needs hand-written copy that matches real search intent.
COLLECTIONS = [
    {
        "slug": "shadow-box-svg",
        "title": "Shadow Box SVG Files",
        "h1": "Shadow Box SVG Cut Files",
        "intro": (
            "Layered shadow box designs built for real physical depth. Each bundle "
            "ships every layer as a separate SVG plus the combined file, so you cut "
            "each sheet from cardstock and stack them in order. Voids in the upper "
            "layers reveal the layers beneath, which is what produces the 3D look."
        ),
        "match": ["shadow box", "shadow-box", "layered", "3d layered"],
    },
    {
        "slug": "cricut-mandala-svg",
        "title": "Cricut Mandala SVG Templates",
        "h1": "Cricut Mandala SVG Templates",
        "intro": (
            "Mandala templates that open directly in Cricut Design Space. Every shape "
            "is a clean vector path, so there is nothing to trace and nothing to clean "
            "up after import. Sized for cardstock and mat board."
        ),
        "match": ["mandala", "cricut"],
    },
    {
        "slug": "layered-svg-bundle",
        "title": "Layered SVG Bundles",
        "h1": "Layered SVG Bundles",
        "intro": (
            "Multi-layer SVG bundles with one file per layer plus a combined design. "
            "Works in Cricut Design Space, Silhouette Studio, Inkscape, Illustrator "
            "and most laser software. Scales to any size with no quality loss."
        ),
        "match": ["layered svg", "bundle", "layered"],
    },
    {
        "slug": "silhouette-cut-files",
        "title": "Silhouette Cut Files",
        "h1": "Silhouette Cut Files",
        "intro": (
            "Cut files prepared for Silhouette Studio. Grouped and named per layer so "
            "the cut order stays obvious, with registration-friendly outlines and "
            "no rasterised elements."
        ),
        "match": ["silhouette", "layered", "shadow box"],
    },
    {
        "slug": "mandala-svg",
        "title": "Mandala SVG Designs",
        "h1": "Mandala SVG Designs",
        "intro": (
            "Original mandala artwork as vector SVG. Radial symmetry built from "
            "generated geometry rather than traced stock art, so every curve stays "
            "sharp at any scale."
        ),
        "match": ["mandala"],
    },
    {
        "slug": "3d-layered-art",
        "title": "3D Layered Art Templates",
        "h1": "3D Layered Art Templates",
        "intro": (
            "Templates assembled from separate physical layers. Built for paper "
            "crafters and laser cutters who want depth rather than a flat print."
        ),
        "match": ["3d layered", "layered", "shadow box"],
    },
]


def collection_items(cfg: dict, catalog: list[dict], spec: dict) -> list[dict]:
    """Products matching a collection, scored by how many terms they hit."""
    terms = [t.lower() for t in spec["match"]]
    scored = []
    for item in catalog:
        hay = " ".join([
            item.get("title", ""), item.get("description", ""),
            " ".join(item.get("tags", [])), item.get("type", ""),
        ]).lower()
        hits = sum(1 for t in terms if t in hay)
        if hits:
            scored.append((hits, item))
    scored.sort(key=lambda x: (-x[0], x[1].get("created", "")), reverse=False)
    scored.sort(key=lambda x: x[1].get("created", ""), reverse=True)
    return [i for _, i in scored]


def render_collection(cfg: dict, catalog: list[dict], spec: dict) -> str:
    """An indexable landing page for one keyword cluster."""
    base = canonical_url(cfg)
    items = collection_items(cfg, catalog, spec)
    if not items:
        return ""
    cards = []
    for item in items:
        preview_href = rel(item.get("preview", ""))
        cards.append(
            '<div class="card">'
            f'<a class="thumb" href="{product_page_url(cfg, item)}">'
            f'<img loading="lazy" src="{preview_href}" alt="{svgkit.escape(item["title"])}"/></a>'
            '<div class="card-body">'
            f'<h2><a href="{product_page_url(cfg, item)}">{svgkit.escape(item["title"])}</a></h2>'
            f'<div class="tags">{"".join(f"<em>{svgkit.escape(t)}</em>" for t in item.get("tags", [])[:4])}</div>'
            f'<div class="card-price">{svgkit.escape(checkout_price(cfg, item))} '
            f'{svgkit.escape(cfg.get("crypto_network", "USDT (BEP20)"))}</div>'
            '<div class="actions">'
            f'<a class="btn btn-primary" href="{product_page_url(cfg, item)}">View bundle</a>'
            "</div></div></div>"
        )
    others = [c for c in COLLECTIONS if c["slug"] != spec["slug"]]
    links = "".join(
        f'<a class="rel" href="{base}/c/{c["slug"]}/"><span>{svgkit.escape(c["title"])}</span></a>'
        for c in others
    )
    updated = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return (
        '<!DOCTYPE html><html lang="en"><head>'
        '<meta charset="utf-8"/>'
        '<meta name="viewport" content="width=device-width, initial-scale=1"/>'
        f"<title>{svgkit.escape(spec['title'])} | {svgkit.escape(cfg['store_name'])}</title>"
        f'<meta name="description" content="{svgkit.escape(" ".join(spec["intro"].split())[:155])}"/>'
        f'<link rel="canonical" href="{base}/c/{spec["slug"]}/"/>'
        '<meta name="robots" content="index,follow,max-image-preview:large"/>'
        f'<meta property="og:title" content="{svgkit.escape(spec["h1"])}"/>'
        f'<meta property="og:description" content="{svgkit.escape(" ".join(spec["intro"].split())[:155])}"/>'
        f'<meta property="og:image" content="{base}/{svgkit.escape(rel(items[0].get("preview", "")))}"/>'
        f"<style>{CSS}</style></head><body>"
        '<header><p><a href="./../..">&larr; All bundles</a></p>'
        f"<h1>{svgkit.escape(spec['h1'])}</h1>"
        f'<span class="badge">{len(items)} design{"" if len(items)==1 else "s"} &middot; instant download &middot; USDT checkout</span>'
        '</header><main>'
        f'<section class="info"><p>{svgkit.escape(spec["intro"])}</p></section>'
        f'<div class="grid">{"".join(cards)}</div>'
        f'<section class="info"><h3>Browse other collections</h3><div class="related">{links}</div></section>'
        f'<section class="support"><h3>Support this machine</h3>{money_links(cfg)}</section>'
        '</main><footer>Updated ' + updated + ' &middot; '
        '<a href="./../..">All bundles</a> &middot; <a href="./../checkout/">Checkout</a>'
        + contact_link(cfg) + '</footer></body></html>'
    )


def write_seo_files(site_dir: Path, cfg: dict, catalog: list[dict]) -> None:
    """robots.txt + sitemap.xml for search engine indexing."""
    base = canonical_url(cfg)
    site_dir.joinpath("robots.txt").write_text(
        "User-agent: *\nAllow: /\n\n"
        f"Sitemap: {base}/sitemap.xml\n",
        encoding="utf-8",
    )

    urls: list[str] = [f"{base}/", f"{base}/checkout/"]
    for spec in COLLECTIONS:
        if collection_items(cfg, catalog, spec):
            urls.append(f"{base}/c/{spec['slug']}/")
    for item in sorted(catalog, key=lambda x: x["created"], reverse=True):
        urls.append(product_page_url(cfg, item))
        urls.append(f"{base}/downloads/{item['id']}.zip")
    # static pages
    urls.append(f"{base}/privacy.html")

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    entries: list[str] = []
    for u in urls:
        entries.append(
            "<url><loc>" + svgkit.escape(u) + "</loc>"
            f"<lastmod>{today}</lastmod></url>"
        )
    site_dir.joinpath("sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(entries)
        + "\n</urlset>\n",
        encoding="utf-8",
    )

def render_index(cfg: dict, catalog: list[dict]) -> str:
    newest = max(item["created"] for item in catalog)
    cards: list[str] = []
    for item in sorted(catalog, key=lambda x: x["created"], reverse=True):
        tag_html = "".join(f"<em>{svgkit.escape(t)}</em>" for t in item["tags"][:5])
        zip_href = f"downloads/{item['id']}.zip"
        preview_href = rel(item["preview"])
        # Per-format counters for clarity. P5: show one of each format if
        # available (SVG + PNG + MOCKUP if all three exist), up to 3
        # buttons. Otherwise fall back to first 2 files of any type.
        # This way the mockup (when present) is always discoverable.
        # Mockup detection: filename contains '-mockup' (P5 naming).
        def _fmt_of(path_str: str) -> str:
            name = Path(path_str).name
            if "-mockup" in name:
                return "MOCKUP"
            ext = Path(path_str).suffix.upper().lstrip(".")
            return ext or "FILE"
        by_ext: dict[str, list[str]] = {}
        for f in item["files"]:
            fmt = _fmt_of(f)
            by_ext.setdefault(fmt, []).append(f)
        # Priority order: SVG, PNG, MOCKUP
        preferred_order = ["SVG", "PNG", "MOCKUP"]
        displayed: list[tuple[str, str]] = []
        per_format: dict[str, int] = {}
        for ext in preferred_order:
            if ext in by_ext and by_ext[ext]:
                f = by_ext[ext][0]
                per_format[ext] = per_format.get(ext, 0) + 1
                displayed.append((f, f"{ext} {per_format[ext]}"))
        if not displayed:
            # Fallback: first 2 files (no preferred formats found)
            for f in item["files"][:2]:
                fmt = _fmt_of(f)
                per_format[fmt] = per_format.get(fmt, 0) + 1
                displayed.append((f, f"{fmt} {per_format[fmt]}"))
        extra = (
            f'<span style="font-size:.72rem;color:#6e7681">+{len(item["files"]) - 2} more in zip</span>'
            if len(item["files"]) > 2
            else ""
        )
        card_href = product_page_url(cfg, item)
        cards.append(
            '<div class="card">'
            f'<a class="thumb" href="{card_href}"><img loading="lazy" src="{preview_href}" alt="{svgkit.escape(item["title"])}"/></a>'
            '<div class="card-body">'
            f'<h2><a href="{card_href}">{svgkit.escape(item["title"])}</a></h2>'
            f'<div class="tags">{tag_html}</div>'
            f'{extra}'
            '<div class="actions">'
            f'<a class="btn btn-primary" href="{zip_href}" download>Download ZIP</a>'
            f"{file_buttons(item)}"
            "</div></div></div>"
        )
    # Price hint on each card so the catalog itself sells, not just the page.
    for i, item in enumerate(catalog):
        price_html = (
            f'<div class="card-price">{svgkit.escape(checkout_price(cfg, item))} '
            f'{svgkit.escape(cfg.get("crypto_network", "USDT (BEP20)"))}</div>'
        )
        cards[i] = cards[i].replace(
            '<div class="actions">', price_html + '<div class="actions">', 1
        )
    updated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    contact_line = contact_link(cfg)
    return (
        "<!DOCTYPE html><html lang=\"en\"><head>"
        '<meta charset="utf-8"/>'
        '<meta name="viewport" content="width=device-width, initial-scale=1"/>'
        '<meta name="google-site-verification" content="rj9PdWPw8UQNxgVDfJbn3ISodK8t-0nU51F4L6GtbpI"/>'
        f"<title>{svgkit.escape(cfg['store_name'])} - Layered SVG Cut Files</title>"
        '<meta name="description" content="Original 3D layered shadow-box mandala SVG cut files for Cricut, Silhouette and Glowforge. Buy with USDT."/>'
        '<link rel="canonical" href="' + canonical_url(cfg) + '/"/>'
        '<meta property="og:title" content="' + svgkit.escape(cfg["store_name"]) + '"/>'
        '<meta property="og:description" content="Fresh layered SVG design bundles generated daily by automation."/>'
        '<meta property="og:image" content="og.png"/>'
        '<meta name="robots" content="index,follow,max-image-preview:large"/>'
        f"<style>{CSS}</style></head><body>"
        "<header>"
        f"<h1>{svgkit.escape(cfg['store_name'])}</h1>"
        f"<p>{svgkit.escape(cfg['tagline'])}</p>"
        '<span class="badge">&#9889; 100% automated &middot; USDT checkout &middot; no account needed</span>'
        '<div class="stats">'
        f"<span>{len(catalog)} products</span>"
        f"<span>updated {newest}</span>"
        "<span>SVG vector format</span>"
        f'<span><a href="{canonical_url(cfg)}/checkout/">Checkout</a></span>'
        "</div></header><main>"
        f'<section class="info"><h3>Browse by type</h3><div class="related">'
        + "".join(
            f'<a class="rel" href="{canonical_url(cfg)}/c/{c["slug"]}/"><span>{svgkit.escape(c["title"])}</span></a>'
            for c in COLLECTIONS if collection_items(cfg, catalog, c)
        )
        + "</div></section>"
        f'<div class="grid">{"".join(cards)}</div>'
        '<section class="support"><h3>Support this machine</h3>'
        f"{money_links(cfg)}"
        "</section></main>"
        f"<footer>Auto-generated by a GitHub Actions pipeline on {updated}.<br/>"
        "All assets original and generated in-house."
        " &middot; <a href=\"./privacy.html\">Privacy Policy</a>" + contact_line + "</footer>"
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
    (SITE_DIR / "robots.txt").write_text(
        "User-agent: *\nAllow: /\n"
        "Sitemap: https://airdropia.github.io/auto-earn-engine/sitemap.xml\n",
        encoding="utf-8",
    )
    (SITE_DIR / "index.html").write_text(render_index(cfg, catalog), encoding="utf-8")
    # Crypto checkout page (zero-signup: no gateway account, no KYC)
    checkout_dir = SITE_DIR / "checkout"
    checkout_dir.mkdir(parents=True, exist_ok=True)
    (checkout_dir / "index.html").write_text(
        render_checkout(cfg, catalog), encoding="utf-8"
    )
    # SEO collection pages: one indexable page per keyword cluster
    coll_pages = 0
    for spec in COLLECTIONS:
        if not collection_items(cfg, catalog, spec):
            continue
        cdir = SITE_DIR / "c" / spec["slug"]
        cdir.mkdir(parents=True, exist_ok=True)
        (cdir / "index.html").write_text(render_collection(cfg, catalog, spec), encoding="utf-8")
        coll_pages += 1
    # Per-product landing pages (long-tail SEO: one indexable page each)
    pages = 0
    for item in catalog:
        page_dir = SITE_DIR / "p" / item["id"]
        page_dir.mkdir(parents=True, exist_ok=True)
        (page_dir / "index.html").write_text(
            render_product_page(cfg, item, catalog), encoding="utf-8"
        )
        pages += 1
    write_seo_files(SITE_DIR, cfg, catalog)
    extra = ROOT / "site_extra"
    if extra.is_dir():
        shutil.copytree(extra, SITE_DIR, dirs_exist_ok=True)
    print(f"site built: products={len(catalog)} pages={pages} zips={zipped} collections={coll_pages}")


if __name__ == "__main__":
    main()
