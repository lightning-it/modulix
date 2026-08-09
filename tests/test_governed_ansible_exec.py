"""Unit tests for the generic governed Ansible execution recorder.

No test invokes Ansible, a provider, an inventory plugin, or a target host.
"""

from __future__ import annotations

import datetime as dt
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "governed-ansible-exec.py"
SPEC = importlib.util.spec_from_file_location("governed_ansible_exec", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def sample_policy() -> dict:
    return {
        "schema_version": 1,
        "required_repositories": [
            "automation",
            "inventory",
            "foundational",
            "ubuntu",
            "validation",
            "operations",
        ],
        "required_collections": ["foundational", "ubuntu"],
        "signing": {"identity": "approver", "namespace": "lit-test"},
        "target_contract": {
            "target_id_pattern": "^TEST-TARGET$",
            "fqdn_pattern": "^host\\.example\\.test$",
        },
        "actions": {
            "target_plan": {
                "record_prefix": "321",
                "gate": "WBX-G3",
                "prerequisite_gates": ["WBX-G0", "WBX-G1", "WBX-G2"],
                "impact": "security_relevant",
                "mode": "playbook",
                "playbook": "runbooks/example.yml",
                "allowed_extra_vars": ["action"],
                "required_extra_vars": ["action"],
                "extra_var_bindings": {
                    "action": {"kind": "literal", "value": "plan"}
                },
                "required_evidence_references": ["rollback_ref"],
            }
        },
    }


def sample_manifest(policy_digest: str) -> dict:
    commit = "a" * 40
    repositories = {
        name: {"branch": "codex/test", "commit": commit}
        for name in sample_policy()["required_repositories"]
    }
    return {
        "schema_version": 1,
        "manifest_status": "APPROVED",
        "policy_sha256": policy_digest,
        "safety_hold": False,
        "target": {
            "target_id": "TEST-TARGET",
            "fqdn": "host.example.test",
            "public_ipv4": "192.0.2.10",
            "provider_id": "test-provider-1",
        },
        "controller": {
            "device_id": "test-controller",
            "source_cidr": "192.0.2.20/32",
            "ssh": {
                "source_directory": "/private/example",
                "private_key_name": "id_test",
                "private_key_sha256": "9" * 64,
            },
        },
        "runtime": {
            "toolbox_image": "registry.example/toolbox@sha256:" + "b" * 64,
            "run_ee_image": "registry.example/ee@sha256:" + "c" * 64,
            "attestation_sha256": "d" * 64,
            "collections": {
                "foundational": {"version": "1.0.0", "source_commit": "1" * 40},
                "ubuntu": {"version": "1.0.0", "source_commit": "2" * 40},
            },
        },
        "gates": {
            "WBX-G0": "ACCEPTED",
            "WBX-G1": "ACCEPTED",
            "WBX-G2": "ACCEPTED",
            "WBX-G3": "IN_PROGRESS",
            "WBX-G4": "NOT_STARTED",
            "WBX-G5": "NOT_STARTED",
        },
        "repositories": repositories,
        "authorizations": {
            "target_plan": {
                "status": "APPROVED",
                "approval_reference": "TEST-1/comment-1",
                "approval_sha256": "e" * 64,
                "not_before_utc": "2026-08-09T00:00:00Z",
                "expires_utc": "2026-08-10T00:00:00Z",
                "rollback_ref": "TEST-1#rollback",
            }
        },
    }


class GovernedRecorderTests(unittest.TestCase):
    def test_policy_rejects_duplicate_record_prefix(self):
        policy = sample_policy()
        policy["actions"]["second"] = {
            **policy["actions"]["target_plan"],
            "record_prefix": "321",
        }
        with self.assertRaises(MODULE.ContractError):
            MODULE.validate_policy(policy)

    def test_manifest_requires_digest_pinned_images_and_exact_controller_32(self):
        policy = sample_policy()
        payload = json.dumps(policy).encode()
        digest = MODULE.sha256_bytes(payload)
        manifest = sample_manifest(digest)
        MODULE.validate_manifest(manifest, policy, digest)

        manifest["runtime"]["run_ee_image"] = "registry.example/ee:latest"
        with self.assertRaises(MODULE.ContractError):
            MODULE.validate_manifest(manifest, policy, digest)

        manifest = sample_manifest(digest)
        manifest["controller"]["source_cidr"] = "192.0.2.0/24"
        with self.assertRaises(MODULE.ContractError):
            MODULE.validate_manifest(manifest, policy, digest)

    def test_gate_and_safety_hold_are_enforced(self):
        policy = sample_policy()
        action = policy["actions"]["target_plan"]
        digest = "f" * 64
        manifest = sample_manifest(digest)
        now = dt.datetime(2026, 8, 9, 12, tzinfo=dt.timezone.utc)
        authorization = MODULE.validate_authorization(
            "target_plan", action, manifest, now
        )
        self.assertEqual(authorization["status"], "APPROVED")

        manifest["safety_hold"] = True
        with self.assertRaises(MODULE.ContractError):
            MODULE.validate_authorization("target_plan", action, manifest, now)

    def test_blocked_implementation_cannot_be_authorized(self):
        policy = sample_policy()
        action = policy["actions"]["target_plan"]
        action["implementation_status"] = "blocked"
        action["implementation_blocker"] = "dedicated_consumer_missing"
        MODULE.validate_policy(policy)

        manifest = sample_manifest("f" * 64)
        now = dt.datetime(2026, 8, 9, 12, tzinfo=dt.timezone.utc)
        with self.assertRaisesRegex(
            MODULE.ContractError, "implementation is blocked"
        ):
            MODULE.validate_authorization("target_plan", action, manifest, now)

        action.pop("implementation_blocker")
        with self.assertRaises(MODULE.ContractError):
            MODULE.validate_policy(policy)

        manifest["safety_hold"] = False
        manifest["gates"]["WBX-G2"] = "IN_PROGRESS"
        with self.assertRaises(MODULE.ContractError):
            MODULE.validate_authorization("target_plan", action, manifest, now)

    def test_extra_vars_require_private_exact_json_allowlist(self):
        action = sample_policy()["actions"]["target_plan"]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "vars.json"
            path.write_text('{"action":"plan"}\n', encoding="utf-8")
            path.chmod(0o600)
            parsed, digest, resolved = MODULE.validate_extra_vars(path, action)
            self.assertEqual(parsed, {"action": "plan"})
            self.assertEqual(len(digest or ""), 64)
            self.assertEqual(resolved, path.resolve())

            path.write_text('{"ansible_host":"other"}\n', encoding="utf-8")
            with self.assertRaises(MODULE.ContractError):
                MODULE.validate_extra_vars(path, {
                    **action,
                    "allowed_extra_vars": ["ansible_host"],
                    "required_extra_vars": ["ansible_host"],
                })

    def test_extra_vars_reject_secret_bearing_keys(self):
        action = {
            **sample_policy()["actions"]["target_plan"],
            "allowed_extra_vars": ["api_token"],
            "required_extra_vars": ["api_token"],
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "vars.json"
            path.write_text('{"api_token":"exposed"}\n', encoding="utf-8")
            path.chmod(0o600)
            with self.assertRaises(MODULE.ContractError):
                MODULE.validate_extra_vars(path, action)

    def test_only_signed_approval_signature_may_be_multiline(self):
        action = {
            **sample_policy()["actions"]["target_plan"],
            "allowed_extra_vars": ["note"],
            "required_extra_vars": ["note"],
            "extra_var_bindings": {
                "note": {"kind": "literal", "value": "line-one\nline-two"}
            },
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "vars.json"
            path.write_text(
                json.dumps({"note": "line-one\nline-two"}), encoding="utf-8"
            )
            path.chmod(0o600)
            with self.assertRaisesRegex(MODULE.ContractError, "single-line"):
                MODULE.validate_extra_vars(path, action)

    def test_secret_named_metadata_requires_exact_nonsecret_value(self):
        action = {
            **sample_policy()["actions"]["target_plan"],
            "allowed_extra_vars": ["onepassword_password_action"],
            "required_extra_vars": ["onepassword_password_action"],
            "nonsecret_secret_named_vars": ["onepassword_password_action"],
            "extra_var_allowed_values": {
                "onepassword_password_action": ["plan"]
            },
            "extra_var_bindings": {
                "onepassword_password_action": {
                    "kind": "literal",
                    "value": "plan",
                }
            },
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "vars.json"
            path.write_text(
                '{"onepassword_password_action":"plan"}\n', encoding="utf-8"
            )
            path.chmod(0o600)
            parsed, _digest, _resolved = MODULE.validate_extra_vars(path, action)
            self.assertEqual(parsed["onepassword_password_action"], "plan")
            path.write_text(
                '{"onepassword_password_action":"read"}\n', encoding="utf-8"
            )
            with self.assertRaises(MODULE.ContractError):
                MODULE.validate_extra_vars(path, action)

    def test_target_and_approval_confirmation_is_exactly_bound(self):
        action = {
            **sample_policy()["actions"]["target_plan"],
            "allowed_extra_vars": ["confirmation", "plan_sha256"],
            "required_extra_vars": ["confirmation", "plan_sha256"],
            "extra_var_bindings": {
                "confirmation": {
                    "kind": "target_and_authorization_confirmation",
                    "prefix": "ERASE",
                    "field": "approved_plan_sha256",
                },
                "plan_sha256": {
                    "kind": "authorization_field",
                    "field": "approved_plan_sha256",
                },
            },
        }
        manifest = sample_manifest("f" * 64)
        authorization = {"approved_plan_sha256": "a" * 64}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "vars.json"
            path.write_text(
                json.dumps(
                    {
                        "confirmation": "ERASE:host.example.test:" + "a" * 64,
                        "plan_sha256": "a" * 64,
                    }
                ),
                encoding="utf-8",
            )
            path.chmod(0o600)
            MODULE.validate_extra_vars(path, action, manifest, authorization)
            parsed = json.loads(path.read_text(encoding="utf-8"))
            parsed["confirmation"] = "ERASE:other.example.test:" + "a" * 64
            path.write_text(json.dumps(parsed), encoding="utf-8")
            with self.assertRaises(MODULE.ContractError):
                MODULE.validate_extra_vars(path, action, manifest, authorization)

    def test_signed_plugin_approval_is_manifest_bound_and_nonce_is_global(self):
        execution_id = "WBX-EXE-341-A001"
        policy = sample_policy()
        action = {
            **policy["actions"]["target_plan"],
            "allowed_extra_vars": ["onepassword_approval"],
            "required_extra_vars": ["onepassword_approval"],
            "nonsecret_secret_named_vars": ["onepassword_approval"],
            "extra_var_bindings": {
                "onepassword_approval": {
                    "kind": "signed_approval_transport",
                    "field": "onepassword_approval",
                }
            },
        }
        policy["actions"]["target_plan"] = action
        MODULE.validate_policy(policy)
        manifest = sample_manifest("f" * 64)
        with tempfile.TemporaryDirectory() as directory:
            replay = Path(directory) / "replay"
            replay.mkdir(mode=0o700)
            approval = {
                "schema_version": 1,
                "execution_id": execution_id,
                "commit_shas": {
                    name: repository["commit"]
                    for name, repository in manifest["repositories"].items()
                },
                "nonce": "1" * 64,
                "issued_at": "2026-08-09T00:01:00Z",
                "expires_at": "2026-08-09T00:11:00Z",
                "replay_directory": str(replay.resolve()),
                "signature": (
                    "-----BEGIN SSH SIGNATURE-----\n"
                    "U0lHTkFUVVJF\n"
                    "-----END SSH SIGNATURE-----\n"
                ),
            }
            authorization = manifest["authorizations"]["target_plan"]
            authorization["onepassword_approval"] = approval
            path = Path(directory) / "vars.json"
            path.write_text(
                json.dumps({"onepassword_approval": approval}), encoding="utf-8"
            )
            path.chmod(0o600)
            parsed, _digest, _source = MODULE.validate_extra_vars(
                path, action, manifest, authorization, execution_id
            )
            claims = MODULE.claim_signed_approval_transports(
                parsed, action, execution_id
            )
            self.assertEqual(len(claims), 1)
            self.assertEqual(claims[0]["variable"], "onepassword_approval")
            with self.assertRaisesRegex(MODULE.ContractError, "already been consumed"):
                MODULE.claim_signed_approval_transports(parsed, action, execution_id)

            approval["signature"] = "not-an-armored-signature"
            path.write_text(
                json.dumps({"onepassword_approval": approval}), encoding="utf-8"
            )
            authorization["onepassword_approval"] = approval
            with self.assertRaisesRegex(MODULE.ContractError, "signature is malformed"):
                MODULE.validate_extra_vars(
                    path, action, manifest, authorization, execution_id
                )

            approval["signature"] = (
                "-----BEGIN SSH SIGNATURE-----\n"
                "U0lHTkFUVVJF\n"
                "-----END SSH SIGNATURE-----\n"
            )
            approval["execution_id"] = "WBX-EXE-341-A002"
            path.write_text(
                json.dumps({"onepassword_approval": approval}), encoding="utf-8"
            )
            authorization["onepassword_approval"] = approval
            with self.assertRaisesRegex(MODULE.ContractError, "not bound to this attempt"):
                MODULE.validate_extra_vars(
                    path, action, manifest, authorization, execution_id
                )

    def test_started_journal_atomically_reserves_attempt(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "attempt.started.json"
            digest = MODULE.write_new_json(path, {"status": "STARTED"})
            self.assertEqual(len(digest), 64)
            self.assertEqual(path.stat().st_mode & 0o777, 0o400)
            with self.assertRaises(FileExistsError):
                MODULE.write_new_json(path, {"status": "STARTED"})

    def test_governed_recap_requires_only_exact_target(self):
        event = {
            "schema_version": 1,
            "type": "recap",
            "action_id": "target_plan",
            "hosts": {
                "host.example.test": {
                    "ok": 4,
                    "changed": 0,
                    "unreachable": 0,
                    "failed": 0,
                    "skipped": 1,
                    "rescued": 0,
                    "ignored": 0,
                }
            },
        }
        output = (MODULE.EVENT_PREFIX + json.dumps(event) + "\n").encode()
        recaps, artifacts = MODULE.parse_events(output, "target_plan")
        self.assertFalse(artifacts)
        counts = MODULE.validate_target_recap(
            recaps,
            "host.example.test",
            sample_policy()["actions"]["target_plan"],
        )
        self.assertEqual(counts["ok"], 4)

        event["hosts"]["other.example.test"] = event["hosts"][
            "host.example.test"
        ]
        output = (MODULE.EVENT_PREFIX + json.dumps(event) + "\n").encode()
        recaps, _ = MODULE.parse_events(output, "target_plan")
        with self.assertRaises(MODULE.ContractError):
            MODULE.validate_target_recap(
                recaps,
                "host.example.test",
                sample_policy()["actions"]["target_plan"],
            )

    def test_projection_retains_only_allowlisted_nonsecret_fields(self):
        source = {
            "identity": {"fqdn": "host.example.test", "provider_id": "123"},
            "password": "must-not-persist",
        }
        projection = MODULE.select_projection(
            source, ["identity.fqdn", "identity.provider_id"]
        )
        self.assertEqual(set(projection), {"identity"})
        self.assertNotIn("password", json.dumps(projection))
        with self.assertRaises(MODULE.ContractError):
            MODULE.select_projection(source, ["password"])

    def test_signature_verification_uses_fixed_identity_and_namespace(self):
        completed = subprocess.CompletedProcess([], 0, b"ok", b"")
        runner = mock.Mock(return_value=completed)
        with tempfile.TemporaryDirectory() as directory:
            signature = Path(directory) / "manifest.sig"
            signers = Path(directory) / "allowed_signers"
            signature.write_text("signature", encoding="utf-8")
            signers.write_text("approver ssh-ed25519 AAAA", encoding="utf-8")
            signature.chmod(0o400)
            signers.chmod(0o400)
            MODULE.verify_manifest_signature(
                b"manifest",
                signature,
                signers,
                "approver",
                "lit-test",
                runner=runner,
            )
        command = runner.call_args.args[0]
        self.assertIn("approver", command)
        self.assertIn("lit-test", command)

    def test_bounded_runner_uses_no_ansible_and_captures_hashes(self):
        result = MODULE.run_bounded(
            [sys.executable, "-c", "print('safe')"],
            {"PATH": os.environ.get("PATH", "")},
            ROOT,
            timeout_seconds=5,
            max_output_bytes=4096,
        )
        self.assertEqual(result["exit_code"], 0)
        self.assertEqual(result["stdout"], b"safe\n")
        self.assertEqual(len(result["stdout_sha256"]), 64)

    def test_environment_is_digest_pinned_and_secret_averse(self):
        manifest = sample_manifest("f" * 64)
        with mock.patch.dict(os.environ, {"PATH": "/usr/bin"}, clear=True):
            environment = MODULE.make_environment(
                manifest,
                "target_plan",
                {
                    **sample_policy()["actions"]["target_plan"],
                    "impact": "local_validation",
                },
            )
        self.assertEqual(environment["ANSIBLE_TOOLBOX_PULL_POLICY"], "never")
        self.assertIn("@sha256:", environment["ANSIBLE_TOOLBOX_RUN_EE_IMAGE"])
        self.assertNotIn("VAULT_TOKEN", environment)

    def test_live_environment_binds_one_owner_only_private_key_directory(self):
        manifest = sample_manifest("f" * 64)
        action = sample_policy()["actions"]["target_plan"]
        with tempfile.TemporaryDirectory() as directory:
            ssh_source = Path(directory) / "ssh"
            ssh_source.mkdir(mode=0o700)
            private_key = ssh_source / "id_test"
            private_key.write_bytes(b"test-private-key-material\n")
            private_key.chmod(0o600)
            manifest["controller"]["ssh"] = {
                "source_directory": str(ssh_source),
                "private_key_name": private_key.name,
                "private_key_sha256": MODULE.sha256_file(private_key),
            }
            with mock.patch.dict(os.environ, {"PATH": "/usr/bin"}, clear=True):
                environment = MODULE.make_environment(
                    manifest, "target_plan", action
                )
        self.assertEqual(environment["ANSIBLE_TOOLBOX_MOUNT_SSH"], "true")
        self.assertEqual(
            environment["ANSIBLE_TOOLBOX_SSH_SOURCE"], str(ssh_source.resolve())
        )

    def test_agent_bound_action_fails_before_start_without_socket(self):
        action = {
            **sample_policy()["actions"]["target_plan"],
            "requires_ssh_private_key": False,
            "requires_ssh_agent": True,
        }
        with mock.patch.dict(os.environ, {"PATH": "/usr/bin"}, clear=True):
            with self.assertRaises(MODULE.ContractError):
                MODULE.make_environment(sample_manifest("f" * 64), "target_plan", action)


if __name__ == "__main__":
    unittest.main()
