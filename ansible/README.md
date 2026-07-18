# Ansible automation

<<<<<<< HEAD
This repo uses **ansible-navigator** with the **Wunder devtools execution environment** to avoid local
tooling dependencies.

---

## ansible-navigator configuration

The bundled `ansible-navigator.yml` config:
- Enables the execution environment via Docker
- Uses `quay.io/l-it/ee-wunder-ansible-ubi9:v1.7.0`
- (Optional) mounts the Docker socket for roles that need it
- Passes `ANSIBLE_CONFIG` and `ANSIBLE_VAULT_PASSWORD_FILE`
- Disables playbook artifacts and uses stdout mode

---

## Prerequisites: Ansible Collections

Playbooks in this repository depend on additional Ansible Collections (e.g. `lit.foundational`).
They must be installed into the local vendor directory **before** running playbooks:

### Install / update required collections

```bash
ansible-navigator exec -- \
  ansible-galaxy collection install -r /runner/project/collections/requirements.yml \
  -p /runner/project/collections-dev --force
```

### Initial inventory setup
```bash
ansible-navigator run init-inventory.yml -e g_inventory_version=<BRANCH> -e github_token=<PAT>
=======
## Overview

This repo supports two runtime modes:

- As-code mode (`scripts/ansible-nav`): host wrapper that starts the toolbox
  container and runs runbooks in the nested Ansible EE.
- In-container mode (`ansible-nav-local`): run directly inside the toolbox
  container when only container access is available.

In both cases, host installation of `ansible-navigator` is not required.

## Get Started

### As-code mode (`ansible-nav`)

#### 1) Run (collections are handled automatically)

`./scripts/ansible-nav run ...` auto-installs base collections from
`collections/requirements.yml` by default.
If `RH_AUTOMATION_HUB_TOKEN` is set and `collections/requirements-rh.yml` exists,
it is selected automatically instead.

`ANSIBLE_TOOLBOX_AUTO_COLLECTIONS` controls this bootstrap behavior:

- `true` (default): always install collections before `run` (`--force`).
- `auto`: install only when cache is missing or requirements changed.
- `false`: do not install; assume collections are already present.

Use `auto` for faster day-to-day operator runs. Use `true` for strict
reproducibility (for example CI or fresh environments).

For manual collection install modes, see `Tasks` -> `Install collections`.

#### 2) Run a single runbook

```bash
./scripts/ansible-nav run runbooks/<domain>/<area>/<runbook>.yml \
  -i inventories/<env>/inventory.yml --limit <host-or-group>
```

#### 3) Compose customer workflows privately

This public repository provides reusable capability runbooks. Customer-specific
workflow composition belongs in private `modulix-operations-*` repositories.

### In-container mode (`ansible-nav-local`)

If you run directly in the toolbox container runtime, use `ansible-nav-local`.

Workspace-mounted mode (`/runner/project`):

```bash
podman run --rm -it \
  --privileged \
  --security-opt label=disable \
  --user 0:0 \
  -v "$PWD":/runner/project:Z \
  -w /runner/project \
  -v "$HOME/.ssh:/runner/.ssh:ro,Z" \
  -e HOME=/runner \
  -e ANSIBLE_TOOLBOX_NAV_EE_ENABLED=true \
  quay.io/l-it/ee-wunder-toolbox-ubi9:v1.11.1 \
  ansible-nav-local run playbooks/<stage-or-service>/<playbook>.yml \
  -i inventories/<env>/inventory.yml --limit <host-or-group>
```

RPM baseline mode (`/opt/modulix/ansible` in image):

```bash
INVENTORY_DIR=/path/to/inventories
VAULT_PASS_FILE=~/modulix-env/.vault-pass.txt
RUN_EE_IMAGE=localhost/ee-wunder-ansible-ubi9-certified:local

