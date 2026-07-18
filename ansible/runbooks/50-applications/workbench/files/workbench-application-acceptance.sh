#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 8 ]; then
  echo "Usage: $0 REPOSITORY COMMIT SCENARIO WORKDIR ARTIFACTS SCANNER SANITIZER RUN_ID" >&2
  exit 2
fi

repository="$1"
commit="$2"
scenario="$3"
workdir="$4"
artifacts="$5"
scanner="$6"
sanitizer="$7"
run_id="$8"
checkout="$workdir/repository"
raw_log="$artifacts/.application.raw.log"
safe_log="$artifacts/application.log"
scan_report="$artifacts/secret-scan.json"
summary="$artifacts/application-summary.json"

case "$repository" in
  https://github.com/*/*.git) ;;
  *)
    echo "Application repository must be a public HTTPS GitHub clone URL." >&2
    exit 2
    ;;
esac
if ! [[ "$commit" =~ ^[0-9a-f]{40}$ ]]; then
  echo "Application repository commit must be a full SHA-1." >&2
  exit 2
fi
if ! [[ "$scenario" =~ ^[a-z0-9][a-z0-9_-]+$ ]]; then
  echo "Invalid Molecule scenario." >&2
  exit 2
fi
case "$workdir:$artifacts" in
  /tmp/lit-workbench-acceptance/*:/home/*/artifacts/workbench-acceptance/*) ;;
  *)
    echo "Refusing paths outside the acceptance namespaces." >&2
    exit 2
    ;;
esac

umask 077
mkdir -p "$workdir" "$artifacts"

finalize() {
  original_status="$?"
  set +e
  python3 "$scanner" "$raw_log" >"$scan_report"
  scan_status="$?"
  python3 "$sanitizer" \
    "$raw_log" \
    "$safe_log" \
    --replace "$workdir" \
    --replace "$HOME"
  sanitize_status="$?"
  rm -f "$raw_log"
  summary_status=failed
  if [ "$original_status" -eq 0 ] && [ "$scan_status" -eq 0 ] && [ "$sanitize_status" -eq 0 ]; then
    summary_status=passed
  fi
  jq --null-input \
    --arg status "$summary_status" \
    --arg run_id "$run_id" \
    --arg repository "$repository" \
    --arg commit "$commit" \
    --arg scenario "$scenario" \
    '{status: $status, run_id: $run_id, repository: $repository, commit: $commit, molecule_scenario: $scenario}' \
    >"$summary"
  summary_status_code="$?"
  trap - EXIT
  if [ "$original_status" -ne 0 ]; then
    exit "$original_status"
  fi
  if [ "$scan_status" -ne 0 ] || [ "$sanitize_status" -ne 0 ]; then
    exit 92
  fi
  if [ "$summary_status_code" -ne 0 ]; then
    exit 93
  fi
  exit 0
}
trap finalize EXIT

exec >"$raw_log" 2>&1
export GH_TOKEN=
export GITHUB_TOKEN=
export GIT_ASKPASS=/bin/false
export GIT_CONFIG_GLOBAL=/dev/null
export GIT_CONFIG_NOSYSTEM=1
export GIT_TERMINAL_PROMPT=0
export WUNDER_CONTAINER_ENGINE=podman
export WUNDER_DEVTOOLS_STRICT=1
export CI=true

git init "$checkout"
git -C "$checkout" remote add origin "$repository"
git -C "$checkout" -c credential.helper= fetch --depth=1 origin "$commit"
git -C "$checkout" checkout --detach FETCH_HEAD
actual_commit="$(git -C "$checkout" rev-parse HEAD)"
if [ "$actual_commit" != "$commit" ]; then
  echo "Fetched commit does not match the pinned Application contract." >&2
  exit 1
fi

cd "$checkout"
yamllint .
scripts/devtools-ansible-lint.sh
scripts/devtools-collection-smoke.sh
scripts/devtools-molecule.sh "$scenario"
