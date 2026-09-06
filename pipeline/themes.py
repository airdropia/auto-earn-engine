"""
Theming system for daily products (AUDIT.md P2).

Maps a UTC date to a theme token that drives:
  - title prefix and search tags (SEO/click-through)
  - palette for mandala / layered / patterns (visual cohesion)
  - quote text bank (relevant copy)

Deterministic: same date -> same theme (no randomness). Calendar peaks
(Halloween, Diwali, Christmas, etc.) win over seasonal bucket. Seasonal
bucket (month-level) wins over evergreen pool. Three-tier fallback so every
listing is themed and never generic.

Evidence: Etsy/CF bestseller pages are 80%+ theme-driven. Pinterest search
volume for "halloween svg", "christmas pattern" etc. spikes 3-6x in season.
Generic untitled bundles convert materially worse than themed ones.
"""

from __future__ import annotations

from datetime import datetime

# ---------------------------------------------------------------------------
# Theme registry
# ---------------------------------------------------------------------------
# Each theme:
#   label      - human readable, used in titles
#   palette    - 5 hex colors (ink, 2 accents, 2 supports) used by renderers
#   tags       - extra search tags prepended to listings.tags_for
#   quotes     - short relevant copy used by the quotes renderer

THEMES: dict[str, dict] = {
    "halloween": {
        "label": "Halloween",
        "palette": ["#1a1a1a", "#ff6b35", "#f7b801", "#9b5de5", "#2ec4b6"],
        "tags": ["halloween svg", "spooky svg", "halloween mandala", "fall svg",
                 "pumpkin svg", "trick or treat svg"],
        "quotes": [
            "Spooky season",
            "Trick or treat",
            "Witch better have my candy",
            "Boo to you",
            "Hocus pocus",
        ],
    },
    "autumn": {
        "label": "Autumn",
        "palette": ["#5e2c0d", "#b8521f", "#d97e3a", "#e0a96d", "#3a200d"],
        "tags": ["autumn svg", "fall svg", "thanksgiving svg", "harvest svg",
                 "leaves svg", "pumpkin svg", "cozy svg"],
        "quotes": [
            "Hello pumpkin",
            "Sweater weather",
            "Fall in love with autumn",
            "Grateful heart",
            "Leaves are falling",
        ],
    },
    "thanksgiving": {
        "label": "Thanksgiving",
        "palette": ["#4a1f0e", "#a8431a", "#d9853b", "#f2c14e", "#3b2412"],
        "tags": ["thanksgiving svg", "grateful svg", "harvest svg",
                 "fall svg", "autumn svg", "pumpkin svg"],
        "quotes": [
            "Grateful thankful blessed",
            "Give thanks",
            "Thankful heart",
            "Gobble till you wobble",
            "Family and food",
        ],
    },
    "diwali": {
        "label": "Diwali",
        "palette": ["#3a0ca3", "#f72585", "#ffb703", "#06d6a0", "#1a0633"],
        "tags": ["diwali svg", "festival of lights svg", "indian festival svg",
                 "diwali mandala", "rangoli svg", "celebration svg"],
        "quotes": [
            "Happy Diwali",
            "Festival of lights",
            "Shine bright",
            "Light over darkness",
            "Joy and prosperity",
        ],
    },
    "hanukkah": {
        "label": "Hanukkah",
        "palette": ["#0a2463", "#ffd460", "#3e92cc", "#1e5288", "#d8e2dc"],
        "tags": ["hanukkah svg", "jewish holiday svg", "menorah svg",
                 "festival of lights svg", "winter svg"],
        "quotes": [
            "Happy Hanukkah",
            "Festival of lights",
            "Eight nights of light",
            "Shine on",
            "Mazel tov",
        ],
    },
    "winter": {
        "label": "Winter",
        "palette": ["#0d1b2a", "#1b4965", "#62b6cb", "#cae9ff", "#5fa8d3"],
        "tags": ["winter svg", "snowflake svg", "cold weather svg",
                 "snow svg", "cozy svg", "january svg"],
        "quotes": [
            "Winter wonderland",
            "Let it snow",
            "Stay cozy",
            "Cold hands warm heart",
            "Hello winter",
        ],
    },
    "christmas": {
        "label": "Christmas",
        "palette": ["#0b3d2e", "#c1121f", "#ffd60a", "#ffffff", "#2d6a4f"],
        "tags": ["christmas svg", "holiday svg", "santa svg", "xmas svg",
                 "festive svg", "december svg", "gift svg"],
        "quotes": [
            "Merry and bright",
            "Joy to the world",
            "Happy holidays",
            "Tis the season",
            "Believe in magic",
        ],
    },
    "newyear": {
        "label": "New Year",
        "palette": ["#1a1a2e", "#e94560", "#f5b700", "#0f3460", "#fff8e7"],
        "tags": ["new year svg", "celebration svg", "fireworks svg",
                 "2026 svg", "party svg", "january svg"],
        "quotes": [
            "New year new me",
            "Cheers to 2026",
            "Hello new year",
            "New beginnings",
            "Make it count",
        ],
    },
    "valentine": {
        "label": "Valentine",
        "palette": ["#590d22", "#a4133c", "#c9184a", "#ff4d6d", "#fff0f3"],
        "tags": ["valentine svg", "love svg", "heart svg", "romance svg",
                 "february svg", "couples svg"],
        "quotes": [
            "Be mine",
            "Love you more",
            "XOXO",
            "You and me",
            "Forever and always",
        ],
    },
    "easter": {
        "label": "Easter",
        "palette": ["#7cb518", "#f4a261", "#e76f51", "#fff1e6", "#264653"],
        "tags": ["easter svg", "spring svg", "bunny svg", "egg svg",
                 "pastel svg", "april svg"],
        "quotes": [
            "Hello spring",
            "Happy Easter",
            "Bloom where you are planted",
            "Egg-cited",
            "Spring is here",
        ],
    },
    "mothersday": {
        "label": "Mother's Day",
        "palette": ["#5e2a7e", "#d96aa0", "#f5b3c5", "#fce4ec", "#7a3e9d"],
        "tags": ["mother's day svg", "mom svg", "mama svg", "floral svg",
                 "love svg", "may svg"],
        "quotes": [
            "Best mom ever",
            "Mom life",
            "World's greatest mom",
            "Thank you mom",
            "Mama bear",
        ],
    },
    "spring": {
        "label": "Spring",
        "palette": ["#386641", "#6a994e", "#a7c957", "#f2e8cf", "#bc4749"],
        "tags": ["spring svg", "floral svg", "flower svg", "garden svg",
                 "april svg", "may svg", "blossom svg"],
        "quotes": [
            "Hello spring",
            "Bloom with grace",
            "Spring vibes",
            "Fresh starts",
            "In full bloom",
        ],
    },
    "summer": {
        "label": "Summer",
        "palette": ["#003049", "#d62828", "#f77f00", "#fcbf49", "#eae2b7"],
        "tags": ["summer svg", "beach svg", "sun svg", "tropical svg",
                 "vacation svg", "july svg"],
        "quotes": [
            "Hello summer",
            "Sunshine state of mind",
            "Beach please",
            "Summer lovin",
            "Sunkissed",
        ],
    },
    "backtoschool": {
        "label": "Back to School",
        "palette": ["#1d3557", "#457b9d", "#e63946", "#f1faee", "#a8dadc"],
        "tags": ["back to school svg", "school svg", "teacher svg",
                 "education svg", "september svg", "student svg"],
        "quotes": [
            "School days",
            "Hello school",
            "Be kind be cool",
            "Class is in",
            "First day of school",
        ],
    },
    # --- Evergreen fallback pool (rotated deterministically by date) ---
    "floral": {
        "label": "Floral",
        "palette": ["#5f0f40", "#9a031e", "#fb8b24", "#0f4c5c", "#e36414"],
        "tags": ["floral svg", "flower svg", "botanical svg", "garden svg",
                 "bloom svg", "petal svg"],
        "quotes": [
            "Bloom with grace",
            "Hello bloom",
            "In full bloom",
            "Grow through what you go through",
            "Be your own kind of beautiful",
        ],
    },
    "geometric": {
        "label": "Geometric",
        "palette": ["#22223b", "#4a4e69", "#9a8c98", "#c9ada7", "#f2e9e4"],
        "tags": ["geometric svg", "abstract svg", "minimal svg", "shape svg",
                 "modern svg", "pattern svg"],
        "quotes": [
            "Stay sharp",
            "Find your angle",
            "Less is more",
            "Form follows function",
            "Designed with intent",
        ],
    },
    "boho": {
        "label": "Boho",
        "palette": ["#6f1d1b", "#bb9457", "#432818", "#99582a", "#ffe6a7"],
        "tags": ["boho svg", "bohemian svg", "sunburst svg", "tribal svg",
                 "earthy svg", "free spirit svg"],
        "quotes": [
            "Free spirit",
            "Wild and free",
            "Boho soul",
            "Wander often",
            "Sun and moon",
        ],
    },
    "sunburst": {
        "label": "Sunburst",
        "palette": ["#ef476f", "#ffd166", "#06d6a0", "#118ab2", "#073b4c"],
        "tags": ["sunburst svg", "sun svg", "rays svg", "bright svg",
                 "happy svg", "radiant svg"],
        "quotes": [
            "Hello sunshine",
            "Shine bright",
            "Sun-kissed",
            "You are my sunshine",
            "Radiate positivity",
        ],
    },
    "hearts": {
        "label": "Hearts",
        "palette": ["#590d22", "#a4133c", "#c9184a", "#ff4d6d", "#fff0f3"],
        "tags": ["heart svg", "love svg", "romance svg", "affection svg",
                 "sweet svg", "cute svg"],
        "quotes": [
            "Be mine",
            "Love wins",
            "Heart full",
            "Spread love",
            "All you need is love",
        ],
    },
    "stars": {
        "label": "Stars",
        "palette": ["#0a1f44", "#3d5a80", "#98c1d9", "#e0fbfc", "#ee6c4d"],
        "tags": ["star svg", "celestial svg", "night sky svg", "twinkle svg",
                 "dream svg", "constellation svg"],
        "quotes": [
            "Reach for the stars",
            "Twinkle bright",
            "Wish upon a star",
            "You are a star",
            "Dream big",
        ],
    },
    "leaves": {
        "label": "Leaves",
        "palette": ["#2d6a4f", "#40916c", "#52b788", "#74c69d", "#d8f3dc"],
        "tags": ["leaf svg", "leaves svg", "foliage svg", "botanical svg",
                 "greenery svg", "nature svg"],
        "quotes": [
            "Stay grounded",
            "Leaf it to me",
            "Nature heals",
            "Go outside and play",
            "Rooted in love",
        ],
    },
}


