# Wunderbox

The **Wunderbox** is a RHEL-based “core services” VM (no GUI) that provides internal platform services and stable internal endpoints. It is designed to bootstrap and host foundational services required by other components (e.g., OpenShift installs, automation pipelines, internal developer tooling).

This document covers:
- how to run the Wunderbox automation with **ansible-navigator** and the **Wunder devtools execution environment**
- the Wunderbox playbook flow and **all roles** it invokes
- Vault + MinIO + Nexus integration and tfstate migration (role-internal)
- inventory and secrets handling

---

## Ansible automation (ModuLix)

Wunderbox automation is orchestrated from the **ModuLix** repository (Ansible workspace under `modulix/ansible/`).  
The ModuLix workspace uses **ansible-navigator** with the **Wunder devtools execution environment** to avoid local tooling dependencies.

Repo (public): https://github.com/lightning-it/modulix

---

## ansible-navigator configuration

The bundled `ansible-navigator.yml` config:
- Enables the execution environment via Docker
- Uses `quay.io/l-it/ee-wunder-ansible-ubi9:v1.7.0`
- Mounts the Docker socket for roles that need it
- Passes `ANSIBLE_CONFIG` and `ANSIBLE_VAULT_PASSWORD_FILE`
- Disables playbook artifacts and uses stdout mode

---

## Prerequisites: Ansible Collections (ModuLix workspace)

Playbooks are executed from the ModuLix Ansible workspace and depend on additional Ansible Collections (e.g. `lit.foundational`).  
Install/update collections **in the ModuLix workspace** before running playbooks.

### Install / update required collections

Im Execution Environment (ansible-navigator):

```bash

ansible-navigator exec -- \
  ansible-galaxy collection install \
  -r /runner/project/collections/requirements.yml \
  -p /runner/project/collections --force
```

> Notes:
> - In the execution environment, `/runner/project` is the workspace root mounted into the container.
> - `collections/requirements.yml` is kept versioned; `collections-dev/` is the local vendor directory for installed collections.

---

## Running the Wunderbox playbook

### Wunderbox (VM + RHEL9) setup

```bash
ansible-navigator run playbooks/stage-1/infrastructure-platform-vsphere/20-vm-template.yml \
  -i inventories/corp/inventory.yml --limit wunderbox01.prd.dmz.corp.l-it.io

ansible-navigator run playbooks/stage-2a/traditional-operating-systems/rhel9/01-base-setup.yml \
  -i inventories/corp/inventory.yml --limit wunderbox01.prd.dmz.corp.l-it.io

ansible-navigator run playbooks/stage-2b/12-wunderbox.yml \
  -i inventories/corp/inventory.yml --limit wunderbox01.prd.dmz.corp.l-it.io
```

> Notes:
> - Adjust `--limit` to your Wunderbox FQDN(s).
> - Collections must be installed first (see prerequisites).
> - Secrets must be provided via `ANSIBLE_VAULT_PASSWORD_FILE` or equivalent secret management.

---

## Inventory and roles

- Inventory: `inventories/corp/inventory.yml`
- Roles path: `./roles` (set in `ansible.cfg`)
- Adjust variables in `group_vars/` and `host_vars/` as needed.

---

## Secrets

- **Do not commit secrets.**
- Use:
  - Ansible Vault (`ANSIBLE_VAULT_PASSWORD_FILE`)
  - SOPS or your preferred secret store

---

## Wunderbox playbook: scope and flow

The Wunderbox “core services” playbook configures the following stack on the target VM:

- CoreDNS (internal DNS)
- DHCP (system service; not container-based)
- Vault (secrets + bootstrap control-plane)
- MinIO (S3 backend for Terraform/Terragrunt state and buckets)
- Nexus (artifact repository)
- NGINX (internal reverse proxy / stable endpoints)

### High-level execution order

1. `lit.rhel.repos`
2. `fedora.linux_system_roles.firewall`
3. `lit.supplementary.coredns_deploy`
4. `lit.supplementary.dhcp_deploy`
5. Vault stack:
   - `lit.supplementary.vault_deploy`
   - `lit.supplementary.vault_bootstrap`
   - `lit.supplementary.vault_validate`
   - `lit.supplementary.vault_config`
6. MinIO stack:
   - `lit.supplementary.minio_deploy`
   - `lit.supplementary.minio_bootstrap` *(or `lit.foundational.minio_bootstrap` if you moved it)*
7. `lit.supplementary.nexus`
8. NGINX stack:
   - `lit.supplementary.nginx_deploy`
   - `lit.supplementary.nginx_config`

---

## Role reference

### `lit.rhel.repos`
**Purpose:** Enable required RHEL repositories for the Wunderbox (OS packages and dependencies).  
**Outcome:** The host can install packages required by all subsequent roles.

---

### `fedora.linux_system_roles.firewall`
**Purpose:** Apply host firewall policy *only if explicitly configured*.  
**Guardrail:** Runs only when `firewall` vars are present to prevent accidental resets.  
**Outcome:** Required service ports are reachable according to your policy.

---

### `lit.supplementary.coredns_deploy`
**Purpose:** Deploy CoreDNS as the internal DNS provider for service endpoints.  
**Typical responsibilities:**
- install and configure CoreDNS
- apply zone and/or forwarding configuration (authoritative and/or forwarding)
- enable and start the service

---

### `lit.supplementary.dhcp_deploy`
**Purpose:** Deploy the internal DHCP provider as a **system service** (not container-based).  
**Typical responsibilities:**
- install DHCP service packages
- configure subnet ranges, DHCP options, and reservations
- bind explicitly to the intended interface/VLAN
- enable and start the service

---

