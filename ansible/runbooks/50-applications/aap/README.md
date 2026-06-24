# AAP Runbooks

AAP runbooks deploy and operate Red Hat Ansible Automation Platform from
inventory-owned values.

## Runbooks

- `05-artifacts.yml`: stage the AAP setup bundle and manifest using
  `lit.supplementary.aap_prepare` and `lit.supplementary.artifacts`.
- `06-base-os-prepare.yml`: prepare the AAP-specific OS substrate on an
  already-created RHEL host.
- `07-preflight.yml`: verify SSH, DNS, base OS tools, artifact sources, and
  Vault access before deployment.
- `08-tls-selfsigned.yml`: generate temporary controller-local self-signed TLS
  files for lab/disconnected installs when customer PKI is not available.
- `10-deploy.yml`: prepare and deploy AAP, then apply configuration-as-code.
- `20-ops.yml`: run explicit day-2 AAP operations with `aap_ops_action`.

## Helper Scripts

- `scripts/aap-local-lib.sh`: shared local shell functions for the disconnected
  AAP guide, including artifact resolution, execution-environment Ansible, and
  generated local inventory.
- `scripts/prepare-machine-a.sh`: Machine A helper that creates the local
  staging layout, prepares the AAP SSH key, and refreshes the automation
  checkout.
- `scripts/run-aap-playbooks.sh`: AAP-host helper that resolves local
  artifacts, writes the generated inventory, and runs one or more AAP runbooks
  inside the execution environment.
- `scripts/stage-runtime-on-aap-host.sh`: AAP-host helper that unpacks the
  transferred automation checkout, moves installer artifacts into place, loads
  the execution environment image, and writes the generated inventory.
- `scripts/export-transfer-offline-payload.sh`: Machine A helper that pulls and
  exports the execution environment image, packages the automation checkout,
  creates the remote landing zone, and transfers the disconnected payload to
  the AAP host before local Ansible execution is available.

## OS Preparation Boundary

Preferred split for production and customer-provided hosts:

1. stage artifacts with `05-artifacts.yml`
2. prepare AAP-specific OS substrate with `06-base-os-prepare.yml`
3. run preflight with `07-preflight.yml`
4. optionally generate temporary TLS files with `08-tls-selfsigned.yml`
5. deploy and configure AAP with `10-deploy.yml`

`10-deploy.yml` has two plays:

- optional AAP host OS preparation
- AAP artifact staging, deployment, and configuration-as-code

The OS preparation play is for lab and self-managed hosts. Customer-owned
baseline, Satellite, repository, user, or Podman preparation can disable it
from inventory:

```yaml
aap_runbook_os_prep_enabled: false
```

Each OS preparation piece can also be controlled separately:

```yaml
aap_runbook_manage_rhsm: false
aap_runbook_manage_repos: false
aap_runbook_manage_install_user: false
aap_runbook_manage_podman: false
```

When `06-base-os-prepare.yml` has already run, disable the optional OS-prep
section in `10-deploy.yml` for a cleaner deploy-only run:

```yaml
aap_runbook_os_prep_enabled: false
```

## Artifact Staging

`10-deploy.yml` stages AAP artifacts with `lit.supplementary.aap_prepare`
before running the AAP deployment role. Define `aap_prepare_*` variables on the
target AAP host or group when the AAP bundle should be downloaded from Hetzner
Object Storage, another S3-compatible backend, an internal HTTPS endpoint, or
copied from a controller-local path.

The deployment role then consumes the staged bundle through
`aap_deploy_setup_archive_path`.

Generic artifact staging with `lit.supplementary.artifacts` remains available
for non-AAP artifacts, but AAP bundle and manifest handling belongs in
`lit.supplementary.aap_prepare`.

Example inventory shape only. Put real values and copy-paste rollout
instructions in the private operations repository for the environment.

```yaml
aap_prepare_bundle_source: url
aap_prepare_bundle_url: "{{ lookup('ansible.builtin.env', 'AAP_27_BUNDLE_URL') }}"
aap_prepare_bundle_checksum: "sha256:{{ lookup('ansible.builtin.env', 'AAP_27_BUNDLE_SHA256') }}"
aap_prepare_bundle_dest: /srv/aap/bundles/aap-2.7-containerized-setup-bundle.tar.gz
aap_deploy_setup_archive_path: /srv/aap/bundles/aap-2.7-containerized-setup-bundle.tar.gz
```
