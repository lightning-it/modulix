#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Clone all repositories from a GitHub owner (user or org) using GitHub CLI.

Usage:
  ./scripts/github/clone-all.sh <owner> [options]

Options:
  --https                 Clone via HTTPS (default)
  --ssh                   Clone via SSH
  --target-dir <path>     Directory to clone into (default: .)
  --limit <n>             Max repos to list (default: 1000)
  --include-archived      Include archived repos (default: excluded)
  --visibility <v>        public|private|internal (default: all)
  --source-only           Only non-forks
  --forks-only            Only forks
  --depth <n>             Shallow clone with depth n
  --dry-run               Print actions without cloning
  -h, --help              Show this help

Examples:
  ./scripts/github/clone-all.sh lightning-it --ssh --target-dir ./src
  ./scripts/github/clone-all.sh myuser --https --visibility public
USAGE
}

# Defaults
protocol="https"
target_dir="."
limit="1000"
include_archived="false"
visibility=""
fork_filter=""
depth=""
dry_run="false"

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" || $# -lt 1 ]]; then
  usage; exit 0
fi

owner="$1"
shift

while [[ $# -gt 0 ]]; do
  case "$1" in
    --https) protocol="https"; shift ;;
    --ssh) protocol="ssh"; shift ;;
    --target-dir) target_dir="${2:?missing value}"; shift 2 ;;
    --limit) limit="${2:?missing value}"; shift 2 ;;
    --include-archived) include_archived="true"; shift ;;
    --visibility) visibility="${2:?missing value}"; shift 2 ;;
    --source-only) fork_filter="--source"; shift ;;
    --forks-only) fork_filter="--fork"; shift ;;
    --depth) depth="${2:?missing value}"; shift 2 ;;
    --dry-run) dry_run="true"; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage; exit 2 ;;
  esac
done

command -v gh >/dev/null || { echo "ERROR: 'gh' (GitHub CLI) is required."; exit 1; }
command -v git >/dev/null || { echo "ERROR: 'git' is required."; exit 1; }

if ! gh auth status >/dev/null 2>&1; then
  echo "ERROR: gh is not authenticated. Run: gh auth login" >&2
  exit 1
fi

mkdir -p "$target_dir"
cd "$target_dir"

json_field="url"
[[ "$protocol" == "ssh" ]] && json_field="sshUrl"

archived_flag="--no-archived"
[[ "$include_archived" == "true" ]] && archived_flag=""

visibility_flag=()
[[ -n "$visibility" ]] && visibility_flag=(--visibility "$visibility")

depth_args=()
[[ -n "$depth" ]] && depth_args=(--depth "$depth")

mapfile -t urls < <(
  gh repo list "$owner" -L "$limit" \
    $archived_flag $fork_filter \
    "${visibility_flag[@]}" \
    --json "$json_field,nameWithOwner" \
    --jq ".[].${json_field}"
)

if [[ ${#urls[@]} -eq 0 ]]; then
  echo "No repositories found (or no access)."
  exit 0
fi

for url in "${urls[@]}"; do
  name="$(basename "$url" .git)"
  if [[ -d "$name/.git" ]]; then
    echo "SKIP  $name (already cloned)"
    continue
  fi

  if [[ "$dry_run" == "true" ]]; then
    echo "DRY   git clone ${depth_args[*]} $url"
  else
    echo "CLONE $url"
    git clone "${depth_args[@]}" "$url"
  fi
done
