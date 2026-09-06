"""Listing copy generator: SEO titles, descriptions and marketplace tags."""
from __future__ import annotations

NAMES = {
    "mandala": ("Mandala SVG Bundle", "laser-cut ready mandala vectors"),
    "layered-mandala": ("3D Layered Mandala SVG Pack", "cut-ready layered mandala vectors for cardstock"),
    "patterns": ("Seamless Pattern Pack", "tileable vector pattern sheet"),
    "quotes": ("Quote Card Set", "social-media ready motivational cards"),
    "planner": ("Habit Tracker Printable", "minimal printable planner sheet"),
    "weekly-compilation": ("Weekly Compilation Bundle", "best-of-week mega-bundle"),
}

TAGS = {
    "mandala": [
        "mandala svg", "cricut cut file", "laser cut file", "svg bundle",
        "vector art", "coloring page", "vinyl decal svg", "glowforge",
        "zentangle svg", "wall decor svg", "digital download",
        "commercial use svg", "meditation art",
    ],
    "layered-mandala": [
        "3d mandala svg", "layered mandala svg", "cricut mandala",
        "cardstock cut file", "paper craft svg", "mandala layers",
        "3d paper art", "mandala svg bundle", "cut ready svg",
        "vinyl mandala", "digital download", "commercial use svg",
        "wall decor svg",
    ],
    "patterns": [
        "seamless pattern", "surface pattern design", "repeat tile svg",
        "fabric print pattern", "wrapping paper design", "background svg",
        "scrapbook paper", "textile pattern", "digital paper pack",
        "geometric pattern", "printable paper", "craft vinyl",
        "digital download",
    ],
    "quotes": [
        "quote card template", "instagram post template", "motivational quotes",
        "social media templates", "canva alternative svg", "story templates",
        "affirmation cards", "printable quotes", "content creator kit",
        "quote graphics pack", "digital download", "wellness quotes",
        "pinterest pins",
    ],
    "planner": [
        "habit tracker printable", "a4 planner insert", "daily habit log",
        "goal tracker sheet", "productivity printable", "bullet journal page",
        "monthly tracker", "planner pdf alternative", "routine tracker",
        "self care planner", "digital download", "study planner",
        "fitness tracker sheet",
    ],
    "weekly-compilation": [
        "weekly compilation", "best of week", "mega bundle", "svg bundle",
        "weekly mega pack", "designers bundle", "curated collection",
        "commercial use svg", "digital download", "crafters bundle",
        "all-in-one pack",
    ],
}

DESCRIPTIONS = {
    "mandala": (
        "Hand-tuned generative mandala set delivered as clean vector SVG files.\n\n"
        "- Clean closed paths: cuts cleanly on Cricut, Silhouette and laser machines\n"
        "- Scalable to any size with zero quality loss (true vector)\n"
        "- Ideal for wall art, decals, coloring pages, wood engraving\n"
        "- Instant digital download - no physical item ships\n"
        "- Generated and quality-checked by an automated daily pipeline"
    ),
    "layered-mandala": (
        "Cut-ready 3D layered mandala set for Cricut, Silhouette and cardstock crafters.\n\n"
        "- 3 concentric layer files per design: cut each tier from different cardstock "
        "and stack with foam dots for a dimensional mandala\n"
        "- Bold connected shapes, no thin lines or floating pieces: cuts cleanly "
        "without shredding\n"
        "- Layer 1 (outer) through Layer 3 (core) plus a combined full view per design\n"
        "- True vector SVG: scale to any size with zero quality loss\n"
        "- Instant digital download - no physical item ships"
    ),
    "patterns": (
        "A curated sheet of tileable seamless vector patterns on one SVG board.\n\n"
        "- True repeating tiles built with SVG <pattern> primitives\n"
        "- Recolor easily: every shape uses flat fills, no effects\n"
        "- Great for fabric previews, wrapping paper, backgrounds, scrapbooking\n"
        "- Instant digital download - no physical item ships"
    ),
    "quotes": (
        "A fresh set of original motivational quote cards sized for social feeds.\n\n"
        "- Portrait 4:5 layout that fits Instagram and Pinterest feeds\n"
        "- Original public-friendly aphorisms written for this project\n"
        "- Editable vector text: change fonts, colors and wording freely\n"
        "- Consistent palette per set for a cohesive feed aesthetic"
    ),
    "planner": (
        "Minimal A4-landscape habit tracker sheet, print-and-go.\n\n"
        "- 31 day columns x 8 habit rows, fits any month\n"
        "- Crisp thin rules tuned for home printers\n"
        "- Works as bullet journal insert or clipboard sheet\n"
        "- Print at 100% scale on A4 or US Letter with fit-to-page"
    ),
    "weekly-compilation": (
        "Best-of-week mega-bundle: every design from the past 7 days, "
        "curated into one downloadable pack.\n\n"
        "- All daily products from the week, organized by source date in "
        "the filename (YYYY-MM-DD_...)\n"
        "- Includes SVG plus PNG previews where available\n"
        "- One download = the entire week's creative output\n"
        "- Perfect for crafters who want variety without checking back daily\n"
        "- Same commercial-use grant as individual bundles (no reselling "
        "raw files)\n"
        "- Generated and quality-checked by an automated daily pipeline"
    ),
}


def title_for(product_type: str, meta: dict, theme: dict | None = None) -> str:
    base, _sub = NAMES[product_type]
    label = theme["label"] if theme else ""
    head = f"{label} {base}" if label else base
    return f"{head} #{meta['serial']:03d} | {meta['designs']} Design{'s' if meta['designs'] != 1 else ''} (SVG)"


def description_for(product_type: str, meta: dict,
                    theme: dict | None = None) -> str:
    head = DESCRIPTIONS[product_type]
    theme_line = (f"Themed edition: {theme['label']}."
                  if theme else "Themed edition: classic.")
    return f"{head}\n\n{theme_line}\n\nSet {meta['serial']:03d} contains {meta['designs']} file(s)."


def tags_for(product_type: str, theme: dict | None = None) -> list[str]:
    base = list(TAGS[product_type])
    if theme:
        # Theme tags first (higher SEO weight), then product-specific, dedup.
        seen = set()
        out: list[str] = []
        for tag in list(theme["tags"]) + base:
            if tag not in seen:
                seen.add(tag)
                out.append(tag)
        return out
    return base
