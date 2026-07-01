#!/usr/bin/env bash
set -euo pipefail

env_file="${1:-${HOME}/appl/modulix-aap/etc/aap-local.env}"

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
  AUTOMATION_REPO_URL
  MACHINE_A_APPL_ROOT
  MACHINE_A_EXPORT_ROOT
  MACHINE_A_SECRETS_DIR
)

for var_name in "${required_vars[@]}"; do
  if [[ -z "${!var_name:-}" ]]; then
    printf 'Required variable is not set: %s\n' "${var_name}" >&2
    exit 1
  fi
done

install -d -m 0750 \
  "${MACHINE_A_APPL_ROOT}" \
  "${MACHINE_A_APPL_ROOT}/etc" \
  "${MACHINE_A_SECRETS_DIR}" \
  "${MACHINE_A_APPL_ROOT}/artifacts" \
  "${MACHINE_A_EXPORT_ROOT}" \
  "${MACHINE_A_EXPORT_ROOT}/artifacts/aap" \
  "${MACHINE_A_EXPORT_ROOT}/src"

if [[ "${AAP_SSH_KEY_AUTH_ENABLED}" == "true" ]]; then
  if [[ -z "${AAP_BASELINE_SSH_KEY:-}" || -z "${AAP_BOOTSTRAP_SSH_KEY:-}" || -z "${MACHINE_A_SSH_KEY:-}" ]]; then
    printf 'SSH key auth is enabled, but key variables are incomplete.\n' >&2
    exit 1
  fi

  if [[ -s "${AAP_BASELINE_SSH_KEY}" && ! -s "${MACHINE_A_SSH_KEY}" ]]; then
    install -m 0600 "${AAP_BASELINE_SSH_KEY}" "${MACHINE_A_SSH_KEY}"
  fi

  if [[ ! -s "${AAP_BOOTSTRAP_SSH_KEY}" ]]; then
    printf 'AAP bootstrap SSH key not found: %s\n' "${AAP_BOOTSTRAP_SSH_KEY}" >&2
    printf 'Run the customer baseline substrate step first, or set AAP_BOOTSTRAP_SSH_KEY explicitly.\n' >&2
    exit 1
  fi

  if [[ ! -s "${MACHINE_A_SSH_KEY}" ]]; then
    ssh-keygen -t ed25519 -f "${MACHINE_A_SSH_KEY}" -N ''
  fi
  chmod 0600 "${MACHINE_A_SSH_KEY}"
fi

if [[ -n "${VAULT_TOKEN:-}" ]]; then
  printf '%s' "${VAULT_TOKEN}" >"${MACHINE_A_SECRETS_DIR}/.vault-token"
elif [[ -r "${HOME}/.vault-token" ]]; then
  tr -d '\r\n' <"${HOME}/.vault-token" >"${MACHINE_A_SECRETS_DIR}/.vault-token"
fi
if [[ -f "${MACHINE_A_SECRETS_DIR}/.vault-token" ]]; then
  chmod 0600 "${MACHINE_A_SECRETS_DIR}/.vault-token"
fi

if [[ -n "${AAP_AUTOMATION_SOURCE_DIR:-}" ]]; then
  if [[ ! -f "${AAP_AUTOMATION_SOURCE_DIR}/ansible/ansible.cfg" ]]; then
    printf 'AAP automation source directory is not a modulix-automation checkout: %s\n' \
      "${AAP_AUTOMATION_SOURCE_DIR}" >&2
    exit 1
  fi
  mkdir -p "${MACHINE_A_EXPORT_ROOT}/src/modulix-automation"
  rsync -a --delete \
    --exclude='.git' \
    --exclude='.artifacts' \
    --exclude='ansible/.artifacts' \
    --exclude='ansible/.tmp' \
    --exclude='ansible/ansible-navigator.log' \
    --exclude='ansible/venv-*' \
    --exclude='ansible/ansible-automation-platform-containerized-setup-bundle-*.tar.gz' \
    --exclude='ansible/manifest*.zip' \
    --exclude='packaging/rpm/.rpmbuild' \
    --exclude='packaging/rpm/dist' \
    "${AAP_AUTOMATION_SOURCE_DIR}/" \
    "${MACHINE_A_EXPORT_ROOT}/src/modulix-automation/"
elif [[ ! -d "${MACHINE_A_EXPORT_ROOT}/src/modulix-automation" ]]; then
  git clone "${AUTOMATION_REPO_URL}" "${MACHINE_A_EXPORT_ROOT}/src/modulix-automation"
else
  git -C "${MACHINE_A_EXPORT_ROOT}/src/modulix-automation" pull --ff-only
fi

printf 'Machine A AAP staging is ready: %s\n' "${MACHINE_A_APPL_ROOT}"
