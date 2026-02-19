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
- `.copr/Makefile`

## License

GPL-2.0-only. See [LICENSE](LICENSE).
