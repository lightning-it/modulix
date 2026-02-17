# Ansible automation

This repo uses **ansible-navigator** with the **Wunder ansible execution environment** to avoid local tooling dependencies.

---

## Quick Start

### 1) Install collections (choose one mode)

Base dependencies only:

```bash
./scripts/ansible-nav exec -- \
  ansible-galaxy collection install -r /runner/project/collections/requirements.yml \
  -p /runner/project/collections --force
```

Local collection overlays only (`ansible-collection-*` repos):
run this after base dependencies are already installed.

```bash
./scripts/install-local-collections
```

### 2) Run a full Wunderbox rebuild

```bash
./scripts/ansible-nav run playbooks/services/01-wunderbox-rebuild.yml \
  -i inventories/corp/inventory.yml --limit wunderbox01.prd.dmz.corp.l-it.io
```

### 3) Run a single playbook

```bash
./scripts/ansible-nav run playbooks/stage-2a/traditional-operating-systems/rhel9/01-base-setup.yml \
  -i inventories/corp/inventory.yml --limit wunderbox01.prd.dmz.corp.l-it.io
```

For full workflows and all variants, see `How-To`.

---

## How-To

### Use the runtime wrapper

Default usage:

```bash
./scripts/ansible-nav run <playbook.yml> -i inventories/corp/inventory.yml --limit <host-or-group>
```

Force engine when needed:

```bash
ANSIBLE_NAVIGATOR_ENGINE=podman ./scripts/ansible-nav run ...
ANSIBLE_NAVIGATOR_ENGINE=docker ./scripts/ansible-nav run ...
```

### Install collections

Choose one install mode:

1) Base dependencies only (no local collection development):

```bash
./scripts/ansible-nav exec -- \
  ansible-galaxy collection install -r /runner/project/collections/requirements.yml \
  -p /runner/project/collections --force
```

2) Local collection overlays only:

```bash
./scripts/install-local-collections
```

Only selected local collections:

```bash
./scripts/install-local-collections foundational rhel
```

This script only builds and installs local `ansible-collection-*` repos.

### Run playbooks

00 Gateway (baremetal+RHEL9) setup:

```bash
./scripts/ansible-nav run playbooks/stage-1/infrastructure-platform-baremetal/01-oob-virtualmedia-install.yml \
  -i inventories/corp/inventory.yml --limit gw01.prd.edge.pub.l-it.io

./scripts/ansible-nav run playbooks/stage-2a/traditional-operating-systems/rhel9/01-base-setup.yml \
  -i inventories/corp/inventory.yml --limit gw01.prd.edge.pub.l-it.io

./scripts/ansible-nav run playbooks/stage-2b/01-gateway.yml \
  -i inventories/corp/inventory.yml --limit gw01.prd.edge.pub.l-it.io
```

01 vSphere ESXi setup:

```bash
./scripts/ansible-nav run playbooks/stage-1/infrastructure-platform-vsphere/01-esxi-os_install.yml \
  -i inventories/corp/inventory.yml --limit vsphere_esxi

./scripts/ansible-nav run playbooks/stage-1/infrastructure-platform-vsphere/02-esxi-setup.yml \
  -i inventories/corp/inventory.yml --limit vsphere_esxi
```

02 vSphere vCenter setup:

```bash
./scripts/ansible-nav run playbooks/stage-1/infrastructure-platform-vsphere/FIXME \
  -i inventories/corp/inventory.yml --limit vcenter-com.mgmt.corp.l-it.io
```

10 Firewall (VM+RHEL9) setup:

10.1 DMZ

```bash
./scripts/ansible-nav run playbooks/stage-2a/traditional-operating-systems/rhel9/01-base-setup.yml \
  -i inventories/corp/inventory.yml --limit fw01.prd.dmz.corp.l-it.io

./scripts/ansible-nav run playbooks/stage-2b/10-firewall.yml \
  -i inventories/corp/inventory.yml --limit fw01.prd.dmz.corp.l-it.io
```

10.2 COM

```bash
./scripts/ansible-nav run playbooks/stage-2a/traditional-operating-systems/rhel9/01-base-setup.yml \
  -i inventories/corp/inventory.yml --limit fw01.prd.com.corp.l-it.io

./scripts/ansible-nav run playbooks/stage-2b/10-firewall.yml \
  -i inventories/corp/inventory.yml --limit fw01.prd.com.corp.l-it.io
```

10.3 INT

```bash
./scripts/ansible-nav run playbooks/stage-2a/traditional-operating-systems/rhel9/01-base-setup.yml \
  -i inventories/corp/inventory.yml --limit fw01.prd.int.corp.l-it.io

./scripts/ansible-nav run playbooks/stage-2b/10-firewall.yml \
  -i inventories/corp/inventory.yml --limit fw01.prd.int.corp.l-it.io
```

10.4 ISO

```bash
./scripts/ansible-nav run playbooks/stage-1/infrastructure-platform-vsphere/20-vm-template.yml \
  -i inventories/corp/inventory.yml --limit fw01.prd.iso.corp.l-it.io

./scripts/ansible-nav run playbooks/stage-2a/traditional-operating-systems/rhel9/01-base-setup.yml \
  -i inventories/corp/inventory.yml --limit fw01.prd.iso.corp.l-it.io

./scripts/ansible-nav run playbooks/stage-2b/10-firewall.yml \
  -i inventories/corp/inventory.yml --limit fw01.prd.iso.corp.l-it.io
```

20 Workstations (VM+RHEL9) setup:

