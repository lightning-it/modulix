# ModuLix – Enterprise Automation

This repository contains the public ModuLix product inventory and orchestration
for automated rollout of RHEL, OpenShift, Satellite, Artifactory, and related
enterprise infrastructure components using Ansible Collections.

## Local workflows

All helper commands run inside the Wunder devtools container via the
`scripts/wunder-devtools-ee.sh` wrapper or the provided Makefile targets.

### Linting

Run all lint checks (YAML + Ansible) against the `ansible/` content:

```bash
make lint
```

This will:

- run `yamllint` on the `ansible/` directory inside the devtools container
- run `ansible-lint` on `ansible/playbooks/keycloak.yml`

### Deploying Keycloak

To perform a full lint + deploy run of the Keycloak playbook against the PoC
inventory, ensure you have the SSH credentials exported:

```bash
export SSH_PRIVATE_KEY="$(cat /path/to/id_rsa)"
export SSH_KNOWN_HOSTS="$(cat /path/to/known_hosts)"

make deploy-keycloak
```

This will:

- run the lint targets
- write the SSH key and known hosts to `~/.ssh`
- execute the Keycloak Ansible playbook via the Wunder devtools container:

  ```bash
  ./scripts/wunder-devtools-ee.sh ansible-playbook \
    -i ansible/inventories/poc/hosts.yml \
    ansible/playbooks/keycloak.yml
  ```

### CI-style entrypoint

For a CI-like local run (currently equivalent to lint, and extendable as needed):

```bash
make ci
```

You can add additional checks (e.g. Molecule, Terraform tests) to the `ci` target
to mirror your GitHub Actions pipeline locally.

## License

This repository is licensed under the GNU General Public License v2.0 (GPL-2.0-only).
See [LICENSE](LICENSE) for details.
