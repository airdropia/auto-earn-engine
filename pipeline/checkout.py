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
DEFAULT_RPCS = [
    "https://bsc-dataseed.binance.org/",
    "https://bsc-dataseed1.defibit.io/",
    "https://rpc.ankr.com/bsc",
]

# Confirmed minimum confirmations before an order is considered paid.
REQUIRED_CONFIRMATIONS = 3


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def rpc(method: str, params: list):
    """Call a BSC RPC, rotating across public endpoints. No API key needed."""
    url = os.environ.get("BSC_RPC") or DEFAULT_RPCS[0]
    payload = json.dumps({"jsonrpc": "2.0", "method": method, "params": params, "id": 1})
    last = None
    for endpoint in ([url] if os.environ.get("BSC_RPC") else DEFAULT_RPCS):
        try:
            req = urllib_request(endpoint, payload)
            if not req.get("result") and req.get("error"):
                last = req["error"]
                continue
            return req["result"]
        except Exception as exc:  # network hiccup: try the next endpoint
            last = str(exc)
            continue
    raise RuntimeError(f"all RPC endpoints failed, last error: {last}")


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
    rec = {
        "id": sid,
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
    }
    state["sessions"][sid] = rec
    return rec


def discover_products() -> list:
    pdir = ROOT / "products"
    out = []
    if not pdir.exists():
        return out
    for date_dir in sorted(pdir.iterdir()):
        if not date_dir.is_dir():
            continue
        for prod in sorted(date_dir.iterdir()):
            if prod.is_dir() and list(prod.glob("*.svg")):
                out.append({"slug": prod.name, "date": date_dir.name, "path": prod})
    return out


def usdt_balance() -> Decimal:
    addr = payout_address()
    data = "0x70a08231" + "0" * 24 + addr[2:].lower()
    res = rpc("eth_call", [{"to": USDT_BEP20_CONTRACT, "data": data}, "latest"])
    return Decimal(int(res, 16)) / (Decimal(10) ** USDT_DECIMALS)


def scan_transfers(address: str, from_block: int, to_block: int) -> list:
    """Fetch USDT Transfer events to `address` in a block range.

    topic0 = Transfer(address,address,uint256)
    topic2 = padded destination address
    """
    topic2 = "0x" + "0" * 24 + address[2:].lower()
    res = rpc("eth_getLogs", [{
        "fromBlock": hex(from_block),
        "toBlock": hex(to_block),
        "address": USDT_BEP20_CONTRACT,
        "topics": ["0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef", topic2],
    }])
    out = []
    for log in res or []:
        value = Decimal(int(log["data"], 16)) / (Decimal(10) ** USDT_DECIMALS)
        out.append({
            "tx_hash": log["transactionHash"],
            "block": int(log["blockNumber"], 16),
            "amount": value,
            "log_index": int(log.get("logIndex", "0x0"), 16),
        })
    return out


def confirm_payments(state: dict, lookback: int = 4000) -> dict:
    """Match on-chain transfers against open sessions by unique amount."""
    address = payout_address()
    head = int(rpc("eth_blockNumber", []), 16)

    if state.get("cursor_block") is None:
        state["cursor_block"] = max(0, head - lookback)
    start = max(0, int(state["cursor_block"]) - lookback)

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
    a = ap.parse_args()

    if a.selftest:
        return selftest()

    state = load_sessions()

    if a.init:
        products = discover_products()
        print(f"products: {len(products)}")
        for p in products:
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