podman run --rm -it \
  --privileged \
  --security-opt label=disable \
  --user 0:0 \
  -w /opt/modulix/ansible \
  -v "$INVENTORY_DIR:/opt/modulix/ansible/inventories:ro,Z" \
  -v "$VAULT_PASS_FILE:/opt/modulix/ansible/.vault-pass.txt:ro,Z" \
  -v "$HOME/.ssh:/runner/.ssh:ro,Z" \
  -e HOME=/runner \
  -e ANSIBLE_TOOLBOX_NAV_EE_ENABLED=true \
  -e ANSIBLE_TOOLBOX_NAV_EE_IMAGE="$RUN_EE_IMAGE" \
  -e ANSIBLE_TOOLBOX_NAV_PULL_POLICY=never \
  -e ANSIBLE_TOOLBOX_AUTO_COLLECTIONS=false \
  -e ANSIBLE_VAULT_PASSWORD_FILE=/opt/modulix/ansible/.vault-pass.txt \
  quay.io/l-it/ee-wunder-toolbox-ubi9:v1.11.1 \
  ansible-nav-local run playbooks/<stage-or-service>/<playbook>.yml \
  -i inventories/<env>/inventory.yml --limit <host-or-group>
```

`ANSIBLE_TOOLBOX_NAV_EE_ENABLED=true` is required in this example because
`ansible-nav-local` defaults to `--ee false`. EE image/engine defaults come from
`ansible-navigator.yml`. `ANSIBLE_CONFIG` defaults to the active workspace
`ansible.cfg`.

`ANSIBLE_TOOLBOX_NAV_EE_IMAGE` is an explicit run-EE override for in-container
mode. Use a published image tag in standard operations. Use a local tag only when
that image is available to the nested container engine (for example preloaded
with `podman load` inside the toolbox runtime).
Switch between public and certified runtime by changing `RUN_EE_IMAGE` (or
`ANSIBLE_TOOLBOX_NAV_EE_IMAGE`) only. Use
`.../ee-wunder-ansible-ubi9-certified:<tag>` when your execution requires
certified collections not present in the public Galaxy-only image. For registry
hosted certified images, authenticate first (for example `podman login <registry>`).
For local image tags (`localhost/...`) in container-in mode, set
`ANSIBLE_TOOLBOX_NAV_PULL_POLICY=never` and preload the image into the nested
runtime before `ansible-nav-local run`.

Local preload pattern (offline/local validation):

```bash
podman save -o /tmp/run-ee.tar "$RUN_EE_IMAGE"

podman run --rm -it \
  --privileged \
  --security-opt label=disable \
  --user 0:0 \
  -w /opt/modulix/ansible \
  -v /tmp/run-ee.tar:/tmp/run-ee.tar:ro,Z \
  ... \
  localhost/ee-wunder-toolbox-ubi9:local \
  bash -lc 'podman load -i /tmp/run-ee.tar && ansible-nav-local run <runbook.yml> -i inventories/<env>/inventory.yml --limit <host-or-group>'
```

For a complete local image build and runtime workflow, see:
`lcp-docs/30-modulix/50-development/02-containers/20-local-modulix-runtime.md`.

In RPM baseline mode (`/opt/modulix/ansible`), collection bootstrap defaults to
`ANSIBLE_TOOLBOX_AUTO_COLLECTIONS=false` (offline-safe). Collections are expected
to be pre-installed in the runtime. Set `ANSIBLE_TOOLBOX_AUTO_COLLECTIONS=false`
explicitly in container-in commands to avoid inherited host environment values.
Enable bootstrap only when intentionally refreshing collections in connected
environments, for example `-e ANSIBLE_TOOLBOX_AUTO_COLLECTIONS=true`.

Offline operation requirements in RPM baseline mode:

- toolbox image includes `modulix-automation-runtime` payload (`/opt/modulix/ansible`)
- run EE image from `ansible-navigator.yml` is already available to the nested container engine
- required collections/roles are present in that run EE image (for example `fedora.linux_system_roles`)

Why these container flags are used in this mode:

- `--privileged`: allows nested container execution when `ansible-navigator` starts
  the inner execution environment container.
- `--security-opt label=disable`: avoids SELinux labeling conflicts for bind mounts
  and nested container access on SELinux hosts.
- `--user 0:0`: runs toolbox as root so nested Podman operations can start reliably.

If you run `ansible-nav-local` with `ANSIBLE_TOOLBOX_NAV_EE_ENABLED=false`, these
flags are usually not required.

---

## Tasks

### As-code mode (`ansible-nav`)

#### Use the runtime wrapper

Default usage:

```bash
./scripts/ansible-nav run <runbook.yml> -i inventories/<env>/inventory.yml --limit <host-or-group>
```

Container engine selection is automatic by default. Manual override is documented in `Reference` (`ANSIBLE_TOOLBOX_ENGINE`).

#### Install collections

Choose one install mode:

1) Base dependencies only (runtime path):

```bash
./scripts/ansible-nav exec -- \
  ansible-galaxy collection install -r /runner/project/collections/requirements.yml \
  -p /runner/project/collections --force
