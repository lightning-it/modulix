#!/usr/bin/env bash
# Deprecated compatibility entry point. New guides should run
# runbooks/50-applications/aap/02-local-execution-control.yml with
# -e aap_action=transfer_payload.
set -euo pipefail

env_file="${1:-${MACHINE_A_ENV_FILE:-}}"

if [[ -z "${env_file}" ]]; then
  printf 'Pass the target-specific Machine A environment file explicitly.\n' >&2
  exit 1
fi
if [[ -L "${env_file}" || ! -f "${env_file}" || ! -r "${env_file}" ||
      ! -O "${env_file}" ]]; then
  printf 'AAP local env file is missing or unsafe (symlink/ownership/readability): %s\n' "${env_file}" >&2
  exit 1
fi
if [[ "$(stat -c '%a' -- "${env_file}")" != "600" ]]; then
  printf 'AAP local env file must have mode 0600: %s\n' "${env_file}" >&2
  exit 1
fi

# shellcheck source=/dev/null
. "${env_file}"

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
. "${script_dir}/aap-local-lib.sh"
modulix_aap_set_defaults
if [[ "${env_file}" != "${MACHINE_A_ENV_FILE}" ]]; then
  printf 'Selected env file does not match MACHINE_A_ENV_FILE: %s != %s\n' \
    "${env_file}" "${MACHINE_A_ENV_FILE}" >&2
  exit 1
fi
modulix_validate_machine_a_workspace

required_vars=(
  AAP_APPL_ROOT
  AAP_BOOTSTRAP_USER
  AAP_FQDN
  MACHINE_A_AAP_ROOT
  MACHINE_A_APPL_ROOT
  MACHINE_A_BOOTSTRAP_KNOWN_HOSTS
  MACHINE_A_EXPORT_ROOT
  MACHINE_A_TMP_DIR
  MODULIX_RUN_EE_ARCHIVE
  MODULIX_RUN_EE_IMAGE
)

for var_name in "${required_vars[@]}"; do
  if [[ -z "${!var_name:-}" ]]; then
    printf 'Required variable is not set: %s\n' "${var_name}" >&2
    exit 1
  fi
done

if [[ "${AAP_APPL_ROOT}" != "/appl/aap-local" ]]; then
  printf 'This compatibility script requires AAP_APPL_ROOT=/appl/aap-local: %s\n' \
    "${AAP_APPL_ROOT}" >&2
  exit 1
fi

if [[ ! -s "${MACHINE_A_BOOTSTRAP_KNOWN_HOSTS}" ]]; then
  printf 'Verified SSH known hosts file is missing or empty: %s\n' \
    "${MACHINE_A_BOOTSTRAP_KNOWN_HOSTS}" >&2
  exit 1
fi

if [[ "${AAP_SECRET_BACKEND}" == "ansible_vault" ]]; then
  if grep -Eq \
    '^[[:space:]]*(export[[:space:]]+)?VAULT_TOKEN[[:space:]]*=' \
    "${env_file}"; then
    printf 'An Ansible Vault environment file must not contain VAULT_TOKEN.\n' >&2
    exit 1
  fi
  if [[ -L "${MACHINE_A_ANSIBLE_VAULT_PASSWORD_FILE}" ||
        ! -f "${MACHINE_A_ANSIBLE_VAULT_PASSWORD_FILE}" ||
        ! -s "${MACHINE_A_ANSIBLE_VAULT_PASSWORD_FILE}" ]]; then
    printf 'Machine A Ansible Vault password file is missing or unsafe: %s\n' \
      "${MACHINE_A_ANSIBLE_VAULT_PASSWORD_FILE}" >&2
    exit 1
  fi
  if [[ "$(stat -c '%h' -- "${MACHINE_A_ANSIBLE_VAULT_PASSWORD_FILE}")" != "1" ||
        "$(stat -c '%U' -- "${MACHINE_A_ANSIBLE_VAULT_PASSWORD_FILE}")" != "$(id -un)" ]]; then
    printf 'Machine A Ansible Vault password file must be singly linked and owned by %s: %s\n' \
      "$(id -un)" "${MACHINE_A_ANSIBLE_VAULT_PASSWORD_FILE}" >&2
    exit 1
  fi
  case "$(stat -c '%a' -- "${MACHINE_A_ANSIBLE_VAULT_PASSWORD_FILE}")" in
    400 | 600) ;;
    *)
      printf 'Machine A Ansible Vault password file must have mode 0400 or 0600: %s\n' \
        "${MACHINE_A_ANSIBLE_VAULT_PASSWORD_FILE}" >&2
      exit 1
      ;;
  esac
