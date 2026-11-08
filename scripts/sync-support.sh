#!/usr/bin/env bash
# Copy snippets/support-full.md into profile/README.md, between the support markers.
#
#   scripts/sync-support.sh           rewrite the README's section
#   scripts/sync-support.sh --check   exit 1 if the section differs (CI)
#
# The "Support JellyRock" block comes in two lengths, both in snippets/:
#   support-full.md  the long one: this README, and pasted by hand into the
#                    GitHub Sponsors and Buy Me a Coffee profiles
#   support.md       the short one: jellyrock/jellyrock's release workflow
#                    reads it from main for every release's notes, so keep
#                    its path and its "## Support JellyRock" heading stable
# Only support-full.md is built into anything here, so only it is checked.
set -euo pipefail

cd "$(dirname "$0")/.."
snippet=snippets/support-full.md
readme=profile/README.md
start='<!-- support:start (built from snippets/support-full.md by scripts/sync-support.sh; edit that file) -->'
end='<!-- support:end -->'

head -n1 "$snippet" | grep -qx '## Support JellyRock' || {
	echo "::error file=$snippet::must start with the line '## Support JellyRock'" >&2
	exit 1
}
for m in "$start" "$end"; do
	[ "$(grep -cxF -- "$m" "$readme")" = 1 ] || {
		echo "::error file=$readme::needs exactly one line: $m" >&2
		exit 1
	}
done

built=$(awk -v s="$start" -v e="$end" -v f="$snippet" '
	$0 == s { print; print ""; while ((getline l < f) > 0) print l; print ""; skip = 1; next }
	$0 == e { skip = 0 }
	!skip
' "$readme")

if [ "${1:-}" = --check ]; then
	if [ "$built" != "$(cat "$readme")" ]; then
		echo "::error file=$readme::support section differs from $snippet; run scripts/sync-support.sh" >&2
		diff <(cat "$readme") <(printf '%s\n' "$built") || true
		exit 1
	fi
	echo "support section matches $snippet"
else
	printf '%s\n' "$built" > "$readme"
fi
