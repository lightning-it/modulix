# Wunderbox Runbook

The Wunderbox runbook composes the single-node application platform services
for hosts in the `wunderboxes` inventory group. It is intentionally
inventory-driven: the playbook selects roles, while service enablement,
hostnames, ports, credentials, databases, and cross-service wiring come from
inventory variables.

`10-deploy.yml` can deploy and configure these service families:

- Core platform: repositories, firewall, CoreDNS, DHCP, and NGINX.
- Secret and state services: HashiCorp Vault and MinIO.
- Application services: Nexus, Nessus, PostgreSQL, Semaphore, Forgejo, and
  Keycloak.
- Monitoring and logging services may be exposed through the same gateway when
  inventory enables Grafana or Checkmk.
- Day-2 configuration roles such as Vault config, MinIO config/bootstrap,
  Nessus CaC, Semaphore CaC, Forgejo CaC, Keycloak CaC, and Nexus initial
  config.

## Run

```bash
ansible-playbook -i inventory.yml \
  ansible/runbooks/50-applications/wunderbox/10-deploy.yml
```

Enable services through inventory:

```yaml
services:
  wunderbox:
    coredns: enabled
    nginx_deploy: enabled
    nginx_config: enabled
    vault_deploy: enabled
    vault_bootstrap: enabled
    vault_validate: enabled
    minio_deploy: enabled
    minio_config: enabled
    nexus_deploy: enabled
    nessus_deploy: enabled
    postgres_deploy: enabled
    semaphore_deploy: enabled
    forgejo_deploy: enabled
    keycloak_deploy: enabled
    grafana_deploy: enabled
    checkmk_deploy: enabled
```

Per-service overrides may also use `wunderbox_service_<service>: enabled` or
`disabled`.

## Example Endpoints

The table below uses `example.invalid` as a documentation-only domain. Real
hostnames and credentials must come from inventory, HC Vault, or Ansible Vault.

| Service | Example URL | Login |
|---|---|---|
| NGINX gateway | `https://example.invalid` | No direct application login |
| CoreDNS health | `http://dns.example.invalid:8082/health` | No login |
| Vault | `https://vault.example.invalid` | Vault token or configured auth method |
| MinIO API | `https://minio.example.invalid` | Access key and secret key from Vault-backed vars |
| MinIO console | `https://minio-console.example.invalid` | MinIO root or delegated user from Vault-backed vars |
| Nexus | `https://nexus.example.invalid` | Nexus admin/user credentials from Vault-backed vars |
| Nessus | `https://nessus.example.invalid` | Nessus admin credentials from Vault-backed vars |
| Semaphore | `https://semaphore.example.invalid` | Semaphore admin/user credentials from Vault-backed vars |
| Forgejo | `https://forgejo.example.invalid` | Forgejo admin/user credentials from Vault-backed vars |
| Keycloak | `https://keycloak.example.invalid` | Realm user or admin credentials from Vault-backed vars |
| Grafana | `https://grafana.example.invalid` | Grafana admin credentials from Vault-backed vars |
| Checkmk | `https://checkmk.example.invalid` | Checkmk admin credentials from Vault-backed vars |
| PostgreSQL | `postgresql://postgres.example.invalid:5432` | Database credentials from Vault-backed vars |
| DHCP | L2 network service, no browser URL | No user login |

## Verification

At the end of the playbook, the `wunderbox_verify` tag checks enabled HTTP
endpoints from the control node. Current checks cover CoreDNS, NGINX, Vault,
MinIO, Nexus, Nessus, Forgejo, Keycloak, Grafana, and Checkmk.

```bash
ansible-playbook -i inventory.yml \
  ansible/runbooks/50-applications/wunderbox/10-deploy.yml \
  --tags wunderbox_verify
```

DHCP is guarded by explicit production validation variables because it depends
on L2/broadcast behavior. Keep DHCP disabled until network validation evidence
exists in inventory.

## Secret Handling

Do not place plaintext credentials in this runbook. When HC Vault is in use,
roles must read existing values first, generate only missing values, write them
back to Vault, and consume the resulting Vault-backed variables. When HC Vault
is not in use, provide required values through Ansible Vault encrypted
inventory.