fi

machine_a_ee_archive_path="${MACHINE_A_MODULIX_RUN_EE_ARCHIVE_PATH:-${MACHINE_A_APPL_ROOT}/artifacts/${MODULIX_RUN_EE_ARCHIVE}}"
machine_a_source_archive_path="${MACHINE_A_APPL_ROOT}/artifacts/modulix-automation.tar.gz"
machine_a_ssh_key_basename=""
if [[ "${AAP_SSH_KEY_AUTH_ENABLED}" == "true" ]]; then
  if [[ -z "${AAP_BOOTSTRAP_SSH_KEY:-}" || -z "${AAP_SSH_KEY:-}" || -z "${MACHINE_A_SSH_KEY:-}" ]]; then
    printf 'SSH key auth is enabled, but key variables are incomplete.\n' >&2
    exit 1
  fi
  machine_a_ssh_key_basename="$(basename "${MACHINE_A_SSH_KEY}")"
fi
bootstrap_known_hosts="${MACHINE_A_BOOTSTRAP_KNOWN_HOSTS}"

ssh_opts=(
  -o UserKnownHostsFile="${bootstrap_known_hosts}"
  -o StrictHostKeyChecking=yes
)

if [[ "${AAP_SSH_KEY_AUTH_ENABLED}" == "true" ]]; then
  ssh_opts=(-i "${AAP_BOOTSTRAP_SSH_KEY}" -o IdentitiesOnly=yes "${ssh_opts[@]}")
fi

remote="${AAP_BOOTSTRAP_USER}@${AAP_FQDN}"
remote_vault_inbox_pending=false
cleanup_remote_vault_inbox() {
  if [[ "${remote_vault_inbox_pending}" == "true" ]]; then
    ssh "${ssh_opts[@]}" "${remote}" \
      "rm -f -- \"${AAP_APPL_ROOT}/inbox/.vault-pass.txt\"" \
      >/dev/null 2>&1 || true
  fi
}
trap cleanup_remote_vault_inbox EXIT

artifact_dir="${MACHINE_A_EXPORT_ROOT}/artifacts/aap"
mkdir -p "${artifact_dir}"

modulix_aap_download_artifact() {
  local label="$1"
  local url="$2"
  local dest="$3"
  local checksum="${4:-}"

  if [[ -z "${url}" ]]; then
    return 0
  fi

  if [[ ! -s "${dest}" || "${AAP_ARTIFACT_DOWNLOAD_FORCE:-false}" == "true" ]]; then
    printf 'Downloading %s artifact: %s\n' "${label}" "${dest}"
    curl -fL --retry 3 --retry-delay 5 \
      -o "${dest}" \
      "${url}"
  else
    printf 'Using existing %s artifact: %s\n' "${label}" "${dest}"
  fi

  if [[ -n "${checksum}" ]]; then
    printf '%s  %s\n' "${checksum#sha256:}" "${dest}" | sha256sum -c -
  fi
}

modulix_aap_download_artifact \
  "AAP setup bundle" \
  "${AAP_BUNDLE_URL:-}" \
  "${artifact_dir}/${AAP_BUNDLE_FILENAME:-ansible-automation-platform-containerized-setup-bundle-2.7-1.1-x86_64.tar.gz}" \
  "${AAP_BUNDLE_SHA256:-}"

