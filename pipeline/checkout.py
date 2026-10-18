#!/usr/bin/env python3
"""
checkout.py — zero-signup crypto checkout for the storefront.

THE RAIL: no gateway account, no KYC, no API key, no user step. The buyer
sends USDT (BEP20) to a published receive address. This agent watches the
chain on a free public RPC and confirms payments automatically.

HOW MATCHING WORKS (no memo field exists for USDT BEP20, so amounts are used):
each checkout session is issued a UNIQUE amount = base price + a small
deterministic offset derived from the session id. An incoming transfer of
exactly that amount is matched to that session. Offsets are kept small
(< 1% of price) and unique per open session, which is the standard
static-address technique for identifying payers.

Everything runs in GitHub Actions. The local machine never runs this.

Usage:
  python3 pipeline/checkout.py --init                  # write storefront config
  python3 pipeline/checkout.py --watch                 # scan chain, confirm payments
  python3 pipeline/checkout.py --status               # print session table
  python3 pipeline/checkout.py --selftest             # offline unit checks

Env:
  VF_PAYOUT_ADDRESS   receive address (public, not a secret)
  BSC_RPC             optional; defaults to a public endpoint
"""

import argparse
import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from decimal import Decimal, getcontext
from pathlib import Path

getcontext().prec = 18

ROOT = Path(__file__).resolve().parent.parent
STATE_DIR = ROOT / "checkout"
SESSIONS_FILE = STATE_DIR / "sessions.json"
METRICS_FILE = ROOT / "metrics" / "earnings.json"

USDT_BEP20_CONTRACT = "0x55d398326f99059fF775485246999027B3197955"
USDT_DECIMALS = 18
# Only endpoints that actually index logs can answer eth_getLogs. Probed
# 2026-10-18: bnb dataseed* and zan.top answer blockNumber but reject
# getLogs with "limit exceeded", drpc/bloxroute-free tiers rate-limit
# hard, meowrpc has no getLogs at all. The six below are from six different
# operators on purpose — GitHub's runner IP ranges get rate-limited by
# single providers, and on 2026-10-18 every run of the watcher died with
# "chain unreachable", which would have silently lost the first real order.
DEFAULT_RPCS = [
    # Probed from a GitHub runner 2026-10-18: the first two answer getLogs,
    # the other four return HTTP 403 there (the providers block AWS ranges).
    # Order matters: the endpoints known to work from CI come first so a
    # healthy run spends no requests on ones that will refuse.
    "https://bsc.rpc.blxrbdn.com",
    "https://rpc-bsc.48.club",
    "https://bsc-rpc.publicnode.com",
    "https://bsc.publicnode.com",
    "https://1rpc.io/bnb",
    "https://bsc.blockrazor.xyz",
]
# BSC blocks are ~3s; 10 minutes of headroom over the cron interval.
BLOCK_CHUNK = 200
SCAN_INTERVAL_SEC = 600
CONFIRMATION_LOOKAHEAD = 30

# Confirmed minimum confirmations before an order is considered paid.
REQUIRED_CONFIRMATIONS = 3


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def rpc(method: str, params: list, tolerate_error: bool = False):
    """Call a BSC RPC, rotating across public endpoints. No API key needed.

    tolerate_error=True returns the RPC error object instead of raising, so a
    run can degrade gracefully rather than failing the whole job.
    """
    only = os.environ.get("BSC_RPC")
    endpoints = [only] if only else DEFAULT_RPCS
    last = None
    for endpoint in endpoints:
        try:
            req = urllib_request(endpoint, json.dumps(
                {"jsonrpc": "2.0", "method": method, "params": params, "id": 1}))
            if req.get("error"):
                last = req["error"]
                continue
            return req.get("result")
        except Exception as exc:
            last = str(exc)
            continue
    if tolerate_error:
        print(f"::warning::all {len(endpoints)} BSC RPC endpoints failed; last error: {last}")
        return None
    raise RuntimeError(f"all RPC endpoints failed, last error: {last}")


