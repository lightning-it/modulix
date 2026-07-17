#!/usr/bin/env bash
# Deprecated compatibility entry point. New guides should run
# runbooks/50-applications/aap/02-local-execution-control.yml with
# -e aap_action=prepare_machine_a.
set -euo pipefail

env_file="${1:-${MACHINE_A_ENV_FILE:-}}"

if [[ -z "${env_file}" ]]; then
  printf 'Pass the target-specific Machine A environment file explicitly.\n' >&2
  exit 1
fi
if [[ -L "${env_file}" || ! -f "${env_file}" || ! -r "${env_file}" ||
      ! -O "${env_file}" ]]; then
  printf 'AAP local env file not readable: %s\n' "${env_file}" >&2
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
  AUTOMATION_REPO_URL
  MACHINE_A_AAP_ROOT
  MACHINE_A_APPL_ROOT
  MACHINE_A_EXPORT_ROOT
  MACHINE_A_SECRETS_DIR
  MACHINE_A_TMP_DIR
)

for var_name in "${required_vars[@]}"; do
  if [[ -z "${!var_name:-}" ]]; then
    printf 'Required variable is not set: %s\n' "${var_name}" >&2
    exit 1
  fi
done

if [[ "${MACHINE_A_APPL_ROOT}" == \
      "${MACHINE_A_AAP_ROOT}/${AAP_DEPLOYMENT_ID}" ]]; then
  install -d -m 0750 "${MACHINE_A_AAP_ROOT}"
fi
install -d -m 0750 \
  "${MACHINE_A_APPL_ROOT}" \
  "${MACHINE_A_APPL_ROOT}/etc" \
  "${MACHINE_A_APPL_ROOT}/artifacts" \
  "${MACHINE_A_EXPORT_ROOT}" \
  "${MACHINE_A_EXPORT_ROOT}/artifacts/aap" \
  "${MACHINE_A_EXPORT_ROOT}/src"
install -d -m 0700 \
  "${MACHINE_A_SECRETS_DIR}" \
  "${MACHINE_A_TMP_DIR}"
modulix_validate_machine_a_workspace
if [[ "$(stat -c '%a' -- "${MACHINE_A_SECRETS_DIR}")" != "700" ||
      "$(stat -c '%a' -- "${MACHINE_A_TMP_DIR}")" != "700" ]]; then
  printf 'Machine A secrets and temporary directories must have mode 0700.\n' >&2
  exit 1
fi

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

if [[ "${AAP_SECRET_BACKEND}" == "hashicorp_vault" ]]; then
  if [[ -n "${VAULT_TOKEN:-}" ]]; then
    printf '%s' "${VAULT_TOKEN}" >"${MACHINE_A_SECRETS_DIR}/.vault-token"
  elif [[ -r "${HOME}/.vault-token" ]]; then
    tr -d '\r\n' <"${HOME}/.vault-token" >"${MACHINE_A_SECRETS_DIR}/.vault-token"
  fi
  if [[ -f "${MACHINE_A_SECRETS_DIR}/.vault-token" ]]; then
    chmod 0600 "${MACHINE_A_SECRETS_DIR}/.vault-token"
  fi
else
  rm -f "${MACHINE_A_SECRETS_DIR}/.vault-token"
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
