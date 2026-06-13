# Runbooks

Runbooks are the operational entrypoints for ModuLix platform execution.

Collections provide reusable roles and examples. This repository uses
runbooks to define the supported order, scope, and inventory contract for real
platform operations such as VM provisioning, service rebuilds, tenant setup, and
container platform tasks.

Directory model:

- `infrastructure/`: physical or virtual infrastructure provisioning.
- `base-os/`: operating system baselines and hardening.
- `container-platforms/`: container platform substrates such as OpenShift.
- `services/`: service and host-profile configuration.
- `workflows/`: multi-step operational flows that import other runbooks.
- `common/`: shared helper runbooks and examples.

Keep runbooks thin: they should orchestrate roles and import other runbooks,
while environment-specific decisions stay in inventory.