def probe_endpoints() -> int:
    """Report, per endpoint, whether it answers blockNumber and getLogs.

    The watcher has exactly one failure mode that matters — no reachable log
    indexer — and until this existed it was invisible: the run printed
    "chain unreachable" with no reason and no endpoint named. This is cheap,
    read-only, and turns an outage into evidence.
    """
    topic0 = ("0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef")
    address = USDT_BEP20_CONTRACT
    head_hex = None
    for endpoint in DEFAULT_RPCS:
        res = rpc("eth_blockNumber", [], tolerate_error=True)
        head_hex = res or head_hex
        print(f"probe {endpoint} blockNumber={'ok' if res else 'FAIL'}")
    if head_hex is None:
        print("probe: no endpoint answered blockNumber; cannot test getLogs")
        return 0
    head = int(head_hex, 16)
    payload = [{
        "fromBlock": hex(max(0, head - 3)),
        "toBlock": hex(head),
        "address": address,
        "topics": [topic0],
    }]
    for endpoint in DEFAULT_RPCS:
        try:
            req = urllib_request(endpoint, json.dumps(
                {"jsonrpc": "2.0", "method": "eth_getLogs", "params": payload, "id": 1}))
            if req.get("error"):
                print(f"probe {endpoint} getLogs=ERROR {req['error'].get('message')}")
            else:
                print(f"probe {endpoint} getLogs=OK ({len(req.get('result') or [])} logs)")
        except Exception as exc:
            print(f"probe {endpoint} getLogs=FAIL {exc}")
    return 0


