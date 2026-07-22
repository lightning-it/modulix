#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 7 ]; then
  echo "Usage: $0 BASE_IMAGE IMAGE CONTAINER CONTEXT ARTIFACTS RUN_ID EXPECTED_STDOUT" >&2
  exit 2
fi

base_image="$1"
image="$2"
container="$3"
context="$4"
artifacts="$5"
run_id="$6"
expected_stdout="$7"

case "$base_image" in
  *[!A-Za-z0-9._/@:+-]* | "")
    echo "Invalid base image reference." >&2
    exit 2
    ;;
esac
case "$image:$container:$run_id" in
  *[!A-Za-z0-9._:/+-]*)
    echo "Invalid run-owned container identifier." >&2
    exit 2
    ;;
esac
case "$context:$artifacts" in
  /tmp/lit-workbench-acceptance/*:/home/*/artifacts/workbench-acceptance/*) ;;
  *)
    echo "Refusing paths outside the acceptance namespaces." >&2
    exit 2
    ;;
esac
exec 2>"$artifacts/container-error.raw.log"

umask 077
mkdir -p "$context" "$artifacts"
printf '%s\n' "$expected_stdout" >"$context/payload.txt"
cat >"$context/Containerfile" <<EOF
FROM ${base_image}
COPY payload.txt /usr/local/share/lit-heavy-payload.txt
ENTRYPOINT ["/bin/cat", "/usr/local/share/lit-heavy-payload.txt"]
EOF

podman build \
  --layers=false \
  --pull=always \
  --label io.lit.managed-by=modulix-automation \
  --label "io.lit.run-id=${run_id}" \
  --tag "$image" \
  --file "$context/Containerfile" \
  "$context"

actual_stdout="$(
  podman run --rm \
    --name "$container" \
    --label io.lit.managed-by=modulix-automation \
    --label "io.lit.run-id=${run_id}" \
    "$image"
)"
printf '%s\n' "$actual_stdout" >"$artifacts/container-run.txt"
if [ "$actual_stdout" != "$expected_stdout" ]; then
  echo "Container output did not match the acceptance contract." >&2
  exit 1
fi

buildah inspect --type image "$image" >"$artifacts/buildah-inspect.json"
buildah push "$image" "docker-archive:$context/image.tar"
skopeo inspect "docker-archive:$context/image.tar" >"$artifacts/skopeo-inspect.json"
echo "Scanning exported image with Trivy." >&2
trivy image --input "$context/image.tar" --format json --output "$artifacts/trivy.json"
echo "Generating exported-image SBOM with Syft." >&2
syft "docker-archive:$context/image.tar" --output "json=$artifacts/syft.json"
echo "Scanning exported-image SBOM with Grype." >&2
grype "docker-archive:$context/image.tar" --output json --file "$artifacts/grype.json"

for report in \
  buildah-inspect.json \
  skopeo-inspect.json \
  trivy.json \
  syft.json \
  grype.json; do
  jq --exit-status 'type == "object" or type == "array"' "$artifacts/$report" >/dev/null
done

jq --null-input \
  --arg status passed \
  --arg run_id "$run_id" \
  --arg image "$image" \
  --arg container "$container" \
  '{status: $status, run_id: $run_id, image: $image, container: $container}' \
  >"$artifacts/container-summary.json"
