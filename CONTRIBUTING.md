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
4. creates one exact committed branch patch relative to the recorded
   merge-base;
5. sends that patch through stdin to a read-only GitHub Copilot CLI exact-diff
   review and to an
   independent read-only Codex CLI review; and
6. writes short-lived, developer-controlled advisory evidence into the Git
   directory.

The distributed runner derives the repository root from its own canonical
engine path and ignores inherited root-override environment variables. A
repository-specific launcher may authorize another layout only through a
validated in-process binding to that exact engine.
The fresh-base integration uses a hook-disabled real merge in a private
worktree and therefore retains pull-request merge semantics on host Git 2.34,
including stock Ubuntu 22.04.

During iteration,
`python3 scripts/lit-push-ready.py review` can review committed, staged,
unstaged, and safe UTF-8 untracked content, but it does not produce push
evidence.

Codex runs as a host-installed CLI. Copilot always runs in the same pinned,
multi-architecture Wunder Devtool image as the deterministic profile through
local Docker or Podman; a host `copilot` binary is not used. Only a Copilot
token obtained from the approved environment or `gh` session is forwarded by
name, never as a command-line value. Evidence records the container runtime,
CLI version, and immutable image digest. Both agents are mandatory and fail
closed when unavailable; access exceptions require a centrally approved
policy and ADR change, not a local configuration downgrade.

Both agents receive a disposable tracked-only repository snapshot with the
exact patch applied. Copilot runs without shell, writes, remote delegation,
repository hooks, workspace MCP, extensions, custom instructions, or a reused
home. These Copilot boundaries use the fixed CLI safety switches, an isolated
`COPILOT_HOME`, and explicit Prompt Mode environment controls; the runner never
injects or overwrites `.github/copilot/settings.local.json`. A before/after Git
fingerprint fails closed if either agent changes the disposable exact-patch
snapshot. Codex 0.138.0 or newer runs with strict configuration,
apps/hooks/network disabled, an untrusted project, and a dynamically named
permission profile that allows only minimal runtime reads and read access to
the disposable workspace. A runtime self-test must prove that a sibling canary
cannot be read before Codex sees repository content. Neither agent may claim
that the other agent or the GitHub product approved a change.

The local Copilot CLI exact-diff review is a pre-push approximation, not the
GitHub Copilot pull-request review product. Required GitHub Actions checks and
the current-head server review remain authoritative. Evidence records that
product boundary and the remaining runtime and authorization parity gaps in
machine-readable form. The local evidence is not a security attestation and
can be controlled by the developer; current-head branch policy, secret
scanning, GitHub Actions, and the server Copilot review remain security and
merge boundaries. Local secret-like path/content detection is only
defense-in-depth.

An optional pre-push hook can run
`python3 scripts/lit-push-ready.py pre-push --remote-name "$1" --remote-url "$2"`.
The hook consumes Git's ref-update stream, verifies that every pushed ref
resolves to the reviewed evidence `HEAD`, and never repeats checks or agent
calls. Use `python3 scripts/lit-push-ready.py verify` for a manual evidence
check. A pre-commit hook is not required.

The pre-push evidence authorizes exactly one same-name branch update at the
reviewed `HEAD`, and only as a fast-forward when the remote branch already
exists. Tags, additional branches, deletions, and force pushes require their
own governed process. A local agent false positive blocks the push until the
finding is fixed or the central policy is deliberately changed; a false
negative is caught by the mandatory remote checks and becomes a regression
test or profile correction.

An initial migration that changes `.lit/push-ready.json`, the push-ready
runner, or its executable CI profile cannot use that same unmerged policy as
its own trust root. The runner therefore refuses to produce push evidence for
such a bootstrap change. Run the new deterministic profile and the separate
dual-agent `review` command on the exact commit, then rely on the protected
required-CI and current-head Copilot gates for that one migration PR. Bootstrap
PRs do not count toward correction-free first-push acceptance evidence.
