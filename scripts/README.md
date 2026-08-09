# ModuLix helper scripts

Helper scripts for day-to-day automation in this repository.

## Layout

```text
scripts/
  ansible-nav
  github/clone-all.sh
ansible/scripts/
  ansible-nav
  install-local-collections
  install-rh-collections
```

## Requirements

- `git`
- `gh` (GitHub CLI) for `scripts/github/clone-all.sh`
- `podman` or `docker` for containerized helper workflows

## Quick usage

Clone all repositories from a GitHub owner:

```bash
./scripts/github/clone-all.sh <owner> [options]
./scripts/github/clone-all.sh lightning-it --ssh --target-dir ~/sources
```

Run pre-commit inside the devtools container:

```bash
mkdir -p "$HOME/.cache/pre-commit"
systemctl --user enable --now podman.socket
SOCK="/run/user/$(id -u)/podman/podman.sock"
REPO="$PWD"

podman run --rm \
  --userns keep-id \
  --user "$(id -u):$(id -g)" \
  --security-opt label=disable \
  -v "$REPO":"$REPO":z \
  -v "$HOME/.cache":"$HOME/.cache":z \
  -v "$SOCK":"$SOCK" \
  -w "$REPO" \
  -e XDG_CACHE_HOME="$HOME/.cache" \
  -e PRE_COMMIT_HOME="$HOME/.cache/pre-commit" \
  -e DOCKER_HOST="unix://$SOCK" \
  -e GIT_CONFIG_COUNT=1 \
  -e GIT_CONFIG_KEY_0=safe.directory \
  -e GIT_CONFIG_VALUE_0="$REPO" \
  quay.io/l-it/ee-wunder-devtools-ubi9:v1.9.4 \
  pre-commit run --all-files
```

Run ansible-navigator wrapper from repository root:

```bash
./scripts/ansible-nav run runbooks/50-applications/aap/10-deploy.yml \
  -i /path/to/private/inventory.yml --limit <host>
```

Behavior note:
- Docker-based hooks require access to a container API socket in the runtime where `pre-commit` executes.

## Governed Ansible execution

`governed-ansible-exec.py` is the reusable execution and evidence engine for
policy-bound Ansible actions. It validates a fixed controller trust descriptor,
signed manifests and approvals, immutable repository snapshots, runtime
attestations, replay protection, process containment and typed evidence before
it builds an Ansible command from policy-owned inputs.

The engine deliberately contains no customer identity, host name, provider
number, network, firewall allowlist or accepted topology. A policy may instead
pin an environment-owned projection contract by repository, relative path and
SHA-256. The recorder loads that contract only from the authorized read-only
Git snapshot, validates its closed schema, compares its target and controller
with the signed manifest and revalidates the exact bytes at every relevant
process boundary.

Component policy, schema and adapter documentation belongs to the repository
that owns that policy. Concrete inventory values belong to the applicable
inventory repository. Customer-specific commands, paths, evidence locations
and execution order belong in the private operations repository; they must not
be copied into this public reusable component.

The reusable, sanitized Wunderbox binding is owned by this repository under
`policies/wunderbox/`; its fixed adapter is `scripts/wbx-governed-exec.py`.
The separate validation repository remains an immutable execution input, but
does not own production execution or approval logic.