### `lit.supplementary.vault_deploy`
**Purpose:** Deploy HashiCorp Vault on the Wunderbox host.  
**Typical responsibilities:**
- install runtime dependencies (e.g., Podman tooling if containerized)
- create host directories (e.g., `/srv/vault/*`) with correct permissions/SELinux labels
- render Vault configuration and systemd service integration
- start Vault and expose its API endpoint

---

### `lit.supplementary.vault_bootstrap`
**Purpose:** Initialize and unseal Vault on first installation; write init output securely.  
**Key behavior:**
- **First run (uninitialized Vault):**
  - runs `vault operator init`
  - unseals Vault
  - writes an **encrypted init file** to the target (never to the repo)
  - exposes token facts for downstream roles within the same run (e.g., `vault_token`)
- **Later runs (already initialized):**
  - does not overwrite init artifacts
  - expects operational tokens/keys from vaulted inventory vars or explicit extra vars

---

### `lit.supplementary.vault_validate`
**Purpose:** Validate Vault health and expected host/runtime state **after** bootstrap.  
**Typical checks:**
- API health / init / seal status
- permissions/SELinux labels (if applicable)
- basic storage access checks (depending on role settings)

---

### `lit.supplementary.vault_config`
**Purpose:** Apply “Vault content” (policies, auth methods, PKI/AppRole, mounts, etc.) using Terraform/Terragrunt.  

**State model (bootstrap):**
- When MinIO is not yet available, the role uses **local state** under:
  - `/srv/vault/bootstrap` (root-only `*.tfstate*`)

**State migration (role-internal):**
- If the remote backend is ready, the role migrates its local state and deletes local `*.tfstate*`.
- If the backend is not ready, it marks `/srv/vault/bootstrap` as pending migration to be processed later by MinIO bootstrap.

---

### `lit.supplementary.minio_deploy`
**Purpose:** Deploy MinIO (S3-compatible object store) as the backend for Terraform/Terragrunt state and buckets.  
**Key behavior:**
- MinIO root credentials are generated at deploy time and stored in Vault (system of record)

---

### `lit.supplementary.minio_bootstrap`
**Purpose:** Create the remote backend primitives required for Terraform state management.  
**Typical responsibilities:**
- create the `tfstate` bucket
- create a dedicated `terraform` user and minimal policy (not managed by Terraform)
- enable bucket versioning (recommended for tfstate)
- store terraform user credentials in Vault
- set backend facts (`tfstate_backend_ready`, endpoint, bucket, creds)
- migrate pending local state dirs (e.g., `/srv/vault/bootstrap`) and delete local `*.tfstate*` on success

---

### `lit.supplementary.nexus`
**Purpose:** Deploy and configure Sonatype Nexus Repository Manager.  
**Integration notes:**
- Nexus can consume Vault-provisioned credentials (recommended)
- Use short-lived, least-privilege Vault tokens for runtime reads; avoid root tokens

---

### `lit.supplementary.nginx_deploy`
**Purpose:** Install and enable NGINX as a base service (no vhost wiring yet).  
**Tag behavior:**
- `nginx_deploy` is also tagged with `nginx_config` so `-t nginx_config` installs + configures in one run.

---

### `lit.supplementary.nginx_config`
**Purpose:** Apply NGINX virtual host and upstream configuration to publish stable internal endpoints on 443.  
**Typical responsibilities:**
- configure vhosts/upstreams for Vault, MinIO (API + console), and Nexus
- reload/restart NGINX safely

---

## Vault + Nexus notes

The Vault bootstrap writes its init output to the target only. The repo must not store secrets.

Recommended flow:
- First run (`vault_bootstrap`): init runs on the target; init payload is used in-memory for unseal and the root token;
  the encrypted init file is written to the target.
- Subsequent runs: unseal/root token come from vaulted inventory vars (e.g. `group_vars/wunderboxes/vault-init.yml`).
  Playbooks do not read/decrypt the encrypted init file on the target.
- `vault_config` creates AppRole roles and stores credentials in Vault KV at:
  - `stage-2c/<inventory_hostname>/nexus/approle-kv`
  - `stage-2c/<inventory_hostname>/nexus/approle-pki`
- `nexus` reads AppRole credentials from those KV paths at runtime. It needs a Vault token with read access.

Best practice: use a short-lived, least-privilege token for KV read + PKI issue, not a root token.

---

## Terraform state and migration to MinIO (tfstate)

### Local state convention (bootstrap)
During initial bootstrap phases, roles that use Terraform/Terragrunt write local state into the component bootstrap root:

- `/srv/vault/bootstrap/*.tfstate*`

### Migration model (role-internal)
State migration must not live in the playbook. Instead:
- `vault_config` marks its bootstrap directory as pending if the backend is not ready.
- `minio_bootstrap` performs the “catch-up” migration once MinIO is ready and deletes local `*.tfstate*` on success.

### Operational controls (recommended)
All migration-related tasks should be tagged consistently:
- `tfstate`
- `tfstate_migrate`

This allows:
- skip migration temporarily:
  - `--skip-tags tfstate_migrate`
- run only migration tasks (when roles support it):
  - `-t tfstate_migrate`

---

## Troubleshooting (quick)

- **Vault validate fails:** ensure `vault_validate` runs after `vault_bootstrap` (it should in the Wunderbox playbook).
- **MinIO bootstrap cannot write to Vault:** verify Vault is unsealed and the required KV mount exists.
- **tfstate migration did not happen:** ensure:
  - local `*.tfstate*` exists in `/srv/vault/bootstrap` root
  - `minio_bootstrap` sets backend facts and runs the catch-up migration
  - migration tasks are not skipped via tags
- **NGINX endpoints not available:** run `-t nginx_config` and confirm firewall rules and DNS.

---
