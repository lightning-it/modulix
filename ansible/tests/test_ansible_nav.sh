#!/usr/bin/env bash
set -euo pipefail

ansible_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
script="${ansible_root}/scripts/ansible-nav"
test_root="$(mktemp -d)"
trap 'rm -rf -- "${test_root}"' EXIT

invalid_runtime_stderr="${test_root}/invalid-runtime.stderr"
if env ANSIBLE_TOOLBOX_RUNTIME_MODE=invalid \
  "${script}" exec -- /bin/true 2>"${invalid_runtime_stderr}"; then
  echo "ansible-nav accepted an invalid runtime mode." >&2
  exit 1
fi
grep -Fq "Invalid ANSIBLE_TOOLBOX_RUNTIME_MODE='invalid'" \
  "${invalid_runtime_stderr}"

invalid_engine_stderr="${test_root}/invalid-engine.stderr"
if env ANSIBLE_TOOLBOX_ENGINE=invalid \
  "${script}" exec -- /bin/true 2>"${invalid_engine_stderr}"; then
  echo "ansible-nav accepted an invalid container engine." >&2
  exit 1
fi
grep -Fq "Invalid ANSIBLE_TOOLBOX_ENGINE='invalid'" "${invalid_engine_stderr}"

if [[ -f /.dockerenv || -f /run/.containerenv ]]; then
  delegated_output="${test_root}/delegated.out"
  env \
    PATH=/opt/app-root/bin:/usr/bin:/bin \
    ANSIBLE_TOOLBOX_ENGINE=auto \
    ANSIBLE_TOOLBOX_RUNTIME_MODE=disconnected \
    "${script}" exec -- /bin/printf '%s\n' delegated \
    >"${delegated_output}"
  grep -Fxq delegated "${delegated_output}"
fi

echo "ansible-nav security contract tests passed"
