## OCP4 runbook sequence

Run these from `modulix-automation/ansible`:

```bash
ansible-playbook -i hosts runbooks/40-platforms/openshift/4/prepare-ee.yml
ansible-playbook -i hosts runbooks/40-platforms/openshift/4/20-ocp-install.yml
ansible-playbook -i hosts runbooks/40-platforms/openshift/4/20-ocp-agent-incus.yml
ansible-playbook -i hosts runbooks/40-platforms/openshift/4/21-post-install.yml
```

## Incus Agent install

`20-ocp-agent-incus.yml` is the Incus-backed Agent install path. It keeps Incus
VM lifecycle in `lit.ubuntu.incus_instance` and runs `lit.ocp.install_agent`
with `install_agent_provider: external` and `install_agent_platform: none`.

Define these inventory variables for the environment:

- `ocp_incus_instances`: Incus VM shell definitions for `lit.ubuntu.incus_instance`.
- `ocp_incus_nodes`: OCP Agent node data with `hostname`, `role`, `mac`, and optional static network values.
- `ocp_incus_control_plane_replicas`: control-plane replica count.
- `ocp_incus_compute_replicas`: worker replica count.
- `ocp_incus_agent_iso_path_override`: optional ISO path on the Incus host.
