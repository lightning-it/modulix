# Ansible automation

This repo uses **ansible-navigator** with the **Wunder devtools execution environment** to avoid local
tooling dependencies.

---

## ansible-navigator configuration

The bundled `ansible-navigator.yml` config:
- Enables the execution environment via Docker
- Uses `quay.io/l-it/ee-wunder-ansible-ubi9:v1.2.0`
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

---

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

ansible-navigator run playbooks/stage-2b/core-tenant/01-firewall.yml \
  -i inventories/corp/inventory.yml --limit fw01.prd.dmz.corp.l-it.io
```

10.2 COM

```bash
ansible-navigator run playbooks/stage-2a/traditional-operating-systems/rhel9/01-base-setup.yml \
  -i inventories/corp/inventory.yml --limit fw01.prd.com.corp.l-it.io

ansible-navigator run playbooks/stage-2b/core-tenant/01-firewall.yml \
  -i inventories/corp/inventory.yml --limit fw01.prd.com.corp.l-it.io
```

10.3 INT

```bash
ansible-navigator run playbooks/stage-2a/traditional-operating-systems/rhel9/01-base-setup.yml \
  -i inventories/corp/inventory.yml --limit fw01.prd.int.corp.l-it.io

ansible-navigator run playbooks/stage-2b/core-tenant/01-firewall.yml \
  -i inventories/corp/inventory.yml --limit fw01.prd.int.corp.l-it.io
```

10.4 ISO

```bash
ansible-navigator run playbooks/stage-2a/traditional-operating-systems/rhel9/01-base-setup.yml \
  -i inventories/corp/inventory.yml --limit fw01.prd.iso.corp.l-it.io

ansible-navigator run playbooks/stage-2b/core-tenant/01-firewall.yml \
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
ansible-navigator run playbooks/stage-1/infrastructure-platform-vsphere/20-vm-template.yml \
  -i inventories/corp/inventory.yml --limit wunderbox01.prd.dmz.corp.l-it.io

ansible-navigator run playbooks/stage-2a/traditional-operating-systems/rhel9/01-base-setup.yml \
  -i inventories/corp/inventory.yml --limit wunderbox01.prd.dmz.corp.l-it.io

ansible-navigator run playbooks/stage-2b/12-wunderbox.yml \
  -i inventories/corp/inventory.yml --limit wunderbox01.prd.dmz.corp.l-it.io
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
