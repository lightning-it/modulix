"""Static guards for the external 1Password root-of-trust bootstrap path."""

from pathlib import Path
import unittest

import yaml


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
HETZNER_DIRECTORY = (
    REPOSITORY_ROOT / "ansible" / "runbooks" / "10-compute" / "baremetal" / "hetzner"
)
UBUNTU_DIRECTORY = (
    REPOSITORY_ROOT
    / "ansible"
    / "runbooks"
    / "30-operating-systems"
    / "ubuntu"
    / "24"
)
CONTROLLER_DIRECTORY = (
    REPOSITORY_ROOT / "ansible" / "runbooks" / "00-common" / "controller"
)


def load_yaml(path: Path):
    """Load one repository YAML document."""
    with path.open(encoding="utf-8") as stream:
        return yaml.safe_load(stream)


def walk_tasks(tasks):
    """Yield tasks recursively through Ansible block/rescue/always sections."""
    for task in tasks:
        yield task
        for section in ("block", "rescue", "always"):
            yield from walk_tasks(task.get(section, []))


def named_task(plays, name: str):
    """Find one exact task name across every play and nested task section."""
    matches = []
    for play in plays:
        for section in ("pre_tasks", "tasks", "post_tasks"):
            matches.extend(
                task for task in walk_tasks(play.get(section, []))
                if task.get("name") == name
            )
    if len(matches) != 1:
        raise AssertionError(f"expected one task named {name!r}, got {len(matches)}")
    return matches[0]