modulix_aap_download_artifact \
  "AAP manifest" \
  "${AAP_MANIFEST_URL:-}" \
  "${artifact_dir}/${AAP_MANIFEST_FILENAME:-manifest.zip}" \
  "${AAP_MANIFEST_SHA256:-}"

mapfile -t aap_bundle_files < <(
  find "${artifact_dir}" -maxdepth 1 -type f \
    -name 'ansible-automation-platform-containerized-setup-bundle-*-x86_64.tar.gz' |
    sort -V
)
mapfile -t aap_manifest_files < <(
  find "${artifact_dir}" -maxdepth 1 -type f \
    -name 'manifest*.zip' |
    sort -V
)

if [[ "${#aap_bundle_files[@]}" -ne 1 || "${#aap_manifest_files[@]}" -ne 1 ]]; then
  printf 'Expected exactly one AAP setup bundle and one manifest in %s.\n' \
    "${artifact_dir}" >&2
  printf 'Found %s setup bundle file(s) and %s manifest file(s).\n' \
    "${#aap_bundle_files[@]}" "${#aap_manifest_files[@]}" >&2
  printf 'Copy exactly one file matching each pattern before rerunning:\n' >&2
  printf '  %s/ansible-automation-platform-containerized-setup-bundle-*-x86_64.tar.gz\n' "${artifact_dir}" >&2
  printf '  %s/manifest*.zip\n' "${artifact_dir}" >&2
  printf 'Or set AAP_BUNDLE_URL and AAP_MANIFEST_URL in %s.\n' "${env_file}" >&2
  exit 1
fi

aap_artifact_files=("${aap_bundle_files[0]}" "${aap_manifest_files[0]}")
aap_bundle_file="${aap_bundle_files[0]}"
aap_manifest_file="${aap_manifest_files[0]}"

bundle_min_size_bytes="${AAP_BUNDLE_MIN_SIZE_BYTES:-100000000}"
bundle_size_bytes="$(stat -c '%s' "${aap_bundle_file}")"
manifest_size_bytes="$(stat -c '%s' "${aap_manifest_file}")"

if (( bundle_size_bytes < bundle_min_size_bytes )); then
  printf 'AAP setup bundle is too small: %s (%s bytes, minimum %s bytes).\n' \
    "${aap_bundle_file}" "${bundle_size_bytes}" "${bundle_min_size_bytes}" >&2
  printf 'This usually means the file is not the real Red Hat containerized setup bundle.\n' >&2
  exit 1
fi

if (( manifest_size_bytes <= 0 )); then
  printf 'AAP manifest is empty: %s\n' "${aap_manifest_file}" >&2
  exit 1
fi

if [[ -n "${AAP_BUNDLE_SHA256:-}" ]]; then
  printf '%s  %s\n' "${AAP_BUNDLE_SHA256#sha256:}" "${aap_bundle_file}" | sha256sum -c -
fi

if [[ -n "${AAP_MANIFEST_SHA256:-}" ]]; then
  printf '%s  %s\n' "${AAP_MANIFEST_SHA256#sha256:}" "${aap_manifest_file}" | sha256sum -c -
fi

if ! tar -tzf "${aap_bundle_file}" >/dev/null; then
  printf 'AAP setup bundle is not a readable tar.gz archive: %s\n' "${aap_bundle_file}" >&2
  exit 1
fi

if ! python3 - "${aap_manifest_file}" <<'PY'
import sys
import zipfile

path = sys.argv[1]
try:
    with zipfile.ZipFile(path) as archive:
        bad_member = archive.testzip()
except zipfile.BadZipFile:
    raise SystemExit(1)

raise SystemExit(1 if bad_member else 0)
PY
then
  printf 'AAP manifest is not a readable zip archive: %s\n' "${aap_manifest_file}" >&2
  exit 1
fi

