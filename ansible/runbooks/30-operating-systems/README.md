# Operating System Runbooks

Operating system runbooks prepare already-created machines for platform or
application use.

Use this area for:

- RHEL and Ubuntu base configuration
- Ansible runtime prerequisites such as custom `ansible_remote_tmp` paths
- OS registration and repository setup
- package baselines
- OS hardening

Do not create VMs here. Compute lifecycle belongs in `10-compute/`.

## Execution Order

Run base setup before CIS hardening. The base runbooks prepare managed users,
SSH/become behavior, repositories, packages, networking, and other local OS
defaults that the ansible-lockdown roles expect to find stable.

Base-only runbooks:

- RHEL 9: `30-operating-systems/rhel/9/01-base-setup.yml`
- RHEL 10: `30-operating-systems/rhel/10/01-base-setup.yml`
- Ubuntu 24: `30-operating-systems/ubuntu/24/01-base-setup.yml`

Base followed by ansible-lockdown CIS hardening:

- RHEL 9: `30-operating-systems/rhel/9/00-base-and-hardening.yml`
- RHEL 10: `30-operating-systems/rhel/10/00-base-and-hardening.yml`
- Ubuntu 24: `30-operating-systems/ubuntu/24/00-base-and-hardening.yml`

Hardening-only aggregate runbooks:

- All supported OS CIS groups: `30-operating-systems/90-cis-hardening.yml`
- All supported RHEL CIS groups: `30-operating-systems/rhel/90-cis-hardening.yml`
- All supported Ubuntu CIS groups: `30-operating-systems/ubuntu/90-cis-hardening.yml`

Use `--limit` for base runs. CIS hardening uses explicit opt-in inventory
groups such as `rhel9_cis_targets`, `rhel10_cis_targets`, and
`ubuntu24_cis_targets`.

## Local Account Model

Managed Linux hosts use separate local accounts for automation, emergency
access, and named human administration.

- `svc_ansible`: automation account for Ansible, AAP, and CI. It uses the
  managed deploy SSH key, has a locked password, and receives
  `NOPASSWD:ALL` through `/etc/sudoers.d/90-svc_ansible`. Normal managed-host
  inventory should connect as this account so automation does not depend on a
  sudo password prompt.
- `breakglass`: emergency human account for cases where AAP, SSO, Vault, or
  other central services are unavailable. It has a local password hash from
  inventory and belongs to the native admin group, but it does not receive a
  passwordless sudoers file.
- Named humans such as `rene` and `dirk`: interactive local accounts with
  managed SSH keys and membership in the native admin group. They use
  password-required sudo unless a narrower host-specific policy says otherwise.
- `litadm`: bootstrap/transitional account. It may remain on existing hosts and
  template flows, but it is not the default automation account and should not
  receive passwordless sudo.
- `root`: not used as the Ansible remote user and must not be enabled for SSH.
  CIS policies may require the root password to be set or locked.

The native admin group is selected per OS family: `wheel` on Red Hat family
hosts and `sudo` on Debian/Ubuntu family hosts. Ubuntu automation targets are
standardized on Ubuntu 24.04 LTS, and the automation account uses passwordless
sudo so managed runs do not depend on interactive sudo prompt handling.
