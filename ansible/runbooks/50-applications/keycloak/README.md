# Keycloak Runbooks

Deploy and configure Keycloak.

Use `10-deploy.yml` when the target inventory and required Keycloak deployment
variables are already defined by the environment inventory. Use `10-config.yml`
for the older configuration-only flow.

The deploy runbook defaults to the `keycloak` inventory group. To target a
single host, pass `-e keycloak_target=<fqdn>`.
