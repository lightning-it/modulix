# AAP Runbooks

AAP runbooks deploy and operate Red Hat Ansible Automation Platform from
inventory-owned values.

## Artifact Staging

`10-deploy.yml` optionally stages artifacts before running the AAP deployment
role. Define `artifacts_items` on the target AAP host or group when the AAP
bundle should be downloaded from Hetzner Object Storage, another S3-compatible
backend, an internal HTTPS endpoint, or copied from a controller-local path.

The deployment role then consumes the staged bundle through
`aap_deploy_setup_archive_src` or `aap_deploy_setup_archive_path`.

Example inventory shape only. Put real values and copy-paste rollout
instructions in the private operations repository for the environment.

```yaml
artifacts_items:
  - name: aap-2.7-containerized-bundle
    source: url
    url: "{{ lookup('ansible.builtin.env', 'AAP_27_BUNDLE_URL') }}"
    dest: /srv/aap/bundles/aap-2.7-containerized-setup-bundle.tar.gz
    checksum: "sha256:{{ lookup('ansible.builtin.env', 'AAP_27_BUNDLE_SHA256') }}"
    no_log: true

aap_deploy_setup_archive_src: /srv/aap/bundles/aap-2.7-containerized-setup-bundle.tar.gz
```
