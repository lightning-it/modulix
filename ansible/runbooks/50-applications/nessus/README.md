# Nessus

Deploy Nessus as a Podman kube-play application.

```bash
ansible-playbook -i inventories/corp/inventory.yml \
  -e "nessus_target=nessus.example.com" \
  ansible/runbooks/50-applications/nessus/10-deploy.yml
```
