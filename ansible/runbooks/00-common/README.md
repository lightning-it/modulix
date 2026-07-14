# Common Runbooks

The `tasks/` directory contains shared task helpers used across capability
layers. These are implementation helpers rather than standalone entrypoints.

## VAULT login

```bash
VAULT_ADDR=https://vault.example.com:8200 vault login
```

## Print all vars

```bash
ansible-navigator run runbooks/00-common/print_all_vars.yml -i inventory/ --m stdout
```
