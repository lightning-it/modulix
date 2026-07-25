# Agent Instructions

## Shared-Assets First

For any file that is synchronized from `shared-assets`, make the change in the
shared-assets source first and then sync it back to downstream repositories.
Do not treat downstream synced copies as the source of truth.

## Dependency version policy

- Use fixed package versions only. Do not introduce open-ended or floating
  version ranges such as `>=`, `<=`, `~=` , `^`, or `latest` unless the user
  explicitly asks for that behavior.
- Manage package version updates via Renovate whenever possible.
- When adding or changing a package version, prefer wiring it into existing
  Renovate management instead of maintaining it manually.

## Ansible Collection Requirements

- Keep `ansible/collections/requirements.yml` fully resolvable with
  `ansible-galaxy collection install`; do not commit a requirements file that
  only works with a pre-populated local collection cache.
- When a Lightning IT collection version is released as a GitHub Release asset
  but is not available from the configured Galaxy sources, pin the immutable
  release tarball URL with `type: url` instead of using the unresolved
  `namespace.collection` name.
- Before changing collection pins, check transitive dependency constraints from
  collections such as `fedora.linux_system_roles`. Keep direct pins compatible
  with those constraints.
- After changing `ansible/collections/requirements.yml`, verify dependency
  resolution inside the toolbox wrapper with an isolated target path, for
  example:

```bash
cd ansible
./scripts/ansible-nav exec -- ansible-galaxy collection install \
  --force \
  --collections-path /tmp/modulix-collections-check \
  -r /runner/project/collections/requirements.yml
```

## Mandatory validation gate (containerized)

Before finishing any change in this repository, run a full validation pass in
the devtools container. Do not rely on host-installed tooling.

### 1) Run pre-commit (includes YAML lint and inventory checks)

```bash
podman run --rm \
  --security-opt label=disable \
  --userns keep-id \
  --user "$(id -u):$(id -g)" \
  -e HOME=/tmp \
  -e GIT_CONFIG_COUNT=1 \
  -e GIT_CONFIG_KEY_0=safe.directory \
  -e GIT_CONFIG_VALUE_0=/workspace \
  -v "$PWD":/workspace:Z \
  -w /workspace \
  quay.io/l-it/ee-wunder-devtools-ubi9:v1.9.4 \
  pre-commit run --all-files
```

### 2) Run RPM parse/build checks in container

```bash
podman run --rm \
  --security-opt label=disable \
  -v "$PWD":/workspace:Z \
  -w /workspace \
  quay.io/l-it/ee-wunder-devtools-ubi9:v1.9.4 \
  bash -lc 'set -euo pipefail; tmpdir=$(mktemp -d); tar -C /workspace --exclude=./.git --exclude=./ansible/.secrets --exclude=./ansible/.tmp -cf - . | tar -C "$tmpdir" -xf -; cd "$tmpdir"; rpmspec -P packaging/rpm/modulix-automation-runtime.spec >/tmp/modulix.spec.out; ./packaging/rpm/build-srpm.sh --version 0.1.0 --release 1; cp -f packaging/rpm/dist/*.src.rpm /workspace/packaging/rpm/dist/'
```

## RPM validation fallback

When host tooling is missing for RPM checks, do not stop at a local limitation.

- If `rpmspec` and/or `rpmbuild` are not available on the host, run RPM parse/build
  validation in the devtools container first.
- Only report a limitation after the devtools-container path has been attempted.
- Avoid statements like:
  - `Could not run RPM parse/build locally because rpmspec/rpmbuild are not installed in this environment.`
  without also documenting the devtools-container attempt and result.

## Runbook Design Default (Inventory-Driven)

For application and platform runbooks (for example `ansible/runbooks/50-applications/wunderbox/10-deploy.yml`), default behavior MUST be inventory-driven.

1. Runbooks SHOULD orchestrate roles, not implement business/configuration logic that belongs in inventory or roles.
2. Service enablement MUST come from inventory toggles (`services.<group>.*` and/or `wunderbox_service_*` overrides).
3. Service configuration values (endpoints, ports, credentials, DB settings, host mappings) MUST come from inventory/group vars/host vars.
4. Runbooks MUST NOT silently generate environment-specific defaults for service credentials or topology.
5. Cross-service wiring SHOULD be expressed as inventory variables (or role defaults that map inventory inputs), not large `set_fact`/fallback blocks in runbooks.
6. If values are required, fail fast with clear assertions instead of deriving hidden defaults in runbook code.

## Public Documentation Boundary

This repository is public reusable automation. Documentation here MUST explain
generic runbook behavior, variable contracts, and sanitized examples only.

Do not add customer-specific or Lightning IT-specific copy-paste rollout
instructions here. Copy-paste procedures with real repo names, inventory paths,
hostnames, artifact locations, tokens, Vault paths, or operator session setup
belong in the private `modulix-operations-*` repository for that environment.

Allowed here:

- reusable runbook documentation
- generic examples with placeholder paths and sanitized inventory names
- variable contract examples
- development and packaging instructions for this repository

Not allowed here:

- end-to-end operational rollout guides
- real customer or Lightning IT hostnames and inventory paths
- environment-specific artifact locations
- private workflow composition
- instructions that operators are expected to copy and paste into a real
  environment

## Secret Storage Rule

- Never commit secret values, tokens, passwords, private keys, activation codes, or decrypted Vault output.
- When HC Vault is configured for a role or runbook, generated credentials must be read from HC Vault first, generated only when missing, written back to HC Vault, and then consumed by the application from the Vault-backed Ansible variables. Do not keep generated plaintext secret files on the managed host unless a role has an explicit break-glass option such as `*_allow_local_secret_files=true`.
- When HC Vault is not configured, required credentials must be supplied from Ansible Vault encrypted inventory variables. Do not add new plaintext generated-secret fallbacks.
- Tasks that read, generate, write, template, or compare secret material must use `no_log: true`.
