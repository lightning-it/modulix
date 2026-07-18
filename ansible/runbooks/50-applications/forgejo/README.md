# Forgejo Runbooks

Deploy Forgejo as a Podman kube-play application.

Use `10-deploy.yml` when the target inventory and required Forgejo variables are
already defined by the environment inventory.

The runbook defaults to the `forgejo` inventory group. To target a single host,
pass `-e forgejo_target=<fqdn>`.
