#!/usr/bin/env bash
# apply-repo-surface.sh — keep the repository's discovery surface applied.
#
# GitHub topics and the repo description are how people (and GitHub's own
# search) find this project without ad spend. Treating them as deployable
# config means they survive being edited away by accident.
#
# Requires: GH_TOKEN, REPO.

set -uo pipefail

TOPICS='["svg","shadow-box","mandala","cricut","silhouette","laser-cutting","layered-svg","digital-products","generative-art","usdt","crypto-payments","paper-craft","cut-files","design-automation"]'
DESCRIPTION="Original layered SVG shadow-box mandalas for Cricut, Silhouette and Glowforge. Automated design pipeline, USDT checkout, no account needed."

: "${GH_TOKEN:?GH_TOKEN not set}"
: "${REPO:?REPO not set}"

curl -sS -X PUT \
  -H "Authorization: token $GH_TOKEN" \
  -H "Accept: application/vnd.github+json" \
  "https://api.github.com/repos/$REPO/topics" \
  -d "$TOPICS" >/dev/null

curl -sS -X PATCH \
  -H "Authorization: token $GH_TOKEN" \
  -H "Accept: application/vnd.github+json" \
  "https://api.github.com/repos/$REPO" \
  -d "$(printf '{"description":"%s"}' "$DESCRIPTION")" >/dev/null

echo "topics + description applied"
