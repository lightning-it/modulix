"""Static tests for the Wunderbox Recorder-v3 execution binding.

These tests do not invoke Ansible, a provider, an inventory plugin, or a host.
"""

from __future__ import annotations

import argparse
import importlib.util
import ipaddress
import json
import re
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "policies" / "wunderbox" / "root-of-trust-policy.json"
TEMPLATE_PATH = ROOT / "policies" / "wunderbox" / "gate-manifest.template.json"
TRUST_TEMPLATE_PATH = ROOT / "policies" / "wunderbox" / "controller-trust.template.json"
RUNTIME_TEMPLATE_PATH = (
    ROOT / "policies" / "wunderbox" / "runtime-attestation.template.json"
)
ANCHOR_TEMPLATE_PATH = (
    ROOT / "policies" / "wunderbox" / "execution-anchor-acceptance.template.json"
)
ADAPTER_PATH = ROOT / "scripts" / "wbx-governed-exec.py"
SPEC = importlib.util.spec_from_file_location("wbx_governed_exec", ADAPTER_PATH)
assert SPEC and SPEC.loader
ADAPTER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ADAPTER)
RENDERER_PATH = ROOT / "scripts" / "render-wbx-gate-manifest-template.py"
RENDERER_SPEC = importlib.util.spec_from_file_location(
    "render_wbx_gate_manifest", RENDERER_PATH
)
assert RENDERER_SPEC and RENDERER_SPEC.loader
RENDERER = importlib.util.module_from_spec(RENDERER_SPEC)
RENDERER_SPEC.loader.exec_module(RENDERER)

POLICY_KEYS = {
    "schema_version",
    "policy_id",
    "required_repositories",
    "required_collections",
    "collection_repositories",
    "target_contract",
    "projection_contract",
    "actions",
}
RUNTIME_KEYS = {
    "toolbox_image",
    "run_ee_image",
    "attestation_path",
    "attestation_sha256",
    "attestation_signature_path",
}
AUTHORIZATION_BASE_KEYS = {
    "status",
    "approval_reference",
    "approval_sha256",
    "not_before_utc",
    "expires_utc",
    "execution_approval",
    "consumer_approval_contracts",
}
SIGNED_APPROVAL_KEYS = {
    "schema_version",
    "execution_id",
    "commit_shas",
    "nonce",
    "issued_at",
    "expires_at",
    "replay_directory",
    "signature",
}


class WunderboxPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
        cls.template = json.loads(TEMPLATE_PATH.read_text(encoding="utf-8"))
        cls.trust_template = json.loads(TRUST_TEMPLATE_PATH.read_text(encoding="utf-8"))
        cls.runtime_template = json.loads(
            RUNTIME_TEMPLATE_PATH.read_text(encoding="utf-8")
        )
        cls.anchor_template = json.loads(
            ANCHOR_TEMPLATE_PATH.read_text(encoding="utf-8")
        )
        cls.rendered = RENDERER.render()

    def test_policy_is_exact_recorder_v3_schema(self):
        self.assertEqual(set(self.policy), POLICY_KEYS)
        self.assertEqual(self.policy["schema_version"], 2)
        self.assertEqual(self.policy["policy_id"], "wunderbox-root-of-trust-v3")
        self.assertNotIn("signing", self.policy)
        self.assertEqual(
            self.policy["collection_repositories"],
            {"foundational": "foundational", "ubuntu": "ubuntu"},
        )
        self.assertEqual(
            set(self.policy["projection_contract"]),
            {"repository", "path", "sha256"},
        )
        self.assertEqual(self.policy["projection_contract"]["repository"], "inventory")
        self.assertEqual(
            self.policy["projection_contract"]["path"],
            "contracts/inventory-projection.json",
        )
        self.assertRegex(
            self.policy["projection_contract"]["sha256"], r"^[0-9a-f]{64}$"
        )

    def test_manifest_template_uses_exact_recorder_v2_runtime_schema(self):
        self.assertEqual(self.template["schema_version"], 2)
        self.assertEqual(set(self.template["runtime"]), RUNTIME_KEYS)
        self.assertNotIn("collections", self.template["runtime"])
        for field in ("attestation_path", "attestation_signature_path"):
            self.assertTrue(self.template["runtime"][field].startswith("/"))
        self.assertEqual(
            set(self.template["controller"]["ssh"]),
            {
                "source_directory",
                "private_key_name",
                "private_key_sha256",
                "known_hosts_name",
                "known_hosts_sha256",
            },
        )

    def test_external_trust_templates_are_exact_and_nonaccepted(self):
        self.assertEqual(
            set(self.trust_template),
            {
                "schema_version",
                "policy",
                "execution_anchor",
                "replay_broker",
                "process_supervisor",
                "container_engine",
                "manifest_signature",
                "runtime_attestation_signature",
                "approval_authority",
            },
        )
        self.assertEqual(
            self.trust_template["replay_broker"]["kind"],
            "root-brokered-append-only-v1",
        )
        self.assertEqual(
            self.trust_template["process_supervisor"]["kind"],
            "root-brokered-process-domain-v1",
        )
        self.assertEqual(self.anchor_template["status"], "NOT_ACCEPTED")
        self.assertFalse(self.anchor_template["negative_replay_test"])
        for role in ("toolbox", "run_ee"):
            self.assertEqual(
                self.runtime_template[role]["loader"],
                {
                    "collection_paths": [
                        "/usr/share/ansible/collections",
                        "/usr/share/automation-controller/collections",
                    ],
                    "scan_sys_path": False,
                },
            )

    def test_action_and_attempt_are_the_only_execution_selectors(self):
        option_strings = {
            option
            for action in ADAPTER.build_parser()._actions
            for option in action.option_strings
        }
        self.assertIn("--action-id", option_strings)
        self.assertIn("--attempt", option_strings)
        for forbidden in (
            "--policy",
            "--allowed-signers",
            "--target",
            "--inventory",
            "--playbook",
            "--gate",
            "--impact",
            "--command",
            "--tags",
            "--execution-image",
        ):
            self.assertNotIn(forbidden, option_strings)

    def test_action_prefixes_are_unique_and_required_vars_are_bound(self):
        actions = self.policy["actions"]
        prefixes = [action["record_prefix"] for action in actions.values()]
        self.assertEqual(len(prefixes), len(set(prefixes)))
        for action in actions.values():
            required = set(action.get("required_extra_vars", []))
            self.assertEqual(required, set(action.get("extra_var_bindings", {})))

    def test_inventory_projection_pins_complete_firewall_and_ipv4_contract(self):
        self.assertEqual(
            len(
                self.policy["actions"]["target_inventory_projection"][
                    "projection_paths"
                ]
            ),
            54,
        )
        self.assertEqual(
            self.policy["actions"]["target_inventory_projection"]["projection_paths"],
            [
                "hostname_fqdn",
                "hostname_etc_hosts_ip",
                "hetzner_robot_server_number",
                "wunderbox_dns_identity.schema_version",
                "wunderbox_dns_identity.desired.public.fqdn",
                "wunderbox_dns_identity.desired.public.a_records",
                "wunderbox_dns_identity.desired.public.ptr_records",
                "wunderbox_dns_identity.desired.public.aaaa_records",
                "wunderbox_dns_identity.desired.public.cname_records",
                "wunderbox_dns_identity.desired.management.fqdn",
                "wunderbox_dns_identity.desired.management.a_records",
                "wunderbox_dns_identity.desired.management.aaaa_records",
                "wunderbox_dns_identity.desired.management.cname_records",
                "wunderbox_dns_identity.verification.accepted",
                "wunderbox_dns_identity.verification.fresh_readback",
                "wunderbox_dns_identity.verification.evidence_reference",
                "hetzner_baremetal_root_of_trust.schema_version",
                "hetzner_baremetal_root_of_trust.selection_scope",
                "hetzner_baremetal_root_of_trust.inventory_hostname",
                "hetzner_baremetal_root_of_trust.controller_ipv4_cidr",
                "hetzner_baremetal_root_of_trust.server_lifecycle.status",
                "hetzner_baremetal_root_of_trust.server_lifecycle.cancelled",
                "wunderbox_inventory_contract.controller_access.management_services",
                "host_firewall_enabled",
                "host_firewall_action",
                "host_firewall_mode",
                "host_firewall_expected_inventory_hostname",
                "host_firewall_expected_public_ipv4",
                "host_firewall_expected_management_ipv4",
                "host_firewall_expected_public_ipv6",
                "host_firewall_expected_management_ipv6",
                "host_firewall_public_interface",
                "host_firewall_management_interface",
                "host_firewall_management_access",
                "host_firewall_tang_access",
                "host_firewall_controller_source_cidrs",
                "host_firewall_recovery_source_cidrs",
                "host_firewall_egress_policies",
                "host_firewall_egress_policy",
                "host_firewall_provider_ipv6_filter_enabled",
                "host_firewall_provider_ipv6_filter_evidence_reference",
                "hetzner_baremetal_robot_firewall_bootstrap_input_rules",
                "hetzner_baremetal_robot_firewall_hardened_input_rules",
                "hetzner_baremetal_robot_firewall_deferred_tang_input_rules",
                "hetzner_installimage_layout.ipv4_only",
                "ubtu24cis_ipv4_required",
                "ubtu24cis_ipv6_required",
                "ubtu24cis_ipv6_disable",
                "netplan_ethernets",
                "netplan_vlans",
                "wunderbox_inventory_contract.ipv4_only_baseline",
                "hetzner_baremetal_robot_firewall.enabled",
                "hetzner_baremetal_robot_firewall.admin_ipv4",
                "hetzner_baremetal_robot_firewall.filter_ipv6",
            ],
        )

    def test_known_side_effecting_actions_are_not_classified_as_read_only(self):
        expected = {
            "prepare_installimage_plan": "security_relevant",
            "installimage_plan": "security_relevant",
            "cis_audit": "security_relevant",
            "vault_plan": "security_relevant",
            "first_encrypted_boot": "availability",
            "bootstrap_unlock": "recovery",
            "first_boot_reconnect": "security_relevant",
            "installed_acceptance": "availability",
        }
        for action_id, impact in expected.items():
            self.assertEqual(self.policy["actions"][action_id]["impact"], impact)

    def test_live_actions_cannot_run_under_safety_hold(self):
        for action in self.policy["actions"].values():
            if action["gate"] == "WBX-G3":
                self.assertFalse(action.get("allowed_under_safety_hold", False))

    def test_exactly_seven_actions_are_fail_closed(self):
        expected = {
            "recovery_metadata_plan": (
                "blocked_missing_desktop_integrated_onepassword_controller_runtime"
            ),
            "prepare_installimage_plan": (
                "blocked_missing_desktop_integrated_onepassword_controller_runtime"
            ),
            "installimage_plan": (
                "blocked_missing_desktop_integrated_onepassword_controller_runtime"
            ),
            "prepare_installimage_apply": (
                "blocked_missing_desktop_integrated_onepassword_controller_runtime"
            ),
            "installimage_apply": (
                "dedicated_secret_safe_onepassword_installimage_orchestrator_missing"
            ),
            "first_encrypted_boot": (
                "blocked_missing_desktop_integrated_onepassword_controller_runtime"
            ),
            "bootstrap_unlock": (
                "blocked_missing_desktop_integrated_onepassword_controller_runtime"
            ),
        }
        blocked = {
            action_id: action["implementation_blocker"]
            for action_id, action in self.policy["actions"].items()
            if action.get("implementation_status") == "blocked"
        }
        self.assertEqual(blocked, expected)

    def test_every_persisted_callback_artifact_has_an_exact_typed_schema(self):
        expected_artifact_actions = {
            action_id
            for action_id, action in self.policy["actions"].items()
            if action.get("expected_artifact")
        }
        self.assertEqual(len(expected_artifact_actions), 5)
        for action_id in expected_artifact_actions:
            action = self.policy["actions"][action_id]
            schema = action["artifact_schema"]
            self.assertEqual(set(schema), {"schema_id", "fields"})
            self.assertEqual(
                set(schema["fields"]), set(action["artifact_projection_paths"])
            )
            for field in schema["fields"].values():
                self.assertIn("type", field)
                self.assertLessEqual(set(field), {"type", "binding", "allowed_values"})
        for action_id in (
            "installimage_plan",
            "installimage_apply",
            "first_encrypted_boot",
            "first_boot_reconnect",
            "vault_plan",
        ):
            self.assertEqual(
                self.policy["actions"][action_id]["artifact_schema"]["fields"][
                    "target"
                ]["binding"],
                "fqdn",
            )

    def test_renderer_produces_exact_per_action_authorizations(self):
        self.assertEqual(
            set(self.rendered["authorizations"]), set(self.policy["actions"])
        )
        self.assertEqual(
            {entry["status"] for entry in self.rendered["authorizations"].values()},
            {"NOT_APPROVED"},
        )
        for action_id, action in self.policy["actions"].items():
            authorization = self.rendered["authorizations"][action_id]
            authorization_fields = {
                binding["field"]
                for binding in action.get("extra_var_bindings", {}).values()
                if binding.get("kind")
                in {"authorization_field", "target_and_authorization_confirmation"}
            }
            expected_keys = (
                AUTHORIZATION_BASE_KEYS
                | set(action.get("required_evidence_references", []))
                | authorization_fields
            )
            self.assertEqual(set(authorization), expected_keys)
            self.assertNotIn("implementation_status", authorization)
            self.assertNotIn("implementation_blocker", authorization)

    def test_every_action_has_a_distinct_execution_approval(self):
        approvals = [
            authorization["execution_approval"]
            for authorization in self.rendered["authorizations"].values()
        ]
        self.assertEqual(len(approvals), 34)
        self.assertEqual(len({approval["nonce"] for approval in approvals}), 34)
        self.assertEqual(len({approval["execution_id"] for approval in approvals}), 34)
        for approval in approvals:
            self.assertEqual(set(approval), SIGNED_APPROVAL_KEYS)
            self.assertEqual(approval["schema_version"], 1)
            self.assertEqual(
                set(approval["commit_shas"]),
                set(self.policy["required_repositories"]),
            )
            self.assertEqual(len(approval["nonce"]), 64)

    def test_signed_consumer_has_a_separate_exact_contract(self):
        for action_id, action in self.policy["actions"].items():
            expected_variables = {
                variable
                for variable, binding in action.get("extra_var_bindings", {}).items()
                if binding.get("kind") == "signed_approval_transport"
            }
            contracts = self.rendered["authorizations"][action_id][
                "consumer_approval_contracts"
            ]
            self.assertEqual(set(contracts), expected_variables)
            for contract in contracts.values():
                self.assertEqual(set(contract), {"operation", "target", "binding"})
        unlock = self.rendered["authorizations"]["bootstrap_unlock"]
        consumer = unlock["consumer_approval_contracts"][
            "hetzner_bootstrap_unlock_approval"
        ]
        self.assertEqual(consumer["operation"], "unlock-luks-over-ssh-stdin")
        self.assertEqual(consumer["target"], "REPLACE_WITH_EXACT_TARGET_FQDN")
        self.assertNotIn("onepassword_approval", unlock)

    def test_policy_contains_no_concrete_environment_identity(self):
        def string_values(value):
            if isinstance(value, dict):
                for child in value.values():
                    yield from string_values(child)
            elif isinstance(value, list):
                for child in value:
                    yield from string_values(child)
            elif isinstance(value, str):
                yield value

        concrete_fqdn = re.compile(
            r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?"
            r"(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)+"
            r"\.[a-z]{2,63}$",
            re.IGNORECASE,
        )
        numbered_host = re.compile(
            r"^[a-z][a-z-]{2,}[0-9]{2}(?:\.[a-z0-9-]+)*$",
            re.IGNORECASE,
        )
        provider_identifier = re.compile(r"^[0-9]{6,12}$")

        for scalar in string_values(self.policy):
            self.assertIsNone(concrete_fqdn.fullmatch(scalar))
            self.assertIsNone(numbered_host.fullmatch(scalar))
            self.assertIsNone(provider_identifier.fullmatch(scalar))
            for token in re.split(r"[^0-9A-Fa-f:.]+", scalar):
                if not token or ("." not in token and ":" not in token):
                    continue
                try:
                    ipaddress.ip_address(token.strip("."))
                except ValueError:
                    continue
                self.fail(f"policy contains a concrete IP address in {scalar!r}")

    def test_manifest_template_is_deliberately_non_executable(self):
        self.assertEqual(self.template["manifest_status"], "TEMPLATE")
        self.assertTrue(self.template["safety_hold"])
        generic = self.template["authorizations"]["REPLACE_WITH_EACH_POLICY_ACTION_ID"]
        self.assertEqual(generic["status"], "NOT_APPROVED")
        self.assertNotIn(
            "BEGIN SSH SIGNATURE", generic["execution_approval"]["signature"]
        )

    def test_adapter_passes_only_manifest_and_fixed_repository_set(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            args = argparse.Namespace(
                inventory_repo=root / "inventory",
                foundational_repo=root / "foundational",
                ubuntu_repo=root / "ubuntu",
                validation_repo=root / "validation",
                operations_repo=root / "operations",
                gate_manifest=root / "manifest.json",
                gate_signature=root / "manifest.sig",
                action_id="target_inventory_projection",
                attempt=1,
                operator="operator",
                reviewer="reviewer",
                purpose="test",
                jira="TEST-1",
                extra_vars=None,
                evidence_dir=root / "evidence",
            )
            command = ADAPTER.build_core_command(args)
        self.assertEqual(command[0], str(ADAPTER.ROOT_OWNED_LAUNCHER))
        self.assertNotIn("governed-ansible-exec.py", command[:2])
        repo_values = [
            command[index + 1]
            for index, value in enumerate(command)
            if value == "--repo"
        ]
        self.assertEqual(
            {value.split("=", 1)[0] for value in repo_values},
            {
                "automation",
                "inventory",
                "foundational",
                "ubuntu",
                "validation",
                "operations",
            },
        )
        self.assertIn(f"automation={ADAPTER.REPOSITORY_ROOT}", repo_values)
        self.assertIn(f"validation={(root / 'validation').resolve()}", repo_values)
        for forbidden in (
            "--policy",
            "--allowed-signers",
            "--target",
            "--playbook",
        ):
            self.assertNotIn(forbidden, command)


if __name__ == "__main__":
    unittest.main()
