# ModuLix – Enterprise Automation

This repository contains the **ModuLix** product inventory and orchestration for automated rollout
enterprise infrastructure components using **Ansible Collections**.

Most day-to-day work happens in the Ansible workspace:

➡️ **See:** [`ansible/README.md`](ansible/README.md)

## Local workflows (high level)

- **Bootstrap Ansible collections:** see `ansible/README.md` (recommended before any run)
- **Lint / Molecule / CI-like runs:** via the Wunder devtools execution environment and `Makefile` targets

## RPM packaging for toolbox

ModuLix scripts can be shipped as an RPM (`modulix-scripts`) for container/toolbox
consumption. Packaging assets and COPR helper scripts are in:

- `packaging/rpm/modulix-scripts.spec`
- `packaging/rpm/build-srpm.sh`
- `packaging/rpm/configure-copr-scm.sh`
- `packaging/rpm/publish-copr.sh`
- `packaging/rpm/README.md`
- `.github/workflows/rpm-srpm-ci.yml`
- `.github/workflows/semantic-release.yml`
- `.releaserc.json`
- `.copr/Makefile`

## Release process

- Commits to `main` are evaluated by semantic-release using Conventional Commits.
- Expected commit prefixes:
  - `fix:` -> patch release (`vX.Y.Z`)
  - `feat:` -> minor release (`vX.Y.Z`)
  - `feat!:` / `fix!:` or `BREAKING CHANGE:` -> major release (`vX.Y.Z`)
- Commits like `docs:`, `chore:`, or `refactor:` without breaking change usually do not create a release tag.
- Release tags must follow `v<semver>` format (for example `v1.4.2`).
- When a `v*` tag is created (by semantic-release or manually), `RPM SRPM CI` publishes `modulix-scripts` to COPR using version `<semver>` (for example `1.4.2`).

## License

GPL-2.0-only. See [LICENSE](LICENSE).
