# vSphere VM And Template Runbooks

These runbooks manage vSphere VM lifecycle objects from inventory.

Use this area for:

- cloning a VM from an existing vSphere template
- destroying a single inventory-defined VM
- normalizing Linux VM/template objects through VMware Tools
- converting a Linux VM back into a reusable vSphere template

## Template Workflow

The template workflow is inventory-driven. Define one inventory host per target
template and put it in a template group such as `vmware_templates`.

Supported target patterns:

- Clone target: set `vmware_vsphere_template` to an existing source template.
  Run `20-vm-template.yml` first, then `30-template-bootstrap.yml`.
- Existing target: omit `vmware_vsphere_template` when the VM/template object
  already exists in vCenter. Run `30-template-bootstrap.yml` directly.

The bootstrap runbook uses VMware Tools guest operations. It logs into the
guest with `vmware_vsphere_guest_bootstrap_guest_username` and
`vmware_vsphere_guest_bootstrap_guest_password`, writes managed local users from
`users_accounts` and `users_accounts_extra`, cleans template identity state,
powers the VM off, and marks it as a vSphere template.

## Inventory Contract

At minimum, template host inventory needs:

```yaml
vmware_vsphere_vm_name: template-example-linux
vmware_vsphere_guest_id: rhel9_64Guest

# Optional: only for clone targets.
vmware_vsphere_template: source-example-linux

# Required for clone targets.
vmware_vsphere_datastore: datastore-example
vmware_vsphere_folder_name: templates
vmware_vsphere_network:
  - name: network-example
    connected: true
    start_connected: true

# Guest operations login used to repair/bootstrap the template object.
vmware_vsphere_guest_bootstrap_vm_name: "{{ vmware_vsphere_vm_name }}"
vmware_vsphere_guest_bootstrap_guest_username: root
vmware_vsphere_guest_bootstrap_guest_password: "{{ linux_bootstrap_password }}"
vmware_vsphere_guest_bootstrap_mark_as_template: true
vmware_vsphere_guest_bootstrap_convert_template_to_vm: true
vmware_vsphere_guest_bootstrap_power_on: true
vmware_vsphere_guest_bootstrap_power_off: true

# SSH/bootstrap account expected on VMs cloned from the finished template.
linux_bootstrap_user: breakglass
linux_bootstrap_password: "{{ common_password_install }}"
```

The guest-operations login may be different from the initial SSH account used
on cloned VMs. For example, the template object may still require `root` or an
installer account for VMware Tools repair, while finished clones use a managed
account such as `breakglass`.

## Initial OS Installation

Use Packer for the first unattended OS installation from ISO. Keep these
runbooks focused on vCenter object lifecycle and post-install template
normalization.

Recommended split:

- Packer builds the installed source VM/template from the vendor ISO.
- RHEL builds use Kickstart.
- Ubuntu builds use autoinstall/cloud-init seed data.
- The installed source includes `open-vm-tools`, cloud-init where the OS uses
  it, and any package needed by the VMware Tools guest-operations bootstrap.
- The source keeps a temporary repair login such as `root` or an installer
  account, if required.
- `20-vm-template.yml` clones from that source into the final inventory name.
- `30-template-bootstrap.yml` writes the managed local users, including the
  final bootstrap account such as `breakglass`, cleans machine identity, powers
  off the VM, and marks it as a vSphere template.

Typical source and final names:

| OS | Packer source object | Final template host |
| --- | --- | --- |
| RHEL 8 | `rhel-8-minimal` | `template-rhel-8-minimal` |
| RHEL 9 | `rhel-9-minimal` | `template-rhel-9-minimal` |
| RHEL 10 | `rhel-10-minimal` | `template-rhel-10-minimal` |
| Ubuntu 24.04 | `template-ubuntu-24-source` | `template-ubuntu-24-server` |
| Ubuntu 26.04 | `template-ubuntu-26-source` | `template-ubuntu-26-server` |

Do not clone from a source whose installed OS does not match the final template
name. Replace or rebuild the source first.

## Run Commands

Run from `modulix-automation/ansible` with the environment inventory passed on
the command line.

Create a missing clone target:

```bash
./scripts/ansible-nav run \
  runbooks/10-compute/virtualization/vsphere/20-vm-template.yml \
  -i "${INVENTORY_FILE}" \
  --limit "${TEMPLATE_HOST}"
```

Bootstrap and mark the target as a template:

```bash
./scripts/ansible-nav run \
  runbooks/10-compute/virtualization/vsphere/30-template-bootstrap.yml \
  -i "${INVENTORY_FILE}" \
  --limit "${TEMPLATE_HOST}"
```

Destroy a wrongly created target before rebuilding:

```bash
./scripts/ansible-nav run \
  runbooks/10-compute/virtualization/vsphere/90-vm-destroy.yml \
  -i "${INVENTORY_FILE}" \
  --limit "${TEMPLATE_HOST}"
```

## Preflight Checks

Before creating a clone target, verify the source template exists and has the
expected vSphere guest ID:

```bash
ANSIBLE_CONFIG=ansible.cfg ansible-inventory \
  -i "${INVENTORY_FILE}" \
  --host "${TEMPLATE_HOST}" |
  jq -e '
    (.vmware_vsphere_vm_name | length) > 0 and
    (.vmware_vsphere_guest_id | length) > 0 and
    (
      (.vmware_vsphere_template // "") == "" or
      ((.vmware_vsphere_datastore | length) > 0 and
       (.vmware_vsphere_folder_name | length) > 0 and
       (.vmware_vsphere_network | length) > 0)
    ) and
    .vmware_vsphere_guest_bootstrap_mark_as_template == true and
    .vmware_vsphere_guest_bootstrap_power_on == true and
    .vmware_vsphere_guest_bootstrap_power_off == true
  ' >/dev/null
```

Verify final state with vCenter after bootstrap:

```bash
ANSIBLE_CONFIG=ansible.cfg ansible "${TEMPLATE_HOST}" \
  -i "${INVENTORY_FILE}" \
  -c local \
  -e ansible_become=false \
  -m community.vmware.vmware_guest_info \
  -a 'hostname={{ vmware_vsphere_hostname }} username={{ vmware_vsphere_username }} password={{ vmware_vsphere_password }} validate_certs={{ vmware_vsphere_validate_certs }} datacenter={{ vmware_vsphere_datacenter }} name={{ vmware_vsphere_vm_name }}'
```

The target is ready when vCenter reports it as powered off and
`hw_is_template: true`.

## Common Failure Modes

- Source template is missing: import or create the source object first, then
  rerun `20-vm-template.yml`.
- Source template has the wrong OS version: stop and replace the source; do not
  create a misleading target name.
- VMware Tools guest operations fail authentication: repair
  `vmware_vsphere_guest_bootstrap_guest_username` and password inventory, or
  repair the login inside the template object.
- VMware Tools file fetch fails with an ESXi hostname resolution error: fix DNS
  or host resolution for the ESXi hostname reported by vCenter, then rerun the
  bootstrap.
