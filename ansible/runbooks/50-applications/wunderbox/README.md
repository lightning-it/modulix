# Wunderbox Runbook

The Wunderbox runbook composes the single-node application platform services
for hosts in the `wunderboxes` inventory group. It is intentionally
inventory-driven: the playbook selects roles, while service enablement,
hostnames, ports, credentials, databases, and cross-service wiring come from
inventory variables.

`10-deploy.yml` can deploy and configure these service families:

- Core platform: repositories, firewall, CoreDNS, DHCP, and NGINX.
- Secret and state services: HashiCorp Vault and MinIO.
- Application services: Nexus, Nessus, Forgejo, and Keycloak.
- Monitoring and logging services may be exposed through the same gateway when
  inventory enables Grafana or Checkmk.
- Day-2 configuration roles such as Vault config, MinIO config/bootstrap,
  Nessus CaC, Forgejo CaC, Keycloak CaC, and Nexus initial
  config.

## Orchestration Safety Boundary

Every runbook requires an exact `--limit` equal to the one inventory FQDN.
Patterns, groups, and multi-host selections are refused. The connected host,
the Ansible destination, and a runtime target confirmation must all match the
inventory-declared target ID, FQDN, IPv4 address, and provider ID.

The public inventory contract is:

```yaml
wunderbox_orchestration:
  schema_version: 1
  enabled: false
  target:
    id: asset-placeholder
    fqdn: wunderbox.example.invalid
    ipv4: 192.0.2.10
    provider_id: provider-resource-placeholder
  gate:
    id: change-gate-placeholder
    required_status: approved
  approval_tokens:
    prepare_sha256: disabled
    deploy_sha256: disabled
    retirement_sha256: disabled
  retirement:
    allowed: false
```

`wunderbox_request_target` is a runtime-only mapping with the same four target
fields. It must be injected at higher precedence for every invocation; do not
copy it into the expected inventory contract. A productive run additionally
requires `wunderbox_orchestration_action: apply`, a runtime-only
`wunderbox_request_gate` containing `id` and `observed_status`, and the matching
phase approval token. The inventory stores only the expected lowercase SHA-256
digest, never the supplied token.

The default action is `plan`. Both plan action and Ansible check mode run the
identity guard and deployment preflight, then end before any preparation,
deployment, or retirement role. Check mode is therefore a safety preflight,
not a simulated change report from the composed roles.

## Runbooks

- `05-prepare.yml`: plan or apply optional repos and firewall policy; apply
  requires the prepare approval.
- `07-preflight.yml`: read-only target, service inventory, runtime, and guarded
  DHCP validation.
- `10-deploy.yml`: always import `07-preflight.yml` before the guarded deploy
  play; apply requires the deploy approval.
- `20-ops.yml`: inspect Wunderbox runtime status without changing it.
- `30-management-services.yml`: deploy Keycloak, NetBox, Guacamole, the public
  NGINX gateway, or Alloy independently on one exact host. Application secrets
  are read-before-generate in HC Vault and never written to local fallback files.
  Productive NGINX and Alloy applies fail closed until their inventory-declared
  DNS/TLS and mTLS prerequisites are complete.
- `31-management-backup.yml`: create one service database dump, encrypt it
  client-side with the controller's Ansible Vault custody, upload only the
  ciphertext to the protected S3 bucket, and remove the transient plaintext.
  Backup apply is blocked until Vault-backed S3 credentials and controller
  encryption custody are explicitly attested in inventory.
- `32-management-restore-drill.yml`: require a ciphertext-bound confirmation,
  restore into a disposable database, verify its catalog, and always remove the
  disposable database and plaintext staging files.
- `33-management-acceptance.yml`: read back internal health, public HTTPS, and
  listener isolation for one management target or the complete Goal 07 stack.

Semaphore retirement is disabled unless all of these conditions hold:

- the service is disabled in inventory;
- `wunderbox_orchestration.retirement.allowed` is explicitly `true`;
- the runtime-only `wunderbox_retirement_requested` value is the Boolean
  `true` during a non-check deploy apply; and
- the separate retirement approval token matches its inventory hash.

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
    forgejo_deploy: enabled
    keycloak_deploy: enabled
    loki_deploy: enabled
    alloy_deploy: enabled
    grafana_deploy: enabled
    checkmk_deploy: enabled
    netbox_deploy: enabled
    guacamole_deploy: enabled
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
| Forgejo | `https://forgejo.example.invalid` | Forgejo admin/user credentials from Vault-backed vars |
| Keycloak | `https://keycloak.example.invalid` | Realm user or admin credentials from Vault-backed vars |
| NetBox | `https://netbox.example.invalid` | Keycloak OIDC or local break-glass account from Vault |
| Guacamole | `https://guacamole.example.invalid/guacamole/` | Keycloak OIDC or local break-glass account from Vault |
| Grafana | `https://grafana.example.invalid` | Grafana admin credentials from Vault-backed vars |
| Checkmk | `https://checkmk.example.invalid` | Checkmk admin credentials from Vault-backed vars |
| PostgreSQL | `postgresql://postgres.example.invalid:5432` | Database credentials from Vault-backed vars |
| DHCP | L2 network service, no browser URL | No user login |

## Verification

At the end of the playbook, the `wunderbox_verify` tag checks enabled HTTP
endpoints from the control node. Current checks cover CoreDNS, NGINX, Vault,
MinIO, Nexus, Nessus, Forgejo, Keycloak, Grafana, and Checkmk.

Tag selection does not bypass the imported deployment preflight. Endpoint-only
verification through the deploy runbook remains behind the same exact target
and deployment approval boundary.

DHCP is guarded by explicit production validation variables because it depends
on L2/broadcast behavior. Keep DHCP disabled until network validation evidence
exists in inventory.

## Secret Handling

Do not place plaintext credentials in this runbook. When HC Vault is in use,
roles must read existing values first, generate only missing values, write them
back to Vault, and consume the resulting Vault-backed variables. When HC Vault
is not in use, provide required values through Ansible Vault encrypted
inventory.
