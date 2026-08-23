"""Listing copy generator: SEO titles, descriptions and marketplace tags."""
from __future__ import annotations

NAMES = {
    "mandala": ("Mandala SVG Bundle", "laser-cut ready mandala vectors"),
    "patterns": ("Seamless Pattern Pack", "tileable vector pattern sheet"),
    "quotes": ("Quote Card Set", "social-media ready motivational cards"),
    "planner": ("Habit Tracker Printable", "minimal printable planner sheet"),
}

TAGS = {
    "mandala": [
        "mandala svg", "cricut cut file", "laser cut file", "svg bundle",
        "vector art", "coloring page", "vinyl decal svg", "glowforge",
        "zentangle svg", "wall decor svg", "digital download",
        "commercial use svg", "meditation art",
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
}


def title_for(product_type: str, meta: dict) -> str:
    base, _sub = NAMES[product_type]
    return f"{base} #{meta['serial']:03d} | {meta['designs']} Design{'s' if meta['designs'] != 1 else ''} (SVG)"


def description_for(product_type: str, meta: dict) -> str:
    head = DESCRIPTIONS[product_type]
    return f"{head}\n\nSet {meta['serial']:03d} contains {meta['designs']} file(s)."


def tags_for(product_type: str) -> list[str]:
    return list(TAGS[product_type])
