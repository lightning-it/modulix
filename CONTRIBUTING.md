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

## Local push readiness

Commit the final local change, ensure the worktree is clean, and run
`python3 scripts/lit-push-ready.py push-ready` before pushing. The command:

1. runs the single allowlisted deterministic CI profile declared in
   `.lit/push-ready.json`;
2. fetches the governed `origin/develop` ref and runs those checks on an
   isolated synthetic integration tree for the exact fresh base and `HEAD`;
3. fails if a check changes that integration tree or the developer's branch;
4. creates and secret-scans one exact committed branch snapshot relative to
   the recorded merge-base, without sending it to an external AI service; and
5. writes short-lived, developer-controlled advisory evidence into the Git
   directory.

The distributed runner derives the repository root from its own canonical
engine path and ignores inherited root-override environment variables. A
repository-specific launcher may authorize another layout only through a
validated in-process binding to that exact engine.
The fresh-base integration uses a hook-disabled real merge in a private
worktree and therefore retains pull-request merge semantics on host Git 2.34,
including stock Ubuntu 22.04.

During iteration, `python3 scripts/lit-push-ready.py review` performs the same
deterministic exact-patch and secret-safety scan for committed, staged,
unstaged, and safe UTF-8 untracked content, but it does not produce push
evidence or invoke AI.

Local Push-Ready execution is deliberately AI-free. It never invokes Codex,
GitHub Copilot, another model, or an external AI endpoint; it never copies
personal AI credentials into an isolated home or container. Evidence records
this prohibition as `local_ai_egress=prohibited`.

Required GitHub Actions checks and the protected current-revision review on the
exact PR head remain authoritative. Human PRs follow the author-specific GitHub
review policy. Same-repository Release-App PRs use only the protected MLX-90
§7.2 Exact-Revision Codex workflow and never fall back to GitHub Copilot. Local
evidence is not a security attestation and remains developer-controlled.

An optional pre-push hook can run
`python3 scripts/lit-push-ready.py pre-push --remote-name "$1" --remote-url "$2"`.
The hook consumes Git's ref-update stream, verifies that every pushed ref
resolves to the validated evidence `HEAD`, and never repeats checks or invokes
AI. Use `python3 scripts/lit-push-ready.py verify` for a manual evidence
check. A pre-commit hook is not required.

The pre-push evidence authorizes exactly one same-name branch update at the
validated `HEAD`, and only as a fast-forward when the remote branch already
exists. Tags, additional branches, deletions, and force pushes require their
own governed process. Defects found by mandatory remote checks become
regression tests or deterministic profile corrections.

An initial migration that changes `.lit/push-ready.json`, the push-ready
runner, or its executable CI profile cannot use that same unmerged policy as
its own trust root. The runner therefore refuses to produce push evidence for
such a bootstrap change. Run the new deterministic profile and the separate
AI-free `review` command on the exact commit, then rely on the protected
required-CI and current-revision gates for that one migration PR. Bootstrap
PRs do not count toward correction-free first-push acceptance evidence.
