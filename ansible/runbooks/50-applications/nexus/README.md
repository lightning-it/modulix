# Nexus Runbooks

This application area contains runbooks for Sonatype Nexus deployment and
configuration as a Podman kube-play application.

Use `10-deploy.yml` when the target inventory and required Nexus variables are
already defined by the environment inventory.

The runbook defaults to the `nexus` inventory group. To target a single host,
pass `-e nexus_target=<fqdn>`.
