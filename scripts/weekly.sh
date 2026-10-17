#!/usr/bin/env bash
# Weekly ShopBot Index update: crawl -> rebuild -> commit -> push (GitHub Pages redeploys on push).
# Usage: scripts/weekly.sh            (crawl, build, commit, push)
#        scripts/weekly.sh --no-push  (crawl and build only; nothing leaves the machine)
set -euo pipefail
cd "$(dirname "$0")/.."
python3 scripts/crawl.py
python3 scripts/build.py
[ "${1:-}" = "--no-push" ] && { echo "Built dist/ (not committed, not pushed)."; exit 0; }
git add -A data dist
if git diff --cached --quiet; then echo "No changes to publish."; exit 0; fi
git -c user.name=cstath71 -c user.email=227154513+cstath71@users.noreply.github.com commit -q -m "Weekly crawl $(date +%F)"
git push -q origin main
echo "Pushed weekly crawl $(date +%F)."
