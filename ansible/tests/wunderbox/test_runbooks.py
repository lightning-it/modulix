"""Static fail-closed guards for the Wunderbox orchestration runbooks."""

from collections.abc import Mapping
from pathlib import Path
import unittest

import yaml


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
RUNBOOK_DIRECTORY = (
    REPOSITORY_ROOT / "ansible" / "runbooks" / "50-applications" / "wunderbox"
)
GUARD_PATH = RUNBOOK_DIRECTORY / "tasks" / "orchestration-guard.yml"


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


class WunderboxRunbookSafetyTests(unittest.TestCase):
    """Keep target, approval, preflight, and retirement guards reviewable."""

    def test_all_public_runbooks_are_single_host_fail_closed(self):
        for name in ("05-prepare.yml", "07-preflight.yml", "10-deploy.yml", "20-ops.yml"):
            with self.subTest(runbook=name):
                plays = load_yaml(RUNBOOK_DIRECTORY / name)
                play = plays[-1]
                self.assertEqual(play["hosts"], "wunderboxes")
                self.assertEqual(play["serial"], 1)
                self.assertIs(play["any_errors_fatal"], True)
                self.assertIs(play["gather_facts"], True)

                guard_import = play["pre_tasks"][0]
                self.assertEqual(
                    guard_import["ansible.builtin.import_tasks"],
                    "tasks/orchestration-guard.yml",
                )
                self.assertIn("always", guard_import["tags"])

    def test_target_guard_requires_limit_inventory_request_and_host_facts(self):
        guard = GUARD_PATH.read_text(encoding="utf-8")

        for condition in (
            "ansible_limit is defined",
            "ansible_limit | string | trim == inventory_hostname",
            "ansible_play_hosts_all | length == 1",
            "ansible_play_hosts_all == [inventory_hostname]",
            "inventory_hostname == wunderbox_orchestration.target.fqdn",
            "wunderbox_request_target.id == wunderbox_orchestration.target.id",
            "wunderbox_request_target.fqdn == wunderbox_orchestration.target.fqdn",
            "wunderbox_request_target.ipv4 == wunderbox_orchestration.target.ipv4",
            "wunderbox_request_target.provider_id",
            "== wunderbox_orchestration.target.provider_id",
            "ansible_facts.get('fqdn', '') == wunderbox_orchestration.target.fqdn",
            "ansible_facts.get('default_ipv4', {}).get('address', '')",
            "ansible_host | string == wunderbox_orchestration.target.ipv4",
        ):
            with self.subTest(condition=condition):
                self.assertIn(condition, guard)

    def test_inventory_gate_cannot_supply_observed_runtime_approval(self):
        guard = GUARD_PATH.read_text(encoding="utf-8")

        self.assertIn("wunderbox_orchestration.gate.required_status == 'approved'", guard)
        self.assertIn("wunderbox_request_gate.observed_status", guard)
        self.assertIn("== wunderbox_orchestration.gate.required_status", guard)
        self.assertIn("wunderbox_request_gate.id == wunderbox_orchestration.gate.id", guard)
        self.assertNotIn("wunderbox_orchestration.gate.observed_status", guard)
        self.assertNotIn("wunderbox_orchestration.approval_tokens.token", guard)

        for phase in ("prepare", "deploy", "retirement"):
            with self.subTest(phase=phase):
                self.assertIn(f"approval_tokens.{phase}_sha256", guard)
                self.assertIn(f"wunderbox_{phase}_approval_token", guard)
                self.assertIn("hash('sha256')", guard)

    def test_productive_plays_default_to_a_read_only_end_play(self):
        for name in ("05-prepare.yml", "10-deploy.yml"):
            with self.subTest(runbook=name):
                play = load_yaml(RUNBOOK_DIRECTORY / name)[-1]
                self.assertIs(play["vars"]["_wunderbox_orchestration_mutating"], True)
                end_play = play["pre_tasks"][1]
                self.assertEqual(end_play["ansible.builtin.meta"], "end_play")
                self.assertIn("ansible_check_mode", end_play["when"])
                self.assertIn("default('plan') == 'plan'", end_play["when"])
                self.assertIn("always", end_play["tags"])

    def test_deploy_imports_unskippable_preflight_first(self):
        deploy = load_yaml(RUNBOOK_DIRECTORY / "10-deploy.yml")
        self.assertEqual(
            deploy[0]["ansible.builtin.import_playbook"], "07-preflight.yml"
        )

        preflight = load_yaml(RUNBOOK_DIRECTORY / "07-preflight.yml")[0]
        self.assertIs(preflight["vars"]["_wunderbox_orchestration_mutating"], False)
        for task in preflight["tasks"]:
            with self.subTest(task=task["name"]):
                self.assertIn("always", task["tags"])

    def test_preflight_and_guard_tasks_are_read_only(self):
        forbidden_modules = {
            "ansible.builtin.copy",
            "ansible.builtin.file",
            "ansible.builtin.include_role",
            "ansible.builtin.package",
            "ansible.builtin.service",
            "ansible.builtin.systemd_service",
            "ansible.builtin.template",
            "copy",
            "file",
            "include_role",
            "package",
            "service",
            "systemd_service",
            "template",
        }

        task_sets = (
            load_yaml(GUARD_PATH),
            load_yaml(RUNBOOK_DIRECTORY / "07-preflight.yml")[0]["tasks"],
        )
        for tasks in task_sets:
            for task in tasks:
                with self.subTest(task=task["name"]):
                    modules = normalized_task_module_names(task)
                    self.assertFalse(forbidden_modules.intersection(modules))
                    if "command" in modules:
                        self.assertIs(task.get("changed_when"), False)

    def test_retirement_requires_inventory_and_runtime_opt_in(self):
        deploy = load_yaml(RUNBOOK_DIRECTORY / "10-deploy.yml")[-1]
        retirement = next(
            task
            for task in deploy["tasks"]
            if task["name"] == "Retire Semaphore from Wunderbox when disabled"
        )
        conditions = "\n".join(retirement["when"])
        self.assertIn("wunderbox_retirement_requested", conditions)
        self.assertIn("semaphore_deploy", conditions)

        guard = GUARD_PATH.read_text(encoding="utf-8")
        self.assertIn("wunderbox_orchestration.retirement.allowed | bool", guard)
        self.assertIn("wunderbox_retirement_approval_token", guard)
        self.assertIn("or not ansible_check_mode", guard)

    def test_public_documentation_uses_only_sanitized_contract_values(self):
        readme = (RUNBOOK_DIRECTORY / "README.md").read_text(encoding="utf-8")
        self.assertIn("example.invalid", readme)
        self.assertIn("192.0.2.10", readme)
        self.assertIn("deploy_sha256: disabled", readme)

    def test_management_gateway_requires_vault_only_certificate_custody(self):
        runbook = load_yaml(RUNBOOK_DIRECTORY / "30-management-services.yml")[-1]
        source = (RUNBOOK_DIRECTORY / "30-management-services.yml").read_text(
            encoding="utf-8"
        )

        custody_guard = next(
            task
            for task in runbook["pre_tasks"]
            if task["name"] == "Enforce Vault-only public certificate custody"
        )
        assertions = custody_guard["ansible.builtin.assert"]["that"]
        normalized_assertions = {" ".join(assertion.split()) for assertion in assertions}
        self.assertIn(
            "nginx_config_tls_source | default('', true) == 'vault'",
            normalized_assertions,
        )
        self.assertIn(
            "not ( nginx_config_vault_allow_local_fallback | default(true) | bool )",
            normalized_assertions,
        )
        self.assertIn("vault_secret_bundle_generate_missing: false", source)
        for key in ("ca_certificate", "client_certificate", "private_key"):
            self.assertIn(f"name: {key}", source)

    def test_management_guards_default_missing_inventory_contracts(self):
        for name in (
            "30-management-services.yml",
            "31-management-backup.yml",
            "33-management-acceptance.yml",
        ):
            with self.subTest(runbook=name):
                source = (RUNBOOK_DIRECTORY / name).read_text(encoding="utf-8")
                self.assertIn(
                    "wunderbox_goal07_management_services | default({})", source
                )
                self.assertIn("'external_prerequisites'", source)
                self.assertIn("is mapping", source)
                self.assertNotIn(
                    "wunderbox_goal07_management_services.external_prerequisites.",
                    source,
                )
                if name == "31-management-backup.yml":
                    self.assertNotIn("wunderbox_management_backup.", source)
                    for key in (
                        "backup_dir",
                        "database",
                        "database_user",
                        "container",
                    ):
                        self.assertNotIn(
                            f"_management_backup_contract.{key}", source
                        )

    def test_management_acceptance_verifies_vault_tls_files_and_identity(self):
        source = (RUNBOOK_DIRECTORY / "33-management-acceptance.yml").read_text(
            encoding="utf-8"
        )

        self.assertIn("Vault-only private-key custody", source)
        self.assertIn("stat.mode == '0600'", source)
        self.assertIn("-checkend", source)
        self.assertIn("-checkhost", source)
        self.assertIn("Verify NGINX certificate and private key match", source)

    def test_management_acceptance_verifies_vault_mtls_files_and_identity(self):
        source = (RUNBOOK_DIRECTORY / "33-management-acceptance.yml").read_text(
            encoding="utf-8"
        )

        self.assertIn("Require Vault-backed Alloy mTLS files", source)
        self.assertIn("atlas_loki_mtls_material_present_in_vault", source)
        self.assertIn("Verify Alloy client certificate against its Vault CA bundle", source)
        self.assertIn("Verify Alloy client certificate and private key match", source)


if __name__ == "__main__":
    unittest.main()