# ---------------------------------------------------------------------------
# Calendar rules (fixed-date peaks win over seasonal bucket)
# ---------------------------------------------------------------------------
# Each entry: (month, day, "MM-DD") -> theme name
# Multi-day windows: (month, day_start, day_end) -> theme name

_FIXED_DATES: list[tuple[int, int, int | None, str]] = [
    # (month, day_start, day_end_or_None, theme)
    (1, 1, 5, "newyear"),
    (2, 10, 16, "valentine"),
    (3, 15, 25, "spring"),
    (4, 1, 20, "easter"),
    (5, 8, 14, "mothersday"),  # 2nd Sunday window approximation
    (6, 15, 30, "summer"),
    (7, 1, 20, "summer"),
    (8, 15, 31, "backtoschool"),
    (9, 1, 15, "backtoschool"),
    (10, 25, 31, "halloween"),
    (11, 6, 10, "diwali"),     # Diwali 2026 = Nov 8
    (11, 22, 28, "thanksgiving"),  # 4th Thursday window
    (12, 4, 12, "hanukkah"),   # Hanukkah 2026 = Dec 4-12
    (12, 20, 31, "christmas"),
    (12, 1, 19, "winter"),
]

# Seasonal bucket (month-level fallback)
_SEASONAL_BUCKET: dict[int, str] = {
    1: "winter",
    2: "winter",
    3: "spring",
    4: "spring",
    5: "spring",
    6: "summer",
    7: "summer",
    8: "summer",
    9: "autumn",
    10: "autumn",
    11: "autumn",
    12: "winter",
}

