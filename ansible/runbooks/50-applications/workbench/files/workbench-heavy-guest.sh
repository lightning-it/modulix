#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 5 ]; then
  echo "Usage: $0 INVENTORY PLAYBOOK FIRST_LOG SECOND_LOG LOCAL_TEMP" >&2
  exit 2
fi

inventory="$1"
playbook="$2"
first_log="$3"
second_log="$4"
local_temp="$5"

case "$inventory:$playbook:$local_temp" in
  /tmp/lit-workbench-acceptance/*:/tmp/lit-workbench-acceptance/*:/tmp/lit-workbench-acceptance/*) ;;
  *)
    echo "Refusing guest-test paths outside the acceptance namespace." >&2
    exit 2
    ;;
esac
case "$first_log:$second_log" in
  /home/*/artifacts/workbench-acceptance/*:/home/*/artifacts/workbench-acceptance/*) ;;
  *)
    echo "Refusing guest evidence paths outside the artifact namespace." >&2
    exit 2
    ;;
esac

mkdir -p "$local_temp"
export ANSIBLE_LOCAL_TEMP="$local_temp"
export ANSIBLE_REMOTE_TEMP=/tmp/lit-workbench-ansible
ansible_config_dir="$(dirname "$playbook")"
export ANSIBLE_CONFIG="$ansible_config_dir/ansible.cfg"
export ANSIBLE_HOST_KEY_CHECKING=false
export ANSIBLE_NOCOLOR=1
export ANSIBLE_RETRY_FILES_ENABLED=false
export LC_ALL=C.UTF-8

ready=0
for _attempt in $(seq 1 60); do
  if ansible -i "$inventory" all -m ansible.builtin.ping >/dev/null 2>&1; then
    ready=1
    break
  fi
  sleep 5
done
if [ "$ready" -ne 1 ]; then
  echo "Nested Ansible could not reach the ephemeral guest." >&2
  exit 1
fi

ansible-playbook -i "$inventory" "$playbook" >"$first_log" 2>&1
ansible-playbook -i "$inventory" "$playbook" >"$second_log" 2>&1

if ! grep -Eq 'changed=[1-9][0-9]*[[:space:]]+unreachable=0[[:space:]]+failed=0' "$first_log"; then
  echo "The first guest-role application did not produce a successful change." >&2
  exit 1
fi
if ! grep -Eq 'changed=0[[:space:]]+unreachable=0[[:space:]]+failed=0' "$second_log"; then
  echo "The second guest-role application was not idempotent." >&2
  exit 1
fi