if [[ "${AAP_EE_TRANSFER_ENABLED}" == "true" ]]; then
  if podman image exists "${MODULIX_RUN_EE_IMAGE}" && [[ "${AAP_EE_PULL_FORCE:-false}" != "true" ]]; then
    printf 'Using local execution environment: %s\n' "${MODULIX_RUN_EE_IMAGE}"
  else
    printf 'Pulling execution environment: %s\n' "${MODULIX_RUN_EE_IMAGE}"
    podman pull "${MODULIX_RUN_EE_IMAGE}"
  fi
  podman image inspect "${MODULIX_RUN_EE_IMAGE}" >/dev/null

  printf 'Saving execution environment archive: %s\n' "${machine_a_ee_archive_path}"
  podman save --format oci-archive \
    -o "${machine_a_ee_archive_path}" \
    "${MODULIX_RUN_EE_IMAGE}"
else
  printf 'Skipping execution environment archive transfer; AAP host will use registry image: %s\n' \
    "${MODULIX_RUN_EE_IMAGE}"
fi

printf 'Creating automation source archive.\n'
tar -C "${MACHINE_A_EXPORT_ROOT}/src" \
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
  -czf "${machine_a_source_archive_path}" \
  modulix-automation

printf 'AAP artifacts selected for transfer:\n'
ls -lh "${aap_artifact_files[@]}"

printf 'Creating remote landing zone on %s.\n' "${AAP_FQDN}"
ssh "${ssh_opts[@]}" "${remote}" \
  'set -euo pipefail
   aap_setup_user=svc_ansible
   aap_setup_group="$(id -gn "${aap_setup_user}")"
   sudo install -d -m 0750 -o "${aap_setup_user}" -g "${aap_setup_group}" \
     /appl/aap-local \
     /appl/aap-local/etc \
     /appl/aap-local/secrets \
     /appl/aap-local/artifacts \
     /appl/aap-local/inbox \
     /appl/aap-local/scripts \
     /appl/aap-local/src
   sudo install -d -m 1777 /appl/tmp /appl/ansible-tmp
   sudo install -d -m 0755 \
     /appl/home \
     /appl/podman
   sudo install -d -m 0700 -o "${aap_setup_user}" -g "${aap_setup_group}" \
     /appl/podman/root-storage \
     /appl/podman/root-run
   find /appl/aap-local/inbox -mindepth 1 -maxdepth 1 -type f -delete'

transfer_files=(
  "${env_file}"
  "${machine_a_source_archive_path}"
  "${script_dir}/aap-local-lib.sh"
  "${script_dir}/run-aap-playbooks.sh"
  "${script_dir}/stage-runtime-on-aap-host.sh"
  "${aap_artifact_files[@]}"
)
if [[ "${AAP_EE_TRANSFER_ENABLED}" == "true" ]]; then
  transfer_files+=("${machine_a_ee_archive_path}")
fi

printf 'Transferring offline payload to %s.\n' "${AAP_FQDN}"
scp "${ssh_opts[@]}" \
  "${transfer_files[@]}" \
  "${remote}:${AAP_APPL_ROOT}/inbox/"

scp "${ssh_opts[@]}" \
  "${MACHINE_A_BOOTSTRAP_KNOWN_HOSTS}" \
  "${remote}:${AAP_APPL_ROOT}/inbox/bootstrap_known_hosts"

if [[ "${AAP_SSH_KEY_AUTH_ENABLED}" == "true" ]]; then
  scp "${ssh_opts[@]}" \
    "${MACHINE_A_SSH_KEY}" \
    "${remote}:${AAP_APPL_ROOT}/inbox/"
fi

if [[ "${AAP_SECRET_BACKEND}" == "ansible_vault" ]]; then
  remote_vault_inbox_pending=true
  scp "${ssh_opts[@]}" \
    "${MACHINE_A_ANSIBLE_VAULT_PASSWORD_FILE}" \
    "${remote}:${AAP_APPL_ROOT}/inbox/.vault-pass.txt"
