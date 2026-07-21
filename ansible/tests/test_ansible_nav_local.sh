#!/usr/bin/env bash
set -euo pipefail

ansible_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
script="${ansible_root}/scripts/ansible-nav-local"
test_root="$(mktemp -d)"
trap 'rm -rf -- "${test_root}"' EXIT

fake_bin="${test_root}/bin"
home="${test_root}/home"
mkdir -p "${fake_bin}" "${home}/.ssh"

cat > "${fake_bin}/ansible-navigator" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
{
  printf 'COLLECTIONS=%s\n' "${ANSIBLE_COLLECTIONS_PATH:-}"
  printf 'ROLES=%s\n' "${ANSIBLE_ROLES_PATH:-}"
  printf 'VAULT_PASSWORD_FILE=%s\n' "${ANSIBLE_VAULT_PASSWORD_FILE:-}"
  printf 'ARG=%s\n' "$@"
  for argument in "$@"; do
    if [[ "${argument}" == *:/runner/.ssh:ro ]]; then
      staged_dir="${argument%:/runner/.ssh:ro}"
      printf 'SSH_STAGE_FILES=%s\n' "$(find "${staged_dir}" -maxdepth 1 -type f -printf '%f\n' | sort | paste -sd, -)"
      printf 'SSH_STAGE_MODES=%s\n' "$(
        stat -c '%a' \
          "${staged_dir}/config" \
          "${staged_dir}/id_selected" \
          "${staged_dir}/known_hosts" \
          | paste -sd, -
      )"
      printf 'SSH_CONFIG=%s\n' "$(tr '\n' ';' < "${staged_dir}/config")"
    fi
    if [[ "${argument}" == *:/runner/.ansible-secrets:ro ]]; then
      staged_dir="${argument%:/runner/.ansible-secrets:ro}"
      printf 'VAULT_STAGE_FILES=%s\n' "$(find "${staged_dir}" -maxdepth 1 -type f -printf '%f\n' | sort | paste -sd, -)"
      printf 'VAULT_STAGE_MODE=%s\n' "$(stat -c '%a' "${staged_dir}/ansible-vault-pass.txt")"
    fi
  done
} > "${FAKE_NAV_OUTPUT}"
EOF
chmod 0755 "${fake_bin}/ansible-navigator"

common_env=(
  "PATH=${fake_bin}:${PATH}"
  "HOME=${home}"
  "ANSIBLE_HOME=${test_root}/ansible-home"
  "ANSIBLE_TOOLBOX_AUTO_COLLECTIONS=false"
)

ee_only_output="${test_root}/ee-only.out"
env \
  "${common_env[@]}" \
  "FAKE_NAV_OUTPUT=${ee_only_output}" \
  "ANSIBLE_COLLECTIONS_PATH=/tmp/untrusted-overlay" \
  "ANSIBLE_TOOLBOX_AUTO_COLLECTIONS=true" \
  "ANSIBLE_TOOLBOX_EE_ONLY_COLLECTIONS=true" \
  "${script}" run example.yml

grep -Fxq \
  'COLLECTIONS=/usr/share/ansible/collections:/usr/share/automation-controller/collections' \
  "${ee_only_output}"
if grep -Fq '/tmp/untrusted-overlay' "${ee_only_output}"; then
  echo "EE-only mode retained an inherited collection overlay." >&2
  exit 1
fi
grep -Fq '/runner/project/ansible/roles' "${ee_only_output}"

project_overlay_output="${test_root}/project-overlay.out"
env \
  "${common_env[@]}" \
  "FAKE_NAV_OUTPUT=${project_overlay_output}" \
  "ANSIBLE_TOOLBOX_EE_ONLY_COLLECTIONS=false" \
  "${script}" run example.yml

grep -Fq '/runner/project/ansible/collections' "${project_overlay_output}"

