# ModuLix – Enterprise Automation

This repository contains the public ModuLix product inventory and orchestration
for automated rollout of RHEL, OpenShift, Satellite, Artifactory, and related
enterprise infrastructure components using Ansible Collections.

## Tests

All helper commands run inside the Wunder devtools container. Run YAML linting and
inventory validation for the `ansible/` directory:

```bash
make test
```

For a quick connectivity check against the Keycloak inventory:

```bash
make deploy-keycloak
```

Use `make lint` to execute the pre-commit hooks in the same containerized environment.
