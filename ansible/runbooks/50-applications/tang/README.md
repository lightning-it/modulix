# Tang Runbooks

`10-deploy.yml` deploys and validates the inventory-enabled Tang service, then
persists its public signing thumbprint through the declared Vault contract.

The current implementation supports Ubuntu 24.04 through
`lit.ubuntu.tang_deploy`. Firewall and DNS policy remain external
prerequisites.