key="${home}/selected-key"
known_hosts="${home}/selected-known-hosts"
printf '%s\n' 'fixture-private-key' > "${key}"
printf '%s\n' 'fixture.example ssh-ed25519 AAAAfixture' > "${known_hosts}"
chmod 0600 "${key}"
chmod 0644 "${known_hosts}"

ssh_output="${test_root}/ssh.out"
env \
  "${common_env[@]}" \
  "FAKE_NAV_OUTPUT=${ssh_output}" \
  "ANSIBLE_TOOLBOX_NAV_EE_ENABLED=true" \
  "ANSIBLE_TOOLBOX_NAV_CONTAINER_ENGINE=podman" \
  "ANSIBLE_SSH_ARGS=-o ControlPersist=120" \
  "ANSIBLE_TOOLBOX_SSH_PRIVATE_KEY_FILE=${key}" \
  "ANSIBLE_TOOLBOX_SSH_KNOWN_HOSTS_FILE=${known_hosts}" \
  "${script}" run example.yml

grep -Fxq 'ARG=ANSIBLE_PRIVATE_KEY_FILE=/runner/.ssh/id_selected' "${ssh_output}"
grep -Fxq 'ARG=ANSIBLE_HOST_KEY_CHECKING=True' "${ssh_output}"
grep -Fxq 'ARG=ANSIBLE_SSH_COMMON_ARGS=-F /runner/.ssh/config' "${ssh_output}"
grep -Fxq 'ARG=ANSIBLE_SSH_ARGS=-o ControlPersist=120' "${ssh_output}"
grep -Fxq 'SSH_STAGE_FILES=config,id_selected,known_hosts' "${ssh_output}"
grep -Fxq 'SSH_STAGE_MODES=400,400,400' "${ssh_output}"
grep -Fq 'UserKnownHostsFile /runner/.ssh/known_hosts' "${ssh_output}"
grep -Fq 'GlobalKnownHostsFile /dev/null' "${ssh_output}"
grep -Fq 'StrictHostKeyChecking yes' "${ssh_output}"
grep -Fq 'IdentityFile /runner/.ssh/id_selected' "${ssh_output}"
grep -Fq 'IdentitiesOnly yes' "${ssh_output}"
if grep -Fq "${home}/.ssh" "${ssh_output}"; then
  echo "The complete SSH directory was mounted into the execution environment." >&2
  exit 1
fi

vault_password_file="${home}/vault-pass.txt"
printf '%s\n' 'fixture-vault-password' > "${vault_password_file}"
chmod 0600 "${vault_password_file}"

vault_output="${test_root}/vault.out"
env \
  "${common_env[@]}" \
  "FAKE_NAV_OUTPUT=${vault_output}" \
  "ANSIBLE_TOOLBOX_NAV_EE_ENABLED=true" \
  "ANSIBLE_TOOLBOX_NAV_CONTAINER_ENGINE=podman" \
  "ANSIBLE_VAULT_PASSWORD_FILE=${vault_password_file}" \
  "${script}" run example.yml

grep -Fxq \
  'VAULT_PASSWORD_FILE=/runner/.ansible-secrets/ansible-vault-pass.txt' \
  "${vault_output}"
grep -Fxq 'VAULT_STAGE_FILES=ansible-vault-pass.txt' "${vault_output}"
grep -Fxq 'VAULT_STAGE_MODE=400' "${vault_output}"

if env \
  "${common_env[@]}" \
  "FAKE_NAV_OUTPUT=${test_root}/missing-known-hosts.out" \
  "ANSIBLE_TOOLBOX_NAV_EE_ENABLED=true" \
  "ANSIBLE_TOOLBOX_SSH_PRIVATE_KEY_FILE=${key}" \
  "${script}" run example.yml >/dev/null 2>&1; then
  echo "Explicit SSH key use succeeded without a trusted known_hosts file." >&2
  exit 1
fi

echo "ansible-nav-local security contract tests passed"
