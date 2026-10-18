#!/usr/bin/env python3
"""Free in-browser memorial shadow box maker.

The storefront sells cut files, but the buyer's real question is never "is
this SVG valid" — it is "will this look like the one I lost". A preview they
can put their own pet's name on answers that in ten seconds, and it is the
only free thing on the site that carries the buyer's own words into a page
worth indexing and sharing.

It is deliberately a *preview*, not the product: one flattened SVG. The paid
bundle is the seven separate layer files plus the 6500px print render, and
this page says so plainly instead of hiding it.

Everything runs client-side. No account, no server, no key, no upload of the
buyer's grief anywhere.
"""
from __future__ import annotations

import json

# Motifs and palettes mirror pipeline/memorial_generator.py so the free
# preview and the paid cut files are visibly the same product family.
MOTIFS = [
    ("paw", "Paw print", "pet"),
    ("angel", "Angel wings", "someone you lost"),
    ("rainbow", "Rainbow bridge", "a pet"),
    ("heart", "Heart", "a pet"),
    ("leaf", "Leaf", "a pet"),
    ("wave", "Waves", "a pet"),
    ("candle", "Candle in memory", "someone you lost"),
    ("star", "Star", "a person"),
    ("cross", "Cross", "a person"),
]

PALETTES = {
    "midnight": ["#1b2a4a", "#4a6fa5", "#9db4d0", "#f2ede3", "#c9a227"],
    "pearl": ["#1b2a4a", "#4a6fa5", "#b9c9de", "#f7f4ec", "#c9a227"],
    "twilight": ["#1b2a4a", "#5a7fae", "#a8c0dc", "#f7f4ec", "#c9a227"],
    "plum": ["#2a1b3d", "#5a2d82", "#8e44ad", "#f4e1d2", "#c9a227"],
    "forest": ["#1b3a2a", "#2d5a3d", "#5a8a5d", "#f4efe1", "#c9a227"],
    "ocean": ["#0a2a3a", "#1d4a5d", "#3d6a7d", "#e8f4f8", "#c9a227"],
    "violet": ["#3d2b1f", "#6a4c93", "#9b59b6", "#f4e9e2", "#c9a227"],
    "dusk": ["#1a2a3a", "#3d5a7d", "#5a7da0", "#e8f0f8", "#c9a227"],
    "charcoal": ["#2a2a3a", "#4a4a5d", "#6a6a8d", "#f4f4f8", "#c9a227"],
}


def maker_page_html(store_name: str, tagline: str, checkout_url: str,
                    bundle_href: str, maker_url: str) -> str:
    """Render the maker page. Kept as one self-contained file on purpose."""
    data = json.dumps({"motifs": MOTIFS, "palettes": PALETTES})
    schema = json.dumps({
        "@context": "https://schema.org",
        "@type": "WebApplication",
        "name": "Free memorial shadow box maker",
        "applicationCategory": "DesignApplication",
        "operatingSystem": "Any (runs in the browser)",
        "url": maker_url,
        "description": (
            "Type a name and dates to see a memorial shadow box instantly. "
            "Free, no signup, nothing installed."
        ),
        "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"},
    })
    return MAKER_TEMPLATE.replace("__STORE__", store_name) \
        .replace("__TAGLINE__", tagline) \
        .replace("__SCHEMA__", schema) \
        .replace("__MAKER__", maker_url) \
        .replace("__CHECKOUT__", checkout_url) \
        .replace("__BUNDLE__", bundle_href) \
        .replace("__DATA__", data)


