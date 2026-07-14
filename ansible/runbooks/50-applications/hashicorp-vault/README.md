# HashiCorp Vault Runbooks

This application area contains runbooks for HashiCorp Vault deployment and
configuration.

The guarded bare-metal lifecycle entrypoints live under
`30-operating-systems/ubuntu/24/15-vault-plan.yml` through
`19-tang-reboot-acceptance.yml`. They provide immutable plan hashes, explicit
confirmations, controller-local TLS validation, scoped AppRole bootstrap,
encrypted initialization escrow, and Raft snapshot/restore-drill gates. See
the Ubuntu 24 runbook README in that directory for the required order and
recovery behavior.

Use `10-deploy.yml` when the target inventory and required Vault variables are
already defined by the environment inventory.

```bash
ansible-playbook -i inventories/corp/inventory.yml \
  -e "vault_target=vault.example.com" \
  ansible/runbooks/50-applications/hashicorp-vault/10-deploy.yml
```
