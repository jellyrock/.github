#!/usr/bin/env bash
# Audit how every non-archived jellyrock repo is set up for dependency updates, against the
# org contract in renovate/README.md. Read-only: it only calls the GitHub API (gh, logged in
# with read access to the org, private repos included).
#
# Usage: scripts/audit-repos.sh [--markdown]
#
# Columns:
#   preset        renovate.json extends github>jellyrock/.github//renovate/default
#   pr-ci         some workflow runs on pull_request
#   ci-can-fail   no build/test/check command in a workflow is masked with `|| true`
#   protected     main has branch protection
#   required      required status checks on main
#   soak-req      renovate/stability-days is required (README: it must not be)
#   automerge     GitHub can merge on Renovate's behalf (private repos on Free cannot)
#   ui-pin        a shared-ui release pin in the code is tracked by renovate.json
#   open-deps     open Renovate PRs
set -uo pipefail

org=jellyrock
markdown=false
[[ ${1:-} == --markdown ]] && markdown=true

raw() { gh api "repos/$org/$1" -H 'Accept: application/vnd.github.raw' 2>/dev/null; }

header=(repo visibility preset pr-ci ci-can-fail protected required soak-req automerge ui-pin open-deps)
rows=()
for repo in $(gh repo list "$org" --limit 100 --no-archived --json name --jq '.[].name' | sort); do
  visibility=$(gh api "repos/$org/$repo" --jq '.visibility')

  if renovate=$(raw "$repo/contents/renovate.json"); then
    preset=$(grep -q 'jellyrock/.github//renovate/default' <<<"$renovate" && echo yes || echo NO)
  else
    renovate=''
    preset='NO (no renovate.json)'
  fi

  pr_ci=no
  masked=()
  if workflows=$(gh api "repos/$org/$repo/contents/.github/workflows" --jq '.[].name' 2>/dev/null); then
    for wf in $workflows; do
      body=$(raw "$repo/contents/.github/workflows/$wf") || continue
      grep -qE '^\s*pull_request(_target)?\s*:|^on:.*pull_request' <<<"$body" && pr_ci=yes
      if grep -qE '(npm (run )?(build|test|check)|make [a-z-]+|pytest|go test|cargo test|dotnet (build|test))[^#]*\|\|\s*true' <<<"$body"; then
        masked+=("$wf")
      fi
    done
  fi
  can_fail=yes
  ((${#masked[@]})) && can_fail="NO (${masked[*]})"

  if protection=$(gh api "repos/$org/$repo/branches/main/protection" 2>/dev/null); then
    protected=yes
    required=$(jq -r '[.required_status_checks.contexts // [] | .[]] | join(", ") | if . == "" then "none" else . end' <<<"$protection")
  elif [[ $visibility == private ]]; then
    protected='n/a (private on Free)'
    required=n/a
  else
    protected=NO
    required=none
  fi
  soak_req=$(grep -q 'renovate/stability-days' <<<"$required" && echo YES || echo no)

  automerge=yes
  [[ $visibility == private ]] && automerge='NO (private on Free)'

  # Sites consume shared-ui through a fetch-shared-ui script that pins a release tag.
  ui_pin='-'
  if gh api "repos/$org/$repo/git/trees/HEAD?recursive=1" --jq '.tree[].path' 2>/dev/null |
    grep -qE '(^|/)fetch-shared-ui\.[a-z]+$'; then
    ui_pin=$(grep -q 'shared-ui' <<<"$renovate" && echo tracked || echo 'NOT tracked')
  fi

  open_deps=$(gh pr list -R "$org/$repo" --author app/renovate --state open --json number --jq length 2>/dev/null || echo '?')

  rows+=("$repo"$'\t'"$visibility"$'\t'"$preset"$'\t'"$pr_ci"$'\t'"$can_fail"$'\t'"$protected"$'\t'"$required"$'\t'"$soak_req"$'\t'"$automerge"$'\t'"$ui_pin"$'\t'"$open_deps")
done

if $markdown; then
  (IFS='|'; echo "| ${header[*]} |" | sed 's/|/ | /g; s/^ //; s/ $//')
  printf '|%s\n' "$(printf -- '---|%.0s' "${header[@]}")"
  for row in "${rows[@]}"; do echo "| ${row//$'\t'/ | } |"; done
else
  { (IFS=$'\t'; echo "${header[*]}"); printf '%s\n' "${rows[@]}"; } | column -t -s $'\t'
fi
