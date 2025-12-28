# Ansible automation

This repo uses ansible-navigator with the Wunder devtools execution environment to avoid local dependencies

## Running playbooks

Example (vSphere ESXi config):
```bash
ansible-navigator run playbooks/stage-1/infrastructure-platform-vsphere/02-esxi-config.yml \
  -i inventories/corp/inventory.yml
```

The bundled `ansible-navigator.yml` config:
- Enables the execution environment via Docker
- Uses `ghcr.io/lightning-it/wunder-devtools-ee:v1.1.3`
- Mounts the Docker socket for any roles that need it
- Passes `ANSIBLE_CONFIG` and `ANSIBLE_VAULT_PASSWORD_FILE`
- Disables playbook artifacts and uses stdout mode

## Inventory and roles
- Inventory: `inventories/corp/inventory.yml`
- Roles path: `./roles` (set in `ansible.cfg`)
- Adjust vars in `group_vars/` and `host_vars/` as needed.
