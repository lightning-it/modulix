# Ubuntu 24 Bare-Metal Lifecycle

These runbooks turn an already selected Hetzner bare-metal target into an
Ubuntu 24.04 host with encrypted-root recovery, managed OpenSSH, optional
Clevis/Tang unlock, and a guarded HashiCorp Vault lifecycle. Compute-provider
operations remain in `10-compute/baremetal/hetzner/`.

## Required order

1. Run the Hetzner Robot credential, recovery-secret, Rescue validation, and
   installation plan from the provider directory.
2. Use `09-prepare-installimage.yml` only to stage the Ubuntu-specific
   encrypted-root installation hook consumed by the generic installer.
3. Complete first-boot recovery and `01-base-setup.yml`.
4. Use `02-openssh-transition.yml` to move from the bootstrap port to the
   inventory-declared managed port. The transition keeps both ports only for
   the bounded handoff and verifies the managed connection before removing the
   bootstrap listener.
5. Run `13-luks-header-bootstrap-escrow.yml` or
   `13-luks-header-backup.yml`, according to the declared secret backend,
   before any keyslot change.
6. Run `11-luks-unlock.yml` to configure the explicitly selected unlock
   method, then `14-installed-acceptance.yml`.
7. Use the Vault and Tang gates below only after the host baseline and recovery
   evidence pass.

## Vault lifecycle gates

- `15-vault-plan.yml` writes a fresh immutable plan and prints its SHA-256.
- `16-vault-deploy.yml` requires `DEPLOY_VAULT:<host>:<sha256>` and deploys an
  uninitialized, loopback-bound Vault runtime.
- `17-vault-initialize.yml` requires
  `INITIALIZE_VAULT:<host>:<sha256>`, initializes once, escrows the Shamir
  material as Ansible Vault ciphertext, creates a scoped batch AppRole, and
  revokes the initial root token after validation.
- `17-vault-initialize-resume.yml` resumes an interrupted initialization from
  the immutable escrow without initializing again.
- `17-vault-initialize-finalize.yml` validates or repairs the approved legacy
  AppRole document and completes root-token revocation.
- `17-vault-scoped-auth-validate.yml` proves the stored AppRole still has the
  exact policy and that the initial root token is revoked.
- `18-vault-raft-snapshot.yml` performs an encrypted snapshot backup or a
  separately confirmed restore drill.
- `19-tang-reboot-acceptance.yml` proves one non-Tang client can reboot through
  the pinned live Tang trust path.

Each mutating gate requires one exact host limit, a fresh plan, the matching
plan SHA-256, and the operation-specific confirmation. Never reuse an approval
after inventory, image, TLS, policy, escrow, or runtime evidence changes.

## Controller security contract

Controller ciphertext, CA, SSH identity, known-hosts, and plan paths must be
absolute, canonical, non-linked, owned by root or the controller user, and
protected from group/world writes. Inventory declares the loaded Ansible Vault
identity label as `hetzner_baremetal_ansible_vault.vault_id`; password material
is loaded by Ansible and is never supplied to a role or task argument.

Vault remains bound to loopback. Runbooks open a bounded controller-local SSH
forward through the managed host identity, validate the pinned host key and CA,
and close the master socket and listener in an `always` cleanup path. Exported
`VAULT_ADDR`, `VAULT_TOKEN`, or TLS-bypass values are rejected for this flow.

## Failure and recovery

- If deployment fails before initialization, correct the cause, create a new
  plan, and rerun deployment. Do not initialize an unvalidated runtime.
- If initialization is interrupted after escrow, use the resume gate. Never
  run a second initialization against an already initialized Vault.
- If finalization fails, preserve both encrypted initialization and AppRole
  documents and use the finalize gate with a new plan.
- Snapshot restore is a drill-only, separately confirmed path. A lexical path
  match is not sufficient; the selected ciphertext and all ancestors must pass
  canonical ownership, link, mode, size, and checksum validation.
- A Tang reboot timeout is failure. Recover with the independent encrypted
  recovery passphrase, then diagnose networking and trust without replacing
  the Vault pin or LUKS header evidence.
