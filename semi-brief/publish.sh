#!/bin/bash
# publish.sh — git add + commit + push
set -e

REPO_ROOT="$(dirname "$0")/.."
cd "$REPO_ROOT"

VERSION="$1"
COMMIT_MSG="semi-brief ${VERSION}"

git add -A
git diff --cached --quiet && echo "[publish] 无变更，跳过 commit" && exit 0

git commit -m "$COMMIT_MSG"
git push origin main
echo "[publish] 推送完成: $COMMIT_MSG"
