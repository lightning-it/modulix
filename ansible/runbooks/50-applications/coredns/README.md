# CoreDNS Runbooks

Deploy CoreDNS as a Podman kube-play application.

Use `10-deploy.yml` when the target inventory and required CoreDNS variables are
already defined by the environment inventory.

The runbook defaults to the `coredns` inventory group. To target a single host,
pass `-e coredns_target=<fqdn>`.
