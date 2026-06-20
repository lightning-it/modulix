# Incus Runbooks

Incus runbooks configure Incus hosts and manage local Incus platform artifacts.

## Runbooks

- `10-host-setup.yml`: install and initialize Incus on Ubuntu hosts.
- `20-image-artifacts.yml`: stage image artifacts from URL/local sources and
  import them into the local Incus image store.
- `30-esxi-image.yml`: stage private nested ESXi artifacts and prepare a local
  Incus image alias such as `local:esxi-packer-ci` for temporary vSphere/Packer
  validation.

`20-image-artifacts.yml` is inventory-driven. Define `artifacts_items` for
downloads/copies and `incus_image_items` for image aliases in the inventory that
owns the environment.

`30-esxi-image.yml` is also inventory-driven. Define `artifacts_items` when the
private ESXi artifact must be copied or downloaded first, then configure
`incus_esxi_image_metadata` plus optional `incus_esxi_image_rootfs`, or configure
`incus_esxi_image_backup`. VMware ESXi media and derived artifacts are private
licensed materials and must not be committed to the automation repositories.