```

2) RH extension collections at runtime (single public EE model):

```bash
RH_AUTOMATION_HUB_TOKEN=<token> ./scripts/install-rh-collections
```

#### Internal engineering workflows

This is outside the supported platform operations path.
It is intended for platform engineering teams that develop or extend collections.
For controlled development procedures, see:

- `lcp-docs/30-modulix/50-development/00-index.md`
- `lcp-docs/30-modulix/50-development/01-ansible-collections/10-ansible-collection-development.md`

#### Execute runbooks

Use runbooks as reusable capability entrypoints. This README documents runtime
mechanics (`ansible-nav` and `ansible-nav-local`), while private customer
workflow sequencing lives in `modulix-operations-*` repositories.

Runbook content is documented in:

- `lcp-docs/30-modulix/30-runbooks/00-index.md`

Execution pattern:

```bash
./scripts/ansible-nav run <runbook.yml> \
  -i inventories/<env>/inventory.yml --limit <host-or-group>
```

### In-container mode (`ansible-nav-local`)

After starting the toolbox container (see Get Started), use the same runbook
syntax with `ansible-nav-local`:

```bash
ansible-nav-local run <runbook.yml> \
  -i inventories/<env>/inventory.yml --limit <host-or-group>
>>>>>>> origin/develop
```

---

<<<<<<< HEAD
## Running playbooks

00 Gateway (baremetal+RHEL9) setup:

```bash
ansible-navigator run playbooks/stage-1/infrastructure-platform-baremetal/01-oob-virtualmedia-install.yml \
  -i inventories/corp/inventory.yml --limit gw01.prd.edge.pub.l-it.io

ansible-navigator run playbooks/stage-2a/traditional-operating-systems/rhel9/01-base-setup.yml \
  -i inventories/corp/inventory.yml --limit gw01.prd.edge.pub.l-it.io

ansible-navigator run playbooks/stage-2b/01-gateway.yml \
  -i inventories/corp/inventory.yml --limit gw01.prd.edge.pub.l-it.io
```

01 vSphere ESXi setup:

```bash
ansible-navigator run playbooks/stage-1/infrastructure-platform-vsphere/01-esxi-os_install.yml \
  -i inventories/corp/inventory.yml --limit vsphere_esxi

ansible-navigator run playbooks/stage-1/infrastructure-platform-vsphere/02-esxi-setup.yml \
  -i inventories/corp/inventory.yml --limit vsphere_esxi
```

02 vSphere vCenter setup:

```bash
ansible-navigator run playbooks/stage-1/infrastructure-platform-vsphere/FIXME \
  -i inventories/corp/inventory.yml --limit vcenter-com.mgmt.corp.l-it.io
```

10 Firewall (VM+RHEL9) setup:

10.1 DMZ

```bash
ansible-navigator run playbooks/stage-2a/traditional-operating-systems/rhel9/01-base-setup.yml \
  -i inventories/corp/inventory.yml --limit fw01.prd.dmz.corp.l-it.io

