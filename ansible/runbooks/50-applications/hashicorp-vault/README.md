# HashiCorp Vault Runbooks

This application area contains runbooks for HashiCorp Vault deployment and
configuration.

Use `10-deploy.yml` when the target inventory and required Vault variables are
already defined by the environment inventory.

```bash
ansible-playbook -i inventories/corp/inventory.yml \
  -e "vault_target=vault.example.com" \
  ansible/runbooks/50-applications/hashicorp-vault/10-deploy.yml
```
