#!/usr/bin/env bash
# Deprecated compatibility entry point. New guides should run
# runbooks/50-applications/aap/02-local-execution-control.yml with
# -e aap_action=stage_runtime.
set -euo pipefail

env_file="${AAP_ENV_FILE:-/appl/aap-local/etc/aap-local.env}"

if [[ "${1:-}" == "--env-file" ]]; then
  env_file="${2:-}"
  shift 2
fi

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

mkdir -p "${AAP_APPL_ROOT}/src" /appl/tmp /appl/ansible-tmp
modulix_write_podman_storage_conf

if [[ ! -f "${AUTOMATION_ANSIBLE_DIR}/ansible.cfg" ]]; then
  rm -rf "${AUTOMATION_DIR}"
  tar -C "${AAP_APPL_ROOT}/src" \
    -xzf "${AAP_APPL_ROOT}/artifacts/modulix-automation.tar.gz"
fi

mkdir -p "${AAP_ARTIFACT_DIR}"
find "${AAP_APPL_ROOT}/inbox" -maxdepth 1 -type f \
  \( -name 'ansible-automation-platform-containerized-setup-bundle-*-x86_64.tar.gz' -o -name 'manifest*.zip' \) \
  -exec mv {} "${AAP_ARTIFACT_DIR}/" \;

if [[ "${AAP_EE_TRANSFER_ENABLED}" == "true" ]]; then
  podman load -i "${MODULIX_RUN_EE_ARCHIVE_PATH}"
else
  podman pull "${MODULIX_RUN_EE_IMAGE}"
fi
podman image exists "${MODULIX_RUN_EE_IMAGE}"

test -f "${ANSIBLE_VAULT_PASSWORD_FILE}" ||
  openssl rand -base64 32 >"${ANSIBLE_VAULT_PASSWORD_FILE}"
chmod 0600 "${ANSIBLE_VAULT_PASSWORD_FILE}"
if [[ "${AAP_SSH_KEY_AUTH_ENABLED}" == "true" ]]; then
  chmod 0600 "${AAP_SSH_KEY}"
fi

cd "${AUTOMATION_ANSIBLE_DIR}"
modulix_write_aap_inventory
modulix_ansible_ee ansible-playbook --version

modulix_resolve_aap_artifacts
printf 'AAP bundle: %s\n' "${AAP_BUNDLE_REMOTE_SRC}"
printf 'AAP manifest: %s\n' "${AAP_MANIFEST_REMOTE_SRC}"
