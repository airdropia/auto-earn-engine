#!/usr/bin/env bash
# Idempotent hook installer. Run from repo root:
#   bash .github/hooks/install-hooks.sh
# Copies .github/hooks/pre-push -> .git/hooks/pre-push (executable).
# Safe to re-run after every clone/pull.

set -euo pipefail
REPO_ROOT="$(git rev-parse --show-toplevel)"
SRC="$REPO_ROOT/.github/hooks/pre-push"
DST="$REPO_ROOT/.git/hooks/pre-push"

[[ -f "$SRC" ]] || { echo "source missing: $SRC" >&2; exit 1; }
cp "$SRC" "$DST"
chmod +x "$DST"
echo "installed: $DST"
echo "test: SKIP_STATE_GUARD=1 git push  (or just git push)"
