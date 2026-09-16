#!/usr/bin/env python3
"""
pinterest_oauth.py - Pinterest OAuth 2.0 PKCE helper (AGENT-PRINCIPLES friendly).

Handles the full authorize + token-exchange flow for app 1604703:
  1. Generates a PKCE code_verifier + code_challenge (saved to secrets)
  2. Prints an authorize URL (user clicks, approves, pastes callback URL)
  3. Exchanges the auth code for an access token (client_secret required)
  4. Stores the token + scopes into ~/.pi/secrets/pinterest.env
  5. Verifies which scopes the token actually has (read vs write)

Usage:
  python3 ops/pinterest_oauth.py authlink     # step 2: print authorize URL
  python3 ops/pinterest_oauth.py exchange CODE # step 3: exchange code
  python3 ops/pinterest_oauth.py check        # verify token + scopes

Secret env file: ~/.pi/secrets/pinterest.env
  PINTEREST_APP_ID=1604703
  PINTEREST_APP_SECRET=...            (from dashboard "Reset app secret")
  PINTEREST_PKCE_VERIFIER=...
  PINTEREST_PKCE_CHALLENGE=...
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets as pysecrets
import sys
import urllib.parse
import urllib.request
import urllib.error
from pathlib import Path

SECRETS_PATH = Path.home() / ".pi" / "secrets" / "pinterest.env"
APP_ID = "1604703"
REDIRECT_URI = "https://airdropia.github.io/auto-earn-engine/oauth-callback"
TOKEN_ENDPOINT = "https://api.pinterest.com/v5/oauth/token"
AUTH_ENDPOINT = "https://www.pinterest.com/oauth/"
SCOPES = [
    "boards:read", "boards:write", "pins:read", "pins:write",
    "user_accounts:read",
]


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


def save_env(env: dict) -> None:
    SECRETS_PATH.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    for k, v in env.items():
        if v:
            lines.append(f"{k}={v}")
    SECRETS_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def new_pkce() -> tuple[str, str]:
    verifier = base64.urlsafe_b64encode(pysecrets.token_bytes(43)).decode()[:64]
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode()).digest()
    ).decode().rstrip("=")
    return verifier, challenge


def build_auth_url(env: dict) -> str:
    verifier, challenge = new_pkce()
    env["PINTEREST_PKCE_VERIFIER"] = verifier
    env["PINTEREST_PKCE_CHALLENGE"] = challenge
    save_env(env)
    params = {
        "client_id": APP_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "state": "vfd-2026-09-06",
        "scope": ",".join(SCOPES),
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    return AUTH_ENDPOINT + "?" + urllib.parse.urlencode(params)


def exchange_code(env: dict, code: str) -> dict:
    data = urllib.parse.urlencode({
        "grant_type": "authorization_code",
        "code": code.strip(),
        "redirect_uri": REDIRECT_URI,
        "client_id": APP_ID,
        "client_secret": env.get("PINTEREST_APP_SECRET", ""),
        "code_verifier": env.get("PINTEREST_PKCE_VERIFIER", ""),
    }).encode()
    req = urllib.request.Request(TOKEN_ENDPOINT, data=data,
                                 headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        raise RuntimeError(f"HTTP {e.code}: {body[:300]}")


def check_token(env: dict) -> str:
    token = env.get("PINTEREST_ACCESS_TOKEN", "")
    if not token:
        return "no_token"
    req = urllib.request.Request(
        "https://api.pinterest.com/v5/user_account",
        headers={"Authorization": f"Bearer {token}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return f"ok_{resp.status}"
    except urllib.error.HTTPError as e:
        return f"http_{e.code}: {e.read().decode(errors='replace')[:120]}"


def _api_call(method: str, url: str, token: str, body: dict | None = None):
    """Small urllib wrapper used by the demo mode to show live API calls."""
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


def _extract_code(raw: str) -> str:
    """Extract the auth code from a pasted callback URL or raw code."""
    code = raw.strip()
    if "?" in code:
        parsed = urllib.parse.parse_qs(urllib.parse.urlparse(code).query)
        code = parsed.get("code", [""])[0]
    return code


def main(argv: list[str]) -> int:
    env = load_env()
    cmd = argv[1] if len(argv) > 1 else "help"
    if cmd == "authlink":
        print("=== NEW AUTHORIZE URL (click, approve, paste callback URL back) ===")
        print(build_auth_url(env))
        print()
        print("After approving, browser will go to:")
        print(f"  {REDIRECT_URI}?code=...&state=...")
        print("Copy the FULL address-bar URL and run:")
        print("  python3 ops/pinterest_oauth.py exchange <CODE>")
    elif cmd == "exchange":
        if len(argv) < 3:
            print("usage: python3 ops/pinterest_oauth.py exchange <AUTH_CODE>")
            return 1
        code = argv[2]
        if "?" in code:
            parsed = urllib.parse.parse_qs(urllib.parse.urlparse(code).query)
            code = parsed.get("code", [""])[0]
        print(f"exchanging code: {code[:8]}...")
        token_resp = exchange_code(env, code)
        token = token_resp.get("access_token", "")
        if not token:
            print(f"ERROR: no access_token in response: {json.dumps(token_resp)[:200]}")
            return 1
        env["PINTEREST_ACCESS_TOKEN"] = token
        env["PINTEREST_TOKEN_SCOPES"] = ",".join(token_resp.get("scope", "").split(","))
        env["PINTEREST_TOKEN_TYPE"] = token_resp.get("token_type", "")
        save_env(env)
        print(f"SUCCESS! token saved ({len(token)} chars)")
        print(f"scopes: {env['PINTEREST_TOKEN_SCOPES']}")
        print(f"check:   python3 ops/pinterest_oauth.py check")
        return 0
    elif cmd == "demo":
        """RECORDING-READY demo for Standard-access submission.

        After the user pastes the callback URL (auth code), this:
          1. exchanges code -> access token (proves OAuth flow)
          2. GET /user_account (proves auth works)
          3. POST /boards (proves write/integration works - trial
             allows board creation)
        Prints clear PASS/FAIL lines that look good on a screen recording.
        """
        if len(argv) < 3:
            print("usage: python3 ops/pinterest_oauth.py demo <CODE_OR_CALLBACK_URL>")
            return 1
        code = _extract_code(argv[2])
        print(f"[1/3] Exchanging auth code ({code[:8]}...)")
        token_resp = exchange_code(env, code)
        token = token_resp.get("access_token", "")
        if not token:
            print(f"FAIL: no access_token -> {json.dumps(token_resp)[:200]}")
            return 1
        env["PINTEREST_ACCESS_TOKEN"] = token
        env["PINTEREST_TOKEN_SCOPES"] = ",".join(token_resp.get("scope", "").split(","))
        save_env(env)
        print(f"  OK token obtained ({len(token)} chars)")
        print(f"  scopes: {env['PINTEREST_TOKEN_SCOPES']}")

        print("[2/3] GET /v5/user_account")
        status, data = _api_call("GET", "https://api.pinterest.com/v5/user_account", token)
        if status == 200:
            print(f"  OK HTTP {status} - business: {data.get('business_name', '?')}")
        else:
            print(f"  FAIL HTTP {status} - {json.dumps(data)[:150]}")
            return 1

        print("[3/3] POST /v5/boards (create demo board)")
        st2, d2 = _api_call("POST", "https://api.pinterest.com/v5/boards", token, {
            "name": "VectorForge API Demo",
            "description": "Live integration demo for Standard access review",
            "privacy": "PUBLIC",
        })
        if st2 in (200, 201):
            print(f"  OK HTTP {st2} - board id {d2.get('id')} created")
        else:
            print(f"  FAIL HTTP {st2} - {json.dumps(d2)[:150]}")
            return 1

        print()
        print("DEMO PASS - OAuth flow + live API integration verified.")
        print("This console output is what the Standard-access reviewer wants to see.")
        return 0
    elif cmd == "check":
        status = check_token(env)
        print(f"token status: {status}")
        print(f"scopes in env: {env.get('PINTEREST_TOKEN_SCOPES', '')}")
        return 0 if status.startswith("ok") else 1
    else:
        print(__doc__)
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))