# AIO Runbooks

Deploy one Ubuntu host as a small AIO for Semaphore and PostgreSQL only.

The runbook uses `services.aio.<service>` inventory values, with
`aio_service_<service>` variables as per-run overrides. Broader platform
applications such as Vault, Nessus, Nexus, Forgejo, Keycloak, CoreDNS, and DHCP
belong to the Wunderbox runbook.

## Runbooks

- `05-prepare.yml`: optionally prepare Ubuntu and Podman substrate.
- `07-preflight.yml`: validate AIO inventory shape and runtime readiness.
- `10-deploy.yml`: deploy the full AIO Semaphore stack.
- `20-ops.yml`: inspect AIO runtime status.
