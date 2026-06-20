# AIO Semaphore Stack

Deploy one Ubuntu host as a small AIO for Semaphore and PostgreSQL only.

The runbook uses `services.aio.<service>` inventory values, with
`aio_service_<service>` variables as per-run overrides. Broader platform
applications such as Vault, Nessus, Nexus, Forgejo, Keycloak, CoreDNS, and DHCP
belong to the Wunderbox runbook.
