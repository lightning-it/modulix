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

if [[ "${AAP_SECRET_BACKEND}" == "ansible_vault" ]]; then
  modulix_validate_ansible_vault_password_file \
    "${ANSIBLE_VAULT_PASSWORD_FILE}" "${AAP_SETUP_USER}"
  rm -f "${AAP_SECRETS_DIR}/.vault-token"
else
  rm -f "${AAP_SECRETS_DIR}/.vault-pass.txt"
fi

mkdir -p "${AAP_APPL_ROOT}/src" /appl/tmp /appl/ansible-tmp
modulix_write_podman_storage_conf

source_archive="${AAP_APPL_ROOT}/artifacts/modulix-automation.tar.gz"
source_parent="${AAP_APPL_ROOT}/src"
if [[ "$(dirname -- "${AUTOMATION_DIR}")" != "${source_parent}" ]]; then
  printf 'AUTOMATION_DIR must be a direct child of %s, got: %s\n' \
    "${source_parent}" "${AUTOMATION_DIR}" >&2
  exit 1
fi
if [[ ! -s "${source_archive}" ]] || ! tar -tzf "${source_archive}" >/dev/null; then
  printf 'Automation source archive is missing or unreadable: %s\n' \
    "${source_archive}" >&2
  exit 1
fi

source_stage_dir="$(mktemp -d "${source_parent}/.modulix-automation-stage.XXXXXX")"
source_backup_dir="${source_parent}/.modulix-automation-previous.$$"
source_stage_tree="${source_stage_dir}/modulix-automation"
cleanup_source_stage() {
  rm -rf -- "${source_stage_dir}"
}
trap cleanup_source_stage EXIT

tar -C "${source_stage_dir}" -xzf "${source_archive}"
if [[ ! -f "${source_stage_tree}/ansible/ansible.cfg" ]]; then
  printf 'Automation source archive does not contain modulix-automation/ansible/ansible.cfg.\n' >&2
  exit 1
fi

# TLS keys and certificates are runtime state. Preserve them across a fresh
# source tree while allowing every other file, including .artifacts, to refresh.
if [[ -d "${AUTOMATION_ANSIBLE_DIR}/files/tls" ]]; then
  mkdir -p "${source_stage_tree}/ansible/files/tls"
  cp -a "${AUTOMATION_ANSIBLE_DIR}/files/tls/." \
    "${source_stage_tree}/ansible/files/tls/"
fi

rm -rf -- "${source_backup_dir}"
if [[ -e "${AUTOMATION_DIR}" ]]; then
  mv -- "${AUTOMATION_DIR}" "${source_backup_dir}"
fi
if ! mv -- "${source_stage_tree}" "${AUTOMATION_DIR}"; then
  if [[ -e "${source_backup_dir}" && ! -e "${AUTOMATION_DIR}" ]]; then
    mv -- "${source_backup_dir}" "${AUTOMATION_DIR}"
  fi
  printf 'Failed to activate refreshed automation source tree.\n' >&2
  exit 1
fi
rm -rf -- "${source_backup_dir}"
cleanup_source_stage
trap - EXIT

mkdir -p "${AAP_ARTIFACT_DIR}"
mapfile -t aap_bundle_files < <(
  find "${AAP_APPL_ROOT}/inbox" -maxdepth 1 -type f \
    -name 'ansible-automation-platform-containerized-setup-bundle-*-x86_64.tar.gz' |
    sort -V
)
mapfile -t aap_manifest_files < <(
  find "${AAP_APPL_ROOT}/inbox" -maxdepth 1 -type f \
    -name 'manifest*.zip' |
    sort -V
)
if [[ "${#aap_bundle_files[@]}" -ne 1 || "${#aap_manifest_files[@]}" -ne 1 ]]; then
  printf 'Expected exactly one transferred AAP bundle and manifest in %s; found %s and %s.\n' \
    "${AAP_APPL_ROOT}/inbox" "${#aap_bundle_files[@]}" "${#aap_manifest_files[@]}" >&2
  exit 1
fi
rm -f -- \
  "${AAP_ARTIFACT_DIR}"/ansible-automation-platform-containerized-setup-bundle-*-x86_64.tar.gz \
  "${AAP_ARTIFACT_DIR}"/manifest*.zip
# Inbox and project artifacts are on the same /appl tree. Hard links keep the
# retry-safe inbox copies without consuming a second bundle-sized allocation.
ln -- "${aap_bundle_files[0]}" "${AAP_ARTIFACT_DIR}/"
ln -- "${aap_manifest_files[0]}" "${AAP_ARTIFACT_DIR}/"

if [[ "${AAP_EE_TRANSFER_ENABLED}" == "true" ]]; then
  podman load -i "${MODULIX_RUN_EE_ARCHIVE_PATH}"
else
  registry_auth_args=()
  if [[ -n "${REGISTRY_AUTH_FILE:-}" ]]; then
    if [[ ! -s "${REGISTRY_AUTH_FILE}" ]]; then
      printf 'Registry auth file is missing or empty: %s\n' \
        "${REGISTRY_AUTH_FILE}" >&2
      exit 1
    fi
    registry_auth_args=(--authfile="${REGISTRY_AUTH_FILE}")
  fi
  podman pull "${registry_auth_args[@]}" "${MODULIX_RUN_EE_RUNTIME_IMAGE}"
fi
podman image exists "${MODULIX_RUN_EE_RUNTIME_IMAGE}"

if [[ "${AAP_SSH_KEY_AUTH_ENABLED}" == "true" ]]; then
  chmod 0600 "${AAP_SSH_KEY}"
fi

cd "${AUTOMATION_ANSIBLE_DIR}"
modulix_write_aap_inventory
modulix_ansible_ee ansible-playbook --version

modulix_resolve_aap_artifacts
printf 'AAP bundle: %s\n' "${AAP_BUNDLE_REMOTE_SRC}"
printf 'AAP manifest: %s\n' "${AAP_MANIFEST_REMOTE_SRC}"
