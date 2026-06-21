# Common Runbooks
## VAULT login
```bash
VAULT_ADDR=https://ansible03.core.corp.l-it.io:8201 vault login
```

## Print all vars
```bash
ansible-navigator run runbooks/00-common/print_all_vars.yml -i inventory/ --m stdout
```
