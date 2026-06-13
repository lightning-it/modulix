# core-tenant

Source: https://confluence.cloud.l-it.io/wiki/spaces/ModuLix/pages/2460516354/Stage+2b+Core+Tenant

## Incus host

`27-incus-host-setup.yml` configures Ubuntu hosts as Incus hosts for system
containers and VM workloads. See `../../../../docs/incus-host.md`.

## GitHub Actions runner

`25-github-runner-setup.yml` configures Ubuntu-based GitHub Actions runners with
`lit.ubuntu.github_runner`. When nested virtualization workloads are required,
enable the Incus host capability from inventory. See
`../../../../docs/github-actions-runner.md`.

Example inventory variables:

```yaml
github_runner_url: "https://github.com/example-org/example-repo"
github_runner_name: "{{ inventory_hostname_short }}"
github_runner_labels:
  - self-hosted
  - linux
  - x64
  - incus
  - nested-virt
github_runner_registration_token: "{{ lookup('ansible.builtin.env', 'GITHUB_RUNNER_TOKEN') }}"

incus_enabled: true
incus_users:
  - litadm
  - github-runner
github_runner_user_groups_extra:
  - incus-admin
  - kvm
```
