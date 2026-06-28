# Renovate — jellyrock org config

Single source of truth for how [Renovate](https://docs.renovatebot.com/)
works across the `jellyrock` GitHub org. Every repo that wants
dependency-update PRs extends `default.json` from here.

## Architecture

```text
jellyrock/.github
└── renovate/
    ├── default.json   ← org-wide policy
    └── README.md      ← this file
        │
        │ extended by
        ▼
jellyrock/<each-repo>/renovate.json
{
  "extends": ["github>jellyrock/.github//renovate/default"],
  "packageRules": [
    // repo-specific overrides only
  ]
}
```

The org default carries:

- **Sane base preset** — `config:recommended` + dashboard disabled.
- **`rebaseWhen: "conflicted"`** — Renovate rebases a PR branch only when
  it actually conflicts with the base, **not** every time `main` moves.
  With branch protection set to `strict: false` (branches need not be
  up-to-date to merge) there's no protection reason to keep every branch
  current, and `behind-base-branch` rebasing (the old `:rebaseStalePrs`)
  caused a "rebase storm": each merge force-rebased every open Renovate
  branch, re-triggering full CI on each and **orphaning any manual commit
  pushed onto those branches** (e.g. a hand-applied major-bump migration).
  Tradeoff: an automerge PR can land tested against slightly-stale `main`
  (Renovate flags this as not-recommended-with-automerge), but for
  independent dep bumps that risk is low and push-triggered CI on `main`
  catches it; when you DO want a fresh pre-merge integration test on a
  specific PR (a major, say), tick Renovate's **rebase checkbox** to force
  a one-off rebase + CI before merging. Do **not** revert to
  `behind-base-branch`/`:rebaseStalePrs` unless branch protection becomes
  `strict: true`.
- **`separateMinorPatch: true`** — distinct PRs per update type so
  patches can automerge while minors/majors wait for review.
- **Digest pinning** for GitHub Actions, Dockerfiles, and
  docker-compose files. Tag aliases (`v4`, `:latest`) silently
  re-point upstream; digests don't.
- **Exact-version pinning** for npm deps via
  `:pinAllExceptPeerDependencies` — `dependencies` and
  `devDependencies` are pinned to exact versions (`^0.39.0` →
  `0.39.0`); `peerDependencies` stay as ranges. The org has no
  published npm library (`shared-ui` is `private`, consumed at build
  time from GitHub), so nothing downstream depends on these ranges —
  exact pins give reproducible installs and clean, reviewable update
  diffs. Enabling this opens a one-time **"Pin dependencies"** PR per
  repo; that PR's update type is `pin`, which the automerge rule does
  **not** match, so a human reviews each one.
- **ESLint stack grouping** — `eslint` plus glob-matched `@eslint/*`,
  `eslint-config-*`, `eslint-plugin-*`. One coordinated PR instead of
  one-per-plugin, because eslint is version-coupled to its plugins.
  `prettier` and `jshint` are deliberately **not** in this group — they
  release independently, and grouping bundles their soak windows so a
  fresh release of one would gate the other (and the eslint group too).
- **GitHub Actions grouping, majors excepted** — routine minor/patch
  Action bumps are grouped into one PR to cut noise; **major** Action
  bumps get an individual PR each (`groupName: null` override) so each is
  reviewed on its own, since a major can change runner requirements or
  default behavior a green build won't surface.
- **Soak windows** (`minimumReleaseAge`) before automerge: patch/digest
  2 days, minor 5 days, major 7 days. The soak catches a yanked or
  hotfixed release before it lands unattended.
- **PRs are created immediately** (`internalChecksFilter: "none"`), even
  while soaking — so every update is visible and a human can manually
  merge early (e.g. a hotfix). The soak only gates **automerge**.
- **`platformAutomerge: false`** — load-bearing for the soak. Renovate's
  soak is a non-required `renovate/stability-days` status check. With
  GitHub's *platform* automerge (`platformAutomerge: true`, the Renovate
  default), GitHub merges as soon as the *required* checks pass and
  ignores that non-required check — so the soak gets **bypassed** (this
  is how a `minimumReleaseAge` PR can merge minutes after CI, not after
  the window). Setting `platformAutomerge: false` makes Renovate do its
  own merge, which *does* honour `minimumReleaseAge`. Keeping
  `stability-days` non-required is deliberate: it lets a human still
  merge a hotfix early, while Renovate's own automerge waits out the
  soak. **Do not set this back to `true`** unless you also make
  `renovate/stability-days` a required status check (which would also
  block manual early-merge).
