# aap_self_hosted_bootstrap_bootstrap

Bootstraps a target-specific self-hosted AAP workspace from a workstation over
an already trusted SSH path. All environment values and protected file paths
are inventory inputs. The role creates the workspace, checks out an immutable
Git version, creates a dedicated loopback SSH key, trusts only the host's local
Ed25519 public key, and stages encrypted/operator-supplied inputs.

The role does not create operating-system users, disable SSH host-key checking,
generate application secrets, or infer artifact versions and checksums.