ansible-navigator run playbooks/stage-2b/10-firewall.yml \
  -i inventories/corp/inventory.yml --limit fw01.prd.dmz.corp.l-it.io
```

10.2 COM

```bash
ansible-navigator run playbooks/stage-2a/traditional-operating-systems/rhel9/01-base-setup.yml \
  -i inventories/corp/inventory.yml --limit fw01.prd.com.corp.l-it.io

ansible-navigator run playbooks/stage-2b/10-firewall.yml \
  -i inventories/corp/inventory.yml --limit fw01.prd.com.corp.l-it.io
```

10.3 INT

```bash
ansible-navigator run playbooks/stage-2a/traditional-operating-systems/rhel9/01-base-setup.yml \
  -i inventories/corp/inventory.yml --limit fw01.prd.int.corp.l-it.io

ansible-navigator run playbooks/stage-2b/10-firewall.yml \
  -i inventories/corp/inventory.yml --limit fw01.prd.int.corp.l-it.io
```

10.4 ISO

```bash
ansible-navigator run playbooks/stage-1/infrastructure-platform-vsphere/20-vm-template.yml \
  -i inventories/corp/inventory.yml --limit fw01.prd.iso.corp.l-it.io

ansible-navigator run playbooks/stage-2a/traditional-operating-systems/rhel9/01-base-setup.yml \
  -i inventories/corp/inventory.yml --limit fw01.prd.iso.corp.l-it.io

ansible-navigator run playbooks/stage-2b/10-firewall.yml \
  -i inventories/corp/inventory.yml --limit fw01.prd.iso.corp.l-it.io
```

20 Workstations(VM+RHEL9) setup:

20.1 DMZ

```bash
ansible-navigator run playbooks/stage-1/infrastructure-platform-vsphere/20-vm-template.yml \
  -i inventories/corp/inventory.yml --limit workstation01.prd.dmz.corp.l-it.io

ansible-navigator run playbooks/stage-2a/traditional-operating-systems/rhel9/01-base-setup.yml \
  -i inventories/corp/inventory.yml --limit workstation01.prd.dmz.corp.l-it.io

ansible-navigator run playbooks/stage-2b/11-workstation.yml \
  -i inventories/corp/inventory.yml --limit workstation01.prd.dmz.corp.l-it.io
```

21 Wunderbox(VM+RHEL9) setup:

```bash
ansible-navigator run playbooks/stage-1/infrastructure-platform-vsphere/90-vm-destroy.yml \
  -i inventories/corp/inventory.yml --limit wunderbox01.prd.dmz.corp.l-it.io

ansible-navigator run playbooks/stage-1/infrastructure-platform-vsphere/20-vm-template.yml \
  -i inventories/corp/inventory.yml --limit wunderbox01.prd.dmz.corp.l-it.io

ansible-navigator run playbooks/stage-2a/traditional-operating-systems/rhel9/01-base-setup.yml \
  -i inventories/corp/inventory.yml --limit wunderbox01.prd.dmz.corp.l-it.io

ansible-navigator run playbooks/stage-2b/12-wunderbox.yml \
  -i inventories/corp/inventory.yml --limit wunderbox01.prd.dmz.corp.l-it.io
