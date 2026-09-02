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
scripts/lit-ci-profile.sh repository-quality
```

This command is a managed dispatcher into the digest-pinned Devtools image;
it does not use host language runtimes as acceptance evidence. If the image
lacks a required tool, update and normally release the Devtools image and then
repin its managed digest instead of creating a host virtual environment.
Where present, `.github/requirements/repository-quality.lock` is consumed by
this profile and must match the PyYAML version in the pinned Devtools image.

Heavy Incus tests require an Ubuntu host or runner with Incus available, suitable images, and repository-specific scenario configuration. They must use sanitized inputs and must not rely on private inventory values.

## Interpreting GitHub Actions

The GitHub Actions matrix is the primary dashboard. Job names should expose the repository class, OS/runtime where applicable, and profile, for example `repository / quality`.

Release evidence is generated during trusted release workflows and attached to or linked from GitHub Releases where the repository publishes release artifacts.
