# Runbooks

Runbooks are reusable operational capability entrypoints for ModuLix platform
execution.

Collections provide reusable roles and examples. This public repository keeps
runbooks focused on capabilities such as compute provisioning, network
services, operating system baselines, platform hosts, and application services.

Customer-specific workflow composition, rollout order, and delivery procedures
belong in private `modulix-operations-*` repositories.

Directory model:

- `00-common/`: shared helper runbooks and examples.
- `10-compute/`: bare-metal and virtualization provisioning.
- `20-network/`: network services such as gateway, firewall, DNS, proxy, and VPN.
- `30-operating-systems/`: operating system baselines and hardening.
- `40-platforms/`: platform hosts and substrates such as Incus and OpenShift.
- `50-applications/`: application and service configuration.

Keep runbooks thin: they should orchestrate roles for one capability area,
while environment-specific decisions stay in inventory and customer-specific
workflow composition stays private.
