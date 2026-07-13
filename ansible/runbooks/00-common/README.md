# Common Runbooks

The `tasks/` directory contains shared task helpers used across capability
layers. These are implementation helpers rather than standalone entrypoints.

## VAULT login

```bash
VAULT_ADDR=https://ansible03.core.corp.l-it.io:8201 vault login
```

## Print all vars

```bash
ansible-navigator run runbooks/00-common/print_all_vars.yml -i inventory/ --m stdout
```