class OnePasswordRootOfTrustTests(unittest.TestCase):
    """Keep secret creation, public-key staging, and consumption fail closed."""

    def test_creation_returns_only_pinnable_identity_metadata(self):
        path = HETZNER_DIRECTORY / "08-recovery-secrets.yml"
        content = path.read_text(encoding="utf-8")

        self.assertIn("lit.foundational.onepassword_secret_item", content)
        self.assertIn("lit.foundational.onepassword_ssh_key_item", content)
        self.assertIn("password_item.item_version", content)
        self.assertIn("ssh_key_item.item_version", content)
        self.assertIn("ssh_key_item.expected_fingerprint", content)
        self.assertIn("ssh_keygen_path", content)
        self.assertIn("cli_sha256", content)
        self.assertIn("authorized_user_uuids", content)
        self.assertIn("ssh_add_sha256", content)
        self.assertIn("ssh_keygen_sha256", content)
        self.assertIn("approval_authority", content)
        self.assertIn("Report safe 1Password identity metadata", content)
        self.assertNotIn("onepassword_read_secret", content)
        self.assertNotIn("create_confirmation", content)

    def test_macos_controller_runtime_is_plan_first_and_ansible_only(self):
        path = CONTROLLER_DIRECTORY / "10-onepassword-runtime.yml"
        content = path.read_text(encoding="utf-8")
        plays = load_yaml(path)

        self.assertEqual(len(plays), 1)
        self.assertEqual(plays[0]["hosts"], "localhost")
        self.assertEqual(plays[0]["connection"], "local")
        self.assertIs(plays[0]["become"], False)
        self.assertIn("onepassword_controller_target", content)
        self.assertIn("onepassword_controller_runtime_action", content)
        self.assertIn("['plan', 'apply']", content)
        self.assertIn("_controller_runtime_action == 'apply'", content)
        self.assertIn("ansible.builtin.copy", content)
        self.assertIn("ansible.builtin.stat", content)
        self.assertNotIn("ansible.builtin.shell", content)
        self.assertNotIn("ansible.builtin.command", content)
        self.assertNotIn("lookup('pipe'", content)
        self.assertNotIn("op item", content)
        self.assertNotIn("password_recipe", content)

        privileged_tasks = []
        for section in ("pre_tasks", "tasks", "post_tasks"):
            privileged_tasks.extend(
                task for task in plays[0].get(section, []) if task.get("become") is True
            )
        self.assertGreater(len(privileged_tasks), 0)
        for task in privileged_tasks:
            self.assertIs(task.get("vars", {}).get("ansible_become"), True)

    def test_recovery_creation_uses_short_lived_separate_approvals(self):
        path = HETZNER_DIRECTORY / "09-onepassword-recovery-create.yml"
        content = path.read_text(encoding="utf-8")
        plays = load_yaml(path)

        self.assertEqual(plays[0]["hosts"], "hetzner_baremetal")
        self.assertIn("CREATE-ONEPASSWORD-RECOVERY:", content)
        self.assertEqual(content.count("lit.foundational.onepassword_approval:"), 2)
        self.assertIn("create-onepassword-secret", content)
        self.assertIn("create-onepassword-ssh-key", content)
        self.assertIn("validity_seconds: 600", content)
        self.assertEqual(content.count("signing_agent_socket_path:"), 2)
        self.assertNotIn("onepassword_recovery_signing_key_path", content)
        self.assertIn("ansible.builtin.import_playbook: 08-recovery-secrets.yml", content)
        self.assertNotIn("ansible.builtin.shell", content)

    def test_approval_authority_import_is_exact_and_never_logs_private_key(self):
        path = HETZNER_DIRECTORY / "07-onepassword-ssh-agent-import.yml"
        content = path.read_text(encoding="utf-8")
        plays = load_yaml(path)

        self.assertEqual(plays[0]["hosts"], "hetzner_baremetal")
        self.assertIn("lit.foundational.onepassword_ssh_key_import:", content)
        self.assertIn("private_key_path:", content)
        self.assertIn("expected_fingerprint:", content)
        self.assertIn("agent_verified:", content)
        self.assertIn("source_public_key_matches:", content)
        self.assertIn("metadata_repair_required:", content)
        self.assertIn("metadata_repaired:", content)
        self.assertNotIn("ansible.builtin.shell", content)
        import_tasks = [
            task
            for task in plays[0]["tasks"]
            if "lit.foundational.onepassword_ssh_key_import" in task
        ]
        self.assertEqual(len(import_tasks), 1)
        self.assertIs(import_tasks[0].get("no_log"), True)

    def test_controller_agent_policy_is_inventory_bound_and_network_free(self):
        path = CONTROLLER_DIRECTORY / "11-onepassword-ssh-agent-policy.yml"
        content = path.read_text(encoding="utf-8")
        plays = load_yaml(path)

        self.assertEqual(plays[0]["hosts"], "localhost")
        self.assertIn("onepassword_controller_ssh_agent_policy", content)
        self.assertIn("[[ssh-keys]]", content)
        self.assertIn('item = "{{ _agent_policy.item_id }}"', content)
        self.assertNotIn('vault = "{{ _agent_policy.vault_id }}"', content)
        self.assertNotIn('account = "{{ _agent_policy.account_id }}"', content)
        self.assertIn("IdentityAgent", content)
        self.assertIn("- -G", content)
        self.assertNotIn("ansible.builtin.shell", content)
        self.assertNotIn("ansible.builtin.uri", content)

    def test_ssh_key_capability_diagnostic_is_read_only_and_pinned(self):
        path = CONTROLLER_DIRECTORY / "15-onepassword-ssh-key-capability-diagnostic.yml"
        content = path.read_text(encoding="utf-8")
        plays = load_yaml(path)

        self.assertEqual(plays[0]["hosts"], "hetzner_baremetal")
        self.assertIn("hetzner_baremetal_onepassword.cli_sha256", content)
        self.assertIn("item", content)
        self.assertIn("create", content)
        self.assertIn("--help", content)
        self.assertNotIn("ansible.builtin.shell", content)

    def test_every_onepassword_generation_or_transport_task_is_no_log(self):
        sensitive_modules = {
            "lit.foundational.onepassword_secret_item",
            "lit.foundational.onepassword_ssh_key_item",
            "lit.foundational.onepassword_ssh_secret_stdin",
        }
        paths = (
            HETZNER_DIRECTORY / "08-recovery-secrets.yml",
            UBUNTU_DIRECTORY / "09-prepare-installimage.yml",
            UBUNTU_DIRECTORY / "10-bootstrap-unlock.yml",
        )
        sensitive_tasks = []
        for path in paths:
            for play in load_yaml(path):
                for section in ("pre_tasks", "tasks", "post_tasks"):
                    for task in walk_tasks(play.get(section, [])):
                        if sensitive_modules.intersection(task):
                            sensitive_tasks.append((path.name, task))

        self.assertEqual(len(sensitive_tasks), 4)
        for filename, task in sensitive_tasks:
            with self.subTest(file=filename, task=task.get("name")):
                self.assertIs(task.get("no_log"), True)

    def test_backend_orchestration_preserves_fail_closed_day2_contracts(self):
        creation = (HETZNER_DIRECTORY / "08-recovery-secrets.yml").read_text(
            encoding="utf-8"
        )
        resolver = (
            REPOSITORY_ROOT
            / "ansible"
            / "runbooks"
            / "00-common"
            / "tasks"
            / "resolve-recovery-secret.yml"
        ).read_text(encoding="utf-8")
        prepare = (UBUNTU_DIRECTORY / "09-prepare-installimage.yml").read_text(
            encoding="utf-8"
        )
        bootstrap_unlock = (
            UBUNTU_DIRECTORY / "10-bootstrap-unlock.yml"
        ).read_text(encoding="utf-8")
        day2_unlock = (UBUNTU_DIRECTORY / "11-luks-unlock.yml").read_text(
            encoding="utf-8"
        )
        day2_header = (UBUNTU_DIRECTORY / "13-luks-header-backup.yml").read_text(
            encoding="utf-8"
        )

        self.assertIn("'onepassword_cli'", creation)
        self.assertIn("== 'onepassword_cli'", prepare)
        self.assertIn("== 'onepassword_cli'", bootstrap_unlock)
        self.assertNotIn("'onepassword_cli'", resolver)
        for content in (day2_unlock, day2_header):
            self.assertIn("== 'hashicorp_vault'", content)
            self.assertNotIn("'onepassword_cli'", content)

    def test_dropbear_hook_uses_only_the_verified_public_key(self):
        plays = load_yaml(UBUNTU_DIRECTORY / "09-prepare-installimage.yml")
        play = plays[0]
        verify_task = next(
            task
            for task in play["pre_tasks"]
            if task["name"]
            == "Verify the pinned Dropbear public key and its Agent capability"
        )
        self.assertEqual(
            verify_task["lit.foundational.onepassword_ssh_key_item"]["operation"],
            "verify_agent",
        )
        verify_arguments = verify_task[
            "lit.foundational.onepassword_ssh_key_item"
        ]
        for required in (
            "cli_sha256",
            "authorized_user_uuids",
            "ssh_add_sha256",
            "ssh_keygen_sha256",
        ):
            self.assertIn(required, verify_arguments)
        role_task = next(
            task
            for task in play["tasks"]
            if task["name"] == "Stage the secret-free Ubuntu Dropbear hook"
        )
        self.assertEqual(
            role_task["vars"]["luks_unlock_dropbear_authorized_keys"],
            ["{{ _luks_unlock_dropbear_public_identity.public_key }}"],
        )

    def test_unlock_has_no_ansible_secret_fact_or_generic_resolver(self):
        path = UBUNTU_DIRECTORY / "10-bootstrap-unlock.yml"
        content = path.read_text(encoding="utf-8")
        plays = load_yaml(path)
        play = plays[0]
        unlock_task = next(
            task
            for task in play["tasks"]
            if task["name"].startswith("Submit the exact pinned 1Password")
        )
        arguments = unlock_task["lit.foundational.onepassword_ssh_secret_stdin"]

        self.assertIs(unlock_task["no_log"], True)
        self.assertEqual(arguments["remote_command"], "/bin/cryptroot-unlock")
        self.assertIn("password_item_version", arguments)
        self.assertIn("ssh_item_version", arguments)
        self.assertIn("ssh_expected_fingerprint", arguments)
        self.assertIn("cli_sha256", arguments)
        self.assertIn("authorized_user_uuids", arguments)
        self.assertIn("ssh_sha256", arguments)
        self.assertIn("ssh_add_sha256", arguments)
        self.assertIn("ssh_keygen_path", arguments)
        self.assertIn("ssh_keygen_sha256", arguments)
        self.assertIn("destination_host_fingerprint", arguments)
        self.assertIn("known_hosts_sha256", arguments)
        self.assertIn("approval", arguments)
        self.assertIn("approval_authority", arguments)
        self.assertNotIn("confirmation", arguments)
        self.assertNotIn("register", unlock_task)
        self.assertNotIn("resolve-recovery-secret.yml", content)
        self.assertNotIn("_hetzner_baremetal_recovery_passphrase", content)
        self.assertNotIn("ansible.builtin.set_fact", content)
        self.assertNotIn("ansible.builtin.command", content)

    def test_first_boot_explicitly_accepts_the_external_backend(self):
        content = (UBUNTU_DIRECTORY / "10-first-encrypted-boot.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("'onepassword_cli'", content)
        self.assertIn("independently recorded unlock", content)
        self.assertNotIn("under no_log", content)

    def test_boot_unlock_and_reconnect_are_noninteractive_phases(self):
        boot = (UBUNTU_DIRECTORY / "10-first-encrypted-boot.yml").read_text(
            encoding="utf-8"
        )
        unlock = (UBUNTU_DIRECTORY / "10-bootstrap-unlock.yml").read_text(
            encoding="utf-8"
        )
        reconnect = (UBUNTU_DIRECTORY / "11-first-boot-reconnect.yml").read_text(
            encoding="utf-8"
        )

        for content in (boot, unlock, reconnect):
            self.assertNotIn("ansible.builtin.pause", content)
        self.assertIn("End the boot phase before", boot)
        self.assertIn("luks_unlock_dropbear_known_hosts_path", boot)
        self.assertIn("known_hosts_sha256", boot)
        self.assertIn("connection: local", reconnect)
        self.assertIn("hetzner_first_boot_openssh_fingerprint", reconnect)
        self.assertIn("RECONNECT:", reconnect)


if __name__ == "__main__":
    unittest.main()
