# Ubuntu Workbench rollout and acceptance

These playbooks manage only the inventory-enabled Ubuntu Workbench application
layer. They deliberately do not own the OS baseline, encrypted boot, netplan,
automatic updates, firewalld, GUI, Firefox, desktop VS Code, or XRDP.

Every playbook is fail-closed. Inventory must place the target in
`ubuntu_workbenches`, set `workbench_enabled: true`, and declare one exact
`workbench_target_hostname`. Operators must pass that same hostname as the
entire `--limit` value. Group limits, patterns, and multi-host selections are
rejected before a role runs.

## Playbooks

- `20-ubuntu-setup.yml` deploys only explicitly enabled Workbench components.
  It uses `serial: 1` and `any_errors_fatal: true`. Its Incus storage preflight
  creates only an absent, raw, unmounted 128-GiB LV when the encrypted VG has
  enough inventory-declared reserve. It never formats, mounts, resizes, or
  shrinks an LV. On later runs, it accepts Btrfs only when the exact declared
  Incus pool already owns the device and any mount is the expected Incus mount.
- `30-validate.yml` is configuration read-only (it does not install/modify packages, services, or files). It checks developer accounts and workspaces,
  authorized-key counts without returning key content, effective OpenSSH
  policy, pinned tool/Python/npm versions, rootless Podman sockets, the disabled
  privileged Podman socket, Incus/LVM/network/project/profile drift, the exact
  expected instance set, and absence of GitHub Actions runner accounts/services.
- `40-acceptance.yml` dispatches exactly one Tiny, Heavy, or Application
  workflow. Tiny checks the declared tools, rootless Podman, and one ephemeral
  guest. Heavy creates and deletes at least two run-unique guests sequentially,
  reaches each over a temporary SSH inventory, applies a temporary role twice
  with a zero-change second run, and builds/runs/scans a digest-based rootless
  container. Application keeps an Incus test guest running while it checks out
  the approved public repository at the inventory-pinned full commit and runs
  YAML lint, the strict EE Ansible-lint wrapper, collection smoke, and a focused
  Molecule scenario. All temporary resources have ownership-checked `always`
  cleanup.
- `50-cleanup.yml` is recovery cleanup for one exact profile and run ID. It
  refuses deletion unless name, project, managed prefix, owner, profile, and
  run-ID metadata all match. Heavy Podman labels and workspace owner markers
  receive the same check. It never scans for and bulk-deletes stale objects.

## Operator sequence

Set the inventory path and target explicitly. The examples use placeholders so
this public automation stays reusable.

```bash
INVENTORY=/path/to/inventory.yml
TARGET=workbench01.example.net

ansible-playbook -i "$INVENTORY" \
  ansible/runbooks/50-applications/workbench/20-ubuntu-setup.yml \
  --limit "$TARGET" --check --diff

ansible-playbook -i "$INVENTORY" \
  ansible/runbooks/50-applications/workbench/20-ubuntu-setup.yml \
  --limit "$TARGET"

# Repeat deployment: the second run must report no unexpected changes.
ansible-playbook -i "$INVENTORY" \
  ansible/runbooks/50-applications/workbench/20-ubuntu-setup.yml \
  --limit "$TARGET"

ansible-playbook -i "$INVENTORY" \
  ansible/runbooks/50-applications/workbench/30-validate.yml \
  --limit "$TARGET" --check
```

Run each ephemeral profile with a unique lowercase run ID of 3 to 24
characters. Profiles are acceptance inputs, never deployment tags.

The automated Heavy profile is orchestrated only by the SHA-pinned reusable
workflow in `modulix-validation`. This repository deliberately owns the
component-specific playbook and cleanup contract, not the GitHub runner,
environment, or evidence orchestration. See ADR 2886566105.

```bash
for PROFILE in tiny heavy application; do
  ansible-playbook -i "$INVENTORY" \
    ansible/runbooks/50-applications/workbench/40-acceptance.yml \
    --limit "$TARGET" \
    -e "workbench_acceptance_profile=$PROFILE" \
    -e "workbench_acceptance_run_id=manual-001"
done
```

If a controller interruption prevents the `always` block from running, use the
same profile and run ID for exact recovery cleanup:

```bash
ansible-playbook -i "$INVENTORY" \
  ansible/runbooks/50-applications/workbench/50-cleanup.yml \
  --limit "$TARGET" \
  -e workbench_acceptance_profile=heavy \
  -e workbench_acceptance_run_id=manual-001
```

The Incus images are inventory-pinned `images:<64-hex-fingerprint>` references;
acceptance resolves each reference again and requires the returned fingerprint
to match before instance creation. The full Application commit also comes from
inventory, while the Heavy base image must include a SHA-256 manifest digest.
Registry, GitHub, scanner DB, and strict EE image availability are external
runtime prerequisites. No
playbook reads existing credentials, performs interactive GitHub/agent
authentication, or emits inventory and secret dumps. Heavy creates a new
run-local SSH key and deletes it with the owner-marked workspace; only the
public key enters ephemeral guests.

## Evidence and current limits

`30-validate.yml` plus the Tiny lifecycle covers login/account state, Git,
Ansible, Podman, Incus, declared linters, and safe creation/deletion of one
short-lived guest. Heavy retains two first/second nested-Ansible logs plus
Buildah, Skopeo, Trivy, Syft, Grype, container-run, summary, and secret-scan
evidence. Heavy and Application also record each configured and resolved Incus
image fingerprint. Application retains a sanitized execution log, exact
repository and commit summary, and secret-scan result. Evidence paths are:

```text
<operator-home>/artifacts/workbench-acceptance/<run-id>/heavy/
<operator-home>/artifacts/workbench-acceptance/<run-id>/application/
```

Evidence directories are unique and never overwritten or removed by automatic
cleanup. The scanners report only credential pattern names and locations, not
matched values. Runtime success still requires an authorized target-host run;
static controller validation alone is not acceptance evidence. Reboot/LUKS
recovery remains `BLOCKED` in these playbooks and must not be marked successful
without a known unlock path, tested recovery access, and an approved reboot.

Cleanup is deliberately exact-name and run-ID based. The declared maximum age
is not used for automatic bulk deletion because age alone is insufficient
authorization to destroy an instance.

## Controller checks

Run the static safety test, YAML lint, Ansible syntax checks, and `ansible-lint`
before deployment. Syntax and Ansible lint must resolve the current local
`lit.ubuntu` source tree ahead of any packaged collection, for example via a
temporary `ANSIBLE_COLLECTIONS_PATH` overlay.

```bash
python3 -m unittest discover -s ansible/tests/workbench -p 'test_*.py'
yamllint ansible/runbooks/50-applications/workbench
```
