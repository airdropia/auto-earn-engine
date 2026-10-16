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
.howtopay { margin-top:12px; border-top:1px solid #2b3644; padding-top:10px; }
.howtopay summary { cursor:pointer; color:#58a6ff; font-size:.9rem; }
.howtopay ol { color:#9aa7b4; font-size:.88rem; margin:10px 0 4px 18px; }
.howtopay li { margin:6px 0; }
.howtopay p { color:#9aa7b4; font-size:.88rem; margin:8px 0; }
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
.muted { color:#6e7681; font-size:.72rem; text-transform:uppercase; letter-spacing:.04em; }
a.ref-link { font-family:ui-monospace,monospace; font-size:.72rem; color:#58a6ff; }
.card-price { color:#7ee787; font-size:.82rem; font-family:ui-monospace,monospace; margin:2px 0 8px; }
.info h3 { margin-top:20px; font-size:1.05rem; }
.info h3:first-of-type { margin-top:0; }
details.faq { border-bottom:1px solid #21262d; padding:10px 0; }
details.faq summary { cursor:pointer; color:#e6edf3; font-size:.92rem; font-weight:600; }
details.faq[open] summary { margin-bottom:6px; }
details.faq p { color:#9aa7b4; font-size:.9rem; margin:0; }
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

def hero_image(item: dict) -> tuple[str, bool]:
    """Best image for the product hero, and whether it is a raster.

    A phone browser will not render an inline SVG thumbnail, so an SVG hero
    means the buyer sees a blank box on the device most people actually shop
    from. A 1000px raster is used where one exists; the 6500px print render
    stays available as a download but is far too heavy to load inline.
    """
    preview = item.get("preview", "")
    folder = item.get("folder", "")
    pid = item.get("id", "")
    if folder:
        for suffix in ("-1000.png", "-6500.png"):
            candidate = f"{folder}/{pid}{suffix}"
            if (ROOT / candidate).exists():
                return candidate, True
    return preview, False


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
    # The print render is not in the catalog file list (it is generated
    # separately), but it is the format buyers without a cutting machine
    # actually want, so offer it explicitly.
    pid = item.get("id", "")
    folder = item.get("folder", "")
    if folder and not by_fmt.get("PNG"):
        render = f"{folder}/{pid}-6500.png"
        if (ROOT / render).exists():
            by_fmt["PNG"] = [render]
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

def product_faq(cfg: dict, item: dict) -> list[tuple[str, str]]:
    """Question/answer pairs for FAQPage rich results.

    These are the questions buyers actually ask before purchasing digital cut
    files. Answering them on the page earns expandable rich results in search,
    which lifts click-through without any ad spend.

    Memorial products get their own question set. A grieving buyer is not
    asking "do I need a Cricut?" first — they are asking whether the name
    can be changed, whether the design will feel cheap, and whether it can be
    finished in an evening. Answering those is what the copy has to do; the
    generic questions are answerable by every competitor, so they are not
    what makes the page rank or convert.
    """
    t = item.get("title", "")
    layers = "7"
    size = "300mm"
    if item.get("type") in ("memorial", "memorial-bundle"):
        designs = item.get("designs", 1)
        is_bundle = item.get("type") == "memorial-bundle"
        bundle_note = (
            f"This bundle contains {designs} complete memorial designs (pet paw, "
            f"angel wings, rainbow bridge), each seven layers with its own "
            f"editable name plate, so you can cut more than one keepsake from "
            f"a single purchase."
            if is_bundle else
            "This is a seven-layer design with one editable name plate, so "
            "you can cut a single keepsake sized and named exactly as needed."
        )
        return [
            (f"Can I put my pet's or a family member's name on this design?",
             f"Yes, and that is the point of it. Every design here carries an "
             f"editable name plate on its front layer with placeholder text. "
             f"Open the front layer in Cricut Design Space or Silhouette Studio, "
             f"double-click the text and type their name and the years that "
             f"bracket their life. {bundle_note}"),
            ("Is this design appropriate for a gift, or only for me?",
             f"Either. It ships as a plain digital bundle with no preset name, "
             f"so it can be cut for yourself or for someone you are losing. "
             f"Many people cut one for their own wall and a second one to give "
             f"away; the licence covers both."),
            ("How long does it take to make one?",
             f"An evening. Cut the {layers} layers in size order, roughly an "
             f"hour on a Cricut, then stack them with foam tape, about twenty "
             f"minutes. There is no wet glue, no curing time and no hardware "
             f"beyond a backing board."),
            ("Will it look handmade or cheap?",
             f"It is built from {layers} separate sheets with real voids "
             f"between them, so it throws an actual shadow and holds up when "
             f"tilted under light. That physical depth is what separates a "
             f"keepsake from a printed picture, and it is why the piece is "
             f"built as a stack rather than drawn with shading."),
            ("What if I am not able to cut it myself?",
             f"The SVGs open in Cricut Design Space, Silhouette Studio, "
             f"Inkscape, Illustrator, Affinity Designer and most laser "
             f"software, so a craft shop or a laser cutter can produce it from "
             f"the same files. Print-ready PNG renders are included for shops "
             f"that work from images."),
            ("Can I use this design commercially?",
             f"Yes. You may use it for physical products you make and sell, "
             f"for client work and for printed goods. The only restriction is "
             f"that you may not resell or redistribute the raw digital files "
             f"as-is."),
        ]
    return [
        (f"What do I get when I buy the {t}?",
         f"You get the complete {layers}-layer bundle: the combined SVG, one "
         f"separate SVG per physical layer in cut order, and print-ready PNG "
         f"renders. Every file is a vector, so it scales to any size without "
         f"losing quality."),
        ("Do I need a Cricut to use these files?",
         "No. The SVGs open in Cricut Design Space, Silhouette Studio, Inkscape, "
         "Illustrator, Affinity Designer and most laser software. If a tool only "
         "accepts raster images, the included PNG renders work there too."),
        ("How do I assemble the shadow box?",
         "Cut each layer from cardstock, roughly 250-350 gsm, then stack them in "
         "numbered order using foam tape or a small dab of glue between layers. "
         "The voids in the upper layers are what reveal the layers beneath and "
         "produce the three-dimensional effect."),
        ("Can I use this design commercially?",
         "Yes. You may use it for physical products you make and sell, for client "
         "work, and for printed goods. The only restriction is that you may not "
         "resell or redistribute the raw digital files as-is."),
        ("What material and size should I use?",
         f"Cardstock between 250 and 350 gsm works best. The artwork is drawn at "
         f"{size} so it scales to whatever size your machine can cut, from a "
         f"small card front up to a large wall piece."),
        (f"How is this different from a flat SVG?",
         f"It is genuinely layered. A flat SVG is a single plane; this is built "
         f"from {layers} separate physical sheets, so the depth is real and casts "
         f"actual shadows rather than simulating them with colour."),
    ]


def faq_jsonld(cfg: dict, item: dict) -> str:
    """schema.org FAQPage markup for the product's question/answer pairs."""
    import json as _json
    payload = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": q,
             "acceptedAnswer": {"@type": "Answer", "text": a}}
            for q, a in product_faq(cfg, item)
        ],
    }
    return _json.dumps(payload)


def faq_block(cfg: dict, item: dict) -> str:
    """Visible FAQ section. The markup earns nothing without on-page content."""
    rows = "".join(
        f'<details class="faq"><summary>{svgkit.escape(q)}</summary>'
        f'<p>{svgkit.escape(a)}</p></details>'
        for q, a in product_faq(cfg, item)
    )
    return f'<section class="info"><h3>Questions before you buy</h3>{rows}</section>'


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
    """Exact amount the buyer must send, in USDT.

    Each product carries a small unique offset in its invoice (see
    pipeline/checkout.py) so that an incoming on-chain transfer can be matched
    to the right order without a memo field. Showing the base price here would
    make every buyer send an identical amount, and payments would become
    unattributable, so this reads the issued invoice when one exists.
    """
    invoices = load_invoices()
    rec = invoices.get(item.get("id", ""))
    if rec and rec.get("unique_amount_usdt"):
        return str(rec["unique_amount_usdt"])
    override = (item.get("meta") or {}).get("price_usdt") or item.get("price_usdt") \
        or cfg.get("price_usdt", "7.00")
    return str(override)


def _stable_reference(slug: str) -> str:
    """Deterministic order reference for a product, used before a session exists.

    checkout.py issues references from its own session ids, which only exist once
    an invoice is created. The checkout page still has to give a buyer something
    to bookmark before that, so it derives a reference from the product slug.
    Both sides use the same 10-hex-character shape, and a real invoice always
    wins when one is present.
    """
    import hashlib as _h
    return _h.sha1(f"vf-ref:{slug}".encode()).hexdigest()[:10].upper()


def load_invoices() -> dict:
    """Issued checkout sessions, keyed by product slug. Empty if not generated yet.

    checkout.py stores sessions keyed by a session id, so they are re-indexed
    by slug here: that is what the catalog knows each product by.
    """
    path = ROOT / "checkout" / "sessions.json"
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    sessions = data.get("sessions") if isinstance(data, dict) else None
    if not isinstance(sessions, dict):
        return {}
    return {
        rec.get("slug", ""): rec
        for rec in sessions.values()
        if isinstance(rec, dict) and rec.get("slug")
    }


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
        '<details class="howtopay"><summary>No crypto wallet? Here is how to pay in '
        '3 minutes</summary>'
        '<ol><li>Open any crypto exchange account you already have (Binance, '
        'Coinbase, Crypto.com, Kraken, or a wallet app like Trust Wallet or '
        'MetaMask).</li>'
        '<li>Buy USDT and send it on the <strong>BEP20 / BSC</strong> network. '
        'Some apps label it "BNB Smart Chain" or "BSC" - that is the same one. '
        'Do NOT send on Ethereum (ERC20) or Tron (TRC20).</li>'
        f'<li>Send exactly the amount shown to the address on this page. The '
        f'last digits identify your order, so sending a different amount means '
        f'we cannot match it to your purchase.</li></ol>'
        '<p>Once the transfer confirms on-chain (usually under 5 minutes), this '
        'page updates itself and your download link unlocks automatically. There '
        'is nothing to claim and no account to create.</p></details>'
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
    preview, preview_is_raster = hero_image(item)
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
    # Memorial pages lead with sympathy, not with a licence badge. The buyer
    # arriving here has just lost someone; the first thing on the page should
    # acknowledge that, and the personalisation step should be the first
    # instruction they read.
    is_memorial = item.get("type") in ("memorial", "memorial-bundle")
    badge = (
        '<span class="badge">A keepsake you will keep for years</span>'
        if is_memorial else
        f'<span class="badge">{svgkit.escape(cfg.get("store_name", "VectorForge Daily"))} '
        f'&middot; layered SVG cut files &middot; commercial use allowed</span>'
    )
    if is_memorial:
        how_html = (
            '<h3>How to put their name on it</h3>'
            '<ol><li>Open the front layer file ('
            f'<code>{svgkit.escape(item["id"])}-design-1-layer-1.svg</code>) in Cricut '
            'Design Space or Silhouette Studio.</li>'
            '<li>Double-click the placeholder text in the centre and type their name '
            'and the years that bracket their life.</li>'
            '<li>Cut the layers largest to smallest, stack them with foam tape, and '
            'the keepsake is done.</li></ol>'
            '<p>That is the whole process. There is no wet glue, no curing time and no '
            'hardware beyond a backing board, so it can be finished in an evening.</p>'
            '<h3>License</h3>'
            '<p>Free for personal and commercial use. You may cut these designs into '
            'physical products, use them for client work and printed goods. Please do '
            'not resell or redistribute the raw digital files as-is.</p>'
        )
    else:
        how_html = (
            '<h3>License</h3>'
            '<p>Free for personal and commercial use. You may use these designs in physical '
            'products, client work and printed goods. Please do not resell or redistribute '
            'the raw digital files as-is.</p>'
            '<h3>How to use</h3>'
            '<p>SVG opens in Cricut Design Space, Silhouette Studio, Inkscape, Illustrator and '
            'most laser software. PNG files (where included) are 1000&times;1000 transparent '
            'rasters for Canva, Procreate and any tool that does not read SVG. All shapes are '
            'vector - scale to any size with no quality loss.</p>'
        )
    return (
        '<!DOCTYPE html><html lang="en"><head>'
        '<meta charset="utf-8"/>'
        '<meta name="viewport" content="width=device-width, initial-scale=1"/>'
        f"<title>{svgkit.escape(title)} | {svgkit.escape(cfg['store_name'])}</title>"
        f'<meta name="description" content="{svgkit.escape(desc)}"/>'
        f'<link rel="canonical" href="{product_page_url(cfg, item)}"/>'
        f'<meta property="og:title" content="{svgkit.escape(title)}"/>'
        f'<meta property="og:description" content="{svgkit.escape(desc)}"/>'
        f'<meta property="og:image" content="{base}/{svgkit.escape(rel(preview))}"/>'
        '<meta name="twitter:card" content="summary_large_image"/>'
        '<meta name="robots" content="index,follow,max-image-preview:large"/>'
        f'<script type="application/ld+json">{product_jsonld(cfg, item)}</script>'
        f'<script type="application/ld+json">{faq_jsonld(cfg, item)}</script>'
        f"<style>{CSS}</style></head><body>"
        '<header><p><a href="./../..">&larr; Back to all bundles</a></p>'
        f'<h1>{svgkit.escape(title)}</h1>'
        f'<div class="tags">{tag_html}</div>'
        + badge +
        '</header><main>'
        f'<div class="hero"><img src="{base}/{svgkit.escape(rel(preview))}" alt="{svgkit.escape(title)}"/></div>'
        '<div class="actions big">'
        f'<a class="btn btn-primary" href="{base}/downloads/{item["id"]}.zip" download>Download full bundle (ZIP)</a>'
        f"{file_buttons(item)}"
        '</div>'
        + checkout_block(cfg, item)
        + f'<section class="info">{desc_html}'
        + how_html +
        '</section>'
        + faq_block(cfg, item)
        + (f'<section class="info"><h3>More {svgkit.escape(item.get("type", ""))} bundles</h3>'
           f'<div class="related">{related_html}</div></section>' if related_html else "")
        + '<section class="support"><h3>Support this machine</h3>'
        + money_links(cfg)
        + '</section></main>'
        '<footer>Generated by the VectorForge Daily pipeline on ' + updated + '.<br/>'
        '<a href="./../..">All SVG bundles</a> &middot; '
        '<a href="../../checkout.html">Checkout</a> &middot; '
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
    invoices = load_invoices()
    rows = []
    for item in sorted(catalog, key=lambda x: x.get("created", ""), reverse=True):
        amt = checkout_price(cfg, item)
        inv = invoices.get(item.get("id", "")) or {}
        status = inv.get("status", "")
        badge = {
            "awaiting_payment": "available",
            "paid": "processing",
            "confirmed": "in stock",
        }.get(status, "available")
        # Pre-assign a reference at render time so the buyer has something to
        # bookmark even before the session file is refreshed. The reference is
        # derived the same way checkout.py derives it, from the product slug,
        # so it stays stable across builds.
        slug = item.get("id", "")
        ref = inv.get("reference") or _stable_reference(slug)
        rows.append(
            f'<tr><td>{svgkit.escape(item.get("title", "")[:60])}'
            f'<br/><span class="muted">{svgkit.escape(badge)}</span></td>'
            f'<td class="amt">{svgkit.escape(amt)} {svgkit.escape(network)}</td>'
            f'<td><a class="btn btn-ghost" href="{rel(item.get("preview", ""))}">preview</a>'
            f'<br/><a class="ref-link" href="{base}/delivery/{ref}/">order {svgkit.escape(ref)}</a></td></tr>'
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
        '<ol><li>Find your bundle below and <strong>note the exact amount shown</strong> '
        '- each one is unique so your payment can be matched to your order.</li>'
        f'<li>Send exactly that amount of {svgkit.escape(network)} to the address shown.</li>'
        '<li>Wait a few minutes. The payment is detected automatically on-chain, then '
        'your download link appears on your order page. Nothing to sign up for, no '
        'account, no login.</li></ol>'
        f'<p class="payaddr">Send only <strong>{svgkit.escape(network)}</strong> on the '
        'BEP20 network (BSC). Other assets sent here are unrecoverable.</p>'
        f'<p><code id="pay-address">{svgkit.escape(address)}</code>'
        '<button class="copy-btn" type="button" '
        'onclick="navigator.clipboard.writeText(document.getElementById(\'pay-address\').textContent)">Copy</button></p>'
        '<p class="warn">Send the exact amount. If you send less, the order cannot be '
        'matched automatically and you will need to contact support with your '
        'transaction hash.</p>'
        '<p class="muted">Already sent? Open your order page from the table below to '
        'track the confirmation and get your download link.</p>'
        '<details class="howtopay"><summary>No crypto wallet? Here is how to pay in '
        '3 minutes</summary>'
        '<ol><li>Open any crypto exchange account you already have (Binance, '
        'Coinbase, Crypto.com, Kraken, or a wallet app like Trust Wallet or '
        'MetaMask).</li>'
        '<li>Buy USDT and send it on the <strong>BEP20 / BSC</strong> network. '
        'Some apps label it "BNB Smart Chain" or "BSC" - that is the same one. '
        'Do NOT send on Ethereum (ERC20) or Tron (TRC20).</li>'
        '<li>Send exactly the amount in the table for your bundle. Those last '
        'digits identify your order; a different amount cannot be matched '
        'automatically.</li></ol>'
        '<p>Once the transfer confirms on-chain (usually under 5 minutes) your '
        'order page flips to paid and the download unlocks by itself. There is '
        'nothing to claim and no account to create.</p></details>'
        '</section>'
        '<section class="info"><h3>Available bundles</h3>'
        '<table class="price-table"><thead><tr><th>Bundle</th><th>Exact amount to send</th><th></th></tr></thead>'
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
        "slug": "golden-retriever-memorial-svg",
        "title": "Golden Retriever Memorial SVG",
        "h1": "Golden Retriever Memorial Shadow Box SVGs",
        "intro": (
            "A layered shadow box for a golden retriever who is gone. Seven soft "
            "layers with an editable name plate on the front layer: type your "
            "golden's name and dates, cut the sheets, and stack them into a "
            "keepsake that belongs on a wall rather than in a drawer."
        ),
        "match": ["golden retriever", "golden", "retriever"],
        "pinned": ["memorial-pet", "memorial-bundle"],
        "guide": [
            ("Why golden retrievers need their own keepsake", (
                "A golden retriever is a dog people describe with a specific "
                "word: gentle. The keepsake you cut for one should carry that, "
                "which is why the front layer is left blank for their name and "
                "years rather than printed with a generic caption."
            )),
            ("How to personalise the front layer", (
                "Open the layer-1 file in Cricut Design Space or Silhouette "
                "Studio, double-click the placeholder text and type the name and "
                "the years. Nothing else on the sheet changes, so the keepsake "
                "is personalised without any extra cutting."
            )),
        ],
    },
    {
        "slug": "labrador-memorial-svg",
        "title": "Labrador Memorial SVG",
        "h1": "Labrador Memorial Shadow Box SVGs",
        "intro": (
            "Seven-layer memorial shadow boxes for a labrador, with an editable "
            "name plate on the front layer so their name and dates go on the "
            "piece before the first cut. Midnight, pearl and antique gold, built "
            "for real physical depth."
        ),
        "match": ["labrador", "lab", "retriever"],
        "pinned": ["memorial-pet", "memorial-bundle"],
        "guide": [
            ("Cutting for a labrador", (
                "Labs are big dogs, so most makers cut a 12x12 inch box. The "
                "artwork is vector and scales without loss, so the same file "
                "gives a keepsake that fits a mantelpiece or a wall."
            )),
            ("Why the name plate matters most here", (
                "A lab is usually named once and called that for fifteen years. "
                "Putting that name on the front layer is the whole difference "
                "between a decoration and a memorial."
            )),
        ],
    },
    {
        "slug": "cat-memorial-svg",
        "title": "Cat Memorial SVG",
        "h1": "Cat Memorial Shadow Box SVGs",
        "intro": (
            "Memorial shadow boxes for a cat: seven layers, an editable name "
            "plate on the front, and a paw or rainbow bridge motif at the heart. "
            "Designed to be finished in an evening, and to still mean something "
            "in twenty years."
        ),
        "match": ["cat", "kitten", "feline", "pet memorial"],
        "pinned": ["memorial-pet", "memorial-rainbow", "memorial-bundle"],
        "guide": [
            ("Cats and the keepsake habit", (
                "Cat owners keep things for a long time: a collar, a card, a "
                "photograph. A layered shadow box gives that habit a form worth "
                "hanging rather than a drawer."
            )),
            ("Assembly without wet glue", (
                "Foam tape sets an even gap between layers, which is what keeps "
                "a seven-layer box sitting flat on a shelf. Glue sinks the "
                "layers and the depth disappears."
            )),
        ],
    },
    {
        "slug": "dog-memorial-svg",
        "title": "Dog Memorial SVG",
        "h1": "Dog Memorial Shadow Box SVGs",
        "intro": (
            "Seven-layer memorial shadow boxes for a dog, with an editable name "
            "plate on the front layer and a paw print motif at the centre. "
            "Personalise the name and dates in Cricut Design Space before you "
            "cut, then stack the layers for real depth."
        ),
        "match": ["dog", "puppy", "dog memorial", "pet memorial"],
        "pinned": ["memorial-pet", "memorial-bundle"],
        "guide": [
            ("One file, any breed", (
                "The paw motif is breed-neutral on purpose: it is what people "
                "recognise instantly in a photograph of someone's dog, whatever "
                "shape the dog was."
            )),
            ("What arrives in the download", (
                "Seven separate layer SVGs in cut order, the combined design, and "
                "a 6500px print-ready PNG render for shops that cut from images."
            )),
        ],
    },
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
        "guide": [
            ("What a shadow box SVG actually is", (
                "A shadow box design is not a single image with shading. It is a set "
                "of separate cut sheets, stacked in order so that the gaps in each "
                "upper layer reveal the layer beneath. The shadows are cast by real "
                "physical distance between the sheets, which is why the effect holds "
                "up from any angle and under any lighting, unlike printed or "
                "flat-shaded artwork."
            )),
            ("What you need to make one", (
                "Cardstock in the 250-350 gsm range, a craft knife or machine blade, "
                "foam tape or craft glue, and roughly an hour per piece. Nothing else. "
                "The SVG files already contain the cut paths, so there is no tracing, "
                "no cleanup in the software and no test cut needed beyond confirming "
                "your blade offset."
            )),
            ("How to choose the right cardstock weight", (
                "Heavier cardstock gives cleaner cut edges and holds its shape when "
                "stacked, but it also needs a sharper blade and more pressure. Below "
                "250 gsm the layers bow and the depth flattens out. Between 250 and "
                "350 gsm is the range where most layered designs look their best, and "
                "it is what the designs here were proportioned for."
            )),
            ("Sizing and scaling", (
                "The artwork is drawn at 300mm and scales without loss because every "
                "shape is a vector path. If your machine cannot cut that width, scale "
                "it down proportionally before importing. Avoid scaling up beyond "
                "roughly twice the original size, because very fine interior details "
                "in the smallest layer can close up and tear out."
            )),
        ],
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
        "guide": [
            ("Importing into Cricut Design Space", (
                "Upload the SVG directly rather than converting it to an image. Design "
                "Space accepts SVG upload, and keeping it as vector means the cut paths "
                "stay exact. After uploading, confirm the size reads correctly at the "
                "top of the canvas, then ungroup only if you need to move individual "
                "layers independently."
            )),
            ("Why one file per layer matters", (
                "Each layer ships as its own SVG so you can cut it on its own sheet. "
                "If everything arrived as one flattened file you would have to "
                "manually separate the tones by colour, which is slow and error-prone. "
                "Cut in ascending layer order and keep the pieces labelled as you go."
            )),
            ("Adhesive and alignment", (
                "A thin dab of craft glue or a strip of foam tape on the back of each "
                "layer is enough. Too much adhesive causes the layers to sink into each "
                "other and the depth disappears. Align from the centre outwards rather "
                "than corner to corner, so small errors average out instead of "
                "accumulating across the sheet."
            )),
        ],
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
        "guide": [
            ("What is in the bundle", (
                "One combined SVG showing the finished design, one separate SVG per "
                "physical layer, and print-ready PNG renders. The combined file is for "
                "preview and for laser software that wants a single job; the per-layer "
                "files are what you actually cut from cardstock."
            )),
            ("Which software reads these files", (
                "Cricut Design Space, Silhouette Studio, Inkscape, Illustrator, "
                "Affinity Designer, LightBurn and most laser control software all read "
                "SVG natively. Nothing needs converting. If a tool only accepts PNG or "
                "JPG, use the included renders instead, accepting that they are not "
                "cuttable in the same way."
            )),
            ("File conventions", (
                "Layers are named in ascending order so the cut sequence matches the "
                "stacking sequence. Files are named with the product slug, which keeps "
                "them identifiable after downloading and re-importing into a different "
                "library."
            )),
        ],
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
        "guide": [
            ("Preparing for Silhouette Studio", (
                "Import each layer SVG separately and confirm the registration "
                "settings match your blade offset. Silhouette reads SVG directly, so "
                "there is no trace step. Cut with the mat still attached and standard "
                "settings for cardstock, then adjust cut pressure only if a layer "
                "takes more than two passes."
            )),
            ("Silhouette-specific tips", (
                "Silhouette's default blade offset differs between models, so run a "
                "small test cut on the cheapest layer first. Keep the material "
                "consistency high across all sheets, because varying thickness across "
                "layers is what makes the finished shadow box sit unevenly."
            )),
        ],
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
        "guide": [
            ("How these mandalas are constructed", (
                "The geometry is computed rather than traced or stock, so the radial "
                "symmetry is exact at every ring. Motifs repeat around the "
                "circumference with a controlled phase offset between layers, which is "
                "what keeps the negative space legible once the layers are stacked."
            )),
            ("Why the voids matter", (
                "A mandala made only of line work reads flat when cut. The design works "
                "because each upper layer removes more area than the one below it, so "
                "each successive layer reveals a different portion of the pattern. The "
                "voids are the design, not gaps in it."
            )),
        ],
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
        "guide": [
            ("Real depth versus simulated depth", (
                "Printable 3D art fakes depth with gradients and drop shadows, so it "
                "still looks flat from the side and disappears at a viewing angle. A "
                "layered template is built from separate sheets at real distances, so "
                "the parallax is genuine and holds up when held, tilted or hung."
            )),
            ("Depth planning when assembling", (
                "Even spacing between layers reads as deliberate; uneven spacing reads "
                "as an accident. Decide your gap before you start gluing, and use the "
                "same gap throughout. Foam tape is more forgiving than glue because it "
                "sets the spacing consistently."
            )),
        ],
    },
    {
        "slug": "pet-memorial-shadow-box",
        "title": "Pet Memorial Shadow Box",
        "h1": "Pet Memorial Shadow Box SVGs",
        "intro": (
            "A keepsake for the one who is waiting at the rainbow bridge. Seven soft "
            "layers of midnight blue, pearl and antique gold, with a paw print or a "
            "rainbow arc at the heart and an editable name plate on the front layer: "
            "type your dog's or cat's name and dates before you cut, and the design "
            "becomes yours. Built to be held, not just framed."
        ),
        "match": [
            "pet memorial", "dog memorial", "cat memorial", "rainbow bridge",
            "pet loss", "in loving memory", "sympathy", "memorial",
        ],
        "guide": [
            ("How to use the editable name plate", (
                "Open the front layer file in Cricut Design Space or Silhouette Studio, "
                "double-click the placeholder text and type your pet's name and the "
                "years that bracket their life. Everything else on the sheet cuts "
                "exactly as drawn, so the personalisation costs you about two minutes "
                "and no extra material."
            )),
            ("Why a keepsake box rather than a print", (
                "A framed print of a pet is a picture of a memory. A layered shadow box "
                "has physical depth and casts a real shadow on the wall, which reads as "
                "an object rather than a picture - the difference matters when you are "
                "keeping something for twenty years."
            )),
            ("Materials and sizing", (
                "Cut each layer from cardstock in ascending size order and stack them "
                "with foam tape rather than glue; foam sets a consistent gap, so the "
                "depth stays even. A 12x12 inch box is the most common shelf size, and "
                "every design scales without loss because the artwork is vector."
            )),
        ],
    },
    {
        "slug": "in-loving-memory-svg",
        "title": "In Loving Memory SVG",
        "h1": "In Loving Memory SVG Designs",
        "intro": (
            "Memorial shadow boxes with angel wings, a halo and a quiet gold medallion, "
            "made for the people you will never stop missing. Seven layers, soft ivory "
            "and midnight palette, and an editable name plate on the front so their "
            "name and dates belong on the piece before the first cut. Sympathy gifts "
            "that arrive already personal."
        ),
        "match": [
            "in loving memory", "angel wings", "memorial", "sympathy",
            "bereavement", "remembrance", "rainbow bridge",
        ],
        "guide": [
            ("Making a sympathy gift that is not generic", (
                "The most common sympathy gift fails because it could have been given "
                "to anyone. Personalising the name plate is what makes this one "
                "impossible to confuse with a basket of flowers - the name is on the "
                "artwork itself, not on a card tucked in beside it."
            )),
            ("What the front layer carries", (
                "The front layer is the ivory medallion with the editable name and "
                "dates, ringed in gold. It is deliberately the highest-contrast layer "
                "in the stack, so the name stays readable from across a room once the "
                "box is assembled and hung."
            )),
            ("Timing", (
                "Memorial designs are searched for in the first weeks after a loss and "
                "again around anniversaries and birthdays of the year. Cutting one "
                "ahead of time means the keepsake exists before the family has found "
                "the words for what they lost."
            )),
        ],
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
    """An indexable landing page for one keyword cluster.

    A collection may be pinned: `pinned` names product slugs that always
    appear regardless of keyword matching. Breed collections use this,
    because "golden retriever memorial svg" should surface the pet design
    even though no listing is literally tagged with a breed.
    """
    base = canonical_url(cfg)
    items = collection_items(cfg, catalog, spec)
    pinned_ids = spec.get("pinned", [])
    if pinned_ids:
        # Slugs are date-derived (memorial-pet-1ca7d789), so match on the
        # stable prefix rather than the full id.
        pinned = [
            i for i in catalog
            if any(str(i.get("id", "")).startswith(str(p)) for p in pinned_ids)
        ]
        have = {i.get("id") for i in items}
        items = pinned + [i for i in items if i.get("id") not in have]
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
    guide_html = ""
    guide_sections = spec.get("guide") or []
    if guide_sections:
        blocks = "".join(
            f"<h3>{svgkit.escape(h)}</h3><p>{svgkit.escape(body)}</p>"
            for h, body in guide_sections
        )
        guide_html = f'<section class="info"><h3>Buying guide</h3>{blocks}</section>'
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
        + guide_html
        + f'<div class="grid">{"".join(cards)}</div>'
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
    # Memorial designs lead the grid. They are the differentiated product and
    # the ones whose buyer arrives already emotional, so burying them below a
    # wall of interchangeable mandalas hides the only thing worth arriving for.
    # The collection bundle leads even them: it is the product a buyer should
    # be aimed at, since a single design loses on price against the market.
    by_date = sorted(catalog, key=lambda x: x["created"], reverse=True)
    lead = ("memorial-bundle", "memorial")
    ordered = (
        [i for i in by_date if i.get("type") == "memorial-bundle"]
        + [i for i in by_date if i.get("type") == "memorial"]
        + [i for i in by_date if i.get("type") not in lead]
    )
    for item in ordered:
        tag_html = "".join(f"<em>{svgkit.escape(t)}</em>" for t in item["tags"][:5])
        zip_href = f"downloads/{item['id']}.zip"
        preview_href = rel(hero_image(item)[0])
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
