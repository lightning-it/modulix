# Inventory baseline

This repository ships only a dummy inventory baseline.
Environment-specific inventory data is platform-owned and must be provided per deployment environment.

Default placeholder path:
- `inventories/example/inventory.yml`

## Wunderbox service toggles

`playbooks/stage-2b/12-wunderbox.yml` supports per-task service toggles from inventory.

Preferred structure:

```yaml
all:
  vars:
    services:
      wunderbox:
        repos: enabled
        firewall: enabled
        coredns: enabled
        dhcp: enabled
        nginx_deploy: enabled
        vault_deploy: enabled
        vault_bootstrap: enabled
        vault_validate: enabled
        vault_ops: enabled
        vault_config: enabled
        minio_deploy: enabled
        minio_config: enabled
        minio_bootstrap: enabled
        nexus_deploy: enabled
        nginx_config: enabled
        nexus_config: enabled
```

Accepted values:
- enabled: `enabled`, `true`, `yes`, `on`, `1`, `y`
- disabled: anything else (for example `disabled` / `false`)

If a toggle is not set, it is treated as disabled.

Flat overrides are also supported for compatibility, for example:
- `wunderbox_service_repos: enabled`
- `wunderbox_service_vault_config: disabled`

## Generic Firewall Policy Rules

`playbooks/stage-2b/10-firewall.yml` supports a generic inventory dict for additional
inter-zone policy rules.

```yaml
firewall_policy_rules:
  policies:
    ocpmgmt-to-vcenter:
      enabled: true
      ingress_zones:
        - lan
      egress_zones:
        - mgmt
      target: ACCEPT
      rich_rules:
        - rule family=ipv4 source address=10.34.20.0/24 destination address=10.10.30.10 port port=443 protocol=tcp accept
```

Key structure:
- `firewall_policy_rules` is the inventory variable (top-level in host/group vars)
- `firewall_policy_rules.policies` is optional (dict of firewalld policies)
- `firewall_policy_rules.zone_forwards` is optional (list of zone forward toggles)

Optional nested key example (`zone_forwards` inside `firewall_policy_rules`):

```yaml
firewall_policy_rules:
  zone_forwards:
    - zone: lan
      enabled: true
```

Full example:

```yaml
firewall_policy_rules:
  zone_forwards:
    - zone: lan
      enabled: true
  policies:
    lan-to-wan:
      enabled: true
      ingress_zones:
        - lan
      egress_zones:
        - wan
      target: ACCEPT
    ocpmgmt-to-vcenter:
      enabled: true
      ingress_zones:
        - lan
      egress_zones:
        - mgmt
      rich_rules:
        - rule family=ipv4 source address=10.34.20.0/24 destination address=10.10.30.10 port port=443 protocol=tcp accept
```
