# toolbox

A collection of helper scripts for everyday automation tasks.

## Current focus

- **GitHub cloning**: clone all repositories from a GitHub **owner** (user or org) into a target directory.
- **Git pre-commit in container**: run `pre-commit` in `ee-wunder-devtools-ubi9` with sane Podman/Docker defaults.

## Repo layout (v0)

```text
toolbox/
  README.md
  LICENSE
  scripts/
    github/
      clone-all.sh
    git/
      pre-commit-devtools
```

## Requirements

- `git`
- `gh` (GitHub CLI)
- `podman` or `docker` (for `pre-commit-devtools`)

Optional (recommended):
- `ShellCheck` (for linting)

## Setup

1) Install GitHub CLI (`gh`) and authenticate:

```bash
gh --version
gh auth login
```

## Usage

Clone all repositories from a GitHub owner (user or org).

```bash
./scripts/github/clone-all.sh <owner> [options]
```

### Examples

Clone all repos from an org into `~/sources`:

```bash
./scripts/github/clone-all.sh lightning-it --ssh --target-dir ~/sources
```

Run `pre-commit` in a local devtools container (works with GitHub, GitLab, or any Git-hosted repo):

```bash
# build the image (from toolbox repo)
podman build --format docker -t localhost/ee-wunder-devtools-ubi9:local ../container-ee-wunder-devtools-ubi9

# run in a target repo (example: modulix/ansible)
cd ../modulix/ansible
../../toolbox/scripts/git/pre-commit-devtools
```

Pass custom args:

```bash
../../toolbox/scripts/git/pre-commit-devtools run --files README.md
```

Behavior note:
- If no Docker/Podman API socket is available, Docker-based hooks are skipped automatically.
- Set `DEVTOOLS_SKIP_DOCKER_HOOKS=false` to enforce them (they will fail without a socket).

### Podman socket (for Docker-based hooks)

Some hooks use `docker ...` commands (`hadolint-docker`, `container-build`, `container-smoke`, etc.).
With rootless Podman, enable the user socket first:

```bash
systemctl --user enable --now podman.socket
systemctl --user status podman.socket
ls -l /run/user/$UID/podman/podman.sock
```

Then run:

```bash
DEVTOOLS_SKIP_DOCKER_HOOKS=false ../../toolbox/scripts/git/pre-commit-devtools
```

Strict mode expectations:
- If Docker-based hooks run, failures are now usually real lint/build findings (not socket permissions).
- Typical examples:
  - `hadolint` warnings from Dockerfile patterns.
  - `actionlint` findings in `.github/workflows/*.yml`.
- Fix the reported file and rerun the same command.

Troubleshooting:
- `permission denied while trying to connect to the docker API`:
  - ensure you use the latest `pre-commit-devtools` script (it mounts the socket with Podman `:U`)
  - verify socket path exists for your user: `/run/user/$UID/podman/podman.sock`
  - run as your normal user, not `root`
- `Failed to connect to bus: No medium found` while enabling socket:
  - you are likely in the wrong user context (often `root` shell)
  - switch back to your login user and run `systemctl --user ...` there
- repo files suddenly owned by subordinate UIDs (for example `165536+`):
  - restore ownership with rootless user-namespace mapping:
    `podman unshare chown -R 0:0 <repo-path>`

## Extending this repo

Add new scripts under `scripts/<domain>/...`, for example:

```text
scripts/
  github/
  git/
  net/
  fs/
```

Keep scripts small, single-purpose, and add `--help` with examples.

---
