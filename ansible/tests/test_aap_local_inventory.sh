#!/usr/bin/env bash
set -euo pipefail

ansible_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
library="${ansible_root}/runbooks/50-applications/aap/scripts/aap-local-lib.sh"
inventory_template="${ansible_root}/runbooks/50-applications/aap/templates/aap-local/inventories/group_vars/aaps/aap.yml.j2"
test_root="$(mktemp -d)"
trap 'rm -rf -- "${test_root}"' EXIT

export HOME="${test_root}/home"
export AAP_FQDN="aap.example.test"
export AAP_ANSIBLE_HOST="${AAP_FQDN}"
export AAP_APPL_ROOT="${test_root}/aap-local"
export AAP_SECRET_BACKEND="ansible_vault"
export AAP_SSH_KEY_AUTH_ENABLED="false"
export AUTOMATION_DIR="${test_root}/modulix-automation"
export AUTOMATION_ANSIBLE_DIR="${AUTOMATION_DIR}/ansible"
export INVENTORY_NAME="test"
export MODULIX_RUN_EE_IMAGE="example.invalid/ee-wunder-ansible-ubi9:test"

# shellcheck source=/dev/null
. "${library}"
modulix_aap_set_defaults

vault_vars_dir="${AUTOMATION_ANSIBLE_DIR}/inventories/${INVENTORY_NAME}/group_vars/aaps"
mkdir -p "${vault_vars_dir}"
printf '%s\n' '$ANSIBLE_VAULT;1.1;AES256' >"${vault_vars_dir}/aap_ansible_vault.yml"

modulix_write_aap_inventory

rendered_inventory="${vault_vars_dir}/aap.yml"
grep -Fxq \
  'aap_deploy_gateway_main_url: "https://aap.example.test"' \
  "${rendered_inventory}"
grep -Fxq \
  'aap_deploy_gateway_verify_url: "{{ aap_deploy_gateway_main_url }}"' \
  "${rendered_inventory}"

grep -Fxq \
  'aap_deploy_gateway_main_url: "https://{{ aap_fqdn }}"' \
  "${inventory_template}"
grep -Fxq \
  'aap_deploy_gateway_verify_url: "{{ '"'"'{{'"'"' }} aap_deploy_gateway_main_url {{ '"'"'}}'"'"' }}"' \
  "${inventory_template}"

for inventory_source in "${rendered_inventory}" "${inventory_template}"; do
  for forbidden_value in \
    aap_deploy_hub_upload_readiness_url \
    aap_deploy_hub_container_registry_url \
    aap_deploy_hub_seed_execution_environment_images \
    aap_deploy_eda_api_url \
    aap_deploy_reset_partial_install_enabled \
    :8444 \
    :8445 \
    :8446; do
    if grep -Fq "${forbidden_value}" "${inventory_source}"; then
      printf 'AAP inventory source %s contains forbidden direct-service value: %s\n' \
        "${inventory_source}" "${forbidden_value}" >&2
      exit 1
    fi
  done
done

echo "AAP local inventory gateway and clean-install safety tests passed"
