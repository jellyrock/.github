#!/usr/bin/env bash
# Create or update the Renovate update-type labels (renovate/default.json) in every
# non-archived jellyrock repo, so they look and read the same everywhere. Safe to re-run:
# existing labels are updated in place, PRs keep their labels.
#
# Usage: scripts/sync-labels.sh [--dry-run]
set -euo pipefail

org=jellyrock
dry_run=false
[[ ${1:-} == --dry-run ]] && dry_run=true

# name|colour|description (GitHub caps descriptions at 100 characters)
labels=(
  'major|B60205|Major update: never automerges; follow the major-bump SOP in renovate/README.md'
  'minor|FBCA04|Minor update: automerges after a 5-day soak once CI is green'
  'patch|0E8A16|Patch update: automerges after a 2-day soak once CI is green'
  'digest|C5DEF5|Same version, new image/Action digest: automerges after a 2-day soak'
  'pin|D4C5F9|One-time pin to an exact version or digest: needs a human review'
  'lockfile|BFD4F2|Monthly lock file refresh: automerges once CI is green'
)

for repo in $(gh repo list "$org" --limit 100 --no-archived --json name --jq '.[].name' | sort); do
  for entry in "${labels[@]}"; do
    IFS='|' read -r name color description <<<"$entry"
    if $dry_run; then
      echo "would set $org/$repo: $name"
    else
      gh label create "$name" -R "$org/$repo" --color "$color" --description "$description" --force >/dev/null
      echo "set $org/$repo: $name"
    fi
  done
done
