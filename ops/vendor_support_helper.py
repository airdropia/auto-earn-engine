#!/usr/bin/env python3
"""
vendor_support_helper.py - Reusable vendor-support-form pre-filler.

PRINCIPLE: User ki manual involvement = zero (except final 1-click submit
on the vendor's page after agent has pre-filled everything).

Usage:
    python3 ops/vendor_support_helper.py pinterest
    # reads the pre-configured ticket text + opens browser-ready data

    python3 ops/vendor_support_helper.py --print pinterest
    # prints the pre-filled text for direct copy-paste

The actual browser automation (clicking Submit) is left to the user
because:
- Most vendor support forms are behind logins (no public API)
- Headless submission requires Playwright/Selenium (~hundreds of MB
  deps - violates $0 budget and Windows-lightweight rules)
- 1-click is acceptable per AGENT-PRINCIPLES.md Sec 2.1 fallback
"""
from __future__ import annotations

import sys
from pathlib import Path

OPS_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = OPS_DIR / "support_templates"


def load_template(name: str) -> dict:
    """Load a vendor's support template by name (e.g. 'pinterest')."""
    path = TEMPLATES_DIR / f"{name}.txt"
    if not path.exists():
        raise FileNotFoundError(f"No template at {path}")
    return {"name": name, "text": path.read_text(encoding="utf-8")}


def load_secrets(name: str) -> dict:
    """Load the secrets for a vendor from ~/.pi/secrets/<name>.env."""
    secrets_path = Path.home() / ".pi" / "secrets" / f"{name}.env"
    if not secrets_path.exists():
        return {}
    env = {}
    for line in secrets_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env


def render_template(template: dict, secrets: dict) -> str:
    """Substitute {{placeholders}} in template with values from secrets."""
    out = template["text"]
    for k, v in secrets.items():
        out = out.replace("{{" + k + "}}", v)
    return out


def main(argv: list[str]) -> int:
    if len(argv) < 2 or argv[1] not in ("pinterest", "--print", "-h", "--help"):
        print(__doc__)
        return 1

    name = argv[1]
    template = load_template(name)
    secrets = load_secrets(name)
    rendered = render_template(template, secrets)

    print(f"=== VENDOR: {name} ===")
    print(f"=== SECRETS LOADED: {list(secrets.keys())} ===")
    print()
    print(rendered)
    print()
    print("=== NEXT STEPS ===")
    print(f"1. Open the vendor's help center in your browser (already logged in)")
    print(f"2. Open the form (pre-filled text is above)")
    print(f"3. Click Submit (1 click - acceptable per AGENT-PRINCIPLES.md Sec 2.1)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
