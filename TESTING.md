# Testing

This repository uses the Lightning IT shared test model.

## Test Profiles

- `pre-commit`
- `lint`
- `playbook-syntax`
- `inventory-template-validation`
- `smoke`
- `integration-incus`
- `release-validation`

## Supported Matrix

Operating systems and runners:

- `ubuntu-latest`
- `rhel-9`
- `rhel-10`

Products and runtimes:

- `ansible-core`
- `aap-2.6`
- `aap-2.7`
- `incus`

## When Tests Run

- Normal pull requests run the declared test profiles relevant to changed files.
- Renovate and verified shared-assets or repository-quality synchronization pull requests target `develop` and may auto-merge only after required checks pass.
- `develop` to `main` promotion pull requests run the strongest validation profile for this repository.
- Trusted `main` release workflows build and publish artifacts only after validation succeeds.

## Local Commands

Run the managed repository-policy checks:

```bash
python3 scripts/lit-repository-quality.py
```

Run the declared pre-commit profile:

```bash
pre-commit run --all-files
```

Run the repository-specific commands declared in
`.lit/push-ready.json` and the required CI workflow named in
`.lit/repository.yml`. Do not substitute unrelated toolchains.

Heavy Incus tests require an Ubuntu host or runner with Incus available, suitable images, and repository-specific scenario configuration. They must use sanitized inputs and must not rely on private inventory values.

## Interpreting GitHub Actions

The GitHub Actions matrix is the primary dashboard. Job names should expose the repository class, OS/runtime where applicable, and profile, for example `repository / quality`.

Release evidence is generated during trusted release workflows and attached to or linked from GitHub Releases where the repository publishes release artifacts.
