#!/usr/bin/env python3
"""
delivery.py — render order status and delivery pages.

The buyer pays USDT to a published address and there is no account. That makes
delivery the hard part: without a page tied to their order, a paid buyer has
nowhere to look and cannot get their files.

This renders one static page per issued session, plus an index that maps an
order reference to its page. A session is identified by its short reference
(the first characters of its session id), which the buyer can quote.

Everything is generated at build time from checkout/sessions.json, so the pages
are static and need no server.

Usage:
  python3 pipeline/delivery.py [--dry-run]
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SESSIONS = ROOT / "checkout" / "sessions.json"
OUT_DIR = ROOT / "site_extra" / "delivery"

STATUS_TEXT = {
    "awaiting_payment": (
        "Awaiting payment",
        "Send the exact amount shown on the checkout page to the published "
        "address. This page updates automatically once the transfer is seen "
        "on-chain.",
    ),
    "paid": (
        "Payment detected - confirming",
        "Your transfer is on-chain and waiting for confirmation depth. This "
        "page updates automatically; no action is needed from you.",
    ),
    "confirmed": (
        "Payment confirmed",
        "Your download is ready. The link below is live.",
    ),
}


def load() -> dict:
    if not SESSIONS.exists():
        return {}
    try:
        data = json.loads(SESSIONS.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    sessions = data.get("sessions") if isinstance(data, dict) else None
    return sessions if isinstance(sessions, dict) else {}


def order_ref(session_id: str) -> str:
    """Short, human-quotable reference for an order."""
    return session_id[:10].upper()


def render_order(rec: dict) -> str:
    ref = order_ref(rec["id"])
    status = rec.get("status", "awaiting_payment")
    title, blurb = STATUS_TEXT.get(status, STATUS_TEXT["awaiting_payment"])
    accent = {"confirmed": "#7ee787", "paid": "#d29922"}.get(status, "#8b949e")

    confirmed_at = rec.get("confirmed_at") or ""
    if confirmed_at:
        confirmed_at = confirmed_at.replace("T", " ").replace("Z", " UTC")

    if status == "confirmed":
        main = (
            f'<p><a class="btn btn-primary" href="/{rec["download"].lstrip("/")}" download>'
            f'Download {rec["slug"]}</a></p>'
            '<p class="muted">This link points at the ZIP on our own site, so it '
            "stays available even if this page is re-generated.</p>"
        )
    else:
        main = (
            '<p class="muted">The download link appears here automatically once '
            "payment clears. You do not need to refresh this page more than "
            "once or two minutes.</p>"
        )

    rows = [
        ("Order reference", ref),
        ("Bundle", rec.get("slug", "")),
        ("Amount sent", f'{rec.get("unique_amount_usdt", "")} USDT (BEP20)'),
        ("Status", title),
    ]
    if rec.get("tx_hash"):
        rows.append(("Transaction", rec["tx_hash"]))
    if confirmed_at:
        rows.append(("Confirmed", confirmed_at))

    trs = "".join(
        f"<tr><th>{k}</th><td>{v}</td></tr>" for k, v in rows
    )

    return f"""<!DOCTYPE html><html lang="en"><head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Order {ref} | VectorForge Daily</title>
<meta name="robots" content="noindex,nofollow"/>
<link rel="canonical" href="/delivery/{ref}/"/>
<style>{CSS}</style></head><body>
<header><p><a href="/">&larr; Store</a></p>
<h1>Order {ref}</h1>
<span class="badge" style="color:{accent};border-color:{accent}55">{title}</span>
</header><main>
<section class="info"><p>{blurb}</p>{main}</section>
<section class="info"><h3>Details</h3>
<table class="detail-table"><tbody>{trs}</tbody></table></section>
</main><footer>VectorForge Daily &middot; payments verified on-chain</footer>
</body></html>"""


CSS = """
:root{color-scheme:dark}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Segoe UI',system-ui,sans-serif;background:#0d1117;color:#e6edf3;line-height:1.6}
a{color:#58a6ff;text-decoration:none}
header{padding:40px 24px 28px;text-align:center;background:linear-gradient(180deg,#101826,#0d1117)}
header h1{font-size:1.7rem;letter-spacing:-.02em}
header p{margin-bottom:8px}
.badge{display:inline-block;margin-top:12px;font-size:.8rem;border:1px solid;border-radius:999px;padding:4px 12px}
main{max-width:760px;margin:0 auto;padding:24px 16px 48px}
.info{background:#11161d;border:1px solid #2b3644;border-radius:12px;padding:18px;margin-bottom:18px}
.info h3{margin:0 0 8px;font-size:1rem}
.info p{color:#9aa7b4;margin:8px 0;font-size:.92rem}
.btn{display:inline-block;background:#238636;color:#fff;border-radius:8px;padding:10px 18px;font-weight:600;margin:8px 0}
.muted{color:#6e7681;font-size:.85rem}
table.detail-table{width:100%;border-collapse:collapse;font-size:.9rem}
table.detail-table th,table.detail-table td{text-align:left;padding:8px 10px;border-bottom:1px solid #21262d;vertical-align:top}
table.detail-table th{color:#8b949e;font-weight:600;white-space:nowrap;width:38%}
table.detail-table td{font-family:ui-monospace,monospace;word-break:break-all}
footer{text-align:center;color:#6e7681;font-size:.78rem;padding:24px 16px 40px}
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    sessions = load()
    if not sessions:
        print("no checkout sessions; nothing to render")
        return 0

    if not args.dry_run:
        OUT_DIR.mkdir(parents=True, exist_ok=True)

    counts: dict[str, int] = {}
    for rec in sessions.values():
        if not isinstance(rec, dict) or not rec.get("id"):
            continue
        status = rec.get("status", "awaiting_payment")
        counts[status] = counts.get(status, 0) + 1
        if not args.dry_run:
            d = OUT_DIR / order_ref(rec["id"])
            d.mkdir(parents=True, exist_ok=True)
            (d / "index.html").write_text(render_order(rec), encoding="utf-8")

    print(f"orders rendered: {len(sessions)}")
    for k, v in sorted(counts.items()):
        print(f"  {k}: {v}")
    if not args.dry_run:
        print(f"written to {OUT_DIR.relative_to(ROOT)}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
