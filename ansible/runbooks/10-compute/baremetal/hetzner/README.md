# Hetzner Bare-Metal Runbooks

These runbooks manage Hetzner Robot, Rescue, hardware validation, recovery
escrow needed during provisioning, and guarded `installimage` execution. The
provider lifecycle is independent of the selected operating-system image.

The main entrypoints are:

- `07-robot-credentials.yml`: create or verify the encrypted Robot credential
  document.
- `08-recovery-secrets.yml`: create or verify per-host encrypted-root recovery
  secrets used during installation. The external `onepassword_cli` option
  supports an independent root-of-trust bootstrap without depending on a Vault
  service hosted by the target being built.
- `08-recovery-secrets-migrate.yml`: migrate bootstrap recovery documents to
  the declared HashiCorp Vault backend.
- `08-robot-credentials-migrate.yml`: migrate the controller-local Robot
  credential document to the declared HashiCorp Vault backend with KV v2 CAS.
- `09-rescue-preflight.yml`: validate Robot, Rescue, network, and hardware
  prerequisites.
- `09-rescue-extended-smart.yml`: run a separately authorized extended SMART
  workflow.
- `09-robot-ops.yml`: perform one explicitly authorized Robot lifecycle
  operation.
- `09-root-of-trust-g0-observe.yml`: observe one exactly selected root of
  trust through read-only Robot server/firewall calls and a forced-check-mode
  vSwitch probe. Unsafe drift is returned as findings; API or identity
  ambiguity remains fatal.
- `09-root-of-trust-g2-plan.yml`: validate the same exact target, complete
  fleet/install order, root-first prerequisite/Tang/Vault placement, and the
  exact bootstrap/hardened Robot firewall plans entirely on the controller.
- `10-robot-firewall-hardened-tang.yml`: apply the separately authorized Robot
  firewall policy used by a Tang endpoint after its trust material is pinned.
- `10-installimage.yml`: plan or execute an inventory-selected operating-system
  installation.

Provider API work stays in collection roles. The runbooks supply inventory
contracts, explicit confirmations, ordering, and postconditions; they do not
carry raw Robot API or firewall/vSwitch request blocks. `community.hrobot` is
the provider dependency used by `lit.foundational` for Robot certificate,
rescue, firewall, and separately gated operational changes.

## Credentials and authorization

Robot credentials begin as one immutable Ansible Vault ciphertext below the
controller workspace `.secrets` directory. Inventory must declare a Vault
identity label in `hetzner_baremetal_ansible_vault.vault_id`. Callers load the
matching identity through Ansible; passwords, tokens, and plaintext documents
must never be passed as extra vars, command-line arguments, or environment
values. After HashiCorp Vault migration, normal provider operations use the
scoped KV v2 document and TLS-validated controller transport.

An independent root-of-trust target selects `onepassword_cli` for two separate
items in the explicitly selected external vault: a Password item for the LUKS
recovery passphrase and an Ed25519 SSH Key item for Dropbear recovery access.
The CLI creates both values inside 1Password. The private SSH key is never
exported; only its public key is installed into the generated initramfs with the
forced `/bin/cryptroot-unlock` command. Each item is immutable in automation:
after initial discovery or creation, inventory must pin its exact item ID and
positive item version, and the SSH item must additionally pin the locally
recomputed SHA-256 public-key fingerprint.

Password and SSH-key creation are separate gates with separate action selectors
and confirmations. Metadata-only output deliberately exposes the non-sensitive
IDs, versions, public key, and fingerprint so they can be reviewed and pinned;
it never exposes a secret. Before installation and every unlock, the exact
1Password Agent socket must both enumerate the pinned public key and complete a
fresh `ssh-keygen -Y sign`/`verify` challenge. The controller rejects service
account, Connect, and shell-session tokens, so only the already unlocked desktop
integration is accepted.

The dedicated unlock action revalidates both item versions, reads the Password
value only through an inherited descriptor, executes an explicitly pinned
non-TTY SSH session with `/bin/cryptroot-unlock`, sends the passphrase without a
newline, and closes stdin to delimit it by EOF. The value never enters Ansible
facts, registered task content, command arguments, environment variables,
process output, logs, Git, or a plaintext file. Creation confirmations are
`CREATE-ONEPASSWORD-SECRET:<inventory-hostname>` and
`CREATE-ONEPASSWORD-SSH-KEY:<inventory-hostname>`; unlock uses
`UNLOCK:<inventory-hostname>`.

Every destructive or availability-affecting runbook requires an exact
`--limit`, operation selector, and fresh confirmation string. Rescue
validation and extended SMART tests remain separate from `09-robot-ops.yml`,
so a read-only validation run cannot implicitly authorize a reset, rescue
activation, or firewall change.

The two root-of-trust gates share this generic inventory selection shape:

```yaml
hetzner_baremetal_root_of_trust:
  schema_version: 1
  selection_scope: single_root_of_trust
  inventory_hostname: root01.example.invalid
  server_lifecycle:
    status: ready
    cancelled: false
```

Both gates require one exact `--limit` equal to `inventory_hostname`. G0
requires Robot credentials because it reads provider state; G2 never resolves
credentials and does not invoke provider, managed-host, secret-backend, or
installimage/G3 operations. The Collection owns all observation and validation
logic; these runbooks only map rendered inventory into the generic role
entrypoints.

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

## Failure and recovery

- A failed preflight changes no provider state. Correct inventory, trust, or
  credentials and rerun the same validation.
- A failed CAS migration never overwrites a document whose version changed;
  re-read and review the current record before retrying.
- A failed `installimage` run must be recovered through the explicit Rescue
  and installation plan flow. Do not bypass the role with ad-hoc Robot calls.
- Extended SMART and Robot operations are intentionally separate gates; rerun
  only the gate whose exact confirmation is still appropriate.