elif [[ -s "${MACHINE_A_SECRETS_DIR}/.vault-token" ]]; then
  scp "${ssh_opts[@]}" \
    "${MACHINE_A_SECRETS_DIR}/.vault-token" \
    "${remote}:${AAP_APPL_ROOT}/inbox/.vault-token"
fi

printf 'Installing transferred payload into remote staging paths.\n'
ssh "${ssh_opts[@]}" "${remote}" bash -s -- "${MODULIX_RUN_EE_ARCHIVE}" "${machine_a_ssh_key_basename}" "${AAP_EE_TRANSFER_ENABLED}" <<'REMOTE_PAYLOAD'
set -euo pipefail
modulix_run_ee_archive="$1"
machine_a_ssh_key_basename="${2:-}"
ee_transfer_enabled="${3:-true}"

   install -m 0600 /appl/aap-local/inbox/aap-local.env /appl/aap-local/etc/aap-local.env
   . /appl/aap-local/etc/aap-local.env
   install -m 0644 /appl/aap-local/inbox/aap-local-lib.sh /appl/aap-local/scripts/aap-local-lib.sh
   . /appl/aap-local/scripts/aap-local-lib.sh
   modulix_aap_set_defaults
   aap_known_hosts_file="${AAP_KNOWN_HOSTS_FILE:-${AAP_SECRETS_DIR}/bootstrap_known_hosts}"
   if [ -n "${machine_a_ssh_key_basename}" ]; then
     install -m 0600 "/appl/aap-local/inbox/${machine_a_ssh_key_basename}" "${AAP_SSH_KEY}"
   fi
   install -m 0600 /appl/aap-local/inbox/bootstrap_known_hosts "${aap_known_hosts_file}"
   case "${AAP_SECRET_BACKEND}" in
     ansible_vault)
       trap 'rm -f /appl/aap-local/inbox/.vault-pass.txt' EXIT
       install -m 0600 \
         /appl/aap-local/inbox/.vault-pass.txt \
         "${ANSIBLE_VAULT_PASSWORD_FILE}"
       if ! modulix_validate_ansible_vault_password_file \
         "${ANSIBLE_VAULT_PASSWORD_FILE}" "${AAP_SETUP_USER}"; then
         rm -f "${ANSIBLE_VAULT_PASSWORD_FILE}"
         exit 1
       fi
       rm -f \
         /appl/aap-local/inbox/.vault-pass.txt \
         /appl/aap-local/inbox/.vault-token \
         /appl/aap-local/secrets/.vault-token
       trap - EXIT
       ;;
     hashicorp_vault)
       if [ -s /appl/aap-local/inbox/.vault-token ]; then
         install -m 0600 \
           /appl/aap-local/inbox/.vault-token \
           /appl/aap-local/secrets/.vault-token
       fi
       rm -f \
         /appl/aap-local/inbox/.vault-pass.txt \
         /appl/aap-local/secrets/.vault-pass.txt
       ;;
     *)
       printf 'Unsupported AAP_SECRET_BACKEND: %s\n' \
         "${AAP_SECRET_BACKEND}" >&2
       exit 1
       ;;
   esac
   install -m 0755 /appl/aap-local/inbox/run-aap-playbooks.sh /appl/aap-local/scripts/run-aap-playbooks.sh
   install -m 0755 /appl/aap-local/inbox/stage-runtime-on-aap-host.sh /appl/aap-local/scripts/stage-runtime-on-aap-host.sh
   find /appl/aap-local/artifacts -maxdepth 1 -type f \
     \( -name "modulix-automation.tar.gz" -o -name "*.tar" \) -delete
   if [ "${ee_transfer_enabled}" = "true" ]; then
     mv -f "/appl/aap-local/inbox/${modulix_run_ee_archive}" /appl/aap-local/artifacts/
   fi
   mv -f /appl/aap-local/inbox/modulix-automation.tar.gz /appl/aap-local/artifacts/
REMOTE_PAYLOAD

remote_vault_inbox_pending=false
trap - EXIT
printf 'Offline payload transfer completed for %s.\n' "${AAP_FQDN}"
