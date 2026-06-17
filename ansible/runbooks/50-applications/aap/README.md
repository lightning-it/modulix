# AAP Runbooks

AAP runbooks deploy and operate Red Hat Ansible Automation Platform from
inventory-owned values.

## Runbooks

- `10-deploy.yml`: prepare and deploy AAP, then apply configuration-as-code.
- `20-ops.yml`: run explicit day-2 AAP operations with `aap_ops_action`.

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
