# aap_self_hosted_preflight

Validates the prepared RHEL host, rollout workspace, immutable automation tag,
rootless Podman storage, and digest-pinned execution-environment image for self-hosted
AAP deployments. Enable it explicitly with
`aap_self_hosted_preflight_enabled: true`.

Set `aap_preflight_phase: initial` for the first read-only baseline gate. The
default `full` phase additionally validates the installation user's prepared
rootless Podman graph root.
