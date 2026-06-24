#!/usr/bin/env bash
set -euo pipefail

env_file="${AAP_ENV_FILE:-/appl/modulix-aap/etc/aap-local.env}"

if [[ "${1:-}" == "--env-file" ]]; then
  env_file="${2:-}"
  shift 2
fi

if [[ ! -r "${env_file}" ]]; then
  printf 'AAP local env file not readable: %s\n' "${env_file}" >&2
  exit 1
fi
if [[ "$#" -eq 0 ]]; then
  printf 'Usage: %s [--env-file PATH] PLAYBOOK [PLAYBOOK ...] [-- ANSIBLE_PLAYBOOK_ARGS ...]\n' "$0" >&2
  exit 1
fi

playbooks=()
ansible_playbook_args=()
while [[ "$#" -gt 0 ]]; do
  if [[ "$1" == "--" ]]; then
    shift
    ansible_playbook_args=("$@")
    break
  fi
  playbooks+=("$1")
  shift
done

if [[ "${#playbooks[@]}" -eq 0 ]]; then
  printf 'At least one playbook is required.\n' >&2
  exit 1
fi

# shellcheck source=/dev/null
. "${env_file}"

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
. "${script_dir}/aap-local-lib.sh"
modulix_aap_set_defaults

cd "${AUTOMATION_ANSIBLE_DIR}"
modulix_resolve_aap_artifacts
modulix_write_aap_inventory

for playbook in "${playbooks[@]}"; do
  modulix_ansible_ee ansible-playbook \
    "${playbook}" \
    -i "${INVENTORY_REL}" \
    --limit "${AAP_INVENTORY_HOST}" \
    "${ansible_playbook_args[@]}"
done
