# Contributing

Thank you for helping improve this Lightning IT repository.

## Branch Flow

- Open normal changes against `develop` when the repository has a `develop` branch.
- Open emergency or documentation-only changes against the repository default branch only when maintainers ask for it.
- Release promotion from `develop` to `main` is a maintainer-controlled gate.

## Pull Requests

- Keep changes focused and explain the operational impact.
- Include verification steps in the pull request description.
- Do not commit secrets, private inventory values, customer data, tokens, credentials, or credential-bearing examples.
- Use sanitized examples and placeholders for configuration snippets.
- Update `RELEASE.md`, `TESTING.md`, or `OPENSSF.md` only through the shared-assets sync flow unless maintainers request a repository-specific exception.

## Security

Report vulnerabilities using `SECURITY.md`. Do not open public issues or pull requests for undisclosed vulnerabilities.

## Automation

Renovate and shared-assets synchronization pull requests target `develop` where available and may merge only after required checks pass.