- **Automerge** on green CI after soak for **patch + digest** and
  **minor**. **Majors never automerge** — always human-reviewed (see the
  **Major-bump SOP** below). Minor automerge raises the CI bar; see the
  **Automerge contract** below.
- **`lockFileMaintenance` enabled** (automerge, monthly). This exists
  *because* of `minimumReleaseAge`: for npm, Renovate passes
  `--before=<now − soak>` so transitive deps are age-protected too. When
  the existing lockfile already holds packages newer than that cutoff,
  npm errors, Renovate falls back to no `--before`, and logs a noisy
  "npm `--before` could not be enforced …" artifact notice on the PR.
  Monthly lock-file maintenance regenerates the lockfile from scratch
  *with* `--before`, keeping the base lockfile clean so that notice
  doesn't recur on regular dependency PRs. **Don't disable it** without
  also removing `minimumReleaseAge`, or the notices come back.

Things that belong **per-repo**, not in the default:

- Language-/framework-specific groupings (BrighterScript stack in
  `jellyrock/jellyrock`, the BrightScript Shiki grammar tracker in
  `jellyrock/docs`, Ansible image versions in `jellyrock/infra`).
- `prConcurrentLimit` / `prHourlyLimit` overrides — leave the
  preset's defaults unless the repo has a unique scale (e.g.
  `jellyrock/jellyrock` removes the caps because it has ~50 deps).
- Custom managers for non-standard manifests (the
  `customManagers` regex in `infra` that scans
  `group_vars/all.yml`, ditto in `docs` for the vendored grammar's
  `.version-info` marker).

## Private repos on GitHub Free

GitHub's auto-merge feature is **not available on private repositories
under the Free plan** (`github.com/jellyrock` is currently Free). The
GitHub API silently rejects `allow_auto_merge: true` PATCH calls on
private repos at this tier without returning an error.

Practical impact today:

| Repo | Visibility | Patch automerge |
| --- | --- | --- |
| `jellyrock`, `api-docs`, `docs`, `jellyrock.app`, `shared-ui`, `github-runner` | public | Works |
| `infra` | private | **Manual merge required** |

Patch PRs Renovate opens against `infra` will sit open with green CI
until a human merges them. Renovate's `automerge: true` setting is
harmless — the platform just doesn't act on it. Nothing breaks; the
convenience is just unavailable on that one repo.

Three ways to unlock auto-merge on the private repos:

1. **Make the repo public.** Strongest fix; no recurring cost. Audit
   the repo first for secrets-in-history and topology exposure.
2. **Upgrade the org to GitHub Team** ($4/user/month). Unlocks
   auto-merge + other features (Codespaces hours, more Actions minutes,
   audit log). Billing decision.
3. **Status quo + manual merge** for those two repos. Zero cost,
   minor friction. The patch automerge rule remains in the org default;
   it just no-ops on the private repos.

## Automerge contract (patch + digest + minor)

The org default automerges **patch**, **digest-pin**, and **minor**
updates once CI passes **and** the release has soaked
(`minimumReleaseAge`: patch/digest 2 days, minor 5 days) — long enough
for the ecosystem to surface a yanked or hotfixed release before it
lands unattended, short enough not to delay routine fixes. (Digest
updates refresh the upstream image's content hash without changing its
tag — same code, freshly-rebuilt base layer for CVEs — so they're
inherently no-op-risk.) **A repo extending this default must satisfy
these conditions** or automerge will silently land unreviewed code:

1. **PR-triggered CI must exist.** A workflow on `pull_request` (not
   just `workflow_dispatch` or `push`). Renovate's PRs run it; a
   missing workflow means no gate — Renovate would merge with no
   signal. Every existing jellyrock repo satisfies this today.
