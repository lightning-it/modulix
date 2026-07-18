# OpenSSF Readiness

This repository follows the Lightning IT shared OpenSSF readiness model generated from `lightning-it/shared-assets-lit`.

## Repository

- Repository: `modulix-automation`
- Visibility: `public`
- Type: `playbook_runbook`
- Release type: `semantic_release`
- Artifact type: `rpm`

## Scorecard

Enabled through `.github/workflows/openssf-scorecard.yml` with scheduled, manual, and `branch_protection_rule` triggers. The workflow executes a digest-pinned Scorecard container and uploads SARIF to GitHub code scanning. Repository-run results are not published to the OpenSSF API because its workflow verifier does not currently accept the immutable container invocation.

The Scorecard badge is included in `README.md` only for public repositories where the workflow is synced. It can reflect OpenSSF's independent scan rather than a repository-published result.

## Best Practices Badge

Required but not enrolled. Enroll manually at OpenSSF Best Practices, complete the questionnaire until the project reaches the configured target level, then record the numeric project ID as `openssf_best_practices.project_id` in the central `release-model/repositories.yml` inventory in `lightning-it/shared-assets-lit`.

Do not add a passing OpenSSF Best Practices badge until the repository is actually enrolled and passing. Badges must be generated from the central `release-model/repositories.yml` inventory in `lightning-it/shared-assets-lit`; hand-written badges are rejected by the release-model audit.

## Security Policy

`SECURITY.md` describes supported versions, vulnerability reporting, coordinated disclosure, supported artifact scope, and the distinction between public repository content and private customer or infrastructure data.

## Branch Protection And Release Integrity

- `main` is the protected release branch.
- `develop` is the integration branch for normal work, Renovate, and shared-assets-lit PRs.
- Every pull request must have a completed GitHub Copilot review for its current head revision.
- Promotion and integration PRs may auto-merge only after required checks pass and all review conversations are resolved.
- Releases and publishing happen only from trusted `main` workflows after validation.
- Release evidence is generated for repositories with release artifacts.

## Dependency Automation

Dependency automation must target `develop` and must not bypass required checks. Coverage should include GitHub Actions, language dependencies, Ansible content, container base images, pre-commit hooks, and documentation tooling where applicable.

## Security Scanning

linting, syntax validation, release dry-run checks, and secret-safe workflow review.

## Exceptions

Repository-specific exceptions must be documented in this file or in `.lit/repository.yml`. Exceptions must not expose secrets, private infrastructure details, customer data, or credential-bearing examples.
