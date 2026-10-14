#!/usr/bin/env bash
# check-repo-surface.sh — verify the discovery surface is still applied.
#
# Requires: GH_TOKEN, REPO.

set -uo pipefail

: "${GH_TOKEN:?GH_TOKEN not set}"
: "${REPO:?REPO not set}"

CURRENT=$(curl -sS -H "Authorization: token $GH_TOKEN" \
  -H "Accept: application/vnd.github+json" \
  "https://api.github.com/repos/$REPO/topics" | grep -o '"name"' | wc -l)

echo "topics live: $CURRENT"
if [ "$CURRENT" -lt 10 ]; then
  echo "::warning::topic count dropped to $CURRENT"
else
  echo "::notice::discovery surface healthy ($CURRENT topics)"
fi
