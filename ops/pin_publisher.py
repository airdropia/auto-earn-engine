#!/usr/bin/env python3
"""
pin_publisher.py - Publish storefront products as Pinterest pins (autonomous).

Picks the newest catalog items, builds a pin from the product's best
image (mockup PNG if available, else first file), maps to the right
board, and publishes via the Pinterest API. Tracks published product
ids in a local state file so it never re-pins the same product.

Board mapping (secrets: PINTEREST_BOARD_*):
  mandala           -> board_mandala     (Free Mandala SVG Files)
  layered-mandala   -> board_cricut      (Cricut Ideas & Cut Files)
  patterns          -> board_patterns    (Seamless Patterns for Designers)
  quotes            -> board_printables  (Printable Planners & Trackers)
  planner           -> board_printables  (Printable Planners & Trackers)
  weekly-compilation-> skipped (mixed content; pin via main products)

Rate-limit safety (trial access):
  - Default MAX_PINS=3 per run
  - Sleeps between pins (3s)
  - On HTTP 429: stops, preserves progress, next cron retries

Usage:
  python3 ops/pin_publisher.py              # publish up to MAX_PINS
  python3 ops/pin_publisher.py --dry-run    # show what would publish

State: ops/.pin_state.json {'pinned': [product_id, ...]}
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.parse
import urllib.request
import urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / "catalog" / "catalog.json"
STATE_PATH = Path(__file__).resolve().parent / ".pin_state.json"
SECRETS_PATH = Path.home() / ".pi" / "secrets" / "pinterest.env"

STORE_URL = "https://airdropia.github.io/auto-earn-engine/"
MAX_PINS = int(os.environ.get("PINTEREST_MAX_PINS", "3"))
SLEEP_BETWEEN = 3

BOARD_MAP = {
    "mandala": "PINTEREST_BOARD_MANDALA",
    "layered-mandala": "PINTEREST_BOARD_CRICUT",
    "patterns": "PINTEREST_BOARD_PATTERNS",
    "quotes": "PINTEREST_BOARD_PRINTABLES",
    "planner": "PINTEREST_BOARD_PRINTABLES",
}


def load_env() -> dict:
    env: dict[str, str] = {}
    if SECRETS_PATH.exists():
        for line in SECRETS_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env


def load_state() -> dict:
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    return {"pinned": []}


def save_state(state: dict) -> None:
    STATE_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")


def best_image_for(item: dict, env: dict) -> str:
    """Pick the best public image URL for a product: mockup PNG first,
    else first PNG, else empty (Pinterest image_url does NOT support
    SVG - products with only SVG files are skipped by the caller)."""
    for f in item.get("files", []):
        if f.endswith("-mockup.png"):
            return STORE_URL + f
    for f in item.get("files", []):
        if f.endswith(".png"):
            return STORE_URL + f
    return ""


def pin_title(item: dict) -> str:
    t = item.get("title", "")
    # Titles look like "Back to School Mandala SVG Bundle #349 | 8 Designs (SVG)"
    # Pinterest titles: max 100 chars, no #serial noise needed
    t = t.split("|")[0].strip()
    return t[:100]


def pin_description(item: dict) -> str:
    """Build a Pinterest-optimized description under 500 chars with hashtags."""
    title = pin_title(item)
    tags = item.get("tags", [])[:6]
    hashtags = " ".join(
        "#" + t.replace(" ", "").replace("&", "").replace("'", "")[:20]
        for t in tags if t and not t.startswith("#")
    )
    desc = (
        f"{title}. "
        f"Free download from VectorForge Daily - new designs every day. "
        f"SVG, PNG and mockup included. Commercial use allowed. "
        f"{hashtags}"
    )
    return desc[:500]


def api_request(method: str, url: str, token: str, body: dict | None = None):
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode()
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raw = e.read().decode(errors="replace")
        try:
            return e.code, json.loads(raw)
        except json.JSONDecodeError:
            return e.code, {"message": raw[:200]}


def publish_pin(item: dict, env: dict) -> tuple[bool, str]:
    token = env.get("PINTEREST_ACCESS_TOKEN", "")
    board_key = BOARD_MAP.get(item.get("type", ""))
    board_id = env.get(board_key, "") if board_key else ""
    if not token or not board_id:
        return False, "missing token/board for type " + item.get("type", "?")

    image_url = best_image_for(item, env)
    payload = {
        "board_id": board_id,
        "media_source": {"source_type": "image_url", "url": image_url},
        "title": pin_title(item),
        "description": pin_description(item),
        "link": STORE_URL,
        "alt_text": f"{pin_title(item)} free SVG download",
    }
    status, resp = api_request(
        "POST", "https://api.pinterest.com/v5/pins", token, payload
    )
    if status in (200, 201):
        return True, f"pinned (id={resp.get('id')})"
    if status == 429:
        return False, "rate limited (429) - stop and retry later"
    return False, f"HTTP {status}: {json.dumps(resp)[:150]}"


def candidates(catalog: list[dict], state: dict) -> list[dict]:
    done = set(state.get("pinned", []))
    # Newest products first, skip already pinned, skip weekly-compilation
    fresh = sorted(
        [i for i in catalog if i.get("created")]
        + [],
        key=lambda i: i.get("created", ""),
        reverse=True,
    )
    picks = []
    for item in fresh:
        if item.get("id") in done:
            continue
        if item.get("type") == "weekly-compilation":
            continue
        # Skip products with no raster (PNG) image - Pinterest can't
        # ingest SVG via image_url. Only mandala/layered have PNGs today.
        if not best_image_for(item, {}):
            continue
        picks.append(item)
        if len(picks) >= MAX_PINS:
            break
    return picks


def main(argv: list[str]) -> int:
    dry_run = "--dry-run" in argv
    env = load_env()
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    state = load_state()
    picks = candidates(catalog, state)

    if not picks:
        print("pin_publisher: nothing new to pin")
        return 0

    print(f"pin_publisher: {len(picks)} product(s) to pin (dry_run={dry_run})")
    pinned_now = 0
    for item in picks:
        if dry_run:
            img = best_image_for(item, env)
            print(f"  [dry] {item.get('id')} -> {item.get('title')[:40]}")
            print(f"        img={img}")
            continue
        ok, msg = publish_pin(item, env)
        if ok:
            state.setdefault("pinned", []).append(item.get("id"))
            pinned_now += 1
            print(f"  OK  {item.get('id')} ({item.get('type')}): {msg}")
        else:
            print(f"  FAIL {item.get('id')} ({item.get('type')}): {msg}")
            if "429" in msg or "rate" in msg.lower():
                print("  rate limit hit - stopping, will retry next run")
                break
        if pinned_now < len(picks):
            time.sleep(SLEEP_BETWEEN)

    save_state(state)
    print(f"pin_publisher: done, {pinned_now} pinned this run")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))