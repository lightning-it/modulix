#!/usr/bin/env bash

# Deprecated compatibility library. New guides should use
# runbooks/50-applications/aap/02-local-execution-control.yml with
# aap_action=... instead of sourcing this file.

modulix_aap_set_defaults() {
  local modulix_run_ee_last_segment

  if [[ -z "${AAP_FQDN:-}" ]]; then
    printf 'AAP_FQDN is required.\n' >&2
    return 1
  fi
  if [[ ! "${AAP_FQDN}" =~ ^([a-z0-9]([a-z0-9-]*[a-z0-9])?\.)+[a-z0-9]([a-z0-9-]*[a-z0-9])?$ ]]; then
    printf 'AAP_FQDN must be a canonical lower-case FQDN, got: %s\n' \
      "${AAP_FQDN}" >&2
    return 1
  fi
  : "${AAP_DEPLOYMENT_ID:=${AAP_FQDN}}"
  if [[ "${AAP_DEPLOYMENT_ID}" != "${AAP_FQDN}" ]]; then
    printf 'AAP_DEPLOYMENT_ID must exactly match AAP_FQDN: %s != %s\n' \
      "${AAP_DEPLOYMENT_ID}" "${AAP_FQDN}" >&2
    return 1
  fi
  : "${AAP_SHORTNAME:=${AAP_FQDN%%.*}}"
  : "${AAP_USER:=svc_ansible}"
  : "${AAP_SETUP_USER:=${AAP_USER}}"
  : "${AAP_INSTALL_USER:=svc_aap}"
  : "${AAP_ANSIBLE_HOST:=${AAP_FQDN}}"
  : "${AAP_ANSIBLE_BECOME_FLAGS:=}"
  : "${AAP_SECRET_BACKEND:=hashicorp_vault}"
  : "${AAP_HUB_SEED_EXECUTION_ENVIRONMENT_IMAGES:=true}"
  : "${AAP_SSH_KEY_AUTH_ENABLED:=true}"
  : "${AAP_BOOTSTRAP_USER:=${AAP_USER}}"
  if [[ "${AAP_SSH_KEY_AUTH_ENABLED}" != "true" &&
        "${AAP_USER}" == "svc_ansible" &&
        "${AAP_BOOTSTRAP_USER}" != "svc_ansible" ]]; then
    AAP_USER="${AAP_BOOTSTRAP_USER}"
  fi
  if [[ "${AAP_SSH_KEY_AUTH_ENABLED}" != "true" &&
        "${AAP_USER}" == "root" &&
        "${AAP_BOOTSTRAP_USER}" == "root" &&
        -n "${SUDO_USER:-}" &&
        "${SUDO_USER}" != "root" ]]; then
    AAP_BOOTSTRAP_USER="${SUDO_USER}"
    AAP_USER="${SUDO_USER}"
  fi
  if [[ "${AAP_SSH_KEY_AUTH_ENABLED}" == "true" ]]; then
    : "${AAP_BASELINE_SSH_KEY:=${HOME}/sources/modulix-automation/ansible/.tmp/${AAP_SHORTNAME}-secrets/svc_ansible_aap}"
    : "${AAP_BOOTSTRAP_SSH_KEY:=${AAP_BASELINE_SSH_KEY}}"
  else
    : "${AAP_BASELINE_SSH_KEY:=}"
    : "${AAP_BOOTSTRAP_SSH_KEY:=}"
  fi
  : "${AAP_INVENTORY_HOST:=${AAP_SHORTNAME}}"
  : "${AAP_APPL_ROOT:=/appl/aap-local}"
  : "${AAP_ENV_FILE:=${AAP_APPL_ROOT}/etc/aap-local.env}"
  : "${AAP_SECRETS_DIR:=${AAP_APPL_ROOT}/secrets}"
  : "${AAP_KNOWN_HOSTS_FILE:=${AAP_SECRETS_DIR}/bootstrap_known_hosts}"
  : "${AAP_KNOWN_HOSTS_CONTAINER:=/runner/secrets/bootstrap_known_hosts}"
  if [[ "${AAP_SSH_KEY_AUTH_ENABLED}" == "true" ]]; then
    : "${AAP_SSH_KEY:=${AAP_SECRETS_DIR}/svc_ansible_aap}"
  else
    : "${AAP_SSH_KEY:=}"
  fi
  : "${MACHINE_A_AAP_ROOT:=${HOME}/appl/aap}"
  : "${MACHINE_A_APPL_ROOT:=${MACHINE_A_AAP_ROOT}/${AAP_DEPLOYMENT_ID}}"
  : "${MACHINE_A_EXPORT_ROOT:=${MACHINE_A_APPL_ROOT}/export}"
  : "${MACHINE_A_ENV_FILE:=${MACHINE_A_APPL_ROOT}/etc/aap-local.env}"
  : "${MACHINE_A_SECRETS_DIR:=${MACHINE_A_APPL_ROOT}/secrets}"
  : "${MACHINE_A_TMP_DIR:=${MACHINE_A_APPL_ROOT}/tmp}"
  : "${MACHINE_A_ANSIBLE_VAULT_PASSWORD_FILE:=${MACHINE_A_SECRETS_DIR}/.vault-pass.txt}"
  if [[ "${AAP_SSH_KEY_AUTH_ENABLED}" == "true" ]]; then
    : "${MACHINE_A_SSH_KEY:=${MACHINE_A_SECRETS_DIR}/svc_ansible_aap}"
  else
    : "${MACHINE_A_SSH_KEY:=}"
  fi
  : "${MACHINE_A_BOOTSTRAP_KNOWN_HOSTS:=${MACHINE_A_SECRETS_DIR}/bootstrap_known_hosts}"
  if [[ "${AAP_SSH_KEY_AUTH_ENABLED}" == "true" ]]; then
    : "${AAP_SSH_KEY_CONTAINER:=/runner/secrets/$(basename "${AAP_SSH_KEY}")}"
  else
    : "${AAP_SSH_KEY_CONTAINER:=}"
  fi
  : "${AUTOMATION_DIR:=${AAP_APPL_ROOT}/src/modulix-automation}"
  : "${AUTOMATION_ANSIBLE_DIR:=${AUTOMATION_DIR}/ansible}"
  : "${AAP_ARTIFACT_DIR:=${AUTOMATION_ANSIBLE_DIR}/.artifacts}"
  : "${INVENTORY_REL:=inventories/${INVENTORY_NAME}/inventory.yml}"
  : "${INVENTORY_FILE:=${AUTOMATION_ANSIBLE_DIR}/${INVENTORY_REL}}"
  MODULIX_RUN_EE_ARCHIVE="${MODULIX_RUN_EE_IMAGE##*/}.tar"
  MODULIX_RUN_EE_ARCHIVE="${MODULIX_RUN_EE_ARCHIVE//:/-}"
  MODULIX_RUN_EE_ARCHIVE_PATH="${AAP_APPL_ROOT}/artifacts/${MODULIX_RUN_EE_ARCHIVE}"
  : "${MODULIX_RUN_EE_DIGEST:=}"
  # Machine A publishes and saves the tag. Target-side pulls and runs use the
  # immutable repository@digest reference when a registry digest was recorded.
  # Inspect only the final path segment so a registry port is never mistaken
  # for an image tag.
  MODULIX_RUN_EE_REPOSITORY="${MODULIX_RUN_EE_IMAGE}"
  modulix_run_ee_last_segment="${MODULIX_RUN_EE_REPOSITORY##*/}"
  if [[ "${modulix_run_ee_last_segment}" == *:* ]]; then
    MODULIX_RUN_EE_REPOSITORY="${MODULIX_RUN_EE_REPOSITORY%:*}"
  fi
  MODULIX_RUN_EE_RUNTIME_IMAGE="${MODULIX_RUN_EE_IMAGE}"
  if [[ -n "${MODULIX_RUN_EE_DIGEST}" ]]; then
    if [[ "${MODULIX_RUN_EE_IMAGE}" == *@* ]]; then
      printf 'MODULIX_RUN_EE_IMAGE must not contain @ when MODULIX_RUN_EE_DIGEST is set.\n' >&2
      return 1
    fi
    if [[ ! "${MODULIX_RUN_EE_DIGEST}" =~ ^sha256:[0-9a-f]{64}$ ]]; then
      printf 'MODULIX_RUN_EE_DIGEST must be a SHA-256 digest, got: %s\n' \
        "${MODULIX_RUN_EE_DIGEST}" >&2
      return 1
    fi
    MODULIX_RUN_EE_RUNTIME_IMAGE="${MODULIX_RUN_EE_REPOSITORY}@${MODULIX_RUN_EE_DIGEST}"
  fi
  : "${ANSIBLE_TOOLBOX_RUNTIME_MODE:=disconnected}"
  if [[ "${AAP_SECRET_BACKEND}" == "ansible_vault" ]]; then
    : "${ANSIBLE_VAULT_PASSWORD_FILE:=${AAP_SECRETS_DIR}/.vault-pass.txt}"
    if [[ "${ANSIBLE_VAULT_PASSWORD_FILE}" != "${AAP_SECRETS_DIR}/.vault-pass.txt" ]]; then
      printf 'ANSIBLE_VAULT_PASSWORD_FILE must be %s for the fixed EE mount, got: %s\n' \
        "${AAP_SECRETS_DIR}/.vault-pass.txt" "${ANSIBLE_VAULT_PASSWORD_FILE}" >&2
      return 1
    fi
  else
    ANSIBLE_VAULT_PASSWORD_FILE=""
  fi
  : "${ANSIBLE_COLLECTIONS_PATH:=/runner/project/collections:/usr/share/ansible/collections:/usr/share/automation-controller/collections:/runner/collections}"
  : "${AAP_PODMAN_STORAGE_CONF:=${AAP_APPL_ROOT}/etc/containers-storage.conf}"
  : "${AAP_PODMAN_ROOT_GRAPHROOT:=/appl/podman/root-storage}"
  : "${AAP_PODMAN_ROOT_RUNROOT:=/appl/podman/root-run}"
  : "${AAP_PODMAN_TMPDIR:=/appl/tmp}"
  : "${AAP_EE_TRANSFER_ENABLED:=true}"
  : "${AAP_HOST_CA_TRUST_DIR:=/etc/pki/ca-trust}"
  : "${AAP_REQUESTS_CA_BUNDLE:=${AAP_HOST_CA_TRUST_DIR}/extracted/pem/tls-ca-bundle.pem}"

  case "${AAP_SECRET_BACKEND}" in
    hashicorp_vault | ansible_vault) ;;
    *)
      printf 'AAP_SECRET_BACKEND must be hashicorp_vault or ansible_vault, got: %s\n' \
        "${AAP_SECRET_BACKEND}" >&2
      return 1
      ;;
  esac
  case "${AAP_HUB_SEED_EXECUTION_ENVIRONMENT_IMAGES}" in
    true | false) ;;
    *)
      printf 'AAP_HUB_SEED_EXECUTION_ENVIRONMENT_IMAGES must be true or false, got: %s\n' \
        "${AAP_HUB_SEED_EXECUTION_ENVIRONMENT_IMAGES}" >&2
      return 1
      ;;
  esac

  if [[ "${AAP_SECRET_BACKEND}" == "hashicorp_vault" ]]; then
    : "${AAP_VAULT_HOST_KEY:=${AAP_FQDN}}"
    : "${AAP_VAULT_ADMIN_PASSWORDS_KV_PATH:=${AAP_VAULT_HOST_KEY}/aap/deploy/admin_passwords}"
    : "${AAP_VAULT_DEFAULTS_KV_PATH:=defaults}"
    if [[ -z "${VAULT_VALIDATE_CERTS+x}" ]]; then
      case "${VAULT_SKIP_VERIFY:-false}" in
        true) VAULT_VALIDATE_CERTS=false ;;
        false | "") VAULT_VALIDATE_CERTS=true ;;
        *)
          printf 'VAULT_SKIP_VERIFY must be true or false, got: %s\n' \
            "${VAULT_SKIP_VERIFY}" >&2
          return 1
          ;;
      esac
    fi
    case "${VAULT_VALIDATE_CERTS}" in
      true) VAULT_SKIP_VERIFY=false ;;
      false) VAULT_SKIP_VERIFY=true ;;
      *)
        printf 'VAULT_VALIDATE_CERTS must be true or false, got: %s\n' \
          "${VAULT_VALIDATE_CERTS}" >&2
        return 1
        ;;
    esac
    # On the AAP host, the staged token file is authoritative.
    if [[ -s "${AAP_SECRETS_DIR}/.vault-token" ]]; then
      VAULT_TOKEN="$(tr -d '\r\n' <"${AAP_SECRETS_DIR}/.vault-token")"
    fi
  else
    # Never forward inherited HashiCorp context into Ansible Vault runs.
    unset \
      AAP_VAULT_ADMIN_PASSWORDS_KV_PATH \
      AAP_VAULT_DEFAULTS_KV_PATH \
      AAP_VAULT_HOST_KEY \
      VAULT_ADDR \
      VAULT_ENGINE_MOUNT_POINT \
      VAULT_SKIP_VERIFY \
      VAULT_TOKEN \
      VAULT_VALIDATE_CERTS
  fi

  export AAP_DEPLOYMENT_ID AAP_SHORTNAME AAP_USER AAP_SETUP_USER AAP_INSTALL_USER AAP_ANSIBLE_HOST
  export AAP_ANSIBLE_BECOME_FLAGS AAP_SECRET_BACKEND
  export AAP_HUB_SEED_EXECUTION_ENVIRONMENT_IMAGES
  export AAP_SSH_KEY_AUTH_ENABLED
  export AAP_BOOTSTRAP_USER AAP_BASELINE_SSH_KEY AAP_BOOTSTRAP_SSH_KEY
  export AAP_INVENTORY_HOST AAP_APPL_ROOT AAP_ENV_FILE
  export AAP_SECRETS_DIR AAP_SSH_KEY AAP_SSH_KEY_CONTAINER
  export AAP_KNOWN_HOSTS_FILE AAP_KNOWN_HOSTS_CONTAINER
  export MACHINE_A_AAP_ROOT MACHINE_A_APPL_ROOT MACHINE_A_EXPORT_ROOT MACHINE_A_ENV_FILE
  export MACHINE_A_SECRETS_DIR MACHINE_A_TMP_DIR MACHINE_A_ANSIBLE_VAULT_PASSWORD_FILE
  export MACHINE_A_SSH_KEY MACHINE_A_BOOTSTRAP_KNOWN_HOSTS
  export AUTOMATION_DIR AUTOMATION_ANSIBLE_DIR AAP_ARTIFACT_DIR
  export INVENTORY_REL INVENTORY_FILE
  export MODULIX_RUN_EE_ARCHIVE MODULIX_RUN_EE_ARCHIVE_PATH
  export MODULIX_RUN_EE_DIGEST MODULIX_RUN_EE_REPOSITORY MODULIX_RUN_EE_RUNTIME_IMAGE
  export ANSIBLE_TOOLBOX_RUNTIME_MODE ANSIBLE_VAULT_PASSWORD_FILE ANSIBLE_COLLECTIONS_PATH
  export AAP_PODMAN_STORAGE_CONF AAP_PODMAN_ROOT_GRAPHROOT AAP_PODMAN_ROOT_RUNROOT AAP_PODMAN_TMPDIR
  export AAP_EE_TRANSFER_ENABLED
  export AAP_HOST_CA_TRUST_DIR AAP_REQUESTS_CA_BUNDLE
  if [[ "${AAP_SECRET_BACKEND}" == "hashicorp_vault" ]]; then
    export AAP_VAULT_HOST_KEY AAP_VAULT_ADMIN_PASSWORDS_KV_PATH AAP_VAULT_DEFAULTS_KV_PATH
    export VAULT_TOKEN VAULT_VALIDATE_CERTS VAULT_SKIP_VERIFY
  fi
}

