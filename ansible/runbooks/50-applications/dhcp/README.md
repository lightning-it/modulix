# DHCP Runbooks

Deploy DHCP as a rootful Podman kube-play application.

Use `10-deploy.yml` when the target inventory and required `dhcp_deploy_*`
variables are already defined by the environment inventory.

The runbook defaults to the `dhcp` inventory group. To target a single host,
pass `-e dhcp_target=<fqdn>`.

Production use fails closed until the inventory sets the
`dhcp_deploy_production_*` variables. The validation record must prove:

- RHEL-first validation.
- Target Ubuntu validation with the exact Podman, firewall, and network stack.
- L2/broadcast behavior.
- Lease persistence.
- Reboot recovery.
- Renewal behavior.
- Backup/failover expectations.
- No-rogue-DHCP checks.

The `lit.supplementary.dhcp_deploy` role deploys only the Podman kube-play path.