2. **CI must exercise the dependency surface.** "Build + lint" is the
   floor for patch/digest. **Minor automerge raises the bar:** a
   breaking minor can pass a build but fail at runtime, so a repo that
   automerges minors should have CI that exercises runtime behavior
   (unit/integration/smoke tests), not just build+lint. The stronger
   the CI, the higher the confidence.
3. **If a repo can't meet the bar, override per-repo.** Disable minor
   automerge (keep patch) when CI is build+lint only:
   ```jsonc
   {
     "extends": ["github>jellyrock/.github//renovate/default"],
     "packageRules": [
       {
         "description": "CI is build+lint only — minors need human review",
         "matchUpdateTypes": ["minor"],
         "automerge": false
       }
     ]
   }
   ```
   Or disable all automerge (patch + minor) for a repo with no real CI:
   ```jsonc
   {
     "matchUpdateTypes": ["patch", "digest", "minor"],
     "automerge": false
   }
   ```

## Major-bump SOP

Majors never automerge. When a major PR appears, before merging:

1. **Read the upstream changelog / migration guide** for the version
   range (the PR body links the release notes).
2. **Pull the branch and run the repo's full gate locally** — build +
   lint + the complete test suite (on JellyRock that includes the
   on-device BS unit tests and the RTA functional pass, which CI's
   PR-triggered run may not cover end-to-end).
3. **Grep for breaking-API usage** the changelog flags; migrate code in
   the same PR.
4. **For runtime deps bundled into the app** (e.g. the Roku BS libs),
   verify on a real device, not just a green build.
5. Merge only when the gate is green and any required migration is in
   the PR.

Repos may wrap this in a local script or skill so the steps run the same
way every time, rather than doing the checklist by hand.

## Adding a new repo

1. Confirm the repo has PR-triggered CI that exercises the
   dependency surface (see the contract above).
2. Add a one-line `renovate.json` at the repo root:
   ```json
   {
     "$schema": "https://docs.renovatebot.com/renovate-schema.json",
     "extends": ["github>jellyrock/.github//renovate/default"]
   }
   ```
3. Install (or invite) the Renovate GitHub App on the repo. Renovate
   picks the config up on its next scan.
4. The first run usually opens 5-20 PRs as it pin-digests every
   existing reference and discovers stale dependencies. Review and
   merge in waves; patch automerge handles the long tail.

## Adding repo-specific rules

Anything that's true for one repo but not the org belongs in that
repo's `renovate.json`. Examples already in use:

- [`jellyrock/jellyrock`](https://github.com/jellyrock/jellyrock/blob/main/renovate.json)
  — BrighterScript/Roku stack grouping, `prConcurrentLimit: 0`.
- [`jellyrock/infra`](https://github.com/jellyrock/infra/blob/main/renovate.json)
  — `customManagers` regex for Ansible `group_vars/all.yml` image
  versions; Tier-1/2 holdback rules from
  [`docs/version-policy.md`](https://github.com/jellyrock/infra/blob/main/docs/version-policy.md).
- [`jellyrock/docs`](https://github.com/jellyrock/docs/blob/main/renovate.json)
  — `customManagers` regex that tracks the vendored BrightScript
  TextMate grammar's upstream release tag.

Don't paste a rule into the org default unless **every** jellyrock
repo benefits. A rule that only matches packages in one repo just
adds noise to the others' Renovate config evaluation.

## Modifying this default

Edits here cascade to every consuming repo on Renovate's next scan
(usually within a few hours).

- Test changes locally with [Renovate's dry-run mode](https://docs.renovatebot.com/self-hosted-configuration/#dryrun)
  on at least one consuming repo before merging.
- Roll out cautiously when adding new `packageRules` — a misconfigured
  `matchPackageNames` or `matchManagers` can open hundreds of PRs at
  once. `prConcurrentLimit` on consuming repos provides a
  safety net.
- The patch-automerge rule is the highest-stakes setting in this file.
  Toggle with care; an unintentional automerge of a malicious upstream
  patch would land directly on `main` of any repo with the contract
  satisfied.

## See also

- [Renovate docs — Shareable Config Presets](https://docs.renovatebot.com/config-presets/)
- [Renovate docs — `extends`](https://docs.renovatebot.com/configuration-options/#extends)
- [Renovate docs — `automerge`](https://docs.renovatebot.com/configuration-options/#automerge)