20.1 DMZ

```bash
./scripts/ansible-nav run playbooks/stage-1/infrastructure-platform-vsphere/20-vm-template.yml \
  -i inventories/corp/inventory.yml --limit workstation01.prd.dmz.corp.l-it.io

./scripts/ansible-nav run playbooks/stage-2a/traditional-operating-systems/rhel9/01-base-setup.yml \
  -i inventories/corp/inventory.yml --limit workstation01.prd.dmz.corp.l-it.io

./scripts/ansible-nav run playbooks/stage-2b/11-workstation.yml \
  -i inventories/corp/inventory.yml --limit workstation01.prd.dmz.corp.l-it.io
```

21 Wunderbox (VM+RHEL9) setup:

```bash
./scripts/ansible-nav run playbooks/stage-1/infrastructure-platform-vsphere/90-vm-destroy.yml \
  -i inventories/corp/inventory.yml --limit wunderbox01.prd.dmz.corp.l-it.io

./scripts/ansible-nav run playbooks/stage-1/infrastructure-platform-vsphere/20-vm-template.yml \
  -i inventories/corp/inventory.yml --limit wunderbox01.prd.dmz.corp.l-it.io

./scripts/ansible-nav run playbooks/stage-2a/traditional-operating-systems/rhel9/01-base-setup.yml \
  -i inventories/corp/inventory.yml --limit wunderbox01.prd.dmz.corp.l-it.io

./scripts/ansible-nav run playbooks/stage-2b/12-wunderbox.yml \
  -i inventories/corp/inventory.yml --limit wunderbox01.prd.dmz.corp.l-it.io
```

21.1 Wunderbox rebuild (single pipeline playbook):

```bash
./scripts/ansible-nav run playbooks/services/01-wunderbox-rebuild.yml \
  -i inventories/corp/inventory.yml --limit wunderbox01.prd.dmz.corp.l-it.io
```

---

## Knowledge Base

### ansible-navigator configuration details

This repo uses one runtime config:
- `ansible-navigator.yml` (`container-engine: auto`)

Config behavior:
- Enables the execution environment.
- Uses `quay.io/l-it/ee-wunder-ansible-ubi9:v1.7.0`.
- Mounts project path into the execution environment.
- Passes `ANSIBLE_CONFIG` and `ANSIBLE_VAULT_PASSWORD_FILE`.
- Disables playbook artifacts and uses stdout mode.

Wrapper behavior (`scripts/ansible-nav`):
- When a container API socket exists (`/var/run/docker.sock`, `/run/docker.sock`, or `/run/user/$UID/podman/podman.sock`), it is mounted to `/var/run/docker.sock` in the execution environment.
- External inventories are auto-mounted from `../../ansible-inventory-lit/inventories` to `/runner/project/inventories` when available.
- When inventory mount is active, `-i inventories/...` is automatically rewritten to `/runner/project/inventories/...` for execution environment compatibility.
- Host SSH directory is auto-mounted from `~/.ssh` to `/runner/.ssh` so inventory paths like `/runner/.ssh/id_ed25519` work inside the execution environment.
- Host `SSH_AUTH_SOCK` is auto-mounted for SSH agent forwarding (at the same socket path, plus `/runner/ssh-agent.sock` fallback).
- For Podman, wrapper enables `--userns=keep-id`, `--user=$(id -u):$(id -g)`, and `--security-opt=label=disable` so forwarded SSH agent sockets are usable in the execution environment.

Inventory mount controls:
- `ANSIBLE_NAVIGATOR_MOUNT_INVENTORIES=auto|true|false` (default: `auto`)
- `ANSIBLE_NAVIGATOR_INVENTORY_SOURCE=/path/to/inventories`

SSH mount controls:
- `ANSIBLE_NAVIGATOR_MOUNT_SSH=auto|true|false` (default: `auto`)
- `ANSIBLE_NAVIGATOR_SSH_SOURCE=/path/to/.ssh`
- `ANSIBLE_NAVIGATOR_MOUNT_SSH_AGENT=auto|true|false` (default: `auto`)
- `ANSIBLE_NAVIGATOR_PODMAN_KEEP_ID=auto|true|false` (default: `auto`)

### Vault + Nexus notes

The Vault bootstrap writes its init output to the target only. The repo must not store secrets.

Recommended flow:
- First run (`vault_bootstrap`): Vault init runs on the target; the init payload is kept in memory for unseal and root token, and the encrypted init file is written to the target.
- Subsequent runs: unseal/root token come from vaulted inventory vars (`vault_init.*`, e.g. `group_vars/wunderboxes/vault-init.yml`). The playbooks do not read the encrypted init file on the target.
- `vault_config` creates AppRole roles and stores credentials in Vault KV at:
  - `stage-2c/<inventory_hostname>/nexus/approle-kv`
  - `stage-2c/<inventory_hostname>/nexus/approle-pki`
- `nexus` reads AppRole credentials from those KV paths at runtime. It needs `VAULT_TOKEN` with read access.

Best practice: use a short-lived, least-privilege token for KV read + PKI issue, not a root token.

### Inventory and roles

- Inventory: `inventories/corp/inventory.yml`
- Roles path: `./roles` (set in `ansible.cfg`)
- Adjust vars in `group_vars/` and `host_vars/` as needed.

### Secrets

- **Do not commit secrets.**
- Use:
  - Ansible Vault (`ANSIBLE_VAULT_PASSWORD_FILE`)
  - SOPS or your preferred secret store
