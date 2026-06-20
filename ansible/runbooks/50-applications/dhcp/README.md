# DHCP Runbooks

Deploy DHCP as a rootful Podman kube-play application.

Use `10-deploy.yml` when the target inventory and required DHCP kube variables
are already defined by the environment inventory.

The runbook defaults to the `dhcp` inventory group. To target a single host,
pass `-e dhcp_target=<fqdn>`.

Production use requires a successful RHEL validation first, then Ubuntu
validation with the exact target Podman, firewall, and network stack.