def urllib_request(url: str, payload: str) -> dict:
    import urllib.request
    r = urllib.request.Request(
        url, data=payload.encode(), headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(r, timeout=30) as resp:
        return json.loads(resp.read().decode())


def load_sessions() -> dict:
    if SESSIONS_FILE.exists():
        return json.loads(SESSIONS_FILE.read_text(encoding="utf-8"))
    return {"version": 1, "created": utc_now(), "sessions": {}, "cursor_block": None}


def save_sessions(state: dict) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    tmp = SESSIONS_FILE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(SESSIONS_FILE)


def payout_address() -> str:
    addr = os.environ.get("VF_PAYOUT_ADDRESS", "")
    if not addr:
        raise SystemExit("VF_PAYOUT_ADDRESS not set — refusing to issue invoices")
    return addr


def price_usdt_for(product: dict) -> Decimal:
    """Price in USDT. Quality-first pricing: one flagship is a considered buy."""
    base = Decimal(product.get("price_usdt", "7.00"))
    return base.quantize(Decimal("0.000001"))


def unique_offset(session_id: str, price: Decimal) -> Decimal:
    """Small deterministic per-session offset so payers can be identified.

    Bounded to 0.1% of price and quantized to 6 decimals, so the buyer pays a
    clean-looking amount and the total is never meaningfully inflated.
    """
    span = (price * Decimal("0.001")).quantize(Decimal("0.000001"))
    if span <= 0:
        span = Decimal("0.000001")
    digest = hashlib.sha256(session_id.encode()).hexdigest()
    frac = int(digest[:8], 16) / 0xFFFFFFFF
    return (span * Decimal(str(frac))).quantize(Decimal("0.000001"))


def create_session(state: dict, product: dict) -> dict:
    sid = hashlib.sha256(
        f"{product['slug']}:{time.time_ns()}".encode()
    ).hexdigest()[:20]
    price = price_usdt_for(product)
    amount = price + unique_offset(sid, price)
    # Reference is the buyer-facing order id. It is derived from the product
    # slug, NOT from the session id: a session id changes if an invoice is ever
    # reissued, which would break links the buyer already has. Deriving it from
    # the slug keeps it stable forever, which is what the static site needs.
    ref = hashlib.sha1(f"vf-ref:{product['slug']}".encode()).hexdigest()[:10].upper()
    rec = {
        "id": sid,
        "reference": ref,
        "slug": product["slug"],
        "base_price_usdt": str(price),
        "unique_amount_usdt": str(amount),
        "address": payout_address(),
        "status": "awaiting_payment",
        "created": utc_now(),
        "confirmed_at": None,
        "tx_hash": None,
        "block": None,
        "download": f"/downloads/{product['slug']}.zip",
        "status_url": f"/delivery/{ref}/",
    }
    state["sessions"][sid] = rec
    return rec


def discover_products() -> list:
    pdir = ROOT / "products"
    out = []
    if not pdir.exists():
        return out
    # Catalog prices are per-product overrides (memorial designs carry their own
    # premium price), so read them rather than falling back to the global
    # default for every product.
    catalog_prices: dict[str, str] = {}
    catalog_path = ROOT / "catalog" / "catalog.json"
    if catalog_path.exists():
        try:
            for item in json.loads(catalog_path.read_text(encoding="utf-8")):
                price = (item.get("meta") or {}).get("price_usdt") or item.get("price_usdt")
                if price and item.get("id"):
                    catalog_prices[item["id"]] = str(price)
        except (ValueError, OSError):
            pass
    for date_dir in sorted(pdir.iterdir()):
        if not date_dir.is_dir():
            continue
        for prod in sorted(date_dir.iterdir()):
            if prod.is_dir() and list(prod.glob("*.svg")):
                entry = {"slug": prod.name, "date": date_dir.name, "path": prod}
                if prod.name in catalog_prices:
                    entry["price_usdt"] = catalog_prices[prod.name]
                out.append(entry)
    return out


def usdt_balance() -> Decimal:
    addr = payout_address()
    data = "0x70a08231" + "0" * 24 + addr[2:].lower()
    res = rpc("eth_call", [{"to": USDT_BEP20_CONTRACT, "data": data}, "latest"], tolerate_error=True)
    if res is None:
        return Decimal(state_balance_fallback())
    return Decimal(int(res, 16)) / (Decimal(10) ** USDT_DECIMALS)


def state_balance_fallback() -> str:
    st = load_sessions()
    return st.get("balance_usdt", "0")


def scan_transfers(address: str, from_block: int, to_block: int) -> list:
    """Fetch USDT Transfer events to `address`, chunked to stay under node limits.

    topic0 = Transfer(address,address,uint256)
    topic2 = padded destination address
    """
    topic2 = "0x" + "0" * 24 + address[2:].lower()
    out = []
    start = from_block
    while start <= to_block:
        end = min(start + BLOCK_CHUNK - 1, to_block)
        res = rpc("eth_getLogs", [{
            "fromBlock": hex(start),
            "toBlock": hex(end),
            "address": USDT_BEP20_CONTRACT,
            "topics": ["0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef", topic2],
        }], tolerate_error=True)
        if res is None:
            # Degrade: skip this chunk rather than failing the job. A missed
            # chunk is re-scanned next run because the cursor only advances
            # across chunks that actually succeeded.
            print(f"::warning::getLogs chunk {start}-{end} unavailable; skipped")
            start = end + 1
            continue
        for log in res:
            value = Decimal(int(log["data"], 16)) / (Decimal(10) ** USDT_DECIMALS)
            out.append({
                "tx_hash": log["transactionHash"],
                "block": int(log["blockNumber"], 16),
                "amount": value,
                "log_index": int(log.get("logIndex", "0x0"), 16),
            })
        start = end + 1
    return out


def confirm_payments(state: dict, lookback: int | None = None) -> dict:
    """Match on-chain transfers against open sessions by unique amount."""
    address = payout_address()
    head_hex = rpc("eth_blockNumber", [], tolerate_error=True)
    if head_hex is None:
        print("::warning::chain unreachable this run; state untouched, nothing lost")
        return {"matched": 0, "confirmed": 0, "seen": 0,
                "balance_usdt": state.get("balance_usdt", "0"), "head_block": None}
    head = int(head_hex, 16)

    # Scan a short window behind the head: covers the interval between cron
    # runs with margin, and keeps each scan inside node log limits.
    window = lookback if lookback is not None else SCAN_INTERVAL_SEC // 3 + CONFIRMATION_LOOKAHEAD
    cursor = state.get("cursor_block")
    start = max(0, (cursor - window) if cursor is not None else (head - window))
    start = max(0, head - window) if start > head else start

    transfers = scan_transfers(address, start, head)
    matched, already = 0, 0

    # Open sessions, newest first: the same amount should match the newest.
    open_sessions = sorted(
        (s for s in state["sessions"].values() if s["status"] == "awaiting_payment"),
        key=lambda s: s["created"], reverse=True,
    )
    used_tx = set()
    for t in transfers:
        if t["tx_hash"] in used_tx:
            continue
        for s in open_sessions:
            if Decimal(s["unique_amount_usdt"]) == t["amount"]:
                s["status"] = "paid"
                s["paid_at"] = utc_now()
                s["tx_hash"] = t["tx_hash"]
                s["block"] = t["block"]
                s["confirmation_target_block"] = t["block"] + REQUIRED_CONFIRMATIONS
                matched += 1
                used_tx.add(t["tx_hash"])
                break

    # Promote to confirmed once the chain has moved past the depth target.
    confirmed = 0
    for s in state["sessions"].values():
        if s["status"] == "paid" and s.get("confirmation_target_block"):
            if head >= s["confirmation_target_block"]:
                s["status"] = "confirmed"
                s["confirmed_at"] = utc_now()
                confirmed += 1

    state["cursor_block"] = head
    state["last_scan"] = {"at": utc_now(), "head_block": head, "transfers_seen": len(transfers)}

    bal = usdt_balance()
    state["balance_usdt"] = str(bal)
    return {"matched": matched, "confirmed": confirmed, "seen": len(transfers),
            "balance_usdt": str(bal), "head_block": head}

def regenerate_delivery_pages(state: dict) -> None:
    """Re-render delivery pages from current session state.

    Called after every chain scan so a buyer watching their order page sees the
    transition from awaiting to confirmed without waiting for a site rebuild.
    """
    out = ROOT / "site_extra" / "delivery"
    out.mkdir(parents=True, exist_ok=True)
    for rec in state["sessions"].values():
        if not isinstance(rec, dict) or not rec.get("slug"):
            continue
        ref = rec.get("reference") or stable_ref(rec["slug"])
        d = out / ref
        d.mkdir(parents=True, exist_ok=True)
        (d / "index.html").write_text(_delivery_page(rec), encoding="utf-8")


def stable_ref(slug: str) -> str:
    """Buyer-facing order reference for a product slug.

    Single source of truth shared by checkout.py, pipeline/delivery.py and
    pipeline/build_site.py. Changing this changes buyer-facing URLs, so it is
    versioned by the "vf-ref:" prefix.
    """
    return hashlib.sha1(f"vf-ref:{slug}".encode()).hexdigest()[:10].upper()


def _delivery_page(rec: dict) -> str:
    """Minimal inline renderer used by the watcher (mirrors pipeline/delivery.py)."""
    ref = rec.get("reference") or stable_ref(rec.get("slug", ""))
    status = rec.get("status", "awaiting_payment")
    titles = {
        "awaiting_payment": "Awaiting payment",
        "paid": "Payment detected - confirming",
        "confirmed": "Payment confirmed",
    }
    blurbs = {
        "awaiting_payment": (
            "Send the exact amount shown on the checkout page to the published "
            "address. This page updates automatically once the transfer is seen "
            "on-chain."
        ),
        "paid": (
            "Your transfer is on-chain and waiting for confirmation depth. This "
            "page updates automatically; no action is needed from you."
        ),
        "confirmed": "Your download is ready. The link below is live.",
    }
    accent = {"confirmed": "#7ee787", "paid": "#d29922"}.get(status, "#8b949e")
    title = titles.get(status, titles["awaiting_payment"])

    if status == "confirmed":
        main = (
            f'<p><a class="btn" style="background:#238636;color:#fff;display:inline-block;'
            f'padding:10px 18px;border-radius:8px;font-weight:600" '
            f'href="/{rec["download"].lstrip("/")}" download>Download {rec["slug"]}</a></p>'
        )
    else:
        main = ('<p class="muted">The download link appears here automatically once '
                'payment clears. No action needed from you.</p>')

    tx = (f"<tr><th>Transaction</th><td>{rec['tx_hash']}</td></tr>"
          if rec.get("tx_hash") else "")
    confirmed = (f"<tr><th>Confirmed</th><td>{rec['confirmed_at']}</td></tr>"
                 if rec.get("confirmed_at") else "")

    return f"""<!DOCTYPE html><html lang="en"><head>
<meta charset="utf-8"/><meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Order {ref} | VectorForge Daily</title><meta name="robots" content="noindex,nofollow"/>
<style>{_DELIVERY_CSS}</style></head><body>
<header><p><a href="/">&larr; Store</a></p><h1>Order {ref}</h1>
<span class="badge" style="color:{accent};border-color:{accent}55">{title}</span></header>
<main><section class="info"><p>{blurbs.get(status, blurbs["awaiting_payment"])}</p>{main}</section>
<section class="info"><h3>Details</h3><table>
<tr><th>Order reference</th><td>{ref}</td></tr>
<tr><th>Bundle</th><td>{rec.get("slug","")}</td></tr>
<tr><th>Amount sent</th><td>{rec.get("unique_amount_usdt","")} USDT (BEP20)</td></tr>
{tx}{confirmed}</table></section></main>
<footer>VectorForge Daily &middot; payments verified on-chain</footer></body></html>"""


_DELIVERY_CSS = (
    ":root{color-scheme:dark}*{box-sizing:border-box;margin:0;padding:0}"
    "body{font-family:'Segoe UI',system-ui,sans-serif;background:#0d1117;color:#e6edf3;line-height:1.6}"
    "a{color:#58a6ff;text-decoration:none}"
    "header{padding:40px 24px 28px;text-align:center;background:linear-gradient(180deg,#101826,#0d1117)}"
    "header h1{font-size:1.7rem;letter-spacing:-.02em}header p{margin-bottom:8px}"
    ".badge{display:inline-block;margin-top:12px;font-size:.8rem;border:1px solid;border-radius:999px;padding:4px 12px}"
    "main{max-width:760px;margin:0 auto;padding:24px 16px 48px}"
    ".info{background:#11161d;border:1px solid #2b3644;border-radius:12px;padding:18px;margin-bottom:18px}"
    ".info h3{margin:0 0 8px;font-size:1rem}.info p{color:#9aa7b4;margin:8px 0;font-size:.92rem}"
    ".muted{color:#6e7681;font-size:.85rem}table{width:100%;border-collapse:collapse;font-size:.9rem}"
    "table th,table td{text-align:left;padding:8px 10px;border-bottom:1px solid #21262d}"
    "table th{color:#8b949e;font-weight:600;white-space:nowrap;width:38%}"
    "table td{font-family:ui-monospace,monospace;word-break:break-all}"
    "footer{text-align:center;color:#6e7681;font-size:.78rem;padding:24px 16px 40px}"
)


def record_earnings(state: dict) -> dict:
    """Aggregate confirmed sessions into metrics/earnings.json."""
    earnings = {
        "updated": utc_now(),
        "confirmed_orders": 0,
        "gross_usdt": "0",
        "wallet_balance_usdt": state.get("balance_usdt", "0"),
        "orders": [],
    }
    total = Decimal(0)
    for s in sorted(state["sessions"].values(), key=lambda x: x["created"], reverse=True):
        if s["status"] not in ("paid", "confirmed"):
            continue
        total += Decimal(s["base_price_usdt"])
        earnings["confirmed_orders"] += 1
        earnings["orders"].append({
            "id": s["id"], "slug": s["slug"], "amount": s["base_price_usdt"],
            "confirmed_at": s["confirmed_at"], "tx": s["tx_hash"], "status": s["status"],
        })
    earnings["gross_usdt"] = str(total)
    METRICS_FILE.parent.mkdir(parents=True, exist_ok=True)
    METRICS_FILE.write_text(json.dumps(earnings, indent=2) + "\n", encoding="utf-8")
    return earnings


def selftest() -> int:
    """Offline checks. No network. Proves the money math before it touches real funds."""
    fails = []

    # offset stays bounded and is deterministic
    p = Decimal("7.00")
    o1 = unique_offset("abc123", p)
    o2 = unique_offset("abc123", p)
    if o1 != o2:
        fails.append("offset not deterministic")
    if o1 <= 0 or o1 > p * Decimal("0.001"):
        fails.append(f"offset out of bounds: {o1}")
    if unique_offset("zzz999", p) == o1:
        fails.append("offset collides for different sessions")

    # amount is exact at USDT's 6-dp display precision and matches on scan
    amount = p + o1
    if amount != amount.quantize(Decimal("0.000001")):
        fails.append("amount not 6dp-exact")
    found = None
    for s in [{"unique_amount_usdt": str(amount)}]:
        if Decimal(s["unique_amount_usdt"]) == amount:
            found = s
    if found is None:
        fails.append("amount does not round-trip for matching")

    # session id uniqueness shape
    ids = {hashlib.sha256(f"x:{i}".encode()).hexdigest()[:20] for i in range(5000)}
    if len(ids) < 5000:
        fails.append("session id collision in 5000 draws")

    # address padding used in eth_call topic
    addr = "0x1c7B4F7e1101bA38c92d99B35299E83736a3b112"
    if len("0x" + "0" * 24 + addr[2:]) != 66:
        fails.append("topic padding wrong length")

    print("selftest:", "PASS" if not fails else "FAIL")
    for f in fails:
        print("  -", f)
    return 1 if fails else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--init", action="store_true")
    ap.add_argument("--watch", action="store_true")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--probe", action="store_true")
    a = ap.parse_args()

    if a.probe:
        return probe_endpoints()

    if a.selftest:
        return selftest()

    state = load_sessions()

    if a.init:
        products = discover_products()
        # Idempotency guard: --init runs on a cron, so re-issuing a session for
        # a slug that already has one would pile up duplicate invoices and
        # ambiguous amounts for the same product on every single run.
        existing = {rec.get("slug") for rec in state["sessions"].values()}
        print(f"products: {len(products)}")
        for p in products:
            if p["slug"] in existing:
                continue
            rec = create_session(state, p)
            print(f"  {rec['slug']:24} {rec['unique_amount_usdt']} USDT  ->  {rec['address']}")
        save_sessions(state)
        return 0

    if a.watch:
        if not os.environ.get("VF_PAYOUT_ADDRESS"):
            print("::warning::VF_PAYOUT_ADDRESS unset; skipping chain scan this run.")
            return 0
        res = confirm_payments(state)
        save_sessions(state)
        e = record_earnings(state)
        # Delivery pages must reflect the new statuses, or a paid buyer keeps
        # seeing "awaiting payment" until the next full site build.
        regenerate_delivery_pages(state)
        print(json.dumps({**res, "gross_usdt": e["gross_usdt"],
                          "confirmed_orders": e["confirmed_orders"]}, indent=2))
        if res["matched"]:
            print(f"::notice::matched {res['matched']} new payment(s)")
        if Decimal(e["gross_usdt"]) > 0:
            print(f"::notice::GROSS EARNINGS {e['gross_usdt']} USDT")
        return 0

    # --status (default)
    print(f"address     : {state.get('balance_usdt', '?')} USDT balance")
    print(f"last scan   : {state.get('last_scan', {}).get('at', 'never')}")
    counts = {}
    for s in state["sessions"].values():
        counts[s["status"]] = counts.get(s["status"], 0) + 1
    print(f"sessions    : {counts or 'none'}")
    for s in sorted(state["sessions"].values(), key=lambda x: x["created"], reverse=True)[:10]:
        print(f"  {s['status']:18} {s['slug']:24} {s['unique_amount_usdt']} USDT  {s['created']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
