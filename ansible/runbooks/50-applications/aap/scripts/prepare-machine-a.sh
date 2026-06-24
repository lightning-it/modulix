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
  AAP_BASELINE_SSH_KEY
  AAP_BOOTSTRAP_SSH_KEY
  AAP_EXPORT_ROOT
  AAP_SECRETS_DIR
  AAP_SSH_KEY
  AUTOMATION_REPO_URL
)

for var_name in "${required_vars[@]}"; do
  if [[ -z "${!var_name:-}" ]]; then
    printf 'Required variable is not set: %s\n' "${var_name}" >&2
    exit 1
  fi
done

sudo install -d -m 0750 -o "$(id -un)" -g "$(id -gn)" \
  "${AAP_APPL_ROOT}" \
  "${AAP_APPL_ROOT}/etc" \
  "${AAP_SECRETS_DIR}" \
  "${AAP_APPL_ROOT}/artifacts" \
  "${AAP_EXPORT_ROOT}" \
  "${AAP_EXPORT_ROOT}/artifacts/aap" \
  "${AAP_EXPORT_ROOT}/src"

if [[ -s "${AAP_BASELINE_SSH_KEY}" && ! -s "${AAP_SSH_KEY}" ]]; then
  install -m 0600 "${AAP_BASELINE_SSH_KEY}" "${AAP_SSH_KEY}"
fi

if [[ ! -s "${AAP_BOOTSTRAP_SSH_KEY}" ]]; then
  printf 'AAP bootstrap SSH key not found: %s\n' "${AAP_BOOTSTRAP_SSH_KEY}" >&2
  printf 'Run the RHEL 10 baseline substrate step first, or set AAP_BOOTSTRAP_SSH_KEY explicitly.\n' >&2
  exit 1
fi

if [[ ! -s "${AAP_SSH_KEY}" ]]; then
  ssh-keygen -t ed25519 -f "${AAP_SSH_KEY}" -N ''
fi
chmod 0600 "${AAP_SSH_KEY}"

if [[ ! -d "${AAP_EXPORT_ROOT}/src/modulix-automation" ]]; then
  git clone "${AUTOMATION_REPO_URL}" "${AAP_EXPORT_ROOT}/src/modulix-automation"
fi
git -C "${AAP_EXPORT_ROOT}/src/modulix-automation" pull --ff-only

printf 'Machine A AAP staging is ready: %s\n' "${AAP_APPL_ROOT}"
