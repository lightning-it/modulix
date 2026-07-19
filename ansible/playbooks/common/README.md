# common playbook
## VAULT login
```bash
VAULT_ADDR=https://<vault-host>:8200 vault login
```

## Print all vars
```bash
VAULT_TOKEN=$(cat $HOME/.vault-token) ansible-navigator run playbooks/common/print_all_vars.yml -i inventory/ --m stdout -e ins_hashi_vault_auth_method=token
```