# Evergreen pool (final fallback; rotate by day-of-year for variety)
_EVERGREEN_POOL = ["floral", "geometric", "boho", "sunburst",
                   "hearts", "stars", "leaves"]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_today_theme(date_str: str) -> dict:
    """
    Deterministic theme selection for a UTC date string ('YYYY-MM-DD').

    Three-tier resolution:
      1. Fixed calendar peak (e.g., Oct 31 -> halloween, Dec 25 -> christmas)
      2. Seasonal bucket (e.g., September -> autumn)
      3. Evergreen rotation (day-of-year modulo pool size)

    Returns a theme dict (label, palette, tags, quotes). Never returns None
    so every listing is always themed.
    """
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    month, day = dt.month, dt.day

    for m, d_start, d_end, name in _FIXED_DATES:
        if m == month and d_start <= day <= (d_end if d_end else d_start):
            return THEMES[name]

    seasonal = _SEASONAL_BUCKET.get(month)
    if seasonal and seasonal in THEMES:
        return THEMES[seasonal]

    pool_index = dt.timetuple().tm_yday % len(_EVERGREEN_POOL)
    return THEMES[_EVERGREEN_POOL[pool_index]]


def theme_label(theme: dict) -> str:
    return theme["label"]


def theme_palette(theme: dict) -> list[str]:
    return list(theme["palette"])


def theme_tags(theme: dict) -> list[str]:
    return list(theme["tags"])


def theme_quotes(theme: dict) -> list[str]:
    return list(theme["quotes"])


if __name__ == "__main__":
    # Sanity check: 2026-09-05 should resolve to "backtoschool" (Sep 1-15).
    for d in ("2026-09-05", "2026-10-31", "2026-11-08",
              "2026-12-25", "2026-12-31", "2026-02-14"):
        t = get_today_theme(d)
        print(f"{d} -> {t['label']}")
