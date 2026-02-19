# ModuLix helper scripts

Helper scripts for day-to-day automation in this repository.

## Layout

```text
scripts/
  github/clone-all.sh
  git/pre-commit-devtools
  wunder-devtools-ee.sh
  test-ansible.sh
ansible/scripts/
  ansible-nav
  install-local-collections
```

## Requirements

- `git`
- `gh` (GitHub CLI) for `scripts/github/clone-all.sh`
- `podman` or `docker` for containerized devtools wrappers

## Quick usage

Clone all repositories from a GitHub owner:

```bash
./scripts/github/clone-all.sh <owner> [options]
./scripts/github/clone-all.sh lightning-it --ssh --target-dir ~/sources
```

Run pre-commit inside the devtools container:

```bash
# Build local image (from sibling repository)
podman build --format docker -t localhost/ee-wunder-devtools-ubi9:local ../container-ee-wunder-devtools-ubi9

# Run from this repository root
./scripts/git/pre-commit-devtools
./scripts/git/pre-commit-devtools run --files README.md
```

Run basic ansible sanity checks:

```bash
./scripts/test-ansible.sh
```

Behavior note:
- If no Docker/Podman API socket is available, docker-based pre-commit hooks are skipped automatically.
- Set `DEVTOOLS_SKIP_DOCKER_HOOKS=false` to enforce those hooks.

### Podman socket for docker-based hooks

Some hooks execute `docker ...` commands. With rootless Podman:

```bash
systemctl --user enable --now podman.socket
systemctl --user status podman.socket
ls -l /run/user/$UID/podman/podman.sock
```

Then run:

```bash
DEVTOOLS_SKIP_DOCKER_HOOKS=false ./scripts/git/pre-commit-devtools
```
