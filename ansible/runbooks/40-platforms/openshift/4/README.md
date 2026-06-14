## OCP4 runbook sequence

Run these from `modulix-automation/ansible`:

```bash
ansible-playbook -i hosts runbooks/40-platforms/openshift/4/prepare-ee.yml
ansible-playbook -i hosts runbooks/40-platforms/openshift/4/20-ocp-install.yml
ansible-playbook -i hosts runbooks/40-platforms/openshift/4/21-post-install.yml
```
