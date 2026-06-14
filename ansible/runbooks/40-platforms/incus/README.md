# Incus Runbooks

Incus runbooks configure Incus hosts and manage local Incus platform artifacts.

## Runbooks

- `10-host-setup.yml`: install and initialize Incus on Ubuntu hosts.
- `20-image-artifacts.yml`: stage image artifacts from URL/local sources and
  import them into the local Incus image store.

`20-image-artifacts.yml` is inventory-driven. Define `artifacts_items` for
downloads/copies and `incus_image_items` for image aliases in the inventory that
owns the environment.
