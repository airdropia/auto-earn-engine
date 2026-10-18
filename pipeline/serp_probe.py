#!/usr/bin/env python3
"""Search-engine probe: is anything of ours being crawled and indexed?

Page-view counting needs an analytics account, and the zero-account rule
rules one out; every no-auth hit counter on the public web is dead
(countapi.net returns 404, countapi.xyz and countersapi do not resolve).
So the honest measurable signal left is the one the money depends on
eventually: whether crawlers have found the site at all.

Bing's `site:` query is scraped for exactly that, and the answer is written
to metrics/traffic.json as a daily series. Zero when nothing is indexed is a
fact worth having, because it is the difference between "waiting for the
crawl" and "silently broken".

The probe degrades to "unknown" rather than reporting zero: a blocked request
is not the same as an empty index, and conflating them is how a real outage
gets filed under "probably fine".
"""
from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
METRICS = ROOT / "metrics" / "traffic.json"

HOST = "airdropia.github.io"
SITE = "airdropia.github.io/auto-earn-engine"
CC_API = "https://index.commoncrawl.org/"
CC_COLLINFO = CC_API + "collinfo.json"
# A handful of pages that must be indexed before the lane is working at all.
KEY_PAGES = [
    "/auto-earn-engine/maker/",
    "/auto-earn-engine/checkout/",
    "/auto-earn-engine/blog/",
    "/auto-earn-engine/",
]

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")


def _fetch(url: str, timeout: int = 25) -> tuple[int, str]:
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.getcode(), resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        return exc.code, ""
    except Exception:
        return 0, ""


def probe_commoncrawl(collections: int = 3) -> dict:
    """Ask the Common Crawl indexes whether any crawler has fetched us.

    This is the probe that actually works from CI. Bing serves its captcha to
    GitHub's runner ranges — the same class of problem as the public BSC RPCs
    — so a Bing-only probe reported "unknown" forever and would have looked
    like instrumentation while measuring nothing. Common Crawl answers a plain
    API request from a runner and is a real crawler: a capture here means the
    site is discoverable to the web at all.
    """
    code, body = _fetch(CC_COLLINFO)
    if code != 200 or not body:
        return {"status": "unknown", "reason": f"commoncrawl collinfo http {code}"}
    try:
        colls = json.loads(body)[:collections]
    except ValueError:
        return {"status": "unknown", "reason": "collinfo not json"}

    found_any = False
    checked = []
    for coll in colls:
        cid = coll.get("id", "")
        if not cid:
            continue
        url = (CC_API + cid + "-index?url="
               + urllib.parse.quote(SITE + "*") + "&output=json&limit=20")
        ccode, cbody = _fetch(url)
        lines = [l for l in cbody.splitlines() if l.strip().startswith("{")]
        checked.append({"index": cid, "captures": len(lines)})
        if lines:
            found_any = True
    return {
        "status": "ok",
        "captured": found_any,
        "indexes_checked": checked,
    }


def probe_bing() -> dict:
    """Count our own URLs in Bing's site: results, and check key pages."""
    query = urllib.parse.quote(f"site:{HOST}")
    code, html = _fetch(f"https://www.bing.com/search?q={query}&count=30")
    if code != 200 or not html:
        return {"status": "unknown", "reason": f"bing http {code or 'no response'}"}

    blocked = any(marker in html.lower() for marker in
                  ("captcha", "verify you are", "unusual traffic", "blocked"))
    urls = sorted(set(re.findall(rf"https?://{re.escape(HOST)}[^\"'&<>\s]*", html)))
    if blocked:
        return {"status": "unknown", "reason": "bing served a challenge page"}

    found = {
        page: any(HOST + page.rstrip("/") in u or u.startswith(f"https://{HOST}{page}")
                  for u in urls)
        for page in KEY_PAGES
    }
    return {
        "status": "ok",
        "indexed_urls": len(urls),
        "no_results_banner": "there are no results" in html.lower(),
        "key_pages_indexed": sum(1 for v in found.values() if v),
        "key_pages": found,
    }


def main() -> int:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    result = probe_commoncrawl()
    # Bing stays as a secondary signal: it is the index that matters for
    # revenue, but it challenges runner IPs, so its answer is optional.
    result["bing"] = probe_bing()

    history = []
    if METRICS.exists():
        try:
            history = json.loads(METRICS.read_text(encoding="utf-8")).get("series", [])
        except (ValueError, OSError):
            history = []

    entry = {"date": today, **result}
    history = [h for h in history if h.get("date") != today] + [entry]
    history = history[-90:]

    METRICS.parent.mkdir(parents=True, exist_ok=True)
    METRICS.write_text(
        json.dumps({
            "note": (
                "Search-engine crawl signal, not page views. Page-view "
                "counting needs an analytics account, which the zero-account "
                "rule forbids; every no-auth hit counter is dead."
            ),
            "series": history,
        }, indent=2) + "\n",
        encoding="utf-8",
    )

    if result.get("status") == "ok":
        detail = ", ".join(
            f"{c['index']}={c['captures']}" for c in result.get("indexes_checked", [])
        )
        bing = result.get("bing", {})
        bing_txt = (f"bing indexed_urls={bing.get('indexed_urls')}"
                    if bing.get("status") == "ok" else "bing=unknown")
        print(f"commoncrawl captured={result['captured']} ({detail}) {bing_txt}")
    else:
        print(f"::warning::serp probe unavailable ({result.get('reason')})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())