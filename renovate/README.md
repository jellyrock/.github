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

- **Sane base preset** — `config:recommended` + dashboard disabled +
  stale-PR rebasing.
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
- **JS lint stack grouping** — `eslint`, `prettier`, `jshint`, plus
  glob-matched `@eslint/*`, `eslint-config-*`, `eslint-plugin-*`.
  One coordinated PR instead of one-per-plugin.
- **Weekly Monday batch** for minor + major. Patches don't wait.
- **Patch automerge** on green CI. See **Patch automerge contract**
  below.

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

## Patch + digest automerge contract

The org default automerges patch-level **and digest-pin** updates
once CI passes. (Digest updates refresh the upstream image's content
hash without changing its tag — same code, freshly-rebuilt base
layer for CVEs — so they're inherently no-op-risk.) **A repo
extending this default must satisfy these conditions** or automerge
will silently land unreviewed code:

1. **PR-triggered CI must exist.** A workflow on `pull_request` (not
   just `workflow_dispatch` or `push`). Renovate's PRs run it; a
   missing workflow means no gate — Renovate would merge with no
   signal. Every existing jellyrock repo satisfies this today.
2. **CI must exercise the dependency surface.** "Build + lint" is
   the baseline. "Build + lint + unit tests" is better. The
   stronger the CI, the higher the confidence in patches. The
   contract is intentionally fuzzy — repos with high test coverage
   inherit higher safety than repos with just a build check.
3. **If a repo can't meet (1) or (2), override per-repo:**
   ```jsonc
   {
     "extends": ["github>jellyrock/.github//renovate/default"],
     "packageRules": [
       {
         "description": "This repo doesn't have CI strong enough for blind patch automerge",
         "matchUpdateTypes": ["patch", "digest"],
         "automerge": false
       }
     ]
   }
   ```

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