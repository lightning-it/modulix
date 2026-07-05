# ModuLix Automation

<!-- BEGIN LIT_QUALITY_BADGES -->

[![CI](https://github.com/lightning-it/modulix-automation/actions/workflows/rpm-srpm-ci.yml/badge.svg?branch=develop)](https://github.com/lightning-it/modulix-automation/actions/workflows/rpm-srpm-ci.yml)
[![Latest Release](https://img.shields.io/github/v/release/lightning-it/modulix-automation?sort=semver)](https://github.com/lightning-it/modulix-automation/releases/latest)
[![OpenSSF Scorecard](https://api.scorecard.dev/projects/github.com/lightning-it/modulix-automation/badge)](https://scorecard.dev/viewer/?uri=github.com/lightning-it/modulix-automation)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)

<!-- END LIT_QUALITY_BADGES -->

ModuLix automation is the delivery source-of-truth for platform automation baselines.
It is delivered as the `modulix-automation-runtime` RPM.

## Delivery model

- Delivery artifact: `modulix-automation-runtime` RPM
- Default runtime: toolbox wrapper + EE (`scripts/ansible-nav`)
- Runtime payload: Ansible and collection set provided by the configured EE image
- RH extension collections (AAP/CaC) can be installed at runtime from
  `ansible/collections/requirements-rh.yml` (Automation Hub token required)
- Optional runtime: host-native execution (supported with prerequisites)

Release-coupled packaging documentation in this repo:

- Packaging/build: `packaging/rpm/README.md`

## Example Usage

```bash
cd ansible
./scripts/ansible-nav run runbooks/50-applications/wunderbox/10-deploy.yml \
  -i /path/to/private/inventory.yml --limit wunderbox01.prd.dmz.example.invalid
```

This is a generic example only. This public repository provides reusable
capability runbooks, not copy-paste rollout procedures. Customer-specific or
Lightning IT copy-paste operations live in private `modulix-operations-*`
repositories. Sanitized inventory examples live in the public
`ansible-inventory-example` repository.

## Development

When developing local Ansible collections from sibling repos (for example
`ansible-collection-supplementary`, `ansible-collection-foundational`), install
them into the workspace collection path before running runbooks:

```bash
cd ansible
./scripts/install-local-collections
```

What this does:

- Builds local `ansible-collection-*` sources into tarballs.
- Installs them into `ansible/collections`.
- Keeps one active workspace collection tree, so stale generated copies do not
  shadow current source work.

## Operator Documentation

Copy-paste operator guides, environment-specific workflows, and
troubleshooting procedures live in private operations repositories such as:

- `modulix-operations-lit`
- `modulix-operations-<customer>`

This public repository keeps reusable automation docs and examples only.

## Security statement

- No secrets in repository.
- Provide secrets via runtime inputs (for example `ANSIBLE_VAULT_PASSWORD_FILE`, `VAULT_TOKEN`, ssh-agent).

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md) for contribution and review expectations.

## License

See [LICENSE](./LICENSE).

## Security

See [SECURITY.md](./SECURITY.md) for supported versions and vulnerability reporting.

<!-- BEGIN LIT_RELEASE_QUALITY_MODEL -->

## Release and Quality Model

This repository follows the Lightning IT shared release and quality model.
The README shows the current supported and tested matrix.
Exact per-version validation proof is stored with each GitHub Release as `release-evidence.md` and `release-evidence.json`.
Releases are created from the protected `main` branch after a reviewed `develop -> main` release promotion.
Runbook releases validate linting, syntax, sanitized examples, and integration scenarios where configured.

See:

- [RELEASE.md](./RELEASE.md)
- [TESTING.md](./TESTING.md)
- [GitHub Releases](../../releases)

Repository classification: **Playbook/Runbook Repository**.
Required test profiles: `pre-commit, lint, playbook-syntax, inventory-template-validation, smoke, integration-incus, release-validation`.
Publishing targets: `github-release, rpm-srpm`.

<!-- END LIT_RELEASE_QUALITY_MODEL -->

<!-- BEGIN LIT_COMPATIBILITY_MATRIX -->

## Compatibility Matrix

| Platform / Product | Status | Validation |
|---|---:|---|
| ubuntu-latest | Supported | Molecule / Incus |
| rhel-9 | Supported | Molecule / Incus |
| rhel-10 | Supported | Molecule / Incus |
| ansible-core | Tested where applicable | Molecule / Incus |
| aap-2.6 | Tested where applicable | Molecule / Incus |
| aap-2.7 | Tested where applicable | Molecule / Incus |
| incus | Tested where applicable | Molecule / Incus |

Validation proof for each released version is stored in the corresponding GitHub Release evidence.

<!-- END LIT_COMPATIBILITY_MATRIX -->

## Release Evidence

Every released version includes immutable release evidence attached to the corresponding GitHub Release.
The evidence records:

- tested matrix combinations
- GitHub Actions run links
- artifact references
- publish status
- security scan status

See [GitHub Releases](../../releases), [RELEASE.md](./RELEASE.md), and [TESTING.md](./TESTING.md) for the release process and validation model.
