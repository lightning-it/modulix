# Runtime Contract

This document defines the canonical execution contract for ModuLix automation releases.

## Primary entrypoint

- Wrapper: `ansible/scripts/ansible-nav`
- Subcommands:
  - `run <playbook.yml> [playbook args...]`
  - `exec -- <command> [args...]`

## Default runtime behavior

- Runs inside toolbox container image:
  - default `ANSIBLE_TOOLBOX_IMAGE=quay.io/l-it/ee-wunder-toolbox-ubi9:v1.8.4`
- `ansible-navigator run` is always executed with `--ee true`.
- Connected runs resolve collections from `ANSIBLE_COLLECTIONS_PATH` with the
  project collection path first.
- `ansible/scripts/ansible-nav-local run` bootstraps collections by default.
  When `ANSIBLE_TOOLBOX_EE_ONLY_COLLECTIONS=true`, automatic collection
  installation is forced to `false` so the certified EE remains the sole
  collection source.
- If `ansible/files/tls` exists, `ansible-nav-local run` mounts it read-only
  with a private SELinux label at `/runner/project/files/tls` for
  controller-side TLS copy operations.
- Default requirements profile: `ansible/collections/requirements.yml`.
- If `RH_AUTOMATION_HUB_TOKEN` is set and `ansible/collections/requirements-rh.yml`
  exists, that RH profile is selected automatically.

## Runtime options

Supported wrapper options (environment variables):

- `ANSIBLE_TOOLBOX_ENGINE=auto|podman|docker`
- `ANSIBLE_TOOLBOX_RUNTIME_MODE=connected|disconnected`
- `ANSIBLE_TOOLBOX_IMAGE=<image:tag>`
- `MODULIX_RUN_EE_IMAGE=<image:tag>`
- `ANSIBLE_TOOLBOX_RUN_EE_IMAGE=<image:tag>` (compatibility override)
- `ANSIBLE_TOOLBOX_PULL_POLICY=missing|always|never`
- `ANSIBLE_TOOLBOX_NAV_MODE=stdout|interactive`
- `ANSIBLE_TOOLBOX_NAV_EE_IMAGE=<image:tag>` (optional override for `ansible-nav-local`)
- `ANSIBLE_TOOLBOX_MOUNT_INVENTORIES=auto|true|false`
- `ANSIBLE_TOOLBOX_INVENTORY_SOURCE=/path/to/inventories`
- `INVENTORY_FILE=/path/to/inventories/<name>/inventory.yml`
- `ANSIBLE_TOOLBOX_MOUNT_SSH=auto|true|false`
- `ANSIBLE_TOOLBOX_SSH_SOURCE=/path/to/.ssh`
- `ANSIBLE_TOOLBOX_MOUNT_SSH_AGENT=auto|true|false`
- `ANSIBLE_TOOLBOX_RH_COLLECTIONS_MODE=auto|always|never`
- `ANSIBLE_TOOLBOX_RH_COLLECTIONS_STRICT=true|false`
- `ANSIBLE_TOOLBOX_RH_COLLECTIONS_REQUIREMENTS=./collections/requirements-rh.yml`
- `ANSIBLE_TOOLBOX_RH_COLLECTIONS_TARGET=./collections`
- `RH_COLLECTIONS_USE=true|false`

`ANSIBLE_TOOLBOX_RUNTIME_MODE=disconnected` changes runtime defaults only:

- `ANSIBLE_TOOLBOX_AUTO_COLLECTIONS=false`
- `ANSIBLE_TOOLBOX_RH_COLLECTIONS_MODE=never`
- `ANSIBLE_TOOLBOX_RUN_EE_PRELOAD=true`

It does not select an application-specific EE image or artifact directory.
Those values belong to the caller, inventory, or operator procedure.

When `ANSIBLE_TOOLBOX_INVENTORY_SOURCE` is unset, the wrapper can derive the
inventory source from `INVENTORY_FILE` if it points below an `inventories`
directory.

## Required runtime inputs

Depending on playbook:

- inventory (`-i ...`)
- SSH key material (`~/.ssh` and/or ssh-agent)
- secrets (`ANSIBLE_VAULT_PASSWORD_FILE`, vaulted `vault_token`, `VAULT_TOKEN`
  overrides, etc.)
- for AAP/CaC execution with `requirements-rh.yml`: `RH_AUTOMATION_HUB_TOKEN`
  - offline token values are used via Automation Hub `auth_url` flow

## Host-native execution (optional)

Host-native execution is allowed, but the operator must provide equivalent prerequisites:

- compatible `ansible-core`/`ansible-navigator`
- required Ansible collections
- equivalent secret and SSH handling

The containerized wrapper remains the default supported path.
