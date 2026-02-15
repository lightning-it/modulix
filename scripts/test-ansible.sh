#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [ -z "${IN_WUNDER_DEVTOOLS_EE:-}" ] && [ ! -f "/.dockerenv" ]; then
  WRAPPER="$ROOT/scripts/wunder-devtools-ee.sh"
  if [ ! -x "$WRAPPER" ]; then
    echo "Missing wrapper: $WRAPPER" >&2
    exit 1
  fi
  exec "$WRAPPER" env IN_WUNDER_DEVTOOLS_EE=1 "$0" "$@"
fi

echo "Linting YAML under ansible/..."
yamllint ansible

inventory_files=(
  ansible/inventories/nightly/hosts.yml
  ansible/inventories/demo/hosts.yml
)

for inv in "${inventory_files[@]}"; do
  if [ -f "$inv" ]; then
    echo "Validating inventory: $inv"
    ansible-inventory --inventory "$inv" --list >/dev/null
  fi
done
