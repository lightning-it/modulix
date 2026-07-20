# Incus Runbooks

Incus runbooks configure Incus hosts and manage local Incus platform artifacts.

## Runbooks

- `10-host-setup.yml`: install and initialize Incus on Ubuntu hosts.
- `20-image-artifacts.yml`: stage image artifacts from URL/local sources and
  import them into the local Incus image store.
- `30-esxi-image.yml`: stage private nested ESXi artifacts and prepare a local
  Incus image alias such as `local:esxi-packer-ci` for temporary vSphere/Packer
  validation.
- `40-rhel9-vm.yml`: reconcile the Incus daemon ID map and create empty,
  inventory-defined RHEL 9 installation VMs with attached installation media.

`20-image-artifacts.yml` is inventory-driven. Define `artifacts_items` for
downloads/copies and `incus_image_items` for image aliases in the inventory that
owns the environment.

`30-esxi-image.yml` is also inventory-driven. Define `artifacts_items` when the
private ESXi artifact must be copied or downloaded first, then configure
`incus_esxi_image_metadata` plus optional `incus_esxi_image_rootfs`, or configure
`incus_esxi_image_backup`. VMware ESXi media and derived artifacts are private
licensed materials and must not be committed to the automation repositories.

`10-host-setup.yml` and `40-rhel9-vm.yml` run the local
`incus_host_idmap` role before other Incus roles. The role reconciles the
root-owned subordinate UID/GID allocation required by Incus and restarts the
daemon only when that allocation changes.

Use `examples/rhel9-vm.inventory.yml` as the sanitized variable contract for
dedicated VM profiles and RHEL installation VMs. Licensed RHEL media, activation keys, organization IDs,
passwords, and environment hostnames belong in protected environment inventory
or Ansible Vault and must not be committed here. The runbook creates and boots
the VM shell; unattended Kickstart inputs and post-installation snapshots remain
separate lifecycle gates.
