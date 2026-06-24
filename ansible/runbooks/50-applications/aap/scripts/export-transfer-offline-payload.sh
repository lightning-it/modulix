#!/usr/bin/env bash
set -euo pipefail

env_file="${1:-/appl/modulix-aap/etc/aap-local.env}"

if [[ ! -r "${env_file}" ]]; then
  printf 'AAP local env file not readable: %s\n' "${env_file}" >&2
  exit 1
fi

# shellcheck source=/dev/null
. "${env_file}"

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
. "${script_dir}/aap-local-lib.sh"
modulix_aap_set_defaults

required_vars=(
  AAP_APPL_ROOT
  AAP_BOOTSTRAP_SSH_KEY
  AAP_BOOTSTRAP_USER
  AAP_ENV_FILE
  AAP_EXPORT_ROOT
  AAP_FQDN
  AAP_SSH_KEY
  MODULIX_RUN_EE_ARCHIVE
  MODULIX_RUN_EE_ARCHIVE_PATH
  MODULIX_RUN_EE_IMAGE
)

for var_name in "${required_vars[@]}"; do
  if [[ -z "${!var_name:-}" ]]; then
    printf 'Required variable is not set: %s\n' "${var_name}" >&2
    exit 1
  fi
done

bootstrap_known_hosts="${AAP_APPL_ROOT}/secrets/bootstrap_known_hosts"

ssh_opts=(
  -i "${AAP_BOOTSTRAP_SSH_KEY}"
  -o IdentitiesOnly=yes
  -o UserKnownHostsFile="${bootstrap_known_hosts}"
  -o StrictHostKeyChecking=accept-new
)

remote="${AAP_BOOTSTRAP_USER}@${AAP_FQDN}"

mapfile -t aap_artifact_files < <(
  find "${AAP_EXPORT_ROOT}/artifacts/aap" -maxdepth 1 -type f \
    \( -name 'ansible-automation-platform-containerized-setup-bundle-*-x86_64.tar.gz' -o -name 'manifest*.zip' \) |
    sort -V
)

if [[ "${#aap_artifact_files[@]}" -lt 2 ]]; then
  printf 'Expected AAP setup bundle and manifest in %s/artifacts/aap, found %s file(s).\n' \
    "${AAP_EXPORT_ROOT}" "${#aap_artifact_files[@]}" >&2
  exit 1
fi

printf 'Pulling execution environment: %s\n' "${MODULIX_RUN_EE_IMAGE}"
podman pull "${MODULIX_RUN_EE_IMAGE}"
podman run --rm "${MODULIX_RUN_EE_IMAGE}" ansible-galaxy collection list

printf 'Saving execution environment archive: %s\n' "${MODULIX_RUN_EE_ARCHIVE_PATH}"
podman save --format oci-archive \
  -o "${MODULIX_RUN_EE_ARCHIVE_PATH}" \
  "${MODULIX_RUN_EE_IMAGE}"

printf 'Creating automation source archive.\n'
tar -C "${AAP_EXPORT_ROOT}/src" \
  --exclude='modulix-automation/.git' \
  --exclude='modulix-automation/.artifacts' \
  --exclude='modulix-automation/ansible/.artifacts' \
  --exclude='modulix-automation/ansible/.tmp' \
  --exclude='modulix-env/.vault-pass.txt' \
  --exclude='modulix-automation/ansible/ansible-navigator.log' \
  --exclude='modulix-automation/ansible/venv-*' \
  --exclude='modulix-automation/ansible/ansible-automation-platform-containerized-setup-bundle-*.tar.gz' \
  --exclude='modulix-automation/ansible/manifest*.zip' \
  --exclude='modulix-automation/packaging/rpm/.rpmbuild' \
  --exclude='modulix-automation/packaging/rpm/dist' \
  -czf "${AAP_APPL_ROOT}/artifacts/modulix-automation.tar.gz" \
  modulix-automation

printf 'AAP artifacts selected for transfer:\n'
ls -lh "${aap_artifact_files[@]}"

printf 'Creating remote landing zone on %s.\n' "${AAP_FQDN}"
ssh "${ssh_opts[@]}" "${remote}" \
  'set -euo pipefail
   sudo install -d -m 0750 -o "$(id -un)" -g "$(id -gn)" \
     /appl/modulix-aap \
     /appl/modulix-aap/etc \
     /appl/modulix-aap/secrets \
     /appl/modulix-aap/artifacts \
     /appl/modulix-aap/inbox \
     /appl/modulix-aap/scripts \
     /appl/modulix-aap/src
   sudo install -d -m 1777 /appl/tmp /appl/ansible-tmp
   sudo install -d -m 0755 /appl/home /appl/podman'

printf 'Transferring offline payload to %s.\n' "${AAP_FQDN}"
scp "${ssh_opts[@]}" \
  "${AAP_ENV_FILE}" \
  "${AAP_APPL_ROOT}/artifacts/modulix-automation.tar.gz" \
  "${MODULIX_RUN_EE_ARCHIVE_PATH}" \
  "${AAP_SSH_KEY}" \
  "${script_dir}/aap-local-lib.sh" \
  "${script_dir}/stage-runtime-on-aap-host.sh" \
  "${aap_artifact_files[@]}" \
  "${remote}:${AAP_APPL_ROOT}/inbox/"

printf 'Installing transferred payload into remote staging paths.\n'
ssh "${ssh_opts[@]}" "${remote}" bash -s -- "${MODULIX_RUN_EE_ARCHIVE}" <<'REMOTE_PAYLOAD'
set -euo pipefail
modulix_run_ee_archive="$1"

   install -m 0600 /appl/modulix-aap/inbox/aap-local.env /appl/modulix-aap/etc/aap-local.env
   install -m 0600 /appl/modulix-aap/inbox/svc_ansible_aap /appl/modulix-aap/secrets/svc_ansible_aap
   install -m 0644 /appl/modulix-aap/inbox/aap-local-lib.sh /appl/modulix-aap/scripts/aap-local-lib.sh
   install -m 0755 /appl/modulix-aap/inbox/stage-runtime-on-aap-host.sh /appl/modulix-aap/scripts/stage-runtime-on-aap-host.sh
   mv -f "/appl/modulix-aap/inbox/${modulix_run_ee_archive}" /appl/modulix-aap/artifacts/
   mv -f /appl/modulix-aap/inbox/modulix-automation.tar.gz /appl/modulix-aap/artifacts/
REMOTE_PAYLOAD

printf 'Offline payload transfer completed for %s.\n' "${AAP_FQDN}"
