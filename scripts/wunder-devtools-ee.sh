#!/usr/bin/env bash
set -euo pipefail

IMAGE="${WUNDER_DEVTOOLS_EE_IMAGE:-ghcr.io/lightning-it/wunder-devtools-ee:v1.1.0}"

DOCKER_ARGS=(
  -v "$PWD":/workspace
  -w /workspace
  -e HOME=/home/wunder
  -e IN_WUNDER_DEVTOOLS_EE=1
)

# Mount SSH config for ansible if available
if [ -d "$HOME/.ssh" ]; then
  DOCKER_ARGS+=(-v "$HOME/.ssh":/home/wunder/.ssh:ro)
fi

# Allow docker-in-docker if the socket is present (not required for most tasks)
if [ -S /var/run/docker.sock ]; then
  DOCKER_ARGS+=(-v /var/run/docker.sock:/var/run/docker.sock)
fi

exec docker run --rm --entrypoint "" "${DOCKER_ARGS[@]}" "$IMAGE" "$@"