modulix_validate_machine_a_workspace() {
  local -a machine_a_paths
  local expected_appl_root
  local machine_a_path

  expected_appl_root="${MACHINE_A_AAP_ROOT}/${AAP_DEPLOYMENT_ID}"
  if [[ "${MACHINE_A_ENV_FILE}" != "${MACHINE_A_APPL_ROOT}/etc/aap-local.env" ||
        "${MACHINE_A_SECRETS_DIR}" != "${MACHINE_A_APPL_ROOT}/secrets" ||
        "${MACHINE_A_TMP_DIR}" != "${MACHINE_A_APPL_ROOT}/tmp" ]]; then
    printf 'Machine A environment, secrets, and temporary paths must stay inside: %s\n' \
      "${MACHINE_A_APPL_ROOT}" >&2
    return 1
  fi
  if [[ "${MACHINE_A_APPL_ROOT}" == "${expected_appl_root}" ]]; then
    if [[ "${MACHINE_A_EXPORT_ROOT}" != "${expected_appl_root}/export" ]]; then
      printf 'Target-scoped Machine A export must stay inside: %s\n' \
        "${expected_appl_root}" >&2
      return 1
    fi
  elif [[ "${MACHINE_A_APPL_ROOT}" != /* ||
          "${MACHINE_A_EXPORT_ROOT}" != /* ||
          "${MACHINE_A_APPL_ROOT}" == "/" ||
          "${MACHINE_A_EXPORT_ROOT}" == "/" ||
          "${MACHINE_A_APPL_ROOT}" == "${HOME}" ||
          "${MACHINE_A_EXPORT_ROOT}" == "${HOME}" ||
          "${MACHINE_A_EXPORT_ROOT}" == "${MACHINE_A_APPL_ROOT}" ]]; then
    printf 'Explicit legacy Machine A roots are unsafe.\n' >&2
    return 1
  fi

  machine_a_paths=(
    "${MACHINE_A_APPL_ROOT}"
    "${MACHINE_A_APPL_ROOT}/etc"
    "${MACHINE_A_APPL_ROOT}/artifacts"
    "${MACHINE_A_SECRETS_DIR}"
    "${MACHINE_A_TMP_DIR}"
    "${MACHINE_A_EXPORT_ROOT}"
    "${MACHINE_A_EXPORT_ROOT}/src"
    "${MACHINE_A_ENV_FILE}"
  )
  if [[ "${MACHINE_A_APPL_ROOT}" == "${expected_appl_root}" ]]; then
    machine_a_paths=("${MACHINE_A_AAP_ROOT}" "${machine_a_paths[@]}")
  fi

  for machine_a_path in "${machine_a_paths[@]}"; do
    if [[ -L "${machine_a_path}" ]]; then
      printf 'Machine A workspace path must not be a symlink: %s\n' \
        "${machine_a_path}" >&2
      return 1
    fi
    if [[ -e "${machine_a_path}" && ! -O "${machine_a_path}" ]]; then
      printf 'Machine A workspace path must be owned by %s: %s\n' \
        "$(id -un)" "${machine_a_path}" >&2
      return 1
    fi
  done
  return 0
}

modulix_validate_ansible_vault_password_file() {
  local password_file="${1:-${ANSIBLE_VAULT_PASSWORD_FILE:-}}"
  local expected_owner="${2:-${AAP_SETUP_USER:-}}"

  if [[ -z "${password_file}" || -z "${expected_owner}" ]]; then
    printf 'Ansible Vault password-file validation requires a path and expected owner.\n' >&2
    return 1
  fi
  if [[ -L "${password_file}" || ! -f "${password_file}" || ! -s "${password_file}" ]]; then
    printf 'Ansible Vault password file is missing or unsafe: %s\n' \
      "${password_file}" >&2
    return 1
  fi
  if [[ "$(stat -c '%h' -- "${password_file}")" != "1" ]]; then
    printf 'Ansible Vault password file must not have hard links: %s\n' \
      "${password_file}" >&2
    return 1
  fi
  if [[ "$(stat -c '%U' -- "${password_file}")" != "${expected_owner}" ]]; then
    printf 'Ansible Vault password file must be owned by %s: %s\n' \
      "${expected_owner}" "${password_file}" >&2
    return 1
  fi
  if [[ "$(stat -c '%a' -- "${password_file}")" != "600" ]]; then
    printf 'Ansible Vault password file must have mode 0600: %s\n' \
      "${password_file}" >&2
    return 1
  fi
  return 0
}

modulix_write_podman_storage_conf() {
  mkdir -p \
    "$(dirname "${AAP_PODMAN_STORAGE_CONF}")" \
    "${AAP_PODMAN_ROOT_GRAPHROOT}" \
    "${AAP_PODMAN_ROOT_RUNROOT}" \
    "${AAP_PODMAN_TMPDIR}"

  cat >"${AAP_PODMAN_STORAGE_CONF}" <<EOF
[storage]
driver = "overlay"
graphroot = "${AAP_PODMAN_ROOT_GRAPHROOT}"
runroot = "${AAP_PODMAN_ROOT_RUNROOT}"

[storage.options]
EOF

  if [[ -x /usr/bin/fuse-overlayfs ]]; then
    printf 'mount_program = "/usr/bin/fuse-overlayfs"\n' >>"${AAP_PODMAN_STORAGE_CONF}"
  fi

  chmod 0644 "${AAP_PODMAN_STORAGE_CONF}"
  export CONTAINERS_STORAGE_CONF="${AAP_PODMAN_STORAGE_CONF}"
  export TMPDIR="${AAP_PODMAN_TMPDIR}"
}

modulix_resolve_aap_artifacts() {
  mapfile -t AAP_BUNDLE_FILES < <(
    find "${AAP_ARTIFACT_DIR}" -maxdepth 1 -type f \
      -name 'ansible-automation-platform-containerized-setup-bundle-*-x86_64.tar.gz' | sort -V
  )
  mapfile -t AAP_MANIFEST_FILES < <(
    find "${AAP_ARTIFACT_DIR}" -maxdepth 1 -type f \
      -name 'manifest*.zip' | sort -V
  )

  if [[ "${#AAP_BUNDLE_FILES[@]}" -ne 1 ]]; then
    printf 'Expected exactly one AAP setup bundle in %s, found %s.\n' \
      "${AAP_ARTIFACT_DIR}" "${#AAP_BUNDLE_FILES[@]}" >&2
    return 1
  fi
  if [[ "${#AAP_MANIFEST_FILES[@]}" -ne 1 ]]; then
    printf 'Expected exactly one AAP manifest in %s, found %s.\n' \
      "${AAP_ARTIFACT_DIR}" "${#AAP_MANIFEST_FILES[@]}" >&2
    return 1
  fi

  export AAP_BUNDLE_REMOTE_SRC="${AAP_BUNDLE_FILES[0]}"
  export AAP_MANIFEST_REMOTE_SRC="${AAP_MANIFEST_FILES[0]}"
}

modulix_ansible_ee() {
  local -a ssh_agent_args=()
  local -a ansible_vault_args=()
  local -a vault_runtime_args=()
  local aap_local_ansible_config="${AUTOMATION_ANSIBLE_DIR}/aap-local.cfg"
  if [[ -S "${SSH_AUTH_SOCK:-}" ]]; then
    ssh_agent_args=(
      -e SSH_AUTH_SOCK=/runner/ssh-agent
      -v "${SSH_AUTH_SOCK}:/runner/ssh-agent"
    )
  fi

  if [[ ! -d "${AAP_HOST_CA_TRUST_DIR}" || ! -r "${AAP_REQUESTS_CA_BUNDLE}" ]]; then
    printf 'RHEL host CA trust is not readable: %s (bundle: %s)\n' \
      "${AAP_HOST_CA_TRUST_DIR}" "${AAP_REQUESTS_CA_BUNDLE}" >&2
    return 1
  fi
  if [[ ! -s "${AAP_KNOWN_HOSTS_FILE}" ]]; then
    printf 'Verified SSH known hosts file is missing or empty: %s\n' \
      "${AAP_KNOWN_HOSTS_FILE}" >&2
    return 1
  fi
  if [[ ! -r "${aap_local_ansible_config}" ]]; then
    printf 'Dedicated AAP Ansible config is missing or unreadable: %s\n' \
      "${aap_local_ansible_config}" >&2
    return 1
  fi

  if [[ "${AAP_SECRET_BACKEND}" == "ansible_vault" ]]; then
    if ! modulix_validate_ansible_vault_password_file \
      "${ANSIBLE_VAULT_PASSWORD_FILE}" "${AAP_SETUP_USER}"; then
      return 1
    fi
    ansible_vault_args=(
      -e ANSIBLE_VAULT_PASSWORD_FILE=/runner/secrets/.vault-pass.txt
    )
  else
    vault_runtime_args=(
      -e VAULT_ADDR
      -e VAULT_SKIP_VERIFY
      -e VAULT_VALIDATE_CERTS
      -e VAULT_TOKEN
      -e VAULT_ENGINE_MOUNT_POINT
      -e AAP_VAULT_HOST_KEY
      -e AAP_VAULT_ADMIN_PASSWORDS_KV_PATH
      -e AAP_VAULT_DEFAULTS_KV_PATH
    )
  fi

  podman run --rm \
    --network=host \
    --security-opt label=disable \
    --user 0 \
    -e ANSIBLE_CONFIG=/runner/project/aap-local.cfg \
    -e ANSIBLE_HOST_KEY_CHECKING=true \
    -e ANSIBLE_LOCAL_TEMP=/appl/tmp/.ansible/tmp \
    -e ANSIBLE_REMOTE_TEMP \
    -e ANSIBLE_TOOLBOX_RUNTIME_MODE \
    -e ANSIBLE_COLLECTIONS_PATH \
    "${ansible_vault_args[@]}" \
    "${vault_runtime_args[@]}" \
    -e AAP_ARTIFACT_DIR \
    -e AAP_BUNDLE_REMOTE_SRC \
    -e AAP_MANIFEST_REMOTE_SRC \
    -e REQUESTS_CA_BUNDLE="${AAP_REQUESTS_CA_BUNDLE}" \
    -v "${AUTOMATION_ANSIBLE_DIR}:/runner/project" \
    -v "${AAP_SECRETS_DIR}:/runner/secrets:ro" \
    -v "${AAP_HOST_CA_TRUST_DIR}:${AAP_HOST_CA_TRUST_DIR}:ro" \
    -v /appl/tmp:/appl/tmp \
    "${ssh_agent_args[@]}" \
    -w /runner/project \
    "${MODULIX_RUN_EE_RUNTIME_IMAGE}" \
    "$@"
}

modulix_write_aap_inventory() {
  mkdir -p \
    "${AUTOMATION_ANSIBLE_DIR}/inventories/${INVENTORY_NAME}/group_vars/aaps" \
    "${AUTOMATION_ANSIBLE_DIR}/inventories/${INVENTORY_NAME}/host_vars/${AAP_INVENTORY_HOST}" \
    "${AUTOMATION_ANSIBLE_DIR}/files/tls"

  cat >"${INVENTORY_FILE}" <<YAML
---
all:
  hosts:
    localhost:
      ansible_connection: local
      ansible_become: false

  children:
    aaps:
      hosts:
        ${AAP_INVENTORY_HOST}: {}
YAML

  cat >"${AUTOMATION_ANSIBLE_DIR}/inventories/${INVENTORY_NAME}/host_vars/${AAP_INVENTORY_HOST}/connection.yml" <<YAML
---
ansible_host: ${AAP_FQDN}
ansible_user: ${AAP_USER}
ansible_connection: ssh
ansible_become: true
ansible_become_method: sudo
ansible_ssh_common_args: >-
  -o UserKnownHostsFile=${AAP_KNOWN_HOSTS_CONTAINER}
  -o StrictHostKeyChecking=yes
ansible_remote_tmp: /appl/ansible-tmp
YAML

  if [[ "${AAP_SSH_KEY_AUTH_ENABLED}" == "true" ]]; then
    sed -i '/^ansible_ssh_common_args: >-/a\  -o IdentitiesOnly=yes' \
      "${AUTOMATION_ANSIBLE_DIR}/inventories/${INVENTORY_NAME}/host_vars/${AAP_INVENTORY_HOST}/connection.yml"
    printf 'ansible_ssh_private_key_file: %s\n' "${AAP_SSH_KEY_CONTAINER}" \
      >>"${AUTOMATION_ANSIBLE_DIR}/inventories/${INVENTORY_NAME}/host_vars/${AAP_INVENTORY_HOST}/connection.yml"
  fi

  if [[ -n "${AAP_ANSIBLE_BECOME_FLAGS}" ]]; then
    printf 'ansible_become_flags: "%s"\n' "${AAP_ANSIBLE_BECOME_FLAGS}" \
      >>"${AUTOMATION_ANSIBLE_DIR}/inventories/${INVENTORY_NAME}/host_vars/${AAP_INVENTORY_HOST}/connection.yml"
  fi

  cat >"${AUTOMATION_ANSIBLE_DIR}/inventories/${INVENTORY_NAME}/group_vars/aaps/aap.yml" <<YAML
---
aap_secret_backend: "${AAP_SECRET_BACKEND}"
aap_preflight_expected_ansible_user: "${AAP_SETUP_USER}"

aap_deploy_setup_download_version: "2.7"

aap_deploy_install_dir: /appl/aap
aap_deploy_setup_dir: "{{ aap_deploy_install_dir }}/setup"
aap_deploy_tls_dir: "{{ aap_deploy_install_dir }}/tls"
aap_deploy_installed_marker_path: "{{ aap_deploy_install_dir }}/.aap_containerized_installed"
aap_deploy_gateway_main_url: "https://${AAP_FQDN}"
aap_deploy_gateway_verify_url: "{{ aap_deploy_gateway_main_url }}"
aap_deploy_hub_seed_execution_environment_images: ${AAP_HUB_SEED_EXECUTION_ENVIRONMENT_IMAGES}

aap_deploy_install_user: ${AAP_INSTALL_USER}
aap_deploy_install_user_home: /appl/home/${AAP_INSTALL_USER}
aap_deploy_install_user_shell: /bin/bash
aap_deploy_reset_partial_install_enabled: true

aap_deploy_growth_gateway_host: "${AAP_INVENTORY_HOST}"
aap_deploy_growth_controller_host: "${AAP_INVENTORY_HOST}"
aap_deploy_growth_hub_host: "${AAP_INVENTORY_HOST}"
aap_deploy_growth_eda_host: "${AAP_INVENTORY_HOST}"
aap_deploy_growth_automationmetrics_host: "${AAP_INVENTORY_HOST}"
aap_deploy_growth_postgresql_host: "${AAP_INVENTORY_HOST}"
aap_deploy_host_alias_address: "{{ ansible_default_ipv4.address }}"
aap_deploy_gateway_pg_host: "${AAP_ANSIBLE_HOST}"
aap_deploy_controller_pg_host: "${AAP_ANSIBLE_HOST}"
aap_deploy_hub_pg_host: "${AAP_ANSIBLE_HOST}"
aap_deploy_eda_pg_host: "${AAP_ANSIBLE_HOST}"
aap_deploy_automationmetrics_pg_host: "${AAP_ANSIBLE_HOST}"
aap_deploy_automationmetrics_controller_read_pg_host: "${AAP_ANSIBLE_HOST}"

aap_runbook_manage_rhsm: false
aap_runbook_manage_repos: false
aap_runbook_os_prep_enabled: false
aap_runbook_manage_podman: true
aap_runbook_allow_ansible_user_sudo_to_install_user: true

ansible_remote_tmp: /appl/ansible-tmp
ansible_remote_tmp_bootstrap_raw: ${AAP_REMOTE_TMP_BOOTSTRAP_RAW:-true}
aap_deploy_manage_install_tmp_dir: true
aap_deploy_install_tmp_dir: /appl/tmp
aap_deploy_install_environment:
  TMPDIR: /appl/tmp
  TEMP: /appl/tmp
  TMP: /appl/tmp

aap_cac_gateway_hostname: "https://${AAP_FQDN}"

aap_ops_health_url: "https://${AAP_FQDN}/"
aap_ops_validate_certs: true
aap_ops_manage_systemd: false

aap_prepare_bundle_required: true
aap_prepare_no_log: false
aap_prepare_bundle_source: remote
aap_prepare_bundle_remote_src: "{{ lookup('ansible.builtin.env', 'AAP_BUNDLE_REMOTE_SRC') }}"
aap_prepare_bundle_dest: "{{ aap_deploy_install_dir }}/aap-containerized-setup.tar.gz"
aap_prepare_manifest_required: true
aap_prepare_manifest_source: remote
aap_prepare_manifest_remote_src: "{{ lookup('ansible.builtin.env', 'AAP_MANIFEST_REMOTE_SRC') }}"
aap_prepare_manifest_dest: "{{ aap_deploy_install_dir }}/manifest.zip"
aap_prepare_artifact_dir: "{{ lookup('ansible.builtin.env', 'AAP_ARTIFACT_DIR') }}"

aap_deploy_tls_enabled: true
aap_deploy_tls_source: customer_files
aap_tls_selfsigned_output_dir: /runner/project/files/tls
aap_tls_selfsigned_common_name: "${AAP_FQDN}"
aap_tls_selfsigned_dns_names:
  - "${AAP_FQDN}"
  - "${AAP_INVENTORY_HOST}"
aap_deploy_tls_customer_files:
  ca_cert_src: "{{ aap_tls_selfsigned_output_dir }}/aap-selfsigned-ca.crt"
  gateway:
    cert_src: "{{ aap_tls_selfsigned_output_dir }}/aap.crt"
    key_src: "{{ aap_tls_selfsigned_output_dir }}/aap.key"
  controller:
    cert_src: "{{ aap_tls_selfsigned_output_dir }}/aap.crt"
    key_src: "{{ aap_tls_selfsigned_output_dir }}/aap.key"
  hub:
    cert_src: "{{ aap_tls_selfsigned_output_dir }}/aap.crt"
    key_src: "{{ aap_tls_selfsigned_output_dir }}/aap.key"
  eda:
    cert_src: "{{ aap_tls_selfsigned_output_dir }}/aap.crt"
    key_src: "{{ aap_tls_selfsigned_output_dir }}/aap.key"

aap_cac_controller_license_required: true

aap_orgs:
  - name: org-modulix
aap_org_primary: "{{ (aap_orgs | first).name }}"
aap_cac_controller_organizations:
  - name: org-modulix

controller_settings:
  - name: TOWER_URL_BASE
    value: "https://${AAP_FQDN}"
YAML

  cat >"${AUTOMATION_ANSIBLE_DIR}/inventories/${INVENTORY_NAME}/group_vars/aaps/podman.yml" <<YAML
---
rhel_podman_package_manage: false
rhel_podman_rootless_storage_manage: true
rhel_podman_rootless_storage_user: ${AAP_INSTALL_USER}
rhel_podman_rootless_storage_base_path: /appl/podman
rhel_podman_rootless_storage_path: /appl/podman/storage
rhel_podman_rootless_storage_conf_path: /appl/home/${AAP_INSTALL_USER}/.config/containers/storage.conf
YAML

  if [[ "${AAP_SECRET_BACKEND}" == "ansible_vault" ]]; then
    rm -f \
      "${AUTOMATION_ANSIBLE_DIR}/inventories/${INVENTORY_NAME}/group_vars/aaps/aap_hc_vault.yml"
    if [[ ! -s "${AUTOMATION_ANSIBLE_DIR}/inventories/${INVENTORY_NAME}/group_vars/aaps/aap_ansible_vault.yml" ]]; then
      printf 'Ansible Vault group vars are missing: %s\n' \
        "${AUTOMATION_ANSIBLE_DIR}/inventories/${INVENTORY_NAME}/group_vars/aaps/aap_ansible_vault.yml" >&2
      return 1
    fi
    return 0
  fi
  rm -f \
    "${AUTOMATION_ANSIBLE_DIR}/inventories/${INVENTORY_NAME}/group_vars/aaps/aap_ansible_vault.yml"

  cat >"${AUTOMATION_ANSIBLE_DIR}/inventories/${INVENTORY_NAME}/group_vars/aaps/aap_hc_vault.yml" <<YAML
---
vault_address: "{{ lookup('ansible.builtin.env', 'VAULT_ADDR') | default('${VAULT_ADDR}', true) }}"
vault_engine_mount_point: "{{ lookup('ansible.builtin.env', 'VAULT_ENGINE_MOUNT_POINT') | default('${VAULT_ENGINE_MOUNT_POINT}', true) }}"
vault_validate_certs: "{{ lookup('ansible.builtin.env', 'VAULT_VALIDATE_CERTS') | default('true', true) | bool }}"

aap_vault_host_key: "{{ lookup('ansible.builtin.env', 'AAP_VAULT_HOST_KEY') | default('${AAP_VAULT_HOST_KEY}', true) }}"
hc_vault_aap_admin_passwords_kv_path: "{{ lookup('ansible.builtin.env', 'AAP_VAULT_ADMIN_PASSWORDS_KV_PATH') | default(aap_vault_host_key ~ '/aap/deploy/admin_passwords', true) }}"
hc_vault_defaults_kv_path: "{{ lookup('ansible.builtin.env', 'AAP_VAULT_DEFAULTS_KV_PATH') | default('${AAP_VAULT_DEFAULTS_KV_PATH}', true) }}"

hc_vault_addr: "{{ vault_address | trim }}"
hc_vault_engine_mount_point: "{{ vault_engine_mount_point | trim }}"
hc_vault_validate_certs: "{{ vault_validate_certs | bool }}"
hc_vault_token: >-
  {{
    vault_token
    | default(lookup('ansible.builtin.env', 'VAULT_TOKEN') | string | trim, true)
    | string
    | trim
  }}
hc_vault_role_id: "{{ ansible_hashi_vault_role_id | default(vault_aap_role_id | default('', true), true) | string | trim }}"
hc_vault_secret_id: "{{ ansible_hashi_vault_secret_id | default(vault_aap_secret_id | default('', true), true) | string | trim }}"
hc_vault_use_token: "{{ hc_vault_token | length > 0 }}"
hc_vault_auth_method: "{{ 'token' if (hc_vault_use_token | bool) else 'approle' }}"
hc_vault_auth_ok: "{{ (hc_vault_token | length > 0) or ((hc_vault_role_id | length > 0) and (hc_vault_secret_id | length > 0)) }}"

hc_vault_aap_admin_passwords_secret: >-
  {{
    lookup(
      'community.hashi_vault.vault_kv2_get',
      hc_vault_aap_admin_passwords_kv_path,
      engine_mount_point=hc_vault_engine_mount_point,
      url=hc_vault_addr,
      auth_method=hc_vault_auth_method,
      token=hc_vault_token,
      role_id=hc_vault_role_id,
      secret_id=hc_vault_secret_id,
      validate_certs=hc_vault_validate_certs
    )['secret']
    if (hc_vault_auth_ok | bool)
    else {}
  }}
hc_vault_defaults_secret: >-
  {{
    lookup(
      'community.hashi_vault.vault_kv2_get',
      hc_vault_defaults_kv_path,
      engine_mount_point=hc_vault_engine_mount_point,
      url=hc_vault_addr,
      auth_method=hc_vault_auth_method,
      token=hc_vault_token,
      role_id=hc_vault_role_id,
      secret_id=hc_vault_secret_id,
      validate_certs=hc_vault_validate_certs
    )['secret']
    if (hc_vault_auth_ok | bool)
    else {}
  }}

aap_password_seed_enabled: "{{ hc_vault_token | length > 0 }}"
aap_password_seed_get_or_create: true
aap_password_seed_vault_addr: "{{ hc_vault_addr }}"
aap_password_seed_vault_token: "{{ hc_vault_token }}"
aap_password_seed_vault_kv_mount: "{{ hc_vault_engine_mount_point }}"
aap_password_seed_vault_kv_path: "{{ hc_vault_aap_admin_passwords_kv_path }}"
aap_password_seed_vault_validate_certs: "{{ hc_vault_validate_certs | bool }}"
aap_password_seed_rh_offline_token_key: rh_offline_token
aap_password_seed_generated_length: 32
aap_password_seed_generated_chars: "ascii_letters,digits"

aap_defaults_seed_vault_addr: "{{ hc_vault_addr }}"
aap_defaults_seed_vault_token: "{{ hc_vault_token }}"
aap_defaults_seed_vault_kv_mount: "{{ hc_vault_engine_mount_point }}"
aap_defaults_seed_vault_kv_path: "{{ hc_vault_defaults_kv_path }}"
aap_defaults_seed_vault_validate_certs: "{{ hc_vault_validate_certs | bool }}"

aap_username: "{{ lookup('ansible.builtin.env', 'AAP_GATEWAY_USERNAME') | default('admin', true) | trim }}"
aap_validate_certs: true

aap_gateway_admin_password_input: "{{ hc_vault_aap_admin_passwords_secret.get('gateway_admin_password', '') | string | trim }}"
aap_controller_admin_password_input: "{{ hc_vault_aap_admin_passwords_secret.get('controller_admin_password', '') | string | trim }}"
aap_hub_admin_password_input: "{{ hc_vault_aap_admin_passwords_secret.get('hub_admin_password', '') | string | trim }}"
aap_eda_admin_password_input: "{{ hc_vault_aap_admin_passwords_secret.get('eda_admin_password', '') | string | trim }}"
aap_postgresql_admin_password_input: "{{ hc_vault_aap_admin_passwords_secret.get('postgresql_admin_password', '') | string | trim }}"
aap_breakglass_password_input: "{{ hc_vault_aap_admin_passwords_secret.get('breakglass_password', '') | string | trim }}"

aap_password: "{{ aap_gateway_admin_password_input }}"
rh_offline_token: >-
  {{
    hc_vault_defaults_secret.get(
      'rh_offline_token',
      hc_vault_defaults_secret.get(
        'offline_token',
        hc_vault_defaults_secret.get(
          'token',
          hc_vault_defaults_secret.get('RH_AUTOMATION_HUB_TOKEN', '')
        )
      )
    )
    | string
    | trim
  }}
YAML
}
