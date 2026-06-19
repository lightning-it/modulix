# Application Runbooks

Application runbooks deploy or configure services that consume compute,
network, operating system, and platform capabilities.

Use this area for:

- AAP
- HashiCorp Vault
- Nexus
- Semaphore
- GitHub and GitLab runners
- workbench and demo services
- identity and integration services

Private end-to-end workflows that combine multiple layers belong in
`modulix-operations-*` repositories.

Workbench runbooks:

- `workbench/10-setup.yml`: legacy RHEL Workbench setup.
- `workbench/20-ubuntu-setup.yml`: Ubuntu Workbench baseline, GUI/RDP, and
  developer tooling setup.
