#!/usr/bin/env python3
"""
check_pinterest_status.py - Daily vendor response check (autonomous monitor).

PRINCIPLE: User involvement = zero. Agent runs this daily, checks if
Pinterest support has responded, alerts only if deadline passed or
action required.

Run via:
- GitHub Actions cron (free)
- Local cron (user)
- Manual: python3 ops/check_pinterest_status.py

Exit codes:
- 0: status logged, no action needed
- 1: action required (response received, escalation needed, etc.)
- 2: ticket overdue (no response within expected window)
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Load token from secrets (no hardcoding)
SECRETS_PATH = Path.home() / ".pi" / "secrets" / "pinterest.env"
if SECRETS_PATH.exists():
    for line in SECRETS_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

APP_ID = os.environ.get("PINTEREST_APP_ID", "unknown")
TRIAL_PENDING_DAYS_AGO = int(os.environ.get("PINTEREST_TRIAL_PENDING_DAYS", "14"))
TICKET_SUBMITTED = os.environ.get("PINTEREST_TICKET_SUBMITTED", "2026-09-06")
EXPECTED_RESPONSE_DAYS = int(os.environ.get("PINTEREST_EXPECTED_RESPONSE_DAYS", "5"))

# State file tracks last known status across runs
STATE_PATH = Path(__file__).resolve().parent / ".pinterest_status_state.json"


def load_state() -> dict:
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    return {"last_check": None, "last_status": None, "consecutive_no_change": 0}


def save_state(state: dict) -> None:
    STATE_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")


def probe_token_validity() -> str:
    """Hit a benign v5 endpoint to check if Pinterest now accepts the token
    (consumer type classification might have been resolved server-side)."""
    import urllib.request
    import urllib.error

    token = os.environ.get("PINTEREST_ACCESS_TOKEN")
    if not token:
        return "no_token"
    req = urllib.request.Request(
        "https://api.pinterest.com/v5/user_account",
        headers={"Authorization": f"Bearer {token}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return f"ok_{resp.status}"
    except urllib.error.HTTPError as e:
        return f"http_{e.code}"
    except Exception as e:  # noqa: BLE001
        return f"error_{type(e).__name__}"


def main() -> int:
    state = load_state()
    now = datetime.now(timezone.utc).isoformat()
    status = probe_token_validity()
    ticket_age_days = (
        datetime.now(timezone.utc).date()
        - datetime.strptime(TICKET_SUBMITTED, "%Y-%m-%d").date()
    ).days
    overdue = ticket_age_days > EXPECTED_RESPONSE_DAYS

    print(f"[{now}] Pinterest status check")
    print(f"  app_id: {APP_ID}")
    print(f"  ticket submitted: {TICKET_SUBMITTED} ({ticket_age_days} days ago)")
    print(f"  expected response: within {EXPECTED_RESPONSE_DAYS} business days")
    print(f"  API probe: {status}")
    print(f"  overdue: {overdue}")

    # Update state
    if status == state.get("last_status"):
        state["consecutive_no_change"] = state.get("consecutive_no_change", 0) + 1
    else:
        state["consecutive_no_change"] = 0
    state["last_check"] = now
    state["last_status"] = status
    save_state(state)

    if status.startswith("ok_"):
        # 🎉 Pinterest now accepts the token - trial approved!
        print()
        print("=" * 60)
        print("  🎉 PINTEREST TRIAL APPROVED!")
        print("  Token now accepted. Publish pipeline can be activated.")
        print("=" * 60)
        return 1  # signal: action available, alert user
    if overdue:
        print()
        print("=" * 60)
        print(f"  ⚠️  TICKET OVERDUE: {ticket_age_days} days, no response yet.")
        print(f"  Recommended: send follow-up or escalate via community thread.")
        print("=" * 60)
        return 2  # signal: action required
    print()
    print("Status normal. No action needed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
