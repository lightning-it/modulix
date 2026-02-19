# modulix-scripts RPM packaging

This directory contains RPM packaging assets for publishing ModuLix scripts as
`modulix-scripts`.

## What gets packaged

- Script payload under `/opt/modulix`:
  - `/opt/modulix/scripts`
  - `/opt/modulix/ansible/scripts`
- Wrapper commands under `/usr/bin`:
  - `ansible-nav`
  - `install-local-collections`
  - `test-ansible.sh`
  - `wunder-devtools-ee.sh`
  - `pre-commit-devtools`
  - `clone-all.sh`

Wrappers are used instead of raw symlinks so scripts that rely on
`BASH_SOURCE[0]` still resolve their repository-relative paths correctly.

## Build SRPM

```bash
packaging/rpm/build-srpm.sh --version 0.1.0 --release 1
```

Output:

- `packaging/rpm/dist/modulix-scripts-<version>-<release>.src.rpm`

## Publish to COPR

```bash
COPR_OWNER=lightning-it packaging/rpm/publish-copr.sh --create-project
```

or with explicit arguments:

```bash
packaging/rpm/publish-copr.sh \
  --owner lightning-it \
  --project modulix \
  --srpm packaging/rpm/dist/modulix-scripts-0.1.0-1.<dist>.src.rpm
```

This `publish-copr.sh` path is a direct SRPM upload fallback.
Preferred for ongoing builds is the webhook-driven SCM workflow below.

## GitHub Actions automation

Workflow: `.github/workflows/rpm-srpm-ci.yml`

- On pull requests touching RPM packaging files:
  - Builds SRPM and uploads it as a workflow artifact.
- On push to `main`:
  - Builds SRPM and uploads it as a workflow artifact.
- On tag push matching `v*`:
  - Builds SRPM and uploads it as a workflow artifact.
  - Publishes the SRPM to COPR (requires `COPR_CONFIG` secret).
<<<<<<< Updated upstream
=======
  - RPM version is derived from the tag (`v1.2.3` -> `1.2.3`).
- `semantic-release` workflow on `main` can generate these `v*` tags automatically from commit messages.
>>>>>>> Stashed changes
- On manual `workflow_dispatch`:
  - Builds SRPM with optional overrides:
    - `version`
    - `release`
    - `build_script`
    - `spec_path`
    - `output_dir`
    - `srpm_glob`
    - `artifact_prefix`
    - `publish_to_copr`
    - `copr_owner`
    - `copr_project`

Build script contract for workflow:
- The workflow invokes the configured `build_script` with:
  - `--version <v>`
  - `--release <r>`
  - `--spec <path>`
  - `--output-dir <path>`

Repository settings for COPR publish job:
- Secret:
  - `COPR_CONFIG` (contents of your `~/.config/copr` credentials file)
- Optional repository variables:
  - `COPR_OWNER`
  - `COPR_PROJECT`
  (manual workflow inputs override repository variables)

## COPR publish via GitHub Webhook (recommended)

Use COPR SCM integration with GitHub webhook as documented:
https://docs.pagure.org/copr.copr/user_documentation.html#github-webhooks

1. In COPR, create package `modulix-scripts` with source type `SCM`.
2. Set clone URL to this repository.
3. Set build method to `make srpm` (uses `.copr/Makefile`).
4. Enable auto-rebuild.
5. In COPR project `Settings` -> `Integrations`, copy the GitHub webhook URL.
6. In GitHub repo `Settings` -> `Webhooks`, create webhook:
   - Payload URL: COPR webhook URL
   - Content type: `application/json`
   - Events: branch or tag creation (or all pushes, based on your policy)

Notes:
- `.copr/Makefile` runs `packaging/rpm/build-srpm.sh` and puts SRPM into COPR `$(outdir)`.
- If you use plain tags like `v1.2.3`, configure the webhook URL to include package name as
  described in COPR docs (e.g. `.../github/<owner>/<project>/modulix-scripts/`).
- Alternatively, use tags in `modulix-scripts-<version>` format.

### CLI setup (matches COPR docs flow)

You can configure the SCM package from CLI:

```bash
COPR_OWNER=lightning-it packaging/rpm/configure-copr-scm.sh
```

This executes `copr-cli add-package-scm` (or `edit-package-scm`) with:
- `--method make_srpm`
- `--webhook-rebuild on`
- package `modulix-scripts`

Optional webhook secret rotation:

```bash
COPR_OWNER=lightning-it packaging/rpm/configure-copr-scm.sh --rotate-webhook-secret
```
