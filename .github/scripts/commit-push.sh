#!/usr/bin/env bash
# commit-push.sh — idempotent, conflict-tolerant commit+push for bot jobs.
#
# Why this exists: many workflows commit to main on independent schedules, so
# a plain `git push` races against whichever bot pushed a few seconds earlier
# and fails with "fetch first". That turned scheduled jobs red for no reason.
#
# Usage:  bash .github/scripts/commit-push.sh "<commit message>" [path ...]
#
# Behavior:
#   - no changes      -> exits 0 quietly
#   - push conflict   -> pull --rebase, re-stage, retry once
#   - still conflict  -> exits 0 with a warning (never fails the whole job)
#
# Always exits 0 unless something is genuinely wrong, so a cosmetic commit
# problem can never take down the pipeline that ran it.

set -uo pipefail

MSG="${1:-chore: automated update}"
shift || true
PATHS=("$@")

if [ "${#PATHS[@]}" -eq 0 ]; then
  PATHS=(".")
fi

git config user.name "github-actions[bot]"
git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
git config --global --add safe.directory "$GITHUB_WORKSPACE" 2>/dev/null || true

git add -A -- "${PATHS[@]}" 2>/dev/null || git add -A

if git diff --staged --quiet; then
  echo "no changes to commit"
  exit 0
fi

git commit -q -m "$MSG" || { echo "commit failed"; exit 0; }

# Bot commits must never retrigger other workflows. Without this marker a
# commit that touches a workflow path causes a fresh run, which commits again,
# which triggers another run: a loop that turns scheduled jobs red.
# Any commit message containing "skip ci" is ignored by GitHub Actions.
case "$MSG" in
  *"skip ci"*) ;;
  *) git commit -q --amend --no-edit -m "$MSG [skip ci]" 2>/dev/null || true ;;
esac

attempt_push() {
  # Never force: rebase onto whatever landed, then re-apply our commit.
  if git push origin HEAD:$(git rev-parse --abbrev-ref HEAD) 2>/dev/null; then
    echo "push ok"
    return 0
  fi

  echo "push conflicted; rebasing onto origin"
  git pull --rebase --autostash origin HEAD 2>&1 | tail -3 || true

  # The rebase may have already replayed our commit; re-stage in case it did not.
  if git diff --staged --quiet && git log -1 --format=%s | grep -qi "^$MSG"; then
    :
  else
    git add -A -- "${PATHS[@]}" 2>/dev/null || true
    git diff --staged --quiet || git commit -q -m "$MSG" || true
  fi

  if git push origin HEAD:$(git rev-parse --abbrev-ref HEAD) 2>/dev/null; then
    echo "push ok after rebase"
    return 0
  fi
  echo "::warning::could not push after rebase; leaving it for the next run"
  return 0
}

attempt_push
exit 0
