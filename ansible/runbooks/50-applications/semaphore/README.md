# Semaphore Runbooks

Deploy Semaphore UI on Ubuntu application hosts. The runbook configures Ubuntu
netplan first, then deploys Semaphore UI and its optional local PostgreSQL pod
with `lit.supplementary` application roles and Podman kube-play units.

The default target group is `semaphore_hosts`; the corp inventory currently maps
`aio01.prd.dmz.corp.l-it.io` to the `app01` vSphere VM.

## Run

```bash
ansible-playbook -i /path/to/inventory.yml ansible/runbooks/50-applications/semaphore/10-deploy.yml
```
