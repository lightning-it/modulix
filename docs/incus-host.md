# Incus Host

`modulix-automation` can configure Ubuntu hosts as Incus hosts for system
containers and virtual machines.

The best platform description is **Incus host** or **Incus virtualization host**.
Incus manages containers and VMs. For VM workloads, the actual hardware
virtualization path is QEMU/KVM, so avoid calling Incus itself "the hypervisor"
when precision matters.

The standalone operational entrypoint is:

```text
ansible/runbooks/40-platforms/incus/10-host-setup.yml
```

GitHub Actions runners can also consume this host capability through:

```text
ansible/runbooks/50-applications/github-runner/10-setup.yml
```

## Role Shape

`lit.ubuntu.incus` is a host capability role. It owns local host setup:

- Incus and QEMU package installation
- Incus systemd services
- minimal Incus initialization
- local runtime group membership, for example `incus-admin` and `kvm`

It is not a configuration-as-code role. It does not manage Incus projects,
profiles, networks, storage pools, images, or instances beyond minimal local
initialization. Those would be separate roles if needed later, for example:

- `incus_config`: host-local Incus daemon, storage, network, and profile config
- `incus_image`: local image import and lifecycle
- `incus_instance`: container or VM instance lifecycle

## Inventory Contract

Target standalone Incus hosts must be in the `incus_hosts` inventory group.

Example inventory variables:

```yaml
incus_enabled: true
incus_initialize: true
incus_users:
  - litadm
  - github-runner
incus_user_groups:
  - incus-admin
  - kvm
```

`incus_users` is optional. Use it for operator or service accounts that should
run Incus commands without `sudo`.

## Nested Virtualization

Incus VMs require KVM on the host. On vSphere or another virtualization
platform, nested virtualization must be enabled for the VM that will become the
Incus host.

Useful checks on the target host:

```bash
ls -l /dev/kvm
grep -E -m1 'vmx|svm' /proc/cpuinfo
incus info
```

If `/dev/kvm` is missing, Incus containers can still be useful, but Incus VMs
will not run with hardware virtualization.

## Execution

Run with the standard ModuLix Ansible wrapper:

```bash
cd ansible

./scripts/ansible-nav run \
  runbooks/40-platforms/incus/10-host-setup.yml \
  -i inventories/<env>/inventory.yml \
  --limit <incus-host-or-group>
```

When using an external inventory checkout:

```bash
cd ansible

./scripts/ansible-nav run \
  runbooks/40-platforms/incus/10-host-setup.yml \
  -i /path/to/inventories/<env>/inventory.yml \
  --limit <incus-host-or-group>
```
