# Runbooks

Runbooks are reusable operational capability entrypoints for ModuLix platform
execution.

Collections provide reusable roles and examples. This public repository keeps
runbooks focused on capabilities such as VM provisioning, base OS setup,
service configuration, tenant setup, and container platform tasks.

Customer-specific workflow composition, rollout order, and delivery procedures
belong in private `modulix-operations-*` repositories.

Directory model:

- `infrastructure/`: physical or virtual infrastructure provisioning.
- `base-os/`: operating system baselines and hardening.
- `container-platforms/`: container platform substrates such as OpenShift.
- `services/`: service and host-profile configuration.
- `common/`: shared helper runbooks and examples.

Keep runbooks thin: they should orchestrate roles for one capability area,
while environment-specific decisions stay in inventory and customer-specific
workflow composition stays private.
