# ModuLix Automation

<!-- BEGIN LIT_SHARED_RELEASE_MODEL -->

[![CI](https://github.com/lightning-it/modulix-automation/actions/workflows/rpm-srpm-ci.yml/badge.svg?branch=develop)](https://github.com/lightning-it/modulix-automation/actions/workflows/rpm-srpm-ci.yml)
[![Release](https://github.com/lightning-it/modulix-automation/actions/workflows/semantic-release.yml/badge.svg?branch=main)](https://github.com/lightning-it/modulix-automation/actions/workflows/semantic-release.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)

## Release and Quality Model

This repository follows the Lightning IT shared release and quality model.

See [RELEASE.md](./RELEASE.md) for:

- branch and release flow
- required quality checks
- test matrix
- release evidence
- artifact publishing
- supported repository-specific release behavior

Repository classification: **Playbook/Runbook Repository**.
Required test profiles: `pre-commit, lint, playbook-syntax, inventory-template-validation, smoke, integration-incus, release-validation`.
Publishing targets: `github-release, rpm-srpm`.

<!-- END LIT_SHARED_RELEASE_MODEL -->

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