```

---

## Vault + Nexus notes
=======
## Reference

### Execution model

#### As-code mode (`ansible-nav`)

`scripts/ansible-nav` runs the toolbox image directly via Podman or Docker.

Default toolbox image:
- `quay.io/l-it/ee-wunder-toolbox-ubi9:v1.11.1`

Wrapper behavior (`scripts/ansible-nav`):
- External inventories are auto-mounted from `ANSIBLE_TOOLBOX_INVENTORY_SOURCE`,
  or derived from `INVENTORY_FILE` when it points below an `inventories`
  directory.
- When inventory mount is active, `-i inventories/...` is automatically rewritten to `/runner/project/inventories/...` for execution environment compatibility.
- Host SSH directory is auto-mounted from `~/.ssh` to `/runner/.ssh` so inventory paths like `/runner/.ssh/id_ed25519` work inside the execution environment.
- Host `SSH_AUTH_SOCK` is auto-mounted to `/runner/ssh-agent.sock` and exported in-container.
- For `exec`, wrapper runs with host UID/GID and sets `HOME=/runner`.
- For `run`, execution is always nested in toolbox:
  - toolbox starts as privileged root to support nested podman.
  - `ansible-nav-local` runs `ansible-navigator` with EE enabled.
  - inner EE container engine is fixed to `podman`.
  - run EE image:
    - `MODULIX_RUN_EE_IMAGE` (default: `quay.io/l-it/ee-wunder-ansible-ubi9:v1.15.1`).
    - `ANSIBLE_TOOLBOX_RUN_EE_IMAGE` can override it for compatibility.
    - `ANSIBLE_TOOLBOX_RUNTIME_MODE=connected|disconnected` (default: `connected`).
- For `exec`, when a container API socket exists (`/var/run/docker.sock`, `/run/docker.sock`, or `/run/user/$UID/podman/podman.sock`), it is mounted to `/var/run/docker.sock` in the toolbox container.
- For AAP runs (`runbook path contains "aap"` or `--tags/-t` includes `aap`), wrapper runs
  `scripts/install-rh-collections` automatically before runbook execution when
  `ANSIBLE_TOOLBOX_RH_COLLECTIONS_MODE=auto` (default).
- `ANSIBLE_TOOLBOX_RUNTIME_MODE=disconnected` sets offline-safe defaults:
  `ANSIBLE_TOOLBOX_AUTO_COLLECTIONS=false`, `ANSIBLE_TOOLBOX_RH_COLLECTIONS_MODE=never`, and
  `ANSIBLE_TOOLBOX_RUN_EE_PRELOAD=true`.

#### In-container mode (`ansible-nav-local`)

- Execute from inside toolbox container.
- `ansible-nav-local` runs `ansible-navigator` directly.
- Use the same runbook paths, inventory flags, and limits as in as-code mode.
- EE image/engine defaults are taken from `ansible-navigator.yml`.
- `ANSIBLE_CONFIG` defaults to `ansible.cfg` in the active runtime workspace.
- For RH collection profile resolution, provide `RH_AUTOMATION_HUB_TOKEN`.
- Runtime options are listed by `scripts/ansible-nav --help` and
  `scripts/ansible-nav-local --help`.

#### Run EE image variants

| Variant | Technical scope | Build requirement | Access model | Operational guidance |
|---|---|---|---|---|
| `ee-wunder-ansible-ubi9` | Public Galaxy-only runtime image with public/community and non-gated platform collections | None | Public pull | Default option for standard connected environments |
| `ee-wunder-ansible-ubi9-certified` | Runtime image with Automation Hub certified collections baked in at build time | CI must provide `RH_AUTOMATION_HUB_TOKEN` | Credential-gated image pull (registry authentication required) | Use for controlled/offline enterprise environments where required certified collections must already exist in the runtime image |

### Inventory and roles

- Inventory is supplied from an external inventory repository.
- Roles path: `./roles` (set in `ansible.cfg`)
- Adjust vars in `group_vars/` and `host_vars/` as needed.
- Inventory is environment-specific and is not provided as a universal ModuLix baseline.
- Platform teams must define inventory to match their infrastructure and operating context
  (host/group model, network zones, access paths, and required runtime inputs).
- Sanitized public examples live in `ansible-inventory-example`.
- `lit.supplementary.aap` is backend-agnostic and expects resolved password inputs
  (`aap_*_admin_password_input`).
- `runbooks/50-applications/aap/10-deploy.yml` provides an optional Vault pre-step
  (`tasks/aap_seed_passwords_vault.yml`) to read/create admin passwords and publish
  resolved inputs before the AAP roles run.
- `runbooks/50-applications/github-runner/10-setup.yml` configures
  Ubuntu-based GitHub Actions self-hosted runners.
- `runbooks/40-platforms/incus/10-host-setup.yml` configures
  Ubuntu-based Incus hosts for containers and VM workloads.

## Security

### Secrets flow (Vault/Nexus)
>>>>>>> origin/develop

The Vault bootstrap writes its init output to the target only. The repo must not store secrets.

Recommended flow:
<<<<<<< HEAD
- First run (`vault_bootstrap`): Vault init runs on the target; the init payload is kept in memory for unseal and
  root token, and the encrypted init file is written to the target.
- Subsequent runs: unseal/root token come from vaulted inventory vars (`vault_init.*`, e.g.
  `group_vars/wunderboxes/vault-init.yml`). The playbooks do not read the encrypted init file on the target.
- `vault_config` creates AppRole roles and stores credentials in Vault KV at:
  - `stage-2c/<inventory_hostname>/nexus/approle-kv`
  - `stage-2c/<inventory_hostname>/nexus/approle-pki`
- `nexus` reads AppRole credentials from those KV paths at runtime. It needs `VAULT_TOKEN` with read access.

Best practice: use a short‑lived, least‑privilege token for KV read + PKI issue, not a root token.

```bash
ansible-navigator run playbooks/stage-2b/12-wunderbox.yml -i inventories/corp/inventory.yml --limit wunderbox02.prd.dmz.corp.l-it.io -t vault
```

## Inventory and roles

- Inventory: `inventories/corp/inventory.yml`
- Roles path: `./roles` (set in `ansible.cfg`)
- Adjust vars in `group_vars/` and `host_vars/` as needed.

---

## OCP

### Install
```bash
VAULT_TOKEN=$(cat $HOME/.vault-token) ansible-navigator run playbooks/stage-2c/container-platform-ocp4/20-ocp-install.yml -i inventories/corp/inventory.yml -l ocp -e install_agent_hashi_vault_auth_method=token
```

### GitOps
```bash
VAULT_TOKEN=$(cat $HOME/.vault-token) ansible-navigator run playbooks/stage-2c/container-platform-ocp4/21-post-install.yml -i inventories/corp/inventory.yml -l ocp -e install_agent_hashi_vault_auth_method=token -e approve_all=true
```

### Destroy
```bash
VAULT_TOKEN=$(cat $HOME/.vault-token) ansible-navigator run playbooks/stage-2c/container-platform-ocp4/99-ocp-destroy.yml -i inventories/corp/inventory.yml -l ocp -e install_agent_hashi_vault_auth_method=token
```

---

## Secrets

- **Do not commit secrets.**
- Use:
  - Ansible Vault (`ANSIBLE_VAULT_PASSWORD_FILE`)
  - SOPS or your preferred secret store
=======
- First run (`vault_bootstrap`): Vault init runs on the target; the init payload is kept in memory for unseal and root token, and the encrypted init file is written to the target.
- Subsequent runs: unseal/root token come from vaulted inventory vars (`vault_init.*`, e.g. `group_vars/wunderboxes/vault-init.yml`). The runbooks do not read the encrypted init file on the target.
- `vault_config` creates AppRole roles and stores credentials in Vault KV at:
  - `stage-2c/<inventory_hostname>/nexus/approle-kv`
  - `stage-2c/<inventory_hostname>/nexus/approle-pki`
- `nexus` reads AppRole credentials from those KV paths at runtime. It needs
  the vaulted `vault_token` inventory variable, or `VAULT_TOKEN` as a local
  override, with read access.

Best practice: use a short-lived, least-privilege token for KV read + PKI issue, not a root token.

### Runtime secret inputs

- Required at runtime, depending on runbook:
  - `ANSIBLE_VAULT_PASSWORD_FILE`
  - vaulted `vault_token`, or `VAULT_TOKEN` as a local override
- Do not commit secret values to the repository.

## Related Docs

- `lcp-docs/30-modulix/30-runbooks/00-index.md`
>>>>>>> origin/develop
