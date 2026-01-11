# Ansible automation

This repo uses **ansible-navigator** with the **Wunder devtools execution environment** to avoid local
tooling dependencies.

---

## Prerequisites: Ansible Collections

Playbooks in this repository depend on additional Ansible Collections (e.g. `lit.foundational`).
They must be installed into the local vendor directory **before** running playbooks:

### Install / update required collections

If you have `ansible-galaxy` locally:

```bash
ansible-galaxy collection install -r collections/requirements.yml -p ./collections --force
```

### Verify installed collections

Example check for the vSphere role:

```bash
ls -la collections/ansible_collections/lit/foundational/roles/vmware_vsphere
```

---

## ansible-navigator configuration

The bundled `ansible-navigator.yml` config:
- Enables the execution environment via Docker
- Uses `quay.io/l-it/ee-wunder-ansible-ubi9:v1.2.0`
- (Optional) mounts the Docker socket for roles that need it
- Passes `ANSIBLE_CONFIG` and `ANSIBLE_VAULT_PASSWORD_FILE`
- Disables playbook artifacts and uses stdout mode

---

## Running playbooks

01 vSphere ESXi config:

```bash
ansible-navigator run playbooks/stage-1/infrastructure-platform-vsphere/01-esxi-os_install.yml \
  -i inventories/corp/inventory.yml --limit vsphere_esxi
```

02 vSphere ESXi setup:
```bash
ansible-navigator run playbooks/stage-1/infrastructure-platform-vsphere/02-esxi-setup.yml \
  -i inventories/corp/inventory.yml --limit vsphere_esxi
```

Example (vSphere VM template provisioning):

```bash
ansible-navigator run playbooks/stage-1/infrastructure-platform-vsphere/20-vm-template.yml \
  -i inventories/corp/inventory.yml --limit fw01.prd.com.corp.l-it.io

ansible-navigator run playbooks/stage-1/infrastructure-platform-vsphere/20-vm-template.yml \
  -i inventories/corp/inventory.yml --limit workstation01.prd.com.corp.l-it.io
```

02 vSphere ESXi setup:

```bash
ansible-navigator run playbooks/stage-1/infrastructure-platform-vsphere/02-esxi-setup.yml \
  -i inventories/corp/inventory.yml --limit vsphere_esxi
```

03 OS - RHEL 9 setup:

```bash
ansible-navigator run playbooks/stage-2a/traditional-operating-systems/rhel9/01-base-setup.yml \
  -i inventories/corp/inventory.yml --limit fw01.prd.com.corp.l-it.io

ansible-navigator run playbooks/stage-2a/traditional-operating-systems/rhel9/01-base-setup.yml \
  -i inventories/corp/inventory.yml --limit workstation01.prd.com.corp.l-it.io
```

10 Firewall setup:

```bash
ansible-navigator run playbooks/stage-2b/core-tenant/01-firewall.yml \
  -i inventories/corp/inventory.yml --limit fw01.prd.com.corp.l-it.io
```

---

## Inventory and roles

- Inventory: `inventories/corp/inventory.yml`
- Roles path: `./roles` (set in `ansible.cfg`)
- Adjust vars in `group_vars/` and `host_vars/` as needed.

---

## Secrets

- **Do not commit secrets.**
- Use:
  - Environment variables (e.g. `{{ lookup('env','VCENTER_USERNAME') }}`)
  - Ansible Vault (`ANSIBLE_VAULT_PASSWORD_FILE`)
  - SOPS or your preferred secret store
