"""Static safety guards for the Ubuntu Workbench orchestration."""

from collections.abc import Mapping
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

import yaml


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
RUNBOOK_DIRECTORY = (
    REPOSITORY_ROOT / "ansible" / "runbooks" / "50-applications" / "workbench"
)


def load_yaml(path: Path):
    """Load one repository YAML document."""
    with path.open(encoding="utf-8") as stream:
        return yaml.safe_load(stream)


def normalized_task_module_names(task):
    """Return FQCN and short module names from supported Ansible task forms."""
    module_names = {key for key in task if isinstance(key, str)}
    for action_key in ("action", "local_action"):
        action = task.get(action_key)
        module_name = None
        if isinstance(action, str):
            action_parts = action.split(maxsplit=1)
            if action_parts:
                module_name = action_parts[0]
        elif isinstance(action, Mapping):
            module_name = action.get("module")
        if isinstance(module_name, str):
            module_names.add(module_name)

    return module_names | {name.rsplit(".", 1)[-1] for name in module_names}


class WorkbenchRunbookSafetyTests(unittest.TestCase):
    """Keep the single-target and cleanup safety boundaries reviewable."""

    def test_python_package_validation_uses_canonical_names(self):
        validation = (
            RUNBOOK_DIRECTORY / "tasks" / "validate-tools.yml"
        ).read_text(encoding="utf-8")
        self.assertGreaterEqual(
            validation.count("regex_replace('[-_.]+', '-')"), 3
        )

    def test_all_public_workbench_plays_are_serial_and_fail_closed(self):
        for name in (
            "20-ubuntu-setup.yml",
            "30-validate.yml",
            "40-acceptance.yml",
            "50-cleanup.yml",
        ):
            with self.subTest(playbook=name):
                play = load_yaml(RUNBOOK_DIRECTORY / name)[0]
                self.assertEqual(play["hosts"], "ubuntu_workbenches")
                self.assertEqual(play["serial"], 1)
                self.assertIs(play["any_errors_fatal"], True)
                self.assertIs(play["gather_facts"], True)

    def test_deployment_role_scope_is_exact(self):
        play = load_yaml(RUNBOOK_DIRECTORY / "20-ubuntu-setup.yml")[0]
        roles = [item["role"] for item in play["roles"]]
        self.assertEqual(
            roles,
            [
                "lit.ubuntu.repos",
                "lit.ubuntu.users",
                "lit.ubuntu.openssh_server",
                "lit.ubuntu.podman",
                "lit.ubuntu.incus",
                "lit.ubuntu.developer_tools",
            ],
        )

    def test_target_contract_rejects_broad_scope_and_desktop_components(self):
        contract = (RUNBOOK_DIRECTORY / "tasks" / "target-contract.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("ansible_limit", contract)
        self.assertIn("ansible_play_hosts_all | length == 1", contract)
        for component in (
            "baseline",
            "automatic_updates",
            "netplan",
            "vscode_desktop",
            "firefox",
            "gui",
            "xrdp",
            "firewalld",
        ):
            self.assertIn(f"not (workbench_components.{component} | bool)", contract)

    def test_target_contract_requires_exact_ubuntu_2404_facts(self):
        contract = (RUNBOOK_DIRECTORY / "tasks" / "target-contract.yml").read_text(
            encoding="utf-8"
        )

        self.assertIn("ansible_facts is mapping", contract)
        self.assertIn(
            "ansible_facts.get('distribution', '') == 'Ubuntu'", contract
        )
        self.assertIn(
            "ansible_facts.get('distribution_version', '') == '24.04'", contract
        )
        self.assertIn(
            "ansible_facts.get('fqdn', '') == inventory_hostname", contract
        )
        self.assertNotIn("version('24.04', '>=')", contract)
        self.assertNotIn("version('25.04', '<')", contract)

    def test_validation_task_files_contain_no_mutating_modules(self):
        forbidden_modules = {
            "ansible.builtin.apt",
            "ansible.builtin.copy",
            "ansible.builtin.file",
            "ansible.builtin.package",
            "ansible.builtin.service",
            "ansible.builtin.systemd_service",
            "ansible.builtin.template",
            "ansible.builtin.user",
            "community.general.lvol",
        }
        forbidden_module_names = forbidden_modules | {
            module.rsplit(".", 1)[-1] for module in forbidden_modules
        }

        def walk_tasks(tasks):
            for task in tasks:
                yield task
                for section in ("block", "rescue", "always"):
                    nested = task.get(section, [])
                    if isinstance(nested, list):
                        yield from walk_tasks(nested)

        for path in sorted((RUNBOOK_DIRECTORY / "tasks").glob("validate-*.yml")):
            with self.subTest(task_file=path.name):
                tasks = load_yaml(path)
                for task in walk_tasks(tasks):
                    module_names = normalized_task_module_names(task)
                    self.assertFalse(forbidden_module_names.intersection(module_names))
                    if "command" in module_names:
                        self.assertIs(task.get("changed_when"), False)

    def test_module_name_detection_covers_supported_ansible_task_forms(self):
        tasks = (
            {"ansible.builtin.copy": {"src": "a", "dest": "b"}},
            {"copy": {"src": "a", "dest": "b"}},
            {"action": "ansible.builtin.copy src=a dest=b"},
            {"local_action": {"module": "copy", "src": "a", "dest": "b"}},
        )
        for task in tasks:
            with self.subTest(task=task):
                self.assertIn("copy", normalized_task_module_names(task))

    def test_validation_uses_read_only_sudo_policy_inspection(self):
        tasks = load_yaml(RUNBOOK_DIRECTORY / "tasks" / "validate-user.yml")
        policy_task = next(
            task
            for task in tasks
            if task["name"].startswith("Inspect effective sudo policy")
        )
        decode_task = next(
            task
            for task in tasks
            if task["name"].startswith("Decode effective sudo policy")
        )
        policy_text = (RUNBOOK_DIRECTORY / "tasks" / "validate-user.yml").read_text(
            encoding="utf-8"
        )

        self.assertEqual(
            policy_task["ansible.builtin.command"]["argv"],
            [
                "sudo",
                "--non-interactive",
                "--list",
                "--other-user={{ workbench_validation_user.name }}",
            ],
        )
        self.assertEqual(policy_task["become_user"], "root")
        self.assertIs(policy_task["changed_when"], False)
        self.assertIs(policy_task["no_log"], True)
        self.assertIs(decode_task["changed_when"], False)
        self.assertIs(decode_task["no_log"], True)
        self.assertIn("NOPASSWD", policy_text)
        self.assertNotIn("--reset-timestamp", policy_text)

    def test_incus_external_evidence_is_mapping_safe_and_staged(self):
        tasks = load_yaml(RUNBOOK_DIRECTORY / "tasks" / "validate-incus.yml")
        task_names = [task["name"] for task in tasks]
        task_text = (
            RUNBOOK_DIRECTORY / "tasks" / "validate-incus.yml"
        ).read_text(encoding="utf-8")

        self.assertIn("volatile.initial_source", task_text)
        self.assertIn("item.key | replace('_', '-')", task_text)

        root_guard_index = task_names.index(
            "Require mapping-safe decoded Incus evidence roots"
        )
        nested_resolution_index = task_names.index(
            "Resolve nested Incus evidence mappings"
        )
        nested_guard_index = task_names.index(
            "Require mapping-safe nested Incus evidence"
        )
        device_resolution_index = task_names.index(
            "Resolve Incus profile devices and logical-volume report"
        )
        device_guard_index = task_names.index(
            "Require mapping-safe Incus profile devices and logical-volume report"
        )
        row_guard_index = task_names.index(
            "Require a mapping-safe logical-volume evidence row"
        )
        size_guard_index = task_names.index(
            "Require scalar logical-volume size evidence"
        )
        instance_guard_index = task_names.index(
            "Require mapping-safe Incus instance evidence"
        )
        instance_collection_index = task_names.index(
            "Collect normalized Incus instance names"
        )

        self.assertLess(root_guard_index, nested_resolution_index)
        self.assertLess(nested_resolution_index, nested_guard_index)
        self.assertLess(nested_guard_index, device_resolution_index)
        self.assertLess(device_resolution_index, device_guard_index)
        self.assertLess(row_guard_index, size_guard_index)
        self.assertLess(instance_guard_index, instance_collection_index)

        for safe_access in (
            "workbench_validation_incus_storage_data.get('config', none)",
            "workbench_validation_incus_storage_data.get('driver', none)",
            "workbench_validation_incus_network_data.get('config', none)",
            "workbench_validation_incus_network_data.get('type', none)",
            "workbench_validation_incus_project_data.get('config', none)",
            "workbench_validation_incus_profile_data.get('config', none)",
            "workbench_validation_incus_profile_data.get('devices', none)",
            "workbench_validation_incus_storage_config.get('source', none)",
            "workbench_validation_incus_network_config.get('ipv4.address', none)",
            "workbench_validation_incus_network_config.get('ipv4.dhcp', none)",
            "workbench_validation_incus_network_config.get('ipv4.nat', none)",
            "workbench_validation_incus_network_config.get('ipv6.address', none)",
            "workbench_validation_incus_profile_devices.get('eth0', none)",
            "workbench_validation_incus_profile_devices.get('root', none)",
            "workbench_validation_incus_project_config.get(",
            "workbench_validation_incus_profile_config.get('limits.cpu', none)",
            "workbench_validation_incus_profile_config.get('limits.memory', none)",
            "workbench_validation_incus_profile_eth0.get('network', none)",
            "workbench_validation_incus_profile_root.get('pool', none)",
            "workbench_validation_incus_lv_document.get('report', none)",
            "workbench_validation_incus_lv_report.get('lv', none)",
            "workbench_validation_incus_lv_row.get('lv_size', none)",
            "workbench_validation_incus_lv_row.get('lv_size', '-1')",
            "item.get('name', none)",
        ):
            self.assertIn(safe_access, task_text)

        for mapping_variable in (
            "workbench_validation_incus_storage_data",
            "workbench_validation_incus_network_data",
            "workbench_validation_incus_project_data",
            "workbench_validation_incus_profile_data",
            "workbench_validation_incus_storage_config",
            "workbench_validation_incus_network_config",
            "workbench_validation_incus_project_config",
            "workbench_validation_incus_profile_config",
            "workbench_validation_incus_profile_devices",
            "workbench_validation_incus_profile_eth0",
            "workbench_validation_incus_profile_root",
            "workbench_validation_incus_lv_document",
            "workbench_validation_incus_lv_report",
            "workbench_validation_incus_lv_row",
        ):
            self.assertNotRegex(
                task_text,
                rf"{mapping_variable}(?:\[|\.(?!get\())",
            )

        for unsafe_access in (
            "workbench_validation_incus_storage_data.driver",
            "workbench_validation_incus_storage_data.config",
            "workbench_validation_incus_network_data.type",
            "workbench_validation_incus_network_data.config",
            "workbench_validation_incus_project_data.config",
            "workbench_validation_incus_profile_data.config",
            "workbench_validation_incus_profile_data.devices",
            "map(attribute='name')",
            ".report[0].lv",
        ):
            self.assertNotIn(unsafe_access, task_text)

    def test_user_home_and_shell_paths_reject_traversal_segments(self):
        user_tasks = load_yaml(
            RUNBOOK_DIRECTORY / "tasks" / "validate-user.yml"
        )
        contract_task = user_tasks[0]
        contract_conditions = contract_task["ansible.builtin.assert"]["that"]
        home_read_indices = [
            index
            for index, task in enumerate(user_tasks)
            if "workbench_validation_user.home" in repr(task)
            and index > 0
        ]

        self.assertEqual(contract_task["name"].split()[0], "Validate")
        self.assertGreaterEqual(len(home_read_indices), 3)
        self.assertTrue(all(index > 0 for index in home_read_indices))

        for field in ("home", "shell"):
            condition = next(
                item
                for item in contract_conditions
                if f"workbench_validation_user.{field}" in item
                and "is match" in item
            )
            path_pattern = re.search(r"is match\('([^']+)'\)", condition)
            self.assertIsNotNone(path_pattern)
            compiled_path_pattern = re.compile(path_pattern.group(1))

            self.assertIsNotNone(compiled_path_pattern.fullmatch("/home/developer"))
            self.assertIsNotNone(compiled_path_pattern.fullmatch("/usr/bin/bash"))
            for unsafe_path in (
                "/../etc",
                "/home/../etc",
                "/home/./developer",
                "/home//developer",
                "/home/developer/",
            ):
                with self.subTest(field=field, unsafe_path=unsafe_path):
                    self.assertIsNone(compiled_path_pattern.fullmatch(unsafe_path))

    def test_acceptance_paths_validate_contract_before_profile_resolution(self):
        for name in ("40-acceptance.yml", "50-cleanup.yml"):
            with self.subTest(playbook=name):
                tasks = load_yaml(RUNBOOK_DIRECTORY / name)[0]["tasks"]
                imports = [task.get("ansible.builtin.import_tasks") for task in tasks]
                self.assertLess(
                    imports.index("tasks/validate-contract.yml"),
                    imports.index("tasks/acceptance-contract.yml"),
                )

    def test_contract_roots_are_guarded_before_nested_resolution(self):
        acceptance_tasks = load_yaml(
            RUNBOOK_DIRECTORY / "tasks" / "acceptance-contract.yml"
        )
        acceptance_names = [task["name"] for task in acceptance_tasks]
        acceptance_text = (
            RUNBOOK_DIRECTORY / "tasks" / "acceptance-contract.yml"
        ).read_text(encoding="utf-8")
        root_index = acceptance_names.index(
            "Require the Workbench acceptance contract root before profile resolution"
        )
        section_index = acceptance_names.index(
            "Require structured sections for the selected acceptance profile"
        )
        resolution_index = acceptance_names.index("Resolve requested acceptance profile")
        resources_index = acceptance_names.index(
            "Require structured resources for the selected acceptance profile"
        )
        identity_index = acceptance_names.index(
            "Require a safe selected acceptance profile identity"
        )
        base_name_index = acceptance_names.index(
            "Resolve requested acceptance instance base name"
        )

        self.assertLess(root_index, section_index)
        self.assertLess(section_index, resolution_index)
        self.assertLess(resolution_index, resources_index)
        self.assertLess(resources_index, identity_index)
        self.assertLess(identity_index, base_name_index)
        self.assertIn("workbench_acceptance is defined", acceptance_text)
        self.assertIn(
            "workbench_acceptance.get(workbench_acceptance_profile, none) is mapping",
            acceptance_text,
        )
        self.assertNotIn(
            "workbench_acceptance[workbench_acceptance_profile]", acceptance_text
        )

        storage_tasks = load_yaml(
            RUNBOOK_DIRECTORY / "tasks" / "incus-storage.yml"
        )
        storage_text = (
            RUNBOOK_DIRECTORY / "tasks" / "incus-storage.yml"
        ).read_text(encoding="utf-8")
        storage_names = [task["name"] for task in storage_tasks]
        storage_root_index = storage_names.index(
            "Require the dedicated Incus storage contract root"
        )
        storage_resolution_index = storage_names.index(
            "Resolve the Incus storage pool that owns the declared device"
        )
        storage_declaration_index = storage_names.index(
            "Validate the dedicated Incus logical-volume declaration"
        )
        storage_pool_index = storage_names.index(
            "Require one safe Incus storage-pool declaration"
        )
        storage_root = storage_tasks[0]["ansible.builtin.assert"]["that"]
        storage_declaration = storage_tasks[storage_declaration_index][
            "ansible.builtin.assert"
        ]["that"]

        self.assertLess(storage_root_index, storage_resolution_index)
        self.assertLess(storage_resolution_index, storage_declaration_index)
        self.assertLess(storage_declaration_index, storage_pool_index)
        self.assertIn("workbench_incus_storage is defined", storage_root)
        self.assertIn(
            "workbench_incus_storage | default({}) is mapping", storage_root
        )
        self.assertIn(
            "workbench_incus_declared_storage_pools | length == 1",
            storage_declaration,
        )
        self.assertIn("volatile.initial_source", storage_text)
        for task in storage_tasks[:storage_pool_index]:
            self.assertNotIn(
                "workbench_incus_declared_storage_pools[0]", repr(task)
            )

    def test_cleanup_is_bound_to_exact_owner_profile_and_run_id(self):
        cleanup = (RUNBOOK_DIRECTORY / "tasks" / "acceptance-cleanup.yml").read_text(
            encoding="utf-8"
        )
        for guard in (
            "user.lit.managed_by",
            "user.lit.acceptance_profile",
            "user.lit.run_id",
            "workbench_acceptance_instance_name",
            "workbench_acceptance.incus.cleanup.managed_name_prefix",
            "modulix-automation",
        ):
            self.assertIn(guard, cleanup)
        self.assertNotIn("maximum_age_hours", cleanup)

    def test_heavy_and_application_profiles_are_real_and_pinned(self):
        heavy = (RUNBOOK_DIRECTORY / "tasks" / "acceptance-heavy.yml").read_text(
            encoding="utf-8"
        )
        heavy_guest = (
            RUNBOOK_DIRECTORY / "tasks" / "acceptance-heavy-guest.yml"
        ).read_text(encoding="utf-8")
        application = (
            RUNBOOK_DIRECTORY / "tasks" / "acceptance-contract.yml"
        ).read_text(encoding="utf-8")
        application_script = (
            RUNBOOK_DIRECTORY / "files" / "workbench-application-acceptance.sh"
        ).read_text(encoding="utf-8")

        self.assertIn("workbench_acceptance_instance_names", heavy)
        self.assertIn("workbench-heavy-container.sh", heavy)
        self.assertIn("workbench-heavy-guest.sh", heavy)
        self.assertIn(
            "guest-{{ workbench_heavy_guest_sequence }}-first.raw.log", heavy_guest
        )
        self.assertIn(
            "guest-{{ workbench_heavy_guest_sequence }}-second.raw.log", heavy_guest
        )
        self.assertIn("is match('^[0-9a-f]{40}$')", application)
        self.assertIn(
            "https://github.com/lightning-it/ansible-collection-ubuntu.git",
            application,
        )
        self.assertIn("WUNDER_DEVTOOLS_STRICT=1", application_script)
        self.assertIn("scripts/devtools-collection-smoke.sh", application_script)
        self.assertIn("scripts/devtools-molecule.sh", application_script)

    def test_secret_scanner_fails_without_returning_secret_values(self):
        scanner = (
            RUNBOOK_DIRECTORY / "files" / "workbench-secret-scan.py"
        )
        fake_token = "ghp_" + ("A" * 30)
        with tempfile.TemporaryDirectory() as temporary_directory:
            fixture = Path(temporary_directory) / "evidence.log"
            fixture.write_text(f"token={fake_token}\n", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(scanner), str(fixture)],
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertEqual(result.returncode, 1)
        self.assertNotIn(fake_token, result.stdout)
        report = json.loads(result.stdout)
        self.assertEqual(report["status"], "failed")
        self.assertIn(
            "github-token",
            {finding["pattern"] for finding in report["findings"]},
        )

    def test_sanitizer_redacts_private_keys_and_generic_credentials(self):
        sanitizer = RUNBOOK_DIRECTORY / "files" / "workbench-sanitize-log.py"
        private_key = (
            "-----BEGIN PRIVATE KEY-----\n"
            "definitely-not-a-real-private-key\n"
            "-----END PRIVATE KEY-----"
        )
        credential = "password=" + ("s" * 24)
        with tempfile.TemporaryDirectory() as temporary_directory:
            source = Path(temporary_directory) / "source.log"
            destination = Path(temporary_directory) / "sanitized.log"
            source.write_text(f"{private_key}\n{credential}\n", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(sanitizer), str(source), str(destination)],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0)
            sanitized = destination.read_text(encoding="utf-8")

        self.assertNotIn("definitely-not-a-real-private-key", sanitized)
        self.assertNotIn("s" * 24, sanitized)
        self.assertIn("<REDACTED_PRIVATE_KEY>", sanitized)
        self.assertIn("<REDACTED_CREDENTIAL>", sanitized)


if __name__ == "__main__":
    unittest.main()
