#!/usr/bin/env bash
# Deprecated compatibility entry point. New guides should run
# runbooks/50-applications/aap/02-local-execution-control.yml with
# -e aap_action=<artifacts|host_prepare_preflight|tls|deploy|status>.
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
modulix_write_podman_storage_conf

cd "${AUTOMATION_ANSIBLE_DIR}"
resolve_aap_artifacts=false
for playbook in "${playbooks[@]}"; do
  case "$(basename -- "${playbook}")" in
    05-artifacts.yml | 07-preflight.yml | 10-deploy.yml)
      resolve_aap_artifacts=true
      ;;
  esac
done
if [[ "${resolve_aap_artifacts}" == "true" ]]; then
  modulix_resolve_aap_artifacts
fi
modulix_write_aap_inventory

for playbook in "${playbooks[@]}"; do
  modulix_ansible_ee ansible-playbook \
    "${playbook}" \
    -i "${INVENTORY_REL}" \
    --limit "${AAP_INVENTORY_HOST}" \
    "${ansible_playbook_args[@]}"
done
