# Hetzner Bare-Metal Runbooks

These runbooks manage Hetzner Robot, Rescue, hardware validation, recovery
escrow needed during provisioning, and guarded `installimage` execution. The
provider lifecycle is independent of the selected operating-system image.

The main entrypoints are:

- `07-robot-credentials.yml`: create or verify the encrypted Robot credential
  document.
- `08-recovery-secrets.yml`: create or verify per-host encrypted-root recovery
  secrets used during installation.
- `08-recovery-secrets-migrate.yml`: migrate bootstrap recovery documents to
  the declared HashiCorp Vault backend.
- `09-rescue-preflight.yml`: validate Robot, Rescue, network, and hardware
  prerequisites.
- `09-rescue-extended-smart.yml`: run a separately authorized extended SMART
  workflow.
- `09-robot-ops.yml`: perform one explicitly authorized Robot lifecycle
  operation.
- `10-installimage.yml`: plan or execute an inventory-selected operating-system
  installation.

## Operating-system adapters

Inventory must declare the exact `hetzner_installimage_image` and
`hetzner_installimage_expected_image_sha256`. An optional
`hetzner_installimage_expected_os_release` mapping with `id` and `version_id`
lets ordered-install checks validate an already-installed predecessor.

Operating-system-specific post-install preparation stays in
`30-operating-systems/`. For example, Ubuntu encrypted-root installations run
`30-operating-systems/ubuntu/24/09-prepare-installimage.yml` before
both plan and install. That runbook stages the Ubuntu Dropbear/initramfs hook;
inventory exposes its absolute path as
`hetzner_installimage_post_install_script_path` and marks the staged artifact
with `hetzner_installimage_post_install_script_ephemeral: true`. The provider
runbook removes only a path carrying that explicit ownership marker. A Fedora
workflow can stage a Fedora-specific hook while using the same provider
runbook; persistent caller-managed hooks must leave the marker false.

The generic installer does not reboot. First boot, encrypted-root unlock, OS
baseline configuration, and hardening remain operating-system concerns.
