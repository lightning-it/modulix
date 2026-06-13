# GitHub Actions Runner

`modulix-automation` can configure Ubuntu-based GitHub Actions self-hosted
runners for platform CI workloads.

The operational entrypoint is:

```text
ansible/runbooks/stage-2b/core-tenant/25-github-runner-setup.yml
```

The runbook is intentionally inventory-driven. It only orchestrates collection
roles:

- `lit.ubuntu.incus`: optional Incus/QEMU host capability for nested
  virtualization workloads.
- `lit.ubuntu.github_runner`: GitHub Actions runner install, registration, and
  systemd service management.

For standalone Incus host usage, see `docs/incus-host.md`.

## Inventory Contract

Target hosts must be in the `github_runners` inventory group.

Minimum variables for a GitHub runner:

```yaml
github_runner_url: "https://github.com/example-org/example-repo"
github_runner_name: "{{ inventory_hostname_short }}"
github_runner_registration_token: "{{ lookup('ansible.builtin.env', 'GITHUB_RUNNER_TOKEN') }}"
github_runner_labels:
  - self-hosted
  - linux
  - x64
```

Enable Incus support when the runner should execute nested virtualization or
Incus VM workloads:

```yaml
incus_enabled: true
incus_users:
  - litadm
  - github-runner
github_runner_user_groups_extra:
  - incus-admin
  - kvm
github_runner_labels:
  - self-hosted
  - linux
  - x64
  - incus
  - nested-virt
```

## Registration Token

GitHub registration tokens are short-lived secrets. Do not store them in the
repository or plain inventory.

For a repository-level runner:

```bash
export GITHUB_RUNNER_TOKEN="$(
  gh api /repos/example-org/example-repo/actions/runners/registration-token \
    --method POST \
    --jq .token
)"
```

For an organization-level runner, the authenticated GitHub account or token must
have the required organization runner administration permission.

## Execution

Run with the standard ModuLix Ansible wrapper:

```bash
cd ansible

./scripts/ansible-nav run \
  runbooks/stage-2b/core-tenant/25-github-runner-setup.yml \
  -i inventories/<env>/inventory.yml \
  --limit <runner-host-or-group>
```

When using an external inventory checkout:

```bash
cd ansible

./scripts/ansible-nav run \
  runbooks/stage-2b/core-tenant/25-github-runner-setup.yml \
  -i /path/to/inventories/<env>/inventory.yml \
  --limit <runner-host-or-group>
```

## Idempotency

If the runner is already registered and `github_runner_replace` is false, the
role manages the installed binary, local user, and service without requiring a
new GitHub registration token.

Set `github_runner_replace: true` only when intentionally replacing the runner
registration. Replacement requires a fresh registration token.
