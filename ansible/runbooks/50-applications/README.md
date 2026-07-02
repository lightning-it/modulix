# Application Runbooks

Application runbooks deploy or configure services that consume compute,
network, operating system, and platform capabilities.

Use this area for:

- AAP
- AIO Semaphore stacks
- HashiCorp Vault
- Nessus
- Nexus
- Semaphore
- GitHub and GitLab runners
- workbench and demo services
- identity and integration services

Private end-to-end workflows that combine multiple layers belong in
`modulix-operations-*` repositories. Use Wunderbox for the broader application
platform stack.

Application-stack runbooks:

- `aio/10-deploy.yml`: Ubuntu Semaphore plus PostgreSQL AIO.
- `atlas/10-deploy.yml`: LIT Atlas observability appliance with Grafana,
  Prometheus, Loki, Alloy, Alertmanager, rsyslog, and Checkmk.
- `wunderbox/10-deploy.yml`: Wunderbox platform applications such as Vault,
  Nessus, Nexus, Forgejo, Keycloak, CoreDNS, and DHCP.

Workbench runbooks:

- `workbench/10-rhel-setup.yml`: RHEL Workbench Podman, Packer, GUI/RDP, and
  developer tooling setup.
- `workbench/20-ubuntu-setup.yml`: Ubuntu Workbench baseline, Podman, Packer,
  GUI/RDP, and developer tooling setup.