MAKER_TEMPLATE = r"""<!DOCTYPE html><html lang="en"><head>
<meta charset="utf-8"/><meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Free memorial shadow box maker | Type their name, see it instantly | __STORE__</title>
<meta name="description" content="Free memorial shadow box maker. Type your pet's or someone's name and dates, choose a motif, and see the shadow box instantly. No signup. Download a free preview SVG or get the full 7-layer cut file bundle."/>
<link rel="canonical" href="__MAKER__"/>
<meta property="og:url" content="__MAKER__"/>
<meta name="robots" content="index,follow,max-image-preview:large"/>
<meta property="og:title" content="Free memorial shadow box maker"/>
<meta property="og:description" content="Type their name, see the keepsake instantly. No signup, no account."/>
<meta property="og:image" content="__CHECKOUT__"/>
<meta name="twitter:card" content="summary_large_image"/>
<script type="application/ld+json">__SCHEMA__</script>
<style>
:root{color-scheme:dark}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Segoe UI',system-ui,sans-serif;background:#0d1117;color:#e6edf3;line-height:1.5}
a{color:#9db4d0}
header{padding:40px 20px 24px;text-align:center;background:linear-gradient(180deg,#101826,#0d1117)}
header h1{font-size:1.9rem;letter-spacing:-.02em}
header p{color:#9db4d0;margin-top:8px;max-width:640px;margin-left:auto;margin-right:auto}
main{max-width:1080px;margin:0 auto;padding:24px 16px 48px;display:grid;grid-template-columns:340px 1fr;gap:24px}
@media(max-width:820px){main{grid-template-columns:1fr}}
.panel{background:#111823;border:1px solid #1f2a3a;border-radius:12px;padding:18px}
label{display:block;font-size:.78rem;text-transform:uppercase;letter-spacing:.06em;color:#8b949e;margin:14px 0 6px}
input,select{width:100%;padding:10px 12px;border-radius:8px;border:1px solid #26313f;background:#0d131c;color:#e6edf3;font-size:.95rem;font-family:inherit}
input:focus,select:focus{outline:2px solid #4a6fa5}
.row{display:flex;gap:10px}
.btn{display:inline-block;margin-top:14px;padding:12px 16px;border-radius:8px;border:1px solid #26313f;background:#16202c;color:#e6edf3;font-size:.9rem;font-weight:600;cursor:pointer;text-decoration:none;text-align:center}
.btn-primary{background:#4a6fa5;border-color:#4a6fa5;color:#fff;width:100%}
.btn-buy{background:#c9a227;border-color:#c9a227;color:#1b1b1b}
canvas,.preview{width:100%;background:#f7f4ec;border-radius:12px;display:block;aspect-ratio:1/1}
.note{font-size:.8rem;color:#8b949e;margin-top:12px}
h2{font-size:1.05rem;margin:26px 0 10px}
ul{padding-left:20px;color:#9db4d0;font-size:.92rem}
li{margin:6px 0}
.tag{display:inline-block;background:#16202c;border:1px solid #26313f;border-radius:999px;padding:4px 10px;font-size:.72rem;margin:3px 4px 0 0;color:#9db4d0}
footer{padding:24px 16px 48px;text-align:center;color:#6e7681;font-size:.82rem}
#stage{display:flex;flex-direction:column;gap:14px}
#fallback{display:none;background:#111823;border:1px solid #1f2a3a;border-radius:12px;padding:18px;font-size:.9rem}
</style></head><body>
<header>
<h1>Free memorial shadow box maker</h1>
<p>Type their name. See the keepsake. Nothing to install, no account, and your words never leave this page.</p>
<div id="tags"></div>
</header>
<main>
<section class="panel">
<label for="name">Their name</label>
<input id="name" maxlength="28" placeholder="e.g. Bella" value="Bella"/>
<label for="dates">Dates (optional)</label>
<input id="dates" maxlength="34" placeholder="e.g. 12.03.2019 - 04.11.2026" value="2019 - 2026"/>
<label for="line">Line under the name</label>
<input id="line" maxlength="40" placeholder="e.g. Forever in our hearts" value="Forever in our hearts"/>
<label for="motif">Motif</label>
<select id="motif"></select>
<label for="palette">Colours</label>
<select id="palette"></select>
<button class="btn btn-primary" id="download" type="button">Download free preview SVG</button>
<button class="btn" id="share" type="button">Share this design</button>
<p class="note">Free preview: one flattened SVG file for printing or sharing. It is not a cut file &mdash; there are no separated layers.</p>
<a class="btn btn-buy" id="buy" href="__CHECKOUT__">Get the full 7-layer cut file bundle</a>
<p class="note">The bundle is the real product: 7 separate layer files sized for Cricut, Silhouette and Glowforge, plus a 6500px print-ready PNG. __BUNDLE__</p>
</section>
<section id="stage">
<div class="preview"><svg id="art" viewBox="0 0 1200 1200" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Memorial shadow box preview"></svg></div>
<div id="fallback">Your browser blocked the inline preview. The download button still works.</div>
<div class="panel">
<h2>Why this page exists</h2>
<p class="note">A shadow box is not bought from a file listing, it is bought from a picture of the person you lost. Type the name first, decide second.</p>
<h2>What the paid bundle adds</h2>
<ul>
<li>Seven separate SVG layers, each one a physical sheet of cardstock</li>
<li>Editable name plate on the front layer</li>
<li>6500px print-ready PNG render</li>
<li>Materials list: cardstock weights, foam tape thickness, frame depth</li>
<li>Personal and commercial licence, no account needed to buy</li>
</ul>
<h2>Cutting it yourself is the hard part</h2>
<p class="note">If you would rather not cut anything, tell us and we will point you at someone who can.</p>
</div>
</section>
</main>
<footer>
Built by __STORE__ &middot; <a href="__CHECKOUT__">All designs</a> &middot; <a href="__CHECKOUT__">Checkout</a>
</footer>
<script>
const DATA = __DATA__;
const MK_URL = "__MAKER__";
const S = 1200, C = 600;
const esc = (s) => (s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
const f = (n) => Math.round(n * 10) / 10;

function poly(cx, cy, r, fill, points) {
  const pts = [];
  for (let i = 0; i < points * 2; i++) {
    const rr = (i % 2 === 0) ? r : r * 0.42;
    const a = -Math.PI / 2 + i * Math.PI / points;
    pts.push(f(cx + rr * Math.cos(a)) + ',' + f(cy + rr * Math.sin(a)));
  }
  return '<polygon points="' + pts.join(' ') + '" fill="' + fill + '"/>';
}

function heart(cx, cy, r, fill) {
  return '<path d="M ' + f(cx) + ' ' + f(cy + 0.75 * r)
    + ' C ' + f(cx - 1.3 * r) + ' ' + f(cy - 0.1 * r) + ' ' + f(cx - 0.72 * r) + ' ' + f(cy - 1.05 * r) + ' ' + f(cx) + ' ' + f(cy - 0.35 * r)
    + ' C ' + f(cx + 0.72 * r) + ' ' + f(cy - 1.05 * r) + ' ' + f(cx + 1.3 * r) + ' ' + f(cy - 0.1 * r) + ' ' + f(cx) + ' ' + f(cy + 0.75 * r)
    + ' Z" fill="' + fill + '"/>';
}

function motif(kind, cx, cy, r, fill) {
  if (kind === 'paw') {
    let s = '<ellipse cx="' + f(cx) + '" cy="' + f(cy + 0.45 * r) + '" rx="' + f(0.62 * r) + '" ry="' + f(0.5 * r) + '" fill="' + fill + '"/>';
    for (let i = 0; i < 4; i++) {
      const a = -Math.PI / 2 + (i - 1.5) * 0.55;
      s += '<ellipse cx="' + f(cx + 0.78 * r * Math.cos(a)) + '" cy="' + f(cy + 0.78 * r * Math.sin(a))
        + '" rx="' + f(0.26 * r) + '" ry="' + f(0.33 * r) + '" fill="' + fill + '" transform="rotate(' + f((i - 1.5) * 26) + ' ' + f(cx + 0.78 * r * Math.cos(a)) + ' ' + f(cy + 0.78 * r * Math.sin(a)) + ')"/>';
    }
    return s;
  }
  if (kind === 'heart') return heart(cx, cy, r, fill);
  if (kind === 'star') return poly(cx, cy, r, fill, 5);
  if (kind === 'cross') {
    return '<path d="M ' + f(cx - 0.22 * r) + ' ' + f(cy - r) + ' H ' + f(cx + 0.22 * r) + ' V ' + f(cy - 0.3 * r)
      + ' H ' + f(cx + 0.9 * r) + ' V ' + f(cy + 0.12 * r) + ' H ' + f(cx + 0.22 * r) + ' V ' + f(cy + r)
      + ' H ' + f(cx - 0.22 * r) + ' V ' + f(cy + 0.12 * r) + ' H ' + f(cx - 0.9 * r) + ' V ' + f(cy - 0.3 * r)
      + ' H ' + f(cx - 0.22 * r) + ' Z" fill="' + fill + '"/>';
  }
  if (kind === 'angel') {
    let s = '';
    for (const dir of [-1, 1]) {
      s += '<path d="M ' + f(cx) + ' ' + f(cy + 0.1 * r)
        + ' C ' + f(cx + dir * 0.5 * r) + ' ' + f(cy - 0.55 * r) + ' ' + f(cx + dir * 1.05 * r) + ' ' + f(cy - 0.95 * r) + ' ' + f(cx + dir * 1.15 * r) + ' ' + f(cy - 0.2 * r)
        + ' C ' + f(cx + dir * 1.0 * r) + ' ' + f(cy + 0.1 * r) + ' ' + f(cx + dir * 0.75 * r) + ' ' + f(cy + 0.05 * r) + ' ' + f(cx + dir * 0.62 * r) + ' ' + f(cy + 0.42 * r)
        + ' C ' + f(cx + dir * 0.5 * r) + ' ' + f(cy + 0.62 * r) + ' ' + f(cx + dir * 0.3 * r) + ' ' + f(cy + 0.35 * r) + ' ' + f(cx) + ' ' + f(cy + 0.1 * r)
        + ' Z" fill="' + fill + '"/>';
    }
    return s + '<ellipse cx="' + f(cx) + '" cy="' + f(cy - 0.75 * r) + '" rx="' + f(0.3 * r) + '" ry="' + f(0.34 * r) + '" fill="none" stroke="' + fill + '" stroke-width="' + f(0.09 * r) + '"/>';
  }
  if (kind === 'rainbow') {
    let s = '';
    const cols = ['#d9534f', '#e8a33d', '#e8d44d', '#5aa469', '#4a7fa5'];
    for (let i = 0; i < cols.length; i++) {
      const rr = r * (1 - i * 0.17);
      s += '<path d="M ' + f(cx - rr) + ' ' + f(cy + 0.5 * r) + ' A ' + f(rr) + ' ' + f(rr) + ' 0 0 1 ' + f(cx + rr) + ' ' + f(cy + 0.5 * r)
        + '" fill="none" stroke="' + cols[i] + '" stroke-width="' + f(0.16 * r) + '" stroke-linecap="round"/>';
    }
    return s;
  }
  if (kind === 'leaf') {
    return '<path d="M ' + f(cx) + ' ' + f(cy - r) + ' C ' + f(cx + 0.95 * r) + ' ' + f(cy - 0.35 * r) + ' ' + f(cx + 0.6 * r) + ' ' + f(cy + 0.8 * r) + ' ' + f(cx) + ' ' + f(cy + r)
      + ' C ' + f(cx - 0.6 * r) + ' ' + f(cy + 0.8 * r) + ' ' + f(cx - 0.95 * r) + ' ' + f(cy - 0.35 * r) + ' ' + f(cx) + ' ' + f(cy - r) + ' Z" fill="' + fill + '"/>'
      + '<path d="M ' + f(cx) + ' ' + f(cy - 0.95 * r) + ' L ' + f(cx) + ' ' + f(cy + 0.95 * r) + '" stroke="#00000033" stroke-width="' + f(0.05 * r) + '"/>';
  }
  if (kind === 'wave') {
    let s = '';
    for (let i = 0; i < 3; i++) {
      const y = cy - 0.45 * r + i * 0.45 * r;
      s += '<path d="M ' + f(cx - r) + ' ' + f(y) + ' q ' + f(r * 0.5) + ' ' + f(-0.45 * r) + ' ' + f(r) + ' 0 q ' + f(r * 0.5) + ' ' + f(0.45 * r) + ' ' + f(r) + ' 0" fill="none" stroke="' + fill + '" stroke-width="' + f(0.14 * r) + '" stroke-linecap="round"/>';
    }
    return s;
  }
  if (kind === 'candle') {
    return '<rect x="' + f(cx - 0.28 * r) + '" y="' + f(cy - 0.05 * r) + '" width="' + f(0.56 * r) + '" height="' + f(1.0 * r) + '" rx="' + f(0.08 * r) + '" fill="' + fill + '"/>'
      + '<ellipse cx="' + f(cx) + '" cy="' + f(cy - 0.3 * r) + '" rx="' + f(0.17 * r) + '" ry="' + f(0.26 * r) + '" fill="' + fill + '"/>';
  }
  return poly(cx, cy, r, fill, 5);
}

function ringIcon(kind, cx, cy, r, fill) {
  if (kind === 'leaf' || kind === 'wave') return motif(kind, cx, cy, r, fill);
  if (kind === 'paw') return heart(cx, cy, r * 0.8, fill);
  return poly(cx, cy, r, fill, 5);
}

function buildSvg() {
  const pal = DATA.palettes[document.getElementById('palette').value];
  const kind = document.getElementById('motif').value;
  const name = document.getElementById('name').value.trim() || 'Their Name';
  const dates = document.getElementById('dates').value.trim();
  const line = document.getElementById('line').value.trim();
  const [dark, mid, light, cream, gold] = pal;

  let s = '<defs>'
    + '<filter id="sh" x="-20%" y="-20%" width="140%" height="140%">'
    + '<feDropShadow dx="0" dy="10" stdDeviation="14" flood-color="#00000055"/></filter></defs>';
  s += '<rect width="' + S + '" height="' + S + '" fill="' + cream + '"/>';
  s += '<rect x="60" y="60" width="' + (S - 120) + '" height="' + (S - 120) + '" rx="26" fill="' + dark + '" filter="url(#sh)"/>';
  s += '<rect x="96" y="96" width="' + (S - 192) + '" height="' + (S - 192) + '" rx="18" fill="none" stroke="' + mid + '" stroke-width="6"/>';
  s += '<rect x="124" y="124" width="' + (S - 248) + '" height="' + (S - 248) + '" rx="14" fill="' + light + '" opacity="0.13"/>';
  s += '<rect x="150" y="150" width="' + (S - 300) + '" height="' + (S - 300) + '" rx="12" fill="none" stroke="' + gold + '" stroke-width="3" opacity="0.85"/>';

  for (let i = 0; i < 8; i++) {
    const a = -Math.PI / 2 + i * Math.PI / 4;
    s += ringIcon(kind, C + 300 * Math.cos(a), C + 300 * Math.sin(a), 40, gold);
  }
  s += motif(kind, C, C - 78, 168, mid);

  s += '<rect x="270" y="760" width="660" height="250" rx="14" fill="' + cream + '" opacity="0.96"/>';
  s += '<rect x="286" y="776" width="628" height="218" rx="10" fill="none" stroke="' + gold + '" stroke-width="3"/>';
  const size = name.length > 16 ? 62 : (name.length > 10 ? 76 : 92);
  s += '<text x="' + C + '" y="858" text-anchor="middle" font-family="Georgia,serif" font-size="' + size
    + '" fill="' + dark + '" letter-spacing="3">' + esc(name) + '</text>';
  if (dates) {
    s += '<text x="' + C + '" y="918" text-anchor="middle" font-family="Georgia,serif" font-size="40" fill="' + mid + '" letter-spacing="5">'
      + esc(dates) + '</text>';
  }
  if (line) {
    s += '<text x="' + C + '" y="964" text-anchor="middle" font-family="Georgia,serif" font-size="30" fill="' + gold
      + '" letter-spacing="7" font-style="italic">' + esc(line) + '</text>';
  }
  return '<?xml version="1.0" encoding="UTF-8"?>\n'
    // Honest attribution, invisible in the artwork: this is a free tool and
    // the file says where it came from. Every copy that gets shared in a
    // group chat carries the maker's URL with it, which is distribution we
    // do not have to pay for.
    + '<!-- Free preview made with the memorial shadow box maker at '
    + esc(MK_URL) + ' - full 7-layer cut file bundle: ' + esc(MK_URL) + ' -->\n'
    + '<metadata>' + esc('Made with the free memorial shadow box maker at ' + MK_URL) + '</metadata>\n'
    + '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ' + S + ' ' + S + '" width="' + S + '" height="' + S + '">\n' + s + '\n</svg>\n';
}

function render() {
  const art = document.getElementById('art');
  try {
    art.innerHTML = buildSvg().replace(/^<\?xml[^>]*\?>\n/, '')
      .replace(/<!--[\s\S]*?-->/g, '')
      .replace(/<metadata>[\s\S]*?<\/metadata>/g, '')
      .replace(/<\/?svg[^>]*>/g, '');
    document.getElementById('fallback').style.display = 'none';
  } catch (e) {
    document.getElementById('fallback').style.display = 'block';
  }
}

function init() {
  const ms = document.getElementById('motif');
  DATA.motifs.forEach((m) => {
    const o = document.createElement('option');
    o.value = m[0]; o.textContent = m[1] + ' (' + m[2] + ')';
    ms.appendChild(o);
  });
  const ps = document.getElementById('palette');
  Object.keys(DATA.palettes).forEach((k) => {
    const o = document.createElement('option');
    o.value = k; o.textContent = k;
    ps.appendChild(o);
  });
  ps.value = 'midnight';
  document.getElementById('tags').innerHTML = ['free memorial shadow box maker', 'pet memorial svg maker', 'personalised memorial svg', 'cricut memorial', 'no signup']
    .map((t) => '<span class="tag">' + t + '</span>').join('');
  ['name', 'dates', 'line', 'motif', 'palette'].forEach((id) => {
    document.getElementById(id).addEventListener('input', render);
    document.getElementById(id).addEventListener('change', render);
  });
  document.getElementById('download').addEventListener('click', () => {
    const blob = new Blob([buildSvg()], { type: 'image/svg+xml' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'memorial-shadow-box-' + (document.getElementById('name').value.trim() || 'preview')
      .toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '') + '.svg';
    document.body.appendChild(a); a.click(); a.remove();
  });
  document.getElementById('share').addEventListener('click', () => {
    // WhatsApp is where this actually travels: a keepsake for a pet is the
    // kind of thing people send to the group chat they just created for the
    // family. No account, no upload, just a link and a sentence.
    const who = (document.getElementById('name').value.trim() || 'a name');
    const text = 'I made this for ' + who + ' - free memorial shadow box maker: ' + MK_URL;
    const wa = 'https://wa.me/?text=' + encodeURIComponent(text);
    if (navigator.share) {
      navigator.share({ title: 'Memorial shadow box', text: text, url: MK_URL })
        .catch(() => { window.open(wa, '_blank'); });
      return;
    }
    window.open(wa, '_blank');
  });
  render();
}

if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
else init();
</script>
</body></html>
"""