"""Unit tests for the generic governed Ansible execution recorder.

No test invokes Ansible, a provider, an inventory plugin, or a target host.
"""

from __future__ import annotations

import copy
import datetime as dt
import importlib.util
import json
import os
from pathlib import Path
import shutil
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


def sample_host_firewall_egress_policies() -> dict:
    def common_functions() -> dict:
        return {
            "dns_udp": {
                "enabled": True,
                "status": "approved",
                "protocol": "udp",
                "port": 53,
                "modes": ["bootstrap", "hardened"],
                "interface": "enp4s0",
                "destinations_ipv4": ["1.1.1.1/32", "8.8.8.8/32"],
                "destinations_ipv6": [],
                "declared_fqdns": [],
                "mtls_required": False,
                "residual": "",
            },
            "dns_tcp": {
                "enabled": True,
                "status": "approved",
                "protocol": "tcp",
                "port": 53,
                "modes": ["bootstrap", "hardened"],
                "interface": "enp4s0",
                "destinations_ipv4": ["1.1.1.1/32", "8.8.8.8/32"],
                "destinations_ipv6": [],
                "declared_fqdns": [],
                "mtls_required": False,
                "residual": "",
            },
            "ntp": {
                "enabled": True,
                "status": "transitional-port-only",
                "protocol": "udp",
                "port": 123,
                "modes": ["bootstrap", "hardened"],
                "interface": "enp4s0",
                "destinations_ipv4": ["0.0.0.0/0"],
                "destinations_ipv6": [],
                "declared_fqdns": [
                    "ntp1.hetzner.de",
                    "ntp2.hetzner.com",
                    "ntp3.hetzner.net",
                ],
                "mtls_required": False,
                "residual": (
                    "Destination restriction remains open until stable "
                    "resolver-bound NTP addresses exist."
                ),
            },
            "atlas_loki": {
                "enabled": True,
                "status": "approved",
                "protocol": "tcp",
                "port": 3100,
                "modes": ["bootstrap", "hardened"],
                "interface": "enp4s0.4091",
                "destinations_ipv4": ["10.10.30.24/32"],
                "destinations_ipv6": [],
                "declared_fqdns": [],
                "mtls_required": True,
                "residual": (
                    "mTLS identity and trust evidence are validated outside nftables."
                ),
            },
        }

    bootstrap_functions = common_functions()
    bootstrap_functions.update(
        {
            "bootstrap_https": {
                "enabled": True,
                "status": "temporary-maintenance",
                "protocol": "tcp",
                "port": 443,
                "modes": ["bootstrap"],
                "interface": "enp4s0",
                "destinations_ipv4": ["0.0.0.0/0"],
                "destinations_ipv6": [],
                "declared_fqdns": [],
                "mtls_required": False,
                "residual": (
                    "Temporary package bootstrap exception; productive "
                    "confirmation is prohibited."
                ),
            },
            "https_proxy": {
                "enabled": False,
                "status": "disabled-staged-transfer",
                "protocol": "tcp",
                "port": 3128,
                "modes": ["hardened"],
                "interface": "enp4s0.4091",
                "destinations_ipv4": [],
                "destinations_ipv6": [],
                "declared_fqdns": [
                    "mirror.hetzner.com",
                    "fsn1.your-objectstorage.com",
                    "bucket.fsn1.your-objectstorage.com",
                ],
                "mtls_required": False,
                "residual": (
                    "Controller-pull and staged transfer remain authoritative "
                    "while the management proxy is disabled."
                ),
            },
        }
    )
    hardened_functions = common_functions()
    hardened_functions.update(
        {
            "bootstrap_https": {
                "enabled": False,
                "status": "disabled-staged-transfer",
                "protocol": "tcp",
                "port": 443,
                "modes": ["bootstrap"],
                "interface": "enp4s0",
                "destinations_ipv4": [],
                "destinations_ipv6": [],
                "declared_fqdns": [],
                "mtls_required": False,
                "residual": "Bootstrap HTTPS is closed before productive confirmation.",
            },
            "https_proxy": {
                "enabled": False,
                "status": "disabled-staged-transfer",
                "protocol": "tcp",
                "port": 3128,
                "modes": ["hardened"],
                "interface": "enp4s0.4091",
                "destinations_ipv4": [],
                "destinations_ipv6": [],
                "declared_fqdns": [
                    "mirror.hetzner.com",
                    "fsn1.your-objectstorage.com",
                    "bucket.fsn1.your-objectstorage.com",
                ],
                "mtls_required": False,
                "residual": (
                    "Controller-pull and staged transfer remain authoritative "
                    "while the management proxy is disabled."
                ),
            },
        }
    )
    return {
        "bootstrap": {
            "schema": "lit.host_firewall.egress/v1",
            "status": "draft",
            "stance": "bootstrap-restricted",
            "ipv4_only": True,
            "functions": bootstrap_functions,
        },
        "hardened": {
            "schema": "lit.host_firewall.egress/v1",
            "status": "approved",
            "stance": "deny-by-default",
            "ipv4_only": True,
            "functions": hardened_functions,
        },
    }


def sample_policy() -> dict:
    return {
        "schema_version": 2,
        "policy_id": "wunderbox-test-policy",
        "required_repositories": [
            "automation",
            "inventory",
            "foundational",
            "ubuntu",
            "validation",
            "operations",
        ],
        "required_collections": ["foundational", "ubuntu"],
        "collection_repositories": {
            "foundational": "foundational",
            "ubuntu": "ubuntu",
        },
        "target_contract": {
            "target_id_pattern": "^TEST-TARGET$",
            "fqdn_pattern": "^host\\.example\\.test$",
        },
        "projection_contract": {
            "repository": "inventory",
            "path": "contracts/inventory-projection.json",
            "sha256": "0" * 64,
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
                "extra_var_bindings": {"action": {"kind": "literal", "value": "plan"}},
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
        "schema_version": 2,
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
                "known_hosts_name": "known_hosts_test",
                "known_hosts_sha256": "8" * 64,
            },
        },
        "runtime": {
            "toolbox_image": "registry.example/toolbox@sha256:" + "b" * 64,
            "run_ee_image": "registry.example/ee@sha256:" + "c" * 64,
            "attestation_path": "/private/runtime-attestation.json",
            "attestation_sha256": "d" * 64,
            "attestation_signature_path": "/private/runtime-attestation.json.sig",
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
                "execution_approval": {
                    "schema_version": 1,
                    "execution_id": "WBX-EXE-321-A001",
                    "commit_shas": {
                        name: repository["commit"]
                        for name, repository in repositories.items()
                    },
                    "nonce": "1" * 64,
                    "issued_at": "2026-08-09T00:01:00Z",
                    "expires_at": "2026-08-09T00:11:00Z",
                    "replay_directory": "/private/approval-ledger",
                    "signature": (
                        "-----BEGIN SSH SIGNATURE-----\n"
                        "U0lHTkFUVVJF\n"
                        "-----END SSH SIGNATURE-----\n"
                    ),
                },
                "consumer_approval_contracts": {},
                "rollback_ref": "TEST-1#rollback",
            }
        },
    }


def sample_projection_contract(document: dict, target: dict, controller: dict) -> dict:
    policies = document["host_firewall_egress_policies"]
    return {
        "schema_version": 1,
        "contract_id": "test-inventory-projection-v1",
        "target": copy.deepcopy(target),
        "controller": {"source_cidr": controller["source_cidr"]},
        "projection_paths": ["hostname_fqdn"],
        "expectations": {
            "dns_identity": copy.deepcopy(document["wunderbox_dns_identity"]),
            "management_services": copy.deepcopy(
                document["wunderbox_inventory_contract"]["controller_access"][
                    "management_services"
                ]
            ),
            "provider_input_rules": {
                "bootstrap": copy.deepcopy(
                    document["hetzner_baremetal_robot_firewall_bootstrap_input_rules"]
                ),
                "hardened": copy.deepcopy(
                    document["hetzner_baremetal_robot_firewall_hardened_input_rules"]
                ),
                "tang": copy.deepcopy(
                    document[
                        "hetzner_baremetal_robot_firewall_deferred_tang_input_rules"
                    ]
                ),
            },
            "tang_access": copy.deepcopy(document["host_firewall_tang_access"]),
            "legacy_aggregate_sources": {
                "controller": copy.deepcopy(
                    document["host_firewall_controller_source_cidrs"]
                ),
                "recovery": copy.deepcopy(
                    document["host_firewall_recovery_source_cidrs"]
                ),
            },
            "host_firewall": {
                "enabled": document["host_firewall_enabled"],
                "action": document["host_firewall_action"],
                "mode": document["host_firewall_mode"],
                "identity": {
                    "inventory_hostname": document[
                        "host_firewall_expected_inventory_hostname"
                    ],
                    "public_ipv4": document["host_firewall_expected_public_ipv4"],
                    "management_ipv4": document[
                        "host_firewall_expected_management_ipv4"
                    ],
                    "public_ipv6": document["host_firewall_expected_public_ipv6"],
                    "management_ipv6": document[
                        "host_firewall_expected_management_ipv6"
                    ],
                    "public_interface": document["host_firewall_public_interface"],
                    "management_interface": document[
                        "host_firewall_management_interface"
                    ],
                },
                "egress_policies_sha256": MODULE.sha256_bytes(
                    MODULE.canonical_json_bytes(policies)
                ),
                "egress_selector": document["host_firewall_egress_policy"],
                "provider_ipv6_filter": {
                    "verified_enabled": document[
                        "host_firewall_provider_ipv6_filter_enabled"
                    ],
                    "evidence_reference": document[
                        "host_firewall_provider_ipv6_filter_evidence_reference"
                    ],
                    "claim_basis": "PENDING_EXTERNAL_READBACK",
                },
            },
            "ipv4_only_baseline": copy.deepcopy(
                document["wunderbox_inventory_contract"]["ipv4_only_baseline"]
            ),
            "installimage_and_cis": {
                "installimage_ipv4_only": document["hetzner_installimage_layout"][
                    "ipv4_only"
                ],
                "cis_ipv4_required": document["ubtu24cis_ipv4_required"],
                "cis_ipv6_required": document["ubtu24cis_ipv6_required"],
                "cis_ipv6_disable": document["ubtu24cis_ipv6_disable"],
            },
            "netplan_ethernets": copy.deepcopy(document["netplan_ethernets"]),
            "netplan_vlans": copy.deepcopy(document["netplan_vlans"]),
            "provider_firewall": {
                "enabled": document["hetzner_baremetal_robot_firewall"]["enabled"],
                "admin_ipv4": document["hetzner_baremetal_robot_firewall"][
                    "admin_ipv4"
                ],
                "filter_ipv6": document["hetzner_baremetal_robot_firewall"][
                    "filter_ipv6"
                ],
            },
        },
    }


def minimal_projection_contract() -> dict:
    target = {
        "target_id": "TEST-TARGET",
        "fqdn": "host.example.test",
        "public_ipv4": "192.0.2.10",
        "provider_id": "provider-1",
    }
    controller = "192.0.2.20/32"
    management = {
        "management_ssh": {
            "port": 2200,
            "modes": ["bootstrap"],
            "sources_ipv4": [controller],
            "sources_ipv6": [],
        }
    }
    return {
        "schema_version": 1,
        "contract_id": "test-inventory-projection-v1",
        "target": target,
        "controller": {"source_cidr": controller},
        "projection_paths": ["hostname_fqdn"],
        "expectations": {
            "dns_identity": {
                "schema_version": 1,
                "desired": {
                    "public": {
                        "fqdn": target["fqdn"],
                        "a_records": [target["public_ipv4"]],
                        "ptr_records": [target["fqdn"]],
                        "aaaa_records": [],
                        "cname_records": [],
                    },
                    "management": {
                        "fqdn": "host.management.example.test",
                        "a_records": ["192.0.2.30"],
                        "aaaa_records": [],
                        "cname_records": [],
                    },
                },
                "verification": {
                    "accepted": False,
                    "fresh_readback": False,
                    "evidence_reference": "PENDING - test readback",
                },
            },
            "management_services": management,
            "provider_input_rules": {
                "bootstrap": [
                    {
                        "ip_version": "ipv4",
                        "protocol": "tcp",
                        "src_ip": controller,
                        "dst_ip": target["public_ipv4"],
                        "dst_port": "2200",
                        "name": "Test management",
                        "action": "accept",
                    }
                ],
                "hardened": [],
                "tang": [
                    {
                        "ip_version": "ipv4",
                        "protocol": "tcp",
                        "src_ip": "192.0.2.40/32",
                        "dst_ip": target["public_ipv4"],
                        "dst_port": "8000",
                        "name": "Test service",
                        "action": "accept",
                    }
                ],
            },
            "tang_access": {
                "port": 8000,
                "sources_ipv4": ["192.0.2.40/32"],
                "sources_ipv6": [],
            },
            "legacy_aggregate_sources": {"controller": [], "recovery": []},
            "host_firewall": {
                "enabled": False,
                "action": "plan",
                "mode": "bootstrap",
                "identity": {
                    "inventory_hostname": target["fqdn"],
                    "public_ipv4": target["public_ipv4"],
                    "management_ipv4": "192.0.2.30",
                    "public_ipv6": "",
                    "management_ipv6": "",
                    "public_interface": "eth0",
                    "management_interface": "eth1",
                },
                "egress_policies_sha256": "1" * 64,
                "egress_selector": "test_selector",
                "provider_ipv6_filter": {
                    "verified_enabled": False,
                    "evidence_reference": "PENDING - test IPv6 readback",
                    "claim_basis": "PENDING_EXTERNAL_READBACK",
                },
            },
            "ipv4_only_baseline": {
                "decision_id": "TEST-ADR-1",
                "evidence_id": "TEST-EV-1",
                "evidence_sha256": "2" * 64,
                "installimage_ipv4_only": True,
                "cis_ipv4_required": True,
                "cis_ipv6_required": False,
                "cis_ipv6_disable": "test-disable",
                "kernel_ipv6_disabled": True,
                "netplan": {
                    "dhcp6": False,
                    "accept_ra": False,
                    "link_local": [],
                    "source_ipv6": [],
                    "destination_ipv6": [],
                },
                "dns": {"aaaa_records": []},
                "provider": {
                    "required_filter_enabled": True,
                    "ipv6_rules": [],
                    "assigned_prefix": "2001:db8::/64",
                    "assignment_state": "assigned-but-unconfigured",
                },
            },
            "installimage_and_cis": {
                "installimage_ipv4_only": True,
                "cis_ipv4_required": True,
                "cis_ipv6_required": False,
                "cis_ipv6_disable": "test-disable",
            },
            "netplan_ethernets": {
                "eth0": {
                    "dhcp4": False,
                    "dhcp6": False,
                    "accept-ra": False,
                    "link-local": [],
                    "addresses": ["192.0.2.10/24"],
                    "routes": [{"to": "default", "via": "192.0.2.1"}],
                    "nameservers": {"addresses": ["192.0.2.53"]},
                }
            },
            "netplan_vlans": {},
            "provider_firewall": {
                "enabled": True,
                "admin_ipv4": "192.0.2.20",
                "filter_ipv6": True,
            },
        },
    }


def sample_container_engine() -> dict:
    anchor = {
        "transport": "local-root-unix-v1",
        "uri": "unix:///private/runtime/podman.sock",
        "socket_path": "/private/runtime/podman.sock",
        "owner_uid": 0,
        "owner_gid": 0,
        "mode": 0o600,
        "device": 1,
        "inode": 2,
    }
    return {
        "kind": "podman",
        "path": "/usr/bin/true",
        "sha256": "7" * 64,
        "backend_uri": "unix:///private/runtime/podman.sock",
        "backend_identity_sha256": "6" * 64,
        "backend_transport": "local-root-unix-v1",
        "backend_socket_path": "/private/runtime/podman.sock",
        "backend_socket_owner_uid": 0,
        "backend_socket_owner_gid": 0,
        "backend_socket_mode": 0o600,
        "backend_socket_device": 1,
        "backend_socket_inode": 2,
        "_backend_anchor": anchor,
    }


def create_signing_authority(
    root: Path,
    *,
    identity: str = "test-approver",
    namespace: str = MODULE.FOUNDATIONAL_APPROVAL_NAMESPACE,
) -> tuple[Path, dict]:
    ssh_keygen = Path(shutil.which("ssh-keygen") or "/usr/bin/ssh-keygen").resolve()
    key = root / "approval-ed25519"
    subprocess.run(
        [str(ssh_keygen), "-q", "-t", "ed25519", "-N", "", "-f", str(key)],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    public_key = " ".join(
        (root / "approval-ed25519.pub").read_text(encoding="ascii").split()[:2]
    )
    allowed_signers = root / "allowed-signers"
    allowed_signers.write_text(f"{identity} {public_key}\n", encoding="ascii")
    allowed_signers.chmod(0o400)
    replay = root / "approval-ledger"
    replay.mkdir(mode=0o700)
    descriptor = {
        "schema_version": 1,
        "identity": identity,
        "namespace": namespace,
        "fingerprint": MODULE._ed25519_fingerprint(public_key),
        "allowed_signers_path": str(allowed_signers.resolve()),
        "allowed_signers_sha256": MODULE.sha256_file(allowed_signers),
        "ssh_keygen_path": str(ssh_keygen),
        "ssh_keygen_sha256": MODULE.sha256_file(ssh_keygen),
        "replay_directory": str(replay.resolve()),
    }
    authority = MODULE.validate_approval_authority(
        descriptor, trusted_uids={0, os.geteuid()}
    )
    return key, authority


def sign_payload(key: Path, namespace: str, payload: bytes, root: Path) -> bytes:
    source = root / f"payload-{len(list(root.glob('payload-*')))}"
    source.write_bytes(payload)
    source.chmod(0o600)
    subprocess.run(
        [
            str(Path(shutil.which("ssh-keygen") or "/usr/bin/ssh-keygen").resolve()),
            "-Y",
            "sign",
            "-f",
            str(key),
            "-n",
            namespace,
            str(source),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    signature = Path(f"{source}.sig").read_bytes()
    return signature


def signed_approval(
    *,
    key: Path,
    authority: dict,
    manifest: dict,
    execution_id: str,
    nonce: str,
    operation: str,
    target: str,
    binding: object,
    root: Path,
) -> dict:
    transport = {
        "schema_version": 1,
        "execution_id": execution_id,
        "commit_shas": {
            name: repository["commit"]
            for name, repository in manifest["repositories"].items()
        },
        "nonce": nonce,
        "issued_at": "2026-08-09T00:01:00Z",
        "expires_at": "2026-08-09T00:11:00Z",
        "replay_directory": authority["replay_directory"],
    }
    signed_document = {
        "schema_version": 1,
        "authority": MODULE.public_approval_authority(authority),
        **transport,
        "operation": operation,
        "target": target,
        "binding": MODULE.canonical_approval_binding(binding),
    }
    transport["signature"] = sign_payload(
        key,
        authority["namespace"],
        MODULE.canonical_json_bytes(signed_document),
        root,
    ).decode("ascii")
    return transport


class GovernedRecorderTests(unittest.TestCase):
    def test_root_brokered_replay_store_is_exact_and_caller_independent(self):
        normalized = {
            "execution_id": "WBX-EXE-321-A001",
            "approval_digest": "a" * 64,
            "replay_digest": "b" * 64,
        }
        broker = {
            "kind": "root-brokered-append-only-v1",
            "path": "/trusted/replay-broker",
            "sha256": "c" * 64,
            "store_id": "wunderbox-controller-store",
        }

        def accepted(command, **kwargs):
            request = json.loads(kwargs["input"])
            self.assertEqual(command, [broker["path"], request["operation"]])
            self.assertNotIn("HOME", kwargs["env"])
            return subprocess.CompletedProcess(
                command,
                0,
                stdout=MODULE.canonical_json_bytes({**request, "status": "CLAIMED"}),
            )

        claim = MODULE.invoke_replay_broker(
            "claim", normalized, broker, runner=accepted
        )
        self.assertEqual(claim["claim_status"], "CLAIMED_BY_ROOT_BROKER")
        verification = MODULE.invoke_replay_broker(
            "verify", normalized, broker, runner=accepted
        )
        self.assertEqual(verification["claim_status"], "ROOT_BROKER_CLAIM_VERIFIED")

    def test_root_owned_execution_anchor_requires_isolated_safe_python(self):
        with tempfile.TemporaryDirectory() as directory:
            executable = Path(directory) / "installed-recorder"
            executable.write_text("fixture\n", encoding="utf-8")
            executable.chmod(0o500)
            executable = executable.resolve()
            digest = MODULE.sha256_file(executable)
            receipt = Path(directory) / "receipt.json"
            receipt_document = {
                "status": "ACCEPTED",
                "launcher_sha256": digest,
                "interpreter_sha256": digest,
                "recorder_sha256": digest,
            }
            receipt.write_text(json.dumps(receipt_document), encoding="utf-8")
            receipt.chmod(0o400)
            trust = {
                "_trusted_uids": frozenset({0, os.geteuid()}),
                "execution_anchor": {
                    "launcher": {"path": str(executable), "sha256": digest},
                    "interpreter": {"path": str(executable), "sha256": digest},
                    "recorder": {"path": str(executable), "sha256": digest},
                    "acceptance_receipt": {
                        "path": str(receipt.resolve()),
                        "sha256": MODULE.sha256_file(receipt),
                    },
                },
            }
            recorder_fd = os.open(executable, os.O_RDONLY)
            launcher_fd = os.open(executable, os.O_RDONLY)
            receipt_fd = os.open(receipt, os.O_RDONLY)
            try:
                evidence = MODULE.validate_execution_anchor_runtime(
                    trust,
                    interpreter_path=executable,
                    isolated=True,
                    safe_path=True,
                    launcher_fd=launcher_fd,
                    recorder_fd=recorder_fd,
                    receipt_fd=receipt_fd,
                    python_environment={},
                )
                self.assertEqual(evidence["python_mode"], "ISOLATED_SAFE_PATH")
                with self.assertRaises(MODULE.ContractError):
                    MODULE.validate_execution_anchor_runtime(
                        trust,
                        interpreter_path=executable,
                        isolated=False,
                        safe_path=True,
                        launcher_fd=launcher_fd,
                        recorder_fd=recorder_fd,
                        receipt_fd=receipt_fd,
                        python_environment={},
                    )
            finally:
                os.close(receipt_fd)
                os.close(launcher_fd)
                os.close(recorder_fd)

    def test_external_execution_anchor_must_match_frozen_reviewed_sources(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            automation = root / "automation"
            recorder = automation / "scripts" / "governed-ansible-exec.py"
            launcher = (
                automation / "ansible" / "scripts" / "governed-ansible-root-launcher"
            )
            policy = automation / "policies" / "wunderbox" / "root-of-trust-policy.json"
            for path, payload in (
                (recorder, b"recorder\n"),
                (launcher, b"launcher\n"),
                (policy, b"policy\n"),
            ):
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(payload)
            trust = {
                "execution_anchor": {
                    "recorder": {"sha256": MODULE.sha256_file(recorder)},
                    "launcher": {"sha256": MODULE.sha256_file(launcher)},
                },
                "policy": {"sha256": MODULE.sha256_file(policy)},
            }
            snapshots = {"automation": automation}
            MODULE.verify_external_anchor_sources(trust, snapshots)

            recorder.write_bytes(b"changed\n")
            with self.assertRaisesRegex(
                MODULE.ContractError, "does not match the frozen reviewed source"
            ):
                MODULE.verify_external_anchor_sources(trust, snapshots)

    def test_pre_live_environment_cannot_receive_payload_inputs(self):
        environment = {
            "PATH": "/usr/bin:/bin",
            "HOME": "/private/home",
            "TMPDIR": "/private/tmp",
            "ANSIBLE_TOOLBOX_ENGINE_BINARY": "/trusted/podman",
            "CONTAINER_HOST": "unix:///trusted/podman.sock",
            "ANSIBLE_TOOLBOX_INVENTORY_SOURCE": "/snapshot/inventories",
            "ANSIBLE_TOOLBOX_SSH_PRIVATE_KEY_FILE": "/private/key",
            "ANSIBLE_TOOLBOX_SSH_KNOWN_HOSTS_FILE": "/private/known_hosts",
            "ANSIBLE_TOOLBOX_SSH_PRIVATE_KEY_SHA256": "a" * 64,
            "ANSIBLE_TOOLBOX_SSH_KNOWN_HOSTS_SHA256": "b" * 64,
            "ANSIBLE_TOOLBOX_GOVERNED_INPUT_SOURCE": "/private/input",
            "ANSIBLE_TOOLBOX_RUNNER_ARTIFACT_SOURCE": "/private/raw",
            "ANSIBLE_VAULT_PASSWORD_FILE": "/private/vault",
        }
        minimal = MODULE.make_pre_live_environment(environment)
        self.assertEqual(minimal["ANSIBLE_TOOLBOX_MOUNT_INVENTORIES"], "true")
        self.assertEqual(minimal["ANSIBLE_TOOLBOX_NETWORK_MODE"], "none")
        for forbidden in (
            "ANSIBLE_TOOLBOX_SSH_PRIVATE_KEY_FILE",
            "ANSIBLE_TOOLBOX_SSH_KNOWN_HOSTS_FILE",
            "ANSIBLE_TOOLBOX_SSH_PRIVATE_KEY_SHA256",
            "ANSIBLE_TOOLBOX_SSH_KNOWN_HOSTS_SHA256",
            "ANSIBLE_TOOLBOX_GOVERNED_INPUT_SOURCE",
            "ANSIBLE_TOOLBOX_RUNNER_ARTIFACT_SOURCE",
            "ANSIBLE_VAULT_PASSWORD_FILE",
        ):
            self.assertNotIn(forbidden, minimal)

    def test_container_backend_identity_excludes_volatile_runtime_state(self):
        engine = sample_container_engine()
        podman_info = {
            "host": {
                "arch": "arm64",
                "os": "linux",
                "hostname": "podman-machine-default",
                "serviceIsRemote": True,
                "remoteSocket": {"path": "/run/user/1000/podman/podman.sock"},
                "uptime": "1h 2m",
                "memFree": 100,
            },
            "store": {
                "graphDriverName": "overlay",
                "graphRoot": "/var/home/core/.local/share/containers/storage",
                "runRoot": "/run/user/1000/containers",
                "containerStore": {"number": 1},
            },
            "version": {"APIVersion": "5.6.1", "Version": "5.6.1"},
        }
        first = MODULE.normalized_container_backend_identity(podman_info, engine)
        podman_info["host"]["uptime"] = "9h 9m"
        podman_info["host"]["memFree"] = 1
        podman_info["store"]["containerStore"]["number"] = 99
        second = MODULE.normalized_container_backend_identity(podman_info, engine)
        self.assertEqual(first, second)
        self.assertEqual(first["backend_uri"], engine["backend_uri"])
        self.assertEqual(first["client_sha256"], engine["sha256"])

    def test_policy_rejects_duplicate_record_prefix(self):
        policy = sample_policy()
        policy["actions"]["second"] = {
            **policy["actions"]["target_plan"],
            "record_prefix": "321",
        }
        with self.assertRaises(MODULE.ContractError):
            MODULE.validate_policy(policy)

    def test_policy_and_manifest_nested_contracts_are_closed(self):
        policy = sample_policy()
        policy["target_contract"]["unexpected"] = True
        with self.assertRaisesRegex(MODULE.ContractError, "exact-key schema"):
            MODULE.validate_policy(policy)

        policy = sample_policy()
        policy["actions"]["target_plan"]["unexpected"] = True
        with self.assertRaisesRegex(MODULE.ContractError, "closed schema"):
            MODULE.validate_policy(policy)

        policy = sample_policy()
        MODULE.validate_policy(policy)
        payload = json.dumps(policy, sort_keys=True, separators=(",", ":")).encode()
        manifest = sample_manifest(MODULE.sha256_bytes(payload))
        manifest["repositories"]["automation"]["unexpected"] = True
        with self.assertRaisesRegex(MODULE.ContractError, "exact-key schema"):
            MODULE.validate_manifest(manifest, policy, MODULE.sha256_bytes(payload))

    def test_payload_launcher_is_recorded_by_exact_path_and_digest(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            automation = root / "automation"
            inventory = root / "inventory"
            wrapper = automation / "ansible" / "scripts" / "ansible-nav"
            inventory_file = inventory / "inventories" / "pub" / "inventory.yml"
            wrapper.parent.mkdir(parents=True)
            inventory_file.parent.mkdir(parents=True)
            wrapper.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            wrapper.chmod(0o500)
            inventory_file.write_text("all: {}\n", encoding="utf-8")
            command, metadata = MODULE.build_command(
                {
                    "mode": "inventory_projection",
                    "tags": [],
                    "skip_tags": [],
                },
                sample_manifest("f" * 64)["target"],
                {
                    "automation": automation.resolve(),
                    "inventory": inventory.resolve(),
                },
                "WBX-EXE-100-A001",
                None,
            )
            self.assertEqual(command[0], str(wrapper.resolve()))
            self.assertEqual(metadata["launcher_path"], command[0])
            self.assertEqual(metadata["launcher_sha256"], MODULE.sha256_file(wrapper))

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
        with self.assertRaisesRegex(MODULE.ContractError, "implementation is blocked"):
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
                MODULE.validate_extra_vars(
                    path,
                    {
                        **action,
                        "allowed_extra_vars": ["ansible_host"],
                        "required_extra_vars": ["ansible_host"],
                    },
                )

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
            "extra_var_allowed_values": {"onepassword_password_action": ["plan"]},
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

    def test_execution_and_consumer_approvals_are_crypto_verified_and_distinct(self):
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
                    "operation": "unlock-luks-over-ssh-stdin",
                    "contract_binding": {"purpose": "bootstrap-unlock"},
                }
            },
        }
        policy["actions"]["target_plan"] = action
        MODULE.validate_policy(policy)
        manifest = sample_manifest("f" * 64)
        authorization = manifest["authorizations"]["target_plan"]
        authorization["consumer_approval_contracts"] = {
            "onepassword_approval": {
                "operation": "unlock-luks-over-ssh-stdin",
                "target": manifest["target"]["fqdn"],
                "binding": {"purpose": "bootstrap-unlock"},
            }
        }
        now = dt.datetime(2026, 8, 9, 0, 5, tzinfo=dt.timezone.utc)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            key, authority = create_signing_authority(root)
            execution_binding = MODULE.execution_approval_binding(
                "target_plan", action, manifest, authorization
            )
            authorization["execution_approval"] = signed_approval(
                key=key,
                authority=authority,
                manifest=manifest,
                execution_id=execution_id,
                nonce="1" * 64,
                operation="governed-ansible-action",
                target=manifest["target"]["fqdn"],
                binding=execution_binding,
                root=root,
            )
            consumer = signed_approval(
                key=key,
                authority=authority,
                manifest=manifest,
                execution_id=execution_id,
                nonce="2" * 64,
                operation="unlock-luks-over-ssh-stdin",
                target=manifest["target"]["fqdn"],
                binding={"purpose": "bootstrap-unlock"},
                root=root,
            )
            path = root / "vars.json"
            path.write_text(
                json.dumps({"onepassword_approval": consumer}), encoding="utf-8"
            )
            path.chmod(0o600)
            parsed, _digest, _source = MODULE.validate_extra_vars(
                path, action, manifest, authorization, execution_id
            )
            execution, consumers = MODULE.prepare_approvals(
                "target_plan",
                action,
                manifest,
                authorization,
                execution_id,
                parsed,
                authority,
                now,
            )
            self.assertNotEqual(
                execution["replay_digest"],
                consumers["onepassword_approval"]["replay_digest"],
            )
            MODULE._claim_local_approval_marker_for_test(execution, now)
            MODULE.revalidate_approval(
                execution, authority, now, require_unclaimed=False
            )
            execution_claim = MODULE.verify_claimed_approval_marker(
                execution, "post-action execution approval"
            )
            self.assertEqual(execution_claim["claim_status"], "CLAIMED_AND_VERIFIED")
            MODULE._claim_local_approval_marker_for_test(
                consumers["onepassword_approval"], now
            )
            consumer_claim = {
                "store_id": "test-root-store",
                "approval_digest": consumers["onepassword_approval"]["approval_digest"],
                "replay_digest": consumers["onepassword_approval"]["replay_digest"],
            }
            with mock.patch.object(
                MODULE,
                "invoke_replay_broker",
                return_value=consumer_claim,
            ):
                claims = MODULE.verify_consumer_claims(
                    consumers,
                    {
                        "path": "/trusted/replay-broker",
                        "store_id": "test-root-store",
                    },
                    {"onepassword_approval": consumer_claim},
                )
            self.assertEqual(claims[0]["claim_status"], "ROOT_BROKER_CLAIM_VERIFIED")

            execution_marker = Path(execution["_marker"])
            execution_marker.write_text("{}", encoding="utf-8")
            with self.assertRaises(MODULE.ContractError):
                MODULE.verify_claimed_approval_marker(
                    execution, "post-action execution approval"
                )

            consumer["signature"] = consumer["signature"].replace("A", "B", 1)
            with self.assertRaises(MODULE.ContractError):
                MODULE.normalize_and_verify_approval(
                    consumer,
                    manifest,
                    authorization,
                    execution_id,
                    authority,
                    operation="unlock-luks-over-ssh-stdin",
                    target=manifest["target"]["fqdn"],
                    binding={"purpose": "bootstrap-unlock"},
                    now=now,
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
            "execution_id": "WBX-EXE-321-A001",
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
        recaps, artifacts = MODULE.parse_events(
            output, "target_plan", execution_id="WBX-EXE-321-A001"
        )
        self.assertFalse(artifacts)
        counts = MODULE.validate_target_recap(
            recaps,
            "host.example.test",
            sample_policy()["actions"]["target_plan"],
        )
        self.assertEqual(counts["ok"], 4)

        for counter, value, action_override in (
            ("ignored", 1, {}),
            ("changed", 1, {"impact": "target_read"}),
            ("ok", True, {}),
        ):
            with self.subTest(counter=counter):
                rejected = json.loads(json.dumps(event))
                rejected["hosts"]["host.example.test"][counter] = value
                rejected_output = (
                    MODULE.EVENT_PREFIX + json.dumps(rejected) + "\n"
                ).encode()
                rejected_recaps, _ = MODULE.parse_events(
                    rejected_output,
                    "target_plan",
                    execution_id="WBX-EXE-321-A001",
                )
                with self.assertRaises(MODULE.ContractError):
                    MODULE.validate_target_recap(
                        rejected_recaps,
                        "host.example.test",
                        {
                            **sample_policy()["actions"]["target_plan"],
                            **action_override,
                        },
                    )

        event["hosts"]["other.example.test"] = event["hosts"]["host.example.test"]
        output = (MODULE.EVENT_PREFIX + json.dumps(event) + "\n").encode()
        recaps, _ = MODULE.parse_events(
            output, "target_plan", execution_id="WBX-EXE-321-A001"
        )
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

    def test_signature_verification_uses_digest_pinned_trust(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            key, authority = create_signing_authority(
                root, identity="manifest-approver"
            )
            payload = b"manifest"
            signature_payload = sign_payload(key, authority["namespace"], payload, root)
            signature = Path(directory) / "manifest.sig"
            signature.write_bytes(signature_payload)
            signature.chmod(0o400)
            MODULE.verify_manifest_signature(
                payload,
                signature,
                authority,
            )
            authority["allowed_signers_sha256"] = "0" * 64
            with self.assertRaisesRegex(MODULE.ContractError, "pinned SHA-256"):
                MODULE.verify_manifest_signature(payload, signature, authority)

    def test_controller_trust_is_one_fixed_exact_digest_pinned_descriptor(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _key, authority = create_signing_authority(root)
            policy_payload = (
                json.dumps(sample_policy(), sort_keys=True, separators=(",", ":"))
                + "\n"
            ).encode("utf-8")
            policy_path = root / "policy.json"
            policy_path.write_bytes(policy_payload)
            policy_path.chmod(0o400)
            signature_trust = MODULE.public_signature_trust(authority)
            executable = Path(shutil.which("true") or "/usr/bin/true").resolve()
            executable_sha256 = MODULE.sha256_file(executable)
            receipt = {
                "schema_version": 1,
                "status": "ACCEPTED",
                "launcher_sha256": executable_sha256,
                "interpreter_sha256": executable_sha256,
                "recorder_sha256": executable_sha256,
                "replay_broker_sha256": executable_sha256,
                "process_supervisor_sha256": executable_sha256,
                "container_engine_sha256": executable_sha256,
                "negative_replay_test": True,
                "controller_readback_test": True,
                "escaped_descendant_test": True,
                "bounded_output_test": True,
            }
            receipt_path = root / "execution-anchor-receipt.json"
            receipt_path.write_text(
                json.dumps(receipt, sort_keys=True), encoding="utf-8"
            )
            receipt_path.chmod(0o400)
            executable_pin = {
                "path": str(executable),
                "sha256": executable_sha256,
            }
            descriptor = {
                "schema_version": 1,
                "policy": {
                    "path": str(policy_path.resolve()),
                    "sha256": MODULE.sha256_bytes(policy_payload),
                },
                "execution_anchor": {
                    "launcher": executable_pin,
                    "interpreter": executable_pin,
                    "recorder": executable_pin,
                    "acceptance_receipt": {
                        "path": str(receipt_path.resolve()),
                        "sha256": MODULE.sha256_file(receipt_path),
                    },
                },
                "replay_broker": {
                    "kind": "root-brokered-append-only-v1",
                    **executable_pin,
                    "store_id": "test-append-only-store",
                },
                "process_supervisor": {
                    "kind": "root-brokered-process-domain-v1",
                    **executable_pin,
                    "backend": "launchd-job",
                    "profile_id": "test-process-domain",
                },
                "container_engine": {
                    "kind": "podman",
                    **executable_pin,
                    "backend_uri": "unix:///private/runtime/podman.sock",
                    "backend_identity_sha256": "6" * 64,
                    "backend_transport": "local-root-unix-v1",
                    "backend_socket_path": "/private/runtime/podman.sock",
                    "backend_socket_owner_uid": 0,
                    "backend_socket_owner_gid": 0,
                    "backend_socket_mode": 0o600,
                    "backend_socket_device": 1,
                    "backend_socket_inode": 2,
                },
                "manifest_signature": signature_trust,
                "runtime_attestation_signature": signature_trust,
                "approval_authority": {
                    key: authority[key] for key in MODULE.APPROVAL_AUTHORITY_KEYS
                },
            }
            descriptor_path = root / "controller-trust.json"
            descriptor_path.write_text(
                json.dumps(descriptor, sort_keys=True), encoding="utf-8"
            )
            descriptor_path.chmod(0o400)
            backend_anchor = sample_container_engine()["_backend_anchor"]
            with mock.patch.object(
                MODULE,
                "validate_container_backend_anchor",
                return_value=backend_anchor,
            ):
                loaded, policy, observed_payload = MODULE.load_controller_trust(
                    descriptor_path.resolve(), trusted_uids={0, os.geteuid()}
                )
            self.assertEqual(policy, sample_policy())
            self.assertEqual(observed_payload, policy_payload)
            self.assertEqual(loaded["_descriptor_path"], str(descriptor_path.resolve()))
            with mock.patch.object(
                MODULE,
                "validate_container_backend_anchor",
                return_value=backend_anchor,
            ):
                MODULE.revalidate_controller_trust(loaded)

            descriptor["unexpected"] = True
            descriptor_path.chmod(0o600)
            descriptor_path.write_text(json.dumps(descriptor), encoding="utf-8")
            descriptor_path.chmod(0o400)
            with self.assertRaises(MODULE.ContractError):
                MODULE.load_controller_trust(
                    descriptor_path.resolve(), trusted_uids={0, os.geteuid()}
                )

        parser_options = {
            option
            for action in MODULE.build_parser()._actions
            for option in action.option_strings
        }
        self.assertNotIn("--policy", parser_options)
        self.assertNotIn("--allowed-signers", parser_options)

    def test_repository_snapshots_are_tracked_read_only_and_dirty_state_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo = root / "repo"
            repo.mkdir(mode=0o700)
            git = str(MODULE.SYSTEM_GIT)
            subprocess.run([git, "-C", str(repo), "init", "-q"], check=True)
            subprocess.run(
                [git, "-C", str(repo), "config", "user.email", "test@example.invalid"],
                check=True,
            )
            subprocess.run(
                [git, "-C", str(repo), "config", "user.name", "Recorder Test"],
                check=True,
            )
            (repo / ".gitignore").write_text("ignored.tmp\n", encoding="utf-8")
            (repo / "tracked.txt").write_text("frozen\n", encoding="utf-8")
            (repo / "nested").mkdir()
            executable = repo / "nested" / "tool"
            executable.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            executable.chmod(0o755)
            subprocess.run([git, "-C", str(repo), "add", "."], check=True)
            subprocess.run(
                [git, "-C", str(repo), "commit", "-q", "-m", "frozen"],
                check=True,
            )
            expected = {
                "branch": MODULE.run_git(repo, "branch", "--show-current"),
                "commit": MODULE.run_git(repo, "rev-parse", "HEAD"),
            }
            state = MODULE.collect_repository_state("automation", repo, expected)
            runtime = root / "runtime"
            runtime.mkdir(mode=0o700)
            snapshots, evidence = MODULE.create_repository_snapshots([state], runtime)
            MODULE.verify_repository_snapshots(snapshots, evidence)
            self.assertTrue(evidence[0]["tracked_objects_only"])
            self.assertTrue(evidence[0]["git_object_integrity_verified"])
            self.assertTrue(evidence[0]["replace_refs_disabled"])
            self.assertEqual(evidence[0]["file_count"], 3)
            self.assertEqual(
                (snapshots["automation"] / "tracked.txt").read_text(), "frozen\n"
            )
            self.assertEqual(
                (snapshots["automation"] / "nested" / "tool").stat().st_mode & 0o777,
                0o500,
            )
            self.assertEqual(
                (snapshots["automation"] / "tracked.txt").stat().st_mode & 0o777,
                0o400,
            )
            (snapshots["automation"] / "tracked.txt").chmod(0o600)
            with self.assertRaisesRegex(MODULE.ContractError, "permissions changed"):
                MODULE.verify_repository_snapshots(snapshots, evidence)
            (snapshots["automation"] / "tracked.txt").chmod(0o400)
            self.assertTrue(MODULE.remove_private_runtime_tree(runtime))

            (repo / "untracked.txt").write_text("no\n", encoding="utf-8")
            with self.assertRaises(MODULE.ContractError):
                MODULE.collect_repository_state("automation", repo, expected)
            (repo / "untracked.txt").unlink()
            (repo / "ignored.tmp").write_text("no\n", encoding="utf-8")
            with self.assertRaisesRegex(MODULE.ContractError, "ignored"):
                MODULE.collect_repository_state("automation", repo, expected)
            (repo / "ignored.tmp").unlink()
            (repo / "tracked.txt").write_text("changed\n", encoding="utf-8")
            with self.assertRaises(MODULE.ContractError):
                MODULE.collect_repository_state("automation", repo, expected)

            (repo / "tracked.txt").write_text("frozen\n", encoding="utf-8")
            os.symlink("tracked.txt", repo / "tracked-link")
            subprocess.run([git, "-C", str(repo), "add", "tracked-link"], check=True)
            subprocess.run(
                [git, "-C", str(repo), "commit", "-q", "-m", "symlink"],
                check=True,
            )
            expected = {
                "branch": MODULE.run_git(repo, "branch", "--show-current"),
                "commit": MODULE.run_git(repo, "rev-parse", "HEAD"),
            }
            state = MODULE.collect_repository_state("automation", repo, expected)
            unsafe_runtime = root / "unsafe-runtime"
            unsafe_runtime.mkdir(mode=0o700)
            with self.assertRaisesRegex(MODULE.ContractError, "unsupported entry"):
                MODULE.create_repository_snapshots([state], unsafe_runtime)

    def test_repository_snapshots_ignore_replace_refs_and_attribute_overlays(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo = root / "repo"
            repo.mkdir(mode=0o700)
            git = str(MODULE.SYSTEM_GIT)
            subprocess.run([git, "-C", str(repo), "init", "-q"], check=True)
            subprocess.run(
                [git, "-C", str(repo), "config", "user.email", "test@example.invalid"],
                check=True,
            )
            subprocess.run(
                [git, "-C", str(repo), "config", "user.name", "Recorder Test"],
                check=True,
            )
            (repo / "tracked.txt").write_text("frozen\n", encoding="utf-8")
            subprocess.run([git, "-C", str(repo), "add", "tracked.txt"], check=True)
            subprocess.run(
                [git, "-C", str(repo), "commit", "-q", "-m", "frozen"],
                check=True,
            )
            frozen_commit = subprocess.run(
                [git, "-C", str(repo), "rev-parse", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            subprocess.run(
                [git, "-C", str(repo), "branch", "frozen", frozen_commit],
                check=True,
            )
            (repo / "tracked.txt").write_text("attacker\n", encoding="utf-8")
            subprocess.run([git, "-C", str(repo), "add", "tracked.txt"], check=True)
            subprocess.run(
                [git, "-C", str(repo), "commit", "-q", "-m", "attacker"],
                check=True,
            )
            attacker_commit = subprocess.run(
                [git, "-C", str(repo), "rev-parse", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            subprocess.run(
                [git, "-C", str(repo), "checkout", "-q", "frozen"], check=True
            )
            subprocess.run(
                [git, "-C", str(repo), "replace", frozen_commit, attacker_commit],
                check=True,
            )
            replaced_payload = subprocess.run(
                [git, "-C", str(repo), "show", f"{frozen_commit}:tracked.txt"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout
            self.assertEqual(replaced_payload, "attacker\n")

            expected = {"branch": "frozen", "commit": frozen_commit}
            state = MODULE.collect_repository_state("automation", repo, expected)
            replace_runtime = root / "replace-runtime"
            replace_runtime.mkdir(mode=0o700)
            snapshots, evidence = MODULE.create_repository_snapshots(
                [state], replace_runtime
            )
            MODULE.verify_repository_snapshots(snapshots, evidence)
            self.assertEqual(
                (snapshots["automation"] / "tracked.txt").read_text(), "frozen\n"
            )
            self.assertTrue(MODULE.remove_private_runtime_tree(replace_runtime))

            subprocess.run(
                [git, "-C", str(repo), "replace", "-d", frozen_commit],
                check=True,
                capture_output=True,
            )
            attributes = root / "host-attributes"
            attributes.write_text("tracked.txt export-ignore\n", encoding="utf-8")
            subprocess.run(
                [
                    git,
                    "-C",
                    str(repo),
                    "config",
                    "core.attributesFile",
                    str(attributes),
                ],
                check=True,
            )
            with self.assertRaisesRegex(
                MODULE.ContractError, "forbidden key core.attributesfile"
            ):
                MODULE.collect_repository_state("automation", repo, expected)
            subprocess.run(
                [git, "-C", str(repo), "config", "--unset", "core.attributesFile"],
                check=True,
            )

            fsmonitor_marker = root / "fsmonitor-executed"
            fsmonitor = root / "malicious-fsmonitor"
            fsmonitor.write_text(
                f"#!/bin/sh\nprintf compromised > {fsmonitor_marker}\n",
                encoding="utf-8",
            )
            fsmonitor.chmod(0o700)
            subprocess.run(
                [git, "-C", str(repo), "config", "core.fsmonitor", str(fsmonitor)],
                check=True,
            )
            with self.assertRaisesRegex(
                MODULE.ContractError, "forbidden key core.fsmonitor"
            ):
                MODULE.collect_repository_state("automation", repo, expected)
            self.assertFalse(fsmonitor_marker.exists())
            subprocess.run(
                [git, "-C", str(repo), "config", "--unset", "core.fsmonitor"],
                check=True,
            )
            info_attributes = repo / ".git" / "info" / "attributes"
            info_attributes.write_text("tracked.txt export-ignore\n", encoding="utf-8")

            state = MODULE.collect_repository_state("automation", repo, expected)
            attributes_runtime = root / "attributes-runtime"
            attributes_runtime.mkdir(mode=0o700)
            snapshots, evidence = MODULE.create_repository_snapshots(
                [state], attributes_runtime
            )
            MODULE.verify_repository_snapshots(snapshots, evidence)
            self.assertEqual(
                (snapshots["automation"] / "tracked.txt").read_text(), "frozen\n"
            )
            self.assertTrue(MODULE.remove_private_runtime_tree(attributes_runtime))

    def test_linked_worktree_common_and_worktree_configs_are_audited(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            common = root / "common"
            linked = root / "linked"
            common.mkdir(mode=0o700)
            git = str(MODULE.SYSTEM_GIT)
            subprocess.run([git, "-C", str(common), "init", "-q"], check=True)
            subprocess.run(
                [
                    git,
                    "-C",
                    str(common),
                    "config",
                    "user.email",
                    "test@example.invalid",
                ],
                check=True,
            )
            subprocess.run(
                [git, "-C", str(common), "config", "user.name", "Recorder Test"],
                check=True,
            )
            (common / "tracked.txt").write_text("frozen\n", encoding="utf-8")
            subprocess.run([git, "-C", str(common), "add", "tracked.txt"], check=True)
            subprocess.run(
                [git, "-C", str(common), "commit", "-q", "-m", "frozen"],
                check=True,
            )
            subprocess.run(
                [
                    git,
                    "-C",
                    str(common),
                    "worktree",
                    "add",
                    "-q",
                    "-b",
                    "linked",
                    str(linked),
                ],
                check=True,
            )

            marker = root / "fsmonitor-executed"
            fsmonitor = root / "malicious-fsmonitor"
            fsmonitor.write_text(
                f"#!/bin/sh\nprintf compromised > {marker}\n",
                encoding="utf-8",
            )
            fsmonitor.chmod(0o700)
            subprocess.run(
                [git, "-C", str(common), "config", "core.fsmonitor", str(fsmonitor)],
                check=True,
            )
            self.assertEqual(MODULE.git_environment()["GIT_CONFIG_VALUE_4"], "false")
            with self.assertRaisesRegex(
                MODULE.ContractError,
                "Git common config enables forbidden key core.fsmonitor",
            ):
                MODULE.run_git(linked, "status", "--porcelain=v1")
            self.assertFalse(marker.exists())

            subprocess.run(
                [git, "-C", str(common), "config", "--unset", "core.fsmonitor"],
                check=True,
            )
            subprocess.run(
                [git, "-C", str(common), "config", "extensions.worktreeConfig", "true"],
                check=True,
            )
            safe_audit = MODULE.audit_local_git_config(linked)
            self.assertEqual(
                safe_audit["common_directory"]["path"],
                str((common / ".git").resolve()),
            )
            self.assertTrue(safe_audit["worktree_config_enabled"])
            self.assertEqual(MODULE.run_git(linked, "status", "--porcelain=v1"), "")
            subprocess.run(
                [
                    git,
                    "-C",
                    str(linked),
                    "config",
                    "--worktree",
                    "core.fsmonitor",
                    str(fsmonitor),
                ],
                check=True,
            )
            with self.assertRaisesRegex(
                MODULE.ContractError,
                "Git worktree config enables forbidden key core.fsmonitor",
            ):
                MODULE.run_git(linked, "status", "--porcelain=v1")
            self.assertFalse(marker.exists())

    def test_signed_runtime_attestation_matches_effective_collection_tree_probe(self):
        policy = sample_policy()
        manifest = sample_manifest("f" * 64)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            key, trust = create_signing_authority(root)
            collections = {
                name: {
                    "fqcn": f"lit.{name}",
                    "version": "1.0.0",
                    "source_commit": manifest["repositories"][repository]["commit"],
                    "installed_tree_sha256": character * 64,
                }
                for (name, repository), character in zip(
                    policy["collection_repositories"].items(), ("1", "2")
                )
            }
            attestation = {
                "schema_version": 1,
                "toolbox": {
                    "schema_version": 1,
                    "image_role": "toolbox",
                    "image": manifest["runtime"]["toolbox_image"],
                    "loader": MODULE.EXPECTED_RUNTIME_LOADER,
                    "collections": collections,
                },
                "run_ee": {
                    "schema_version": 1,
                    "image_role": "run_ee",
                    "image": manifest["runtime"]["run_ee_image"],
                    "loader": MODULE.EXPECTED_RUNTIME_LOADER,
                    "collections": collections,
                },
            }
            payload = MODULE.canonical_json_bytes(attestation) + b"\n"
            attestation_path = root / "runtime-attestation.json"
            attestation_path.write_bytes(payload)
            attestation_path.chmod(0o400)
            signature_path = root / "runtime-attestation.json.sig"
            signature_path.write_bytes(
                sign_payload(key, trust["namespace"], payload, root)
            )
            signature_path.chmod(0o400)
            manifest["runtime"].update(
                {
                    "attestation_path": str(attestation_path.resolve()),
                    "attestation_sha256": MODULE.sha256_bytes(payload),
                    "attestation_signature_path": str(signature_path.resolve()),
                }
            )
            observed, observed_payload = MODULE.load_and_verify_runtime_attestation(
                manifest, policy, trust
            )
            self.assertEqual(observed, attestation)
            self.assertEqual(observed_payload, payload)
            probe = {
                "schema_version": 1,
                "image_role": "toolbox",
                "image": manifest["runtime"]["toolbox_image"],
                "loader": MODULE.EXPECTED_RUNTIME_LOADER,
                "collections": {
                    name: {
                        "fqcn": collection["fqcn"],
                        "version": collection["version"],
                        "installed_tree_sha256": collection["installed_tree_sha256"],
                    }
                    for name, collection in collections.items()
                },
            }
            MODULE.validate_runtime_probe(
                MODULE.canonical_json_bytes(probe),
                "toolbox",
                attestation["toolbox"],
                policy,
            )
            probe["collections"]["ubuntu"]["installed_tree_sha256"] = "3" * 64
            with self.assertRaises(MODULE.ContractError):
                MODULE.validate_runtime_probe(
                    MODULE.canonical_json_bytes(probe),
                    "toolbox",
                    attestation["toolbox"],
                    policy,
                )

    def test_runtime_probes_cannot_receive_ssh_secrets_inventory_or_runner_mounts(self):
        policy = sample_policy()
        manifest = sample_manifest("f" * 64)
        collections = {
            name: {
                "fqcn": f"lit.{name}",
                "version": "1.0.0",
                "source_commit": manifest["repositories"][repository]["commit"],
                "installed_tree_sha256": character * 64,
            }
            for (name, repository), character in zip(
                policy["collection_repositories"].items(), ("1", "2")
            )
        }
        attestation = {
            role: {
                "schema_version": 1,
                "image_role": role,
                "image": manifest["runtime"][
                    "toolbox_image" if role == "toolbox" else "run_ee_image"
                ],
                "loader": MODULE.EXPECTED_RUNTIME_LOADER,
                "collections": collections,
            }
            for role in ("toolbox", "run_ee")
        }
        with tempfile.TemporaryDirectory() as directory:
            runtime = Path(directory).resolve()
            runtime_tmp = runtime / "tmp"
            runtime_tmp.mkdir(mode=0o700)
            observed_environments = []

            def fake_run(command, environment, _cwd, **_kwargs):
                observed_environments.append(dict(environment))
                role = "toolbox" if command == ["toolbox-probe"] else "run_ee"
                probe = {
                    "schema_version": 1,
                    "image_role": role,
                    "image": attestation[role]["image"],
                    "loader": MODULE.EXPECTED_RUNTIME_LOADER,
                    "collections": {
                        name: {
                            "fqcn": value["fqcn"],
                            "version": value["version"],
                            "installed_tree_sha256": value["installed_tree_sha256"],
                        }
                        for name, value in collections.items()
                    },
                }
                payload = MODULE.canonical_json_bytes(probe)
                return {
                    "exit_code": 0,
                    "termination_reason": None,
                    "stdout": payload,
                    "stdout_sha256": MODULE.sha256_bytes(payload),
                    "stderr_sha256": MODULE.sha256_bytes(b""),
                }

            environment = {
                "PATH": "/usr/bin:/bin",
                "TMPDIR": str(runtime_tmp),
                "ANSIBLE_TOOLBOX_IMAGE": manifest["runtime"]["toolbox_image"],
                "ANSIBLE_TOOLBOX_RUN_EE_IMAGE": manifest["runtime"]["run_ee_image"],
                "ANSIBLE_TOOLBOX_EE_ONLY_COLLECTIONS": "true",
                "SSH_AUTH_SOCK": "/forbidden/agent.sock",
                "ANSIBLE_TOOLBOX_SSH_SOURCE": "/forbidden/ssh",
                "ANSIBLE_TOOLBOX_INVENTORY_SOURCE": "/forbidden/inventory",
                "ANSIBLE_TOOLBOX_RUNNER_ARTIFACT_SOURCE": "/forbidden/raw",
                "ANSIBLE_TOOLBOX_GOVERNED_INPUT_SOURCE": "/forbidden/input",
                "ANSIBLE_VAULT_PASSWORD_FILE": "/forbidden/vault-pass",
            }
            with mock.patch.object(MODULE, "run_bounded", side_effect=fake_run):
                MODULE.run_runtime_provenance_probes(
                    {"toolbox": ["toolbox-probe"], "run_ee": ["run-ee-probe"]},
                    environment,
                    runtime,
                    attestation,
                    policy,
                )
            for observed in observed_environments:
                self.assertFalse(
                    {
                        "SSH_AUTH_SOCK",
                        "ANSIBLE_TOOLBOX_SSH_SOURCE",
                        "ANSIBLE_TOOLBOX_INVENTORY_SOURCE",
                        "ANSIBLE_TOOLBOX_RUNNER_ARTIFACT_SOURCE",
                        "ANSIBLE_TOOLBOX_GOVERNED_INPUT_SOURCE",
                        "ANSIBLE_VAULT_PASSWORD_FILE",
                    }
                    & set(observed)
                )

    def test_persisted_records_reject_password_token_and_root_token_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for index, key in enumerate(("password", "api_token", "root_token")):
                with self.subTest(key=key):
                    with self.assertRaises(MODULE.ContractError):
                        MODULE.write_new_json(
                            root / f"record-{index}.json", {"nested": {key: "value"}}
                        )

    def test_projection_contract_schema_is_closed_at_every_security_boundary(self):
        contract = minimal_projection_contract()
        MODULE.validate_projection_contract(contract)
        for mutation in ("extra", "missing"):
            with self.subTest(mutation=mutation):
                candidate = copy.deepcopy(contract)
                if mutation == "extra":
                    candidate["expectations"]["host_firewall"]["unexpected"] = True
                else:
                    del candidate["expectations"]["host_firewall"]["mode"]
                with self.assertRaisesRegex(MODULE.ContractError, "exact-key"):
                    MODULE.validate_projection_contract(candidate)
        with self.assertRaisesRegex(MODULE.ContractError, "duplicate key"):
            MODULE.strict_json_loads(
                b'{"schema_version":1,"schema_version":1}',
                "projection contract",
            )

    def test_projection_contract_closes_nested_netplan_schema(self):
        contract = minimal_projection_contract()
        MODULE.validate_projection_contract(contract)

        mutations = {
            "unexpected nameserver field": lambda interface: interface[
                "nameservers"
            ].update({"unexpected": True}),
            "missing nameserver addresses": lambda interface: interface[
                "nameservers"
            ].pop("addresses"),
            "wrong nameserver addresses type": lambda interface: interface[
                "nameservers"
            ].update({"addresses": "192.0.2.53"}),
            "unexpected route field": lambda interface: interface["routes"][0].update(
                {"metric": 100}
            ),
            "missing route gateway": lambda interface: interface["routes"][0].pop(
                "via"
            ),
            "wrong route gateway type": lambda interface: interface["routes"][0].update(
                {"via": 192002001}
            ),
        }
        for case, mutate in mutations.items():
            with self.subTest(case=case):
                candidate = copy.deepcopy(contract)
                interface = candidate["expectations"]["netplan_ethernets"]["eth0"]
                mutate(interface)
                with self.assertRaises(MODULE.ContractError):
                    MODULE.validate_projection_contract(candidate)

    def test_projection_contract_loader_rejects_wrong_digest_and_tamper(self):
        contract = minimal_projection_contract()
        payload = MODULE.canonical_json_bytes(contract) + b"\n"
        with tempfile.TemporaryDirectory() as directory_name:
            root = Path(directory_name)
            contract_path = root / "contracts" / "inventory-projection.json"
            contract_path.parent.mkdir(mode=0o700)
            contract_path.write_bytes(payload)
            contract_path.chmod(0o400)
            policy = sample_policy()
            policy["projection_contract"] = {
                "repository": "inventory",
                "path": "contracts/inventory-projection.json",
                "sha256": MODULE.sha256_bytes(payload),
            }
            loaded, loaded_payload, evidence = MODULE.load_projection_contract(
                policy, {"inventory": root}
            )
            self.assertEqual(loaded, contract)
            self.assertEqual(loaded_payload, payload)
            self.assertEqual(evidence["sha256"], MODULE.sha256_bytes(payload))

            wrong_digest = copy.deepcopy(policy)
            wrong_digest["projection_contract"]["sha256"] = "f" * 64
            with self.assertRaisesRegex(MODULE.ContractError, "pinned digest"):
                MODULE.load_projection_contract(wrong_digest, {"inventory": root})

            contract_path.chmod(0o600)
            contract_path.write_bytes(payload + b" ")
            contract_path.chmod(0o400)
            with self.assertRaisesRegex(MODULE.ContractError, "pinned digest"):
                MODULE.load_projection_contract(policy, {"inventory": root})

    def test_generic_recorder_contains_no_environment_topology_literals(self):
        source = SCRIPT.read_text(encoding="utf-8")
        for forbidden in (
            "10.10.30.23",
            "wunderbox01-edge.mgmt.corp.l-it.io",
            "wunderbox01.prd.edge.pub.l-it.io",
            "enp4s0.4091",
            "153.53.58.197",
            "2a01:4f8:212:69e::/64",
            "LIT-PIS-ADR-WBX-016",
        ):
            self.assertNotIn(forbidden, source)

    def test_inventory_projection_is_exactly_target_controller_and_lifecycle_bound(
        self,
    ):
        manifest = sample_manifest("f" * 64)
        target = manifest["target"]
        controller = manifest["controller"]
        management_services = {
            "bootstrap_ssh": {
                "port": 22,
                "modes": ["bootstrap"],
                "sources_ipv4": [controller["source_cidr"]],
                "sources_ipv6": [],
            },
            "openssh": {
                "port": 1905,
                "modes": ["bootstrap", "hardened"],
                "sources_ipv4": [controller["source_cidr"]],
                "sources_ipv6": [],
            },
            "dropbear": {
                "port": 2222,
                "modes": ["bootstrap", "hardened"],
                "sources_ipv4": [controller["source_cidr"]],
                "sources_ipv6": [],
            },
        }
        tang_sources = ["192.0.2.30/32", "192.0.2.31/32", "192.0.2.32/32"]

        def provider_rule(port, source, name):
            return {
                "ip_version": "ipv4",
                "protocol": "tcp",
                "src_ip": source,
                "dst_ip": target["public_ipv4"],
                "dst_port": str(port),
                "name": name,
                "action": "accept",
            }

        egress_policies = sample_host_firewall_egress_policies()
        egress_digest = MODULE.sha256_bytes(
            MODULE.canonical_json_bytes(egress_policies)
        )
        pending_dns = "PENDING - test DNS readback required"
        pending_ipv6 = "PENDING - test provider IPv6 readback required"
        egress_selector = "{{ host_firewall_egress_policies[host_firewall_mode] }}"
        ipv4_only_baseline = {
            "decision_id": "TEST-ADR-1",
            "evidence_id": "TEST-EV-1",
            "evidence_sha256": "1" * 64,
            "installimage_ipv4_only": True,
            "cis_ipv4_required": True,
            "cis_ipv6_required": False,
            "cis_ipv6_disable": "test-disable-mode",
            "kernel_ipv6_disabled": True,
            "netplan": {
                "dhcp6": False,
                "accept_ra": False,
                "link_local": [],
                "source_ipv6": [],
                "destination_ipv6": [],
            },
            "dns": {"aaaa_records": []},
            "provider": {
                "required_filter_enabled": True,
                "ipv6_rules": [],
                "assigned_prefix": "2001:db8::/64",
                "assignment_state": "assigned-but-unconfigured",
            },
        }
        document = {
            "ansible_host": target["public_ipv4"],
            "hostname_fqdn": target["fqdn"],
            "hostname_etc_hosts_ip": target["public_ipv4"],
            "hetzner_robot_server_number": target["provider_id"],
            "wunderbox_dns_identity": {
                "schema_version": 1,
                "desired": {
                    "public": {
                        "fqdn": target["fqdn"],
                        "a_records": [target["public_ipv4"]],
                        "ptr_records": [target["fqdn"]],
                        "aaaa_records": [],
                        "cname_records": [],
                    },
                    "management": {
                        "fqdn": "wunderbox01-edge.mgmt.corp.l-it.io",
                        "a_records": ["10.10.30.23"],
                        "aaaa_records": [],
                        "cname_records": [],
                    },
                },
                "verification": {
                    "accepted": False,
                    "fresh_readback": False,
                    "evidence_reference": pending_dns,
                },
            },
            "wunderbox_inventory_contract": {
                "target_id": target["target_id"],
                "provider": {"server_id": target["provider_id"]},
                "public_identity": {
                    "fqdn": target["fqdn"],
                    "ipv4": target["public_ipv4"],
                },
                "ipv4_only_baseline": copy.deepcopy(ipv4_only_baseline),
                "controller_access": {
                    "management_services": management_services,
                },
            },
            "host_firewall_enabled": False,
            "host_firewall_action": "plan",
            "host_firewall_mode": "bootstrap",
            "host_firewall_expected_inventory_hostname": target["fqdn"],
            "host_firewall_expected_public_ipv4": target["public_ipv4"],
            "host_firewall_expected_management_ipv4": "10.10.30.23",
            "host_firewall_expected_public_ipv6": "",
            "host_firewall_expected_management_ipv6": "",
            "host_firewall_public_interface": "enp4s0",
            "host_firewall_management_interface": "enp4s0.4091",
            "host_firewall_management_access": management_services,
            "host_firewall_controller_source_cidrs": [],
            "host_firewall_recovery_source_cidrs": [],
            "host_firewall_tang_access": {
                "port": 80,
                "sources_ipv4": tang_sources,
                "sources_ipv6": [],
            },
            "host_firewall_egress_policies": egress_policies,
            "host_firewall_egress_policy": (egress_selector),
            "host_firewall_provider_ipv6_filter_enabled": False,
            "host_firewall_provider_ipv6_filter_evidence_reference": (pending_ipv6),
            "hetzner_baremetal_robot_firewall_bootstrap_input_rules": [
                provider_rule(22, controller["source_cidr"], "bootstrap SSH")
            ],
            "hetzner_baremetal_robot_firewall_hardened_input_rules": [
                provider_rule(1905, controller["source_cidr"], "OpenSSH"),
                provider_rule(2222, controller["source_cidr"], "Dropbear"),
                {
                    "ip_version": "ipv4",
                    "protocol": "icmp",
                    "name": "ICMP",
                    "action": "accept",
                },
            ],
            "hetzner_baremetal_robot_firewall_deferred_tang_input_rules": [
                provider_rule(80, source, f"Tang {index}")
                for index, source in enumerate(tang_sources, start=1)
            ],
            "hetzner_installimage_layout": {"ipv4_only": True},
            "ubtu24cis_ipv4_required": True,
            "ubtu24cis_ipv6_required": False,
            "ubtu24cis_ipv6_disable": "grub",
            "netplan_ethernets": {
                "enp4s0": {
                    "dhcp4": False,
                    "dhcp6": False,
                    "accept-ra": False,
                    "link-local": [],
                    "addresses": [f"{target['public_ipv4']}/24"],
                    "routes": [{"to": "default", "via": "192.0.2.1"}],
                    "nameservers": {"addresses": ["192.0.2.53"]},
                }
            },
            "netplan_vlans": {
                "enp4s0.4091": {
                    "id": 4091,
                    "link": "enp4s0",
                    "addresses": ["10.10.30.23/24"],
                    "dhcp6": False,
                    "accept-ra": False,
                    "link-local": [],
                    "mtu": 1400,
                    "optional": True,
                }
            },
            "hetzner_baremetal_robot_firewall": {
                "enabled": True,
                "admin_ipv4": "153.53.58.197",
                "filter_ipv6": True,
            },
            "wunderbox_orchestration": {
                "target": {
                    "id": target["target_id"],
                    "fqdn": target["fqdn"],
                    "ipv4": target["public_ipv4"],
                    "provider_id": target["provider_id"],
                }
            },
            "hetzner_baremetal_root_of_trust": {
                "inventory_hostname": target["fqdn"],
                "controller_ipv4_cidr": controller["source_cidr"],
                "server_lifecycle": {"status": "ready", "cancelled": False},
            },
        }
        projection_contract = sample_projection_contract(document, target, controller)
        projection = MODULE.validate_inventory_target_projection(
            document, target, controller, projection_contract
        )
        self.assertEqual(projection["target"], target)
        self.assertEqual(projection["schema_version"], 3)
        self.assertEqual(
            projection["effective_access"]["management_services"]["openssh"],
            {
                "protocol": "tcp",
                "port": 1905,
                "modes": ["bootstrap", "hardened"],
                "sources_ipv4": [controller["source_cidr"]],
                "sources_ipv6": [],
            },
        )
        self.assertEqual(
            projection["effective_access"]["tang"]["provider_sources_ipv4"],
            tang_sources,
        )
        self.assertEqual(
            projection["host_firewall_contract"]["egress_policies_sha256"],
            egress_digest,
        )
        self.assertEqual(
            projection["host_firewall_contract"]["provider_ipv6_filter"]["claim_basis"],
            "PENDING_EXTERNAL_READBACK",
        )
        document["host_firewall_egress_policy"] = (
            "{{ host_firewall_egress_policies.get(host_firewall_mode, "
            "host_firewall_egress_policies.bootstrap) }}"
        )
        with self.assertRaisesRegex(MODULE.ContractError, "selector"):
            MODULE.validate_inventory_target_projection(
                document, target, controller, projection_contract
            )
        document["host_firewall_egress_policy"] = egress_selector
        document["wunderbox_dns_identity"]["verification"] = {
            "accepted": True,
            "fresh_readback": False,
            "evidence_reference": "WBX-EV-002-Supplement",
        }
        with self.assertRaisesRegex(MODULE.ContractError, "DNS/rDNS"):
            MODULE.validate_inventory_target_projection(
                document, target, controller, projection_contract
            )
        document["wunderbox_dns_identity"]["verification"] = {
            "accepted": False,
            "fresh_readback": False,
            "evidence_reference": pending_dns,
        }
        document["hetzner_baremetal_robot_firewall"]["admin_ipv4"] = "213.232.86.209"
        with self.assertRaisesRegex(MODULE.ContractError, "IPv4-only"):
            MODULE.validate_inventory_target_projection(
                document, target, controller, projection_contract
            )
        document["hetzner_baremetal_robot_firewall"]["admin_ipv4"] = "153.53.58.197"
        document["host_firewall_egress_policies"]["hardened"]["functions"][
            "atlas_loki"
        ]["destinations_ipv4"] = ["10.10.30.99/32"]
        with self.assertRaisesRegex(MODULE.ContractError, "egress policies"):
            MODULE.validate_inventory_target_projection(
                document, target, controller, projection_contract
            )
        egress_policies = sample_host_firewall_egress_policies()
        document["host_firewall_egress_policies"] = egress_policies
        document["host_firewall_egress_policy"] = egress_selector
        document["wunderbox_orchestration"]["target"]["ipv4"] = "192.0.2.99"
        with self.assertRaisesRegex(MODULE.ContractError, "IPv4"):
            MODULE.validate_inventory_target_projection(
                document, target, controller, projection_contract
            )
        document["wunderbox_orchestration"]["target"]["ipv4"] = target["public_ipv4"]
        document["netplan_ethernets"]["enp4s0"]["dhcp6"] = True
        with self.assertRaisesRegex(MODULE.ContractError, "contract-exact"):
            MODULE.validate_inventory_target_projection(
                document, target, controller, projection_contract
            )

    def test_inventory_projection_rejects_cross_port_and_tang_policy_drift(self):
        manifest = sample_manifest("f" * 64)
        target = manifest["target"]
        controller = manifest["controller"]
        management = {
            name: {
                "port": port,
                "modes": modes,
                "sources_ipv4": [controller["source_cidr"]],
                "sources_ipv6": [],
            }
            for name, port, modes in (
                ("bootstrap_ssh", 22, ["bootstrap"]),
                ("openssh", 1905, ["bootstrap", "hardened"]),
                ("dropbear", 2222, ["bootstrap", "hardened"]),
            )
        }

        def rule(port, source):
            return {
                "ip_version": "ipv4",
                "protocol": "tcp",
                "src_ip": source,
                "dst_ip": target["public_ipv4"],
                "dst_port": str(port),
                "action": "accept",
            }

        tang_sources = ["192.0.2.30/32"]
        document = {
            "wunderbox_inventory_contract": {
                "controller_access": {"management_services": management}
            },
            "host_firewall_management_access": copy.deepcopy(management),
            "host_firewall_controller_source_cidrs": [],
            "host_firewall_recovery_source_cidrs": [],
            "host_firewall_tang_access": {
                "port": 80,
                "sources_ipv4": tang_sources,
                "sources_ipv6": [],
            },
            "hetzner_baremetal_robot_firewall_bootstrap_input_rules": [
                rule(22, controller["source_cidr"])
            ],
            "hetzner_baremetal_robot_firewall_hardened_input_rules": [
                rule(1905, controller["source_cidr"]),
                rule(2222, controller["source_cidr"]),
            ],
            "hetzner_baremetal_robot_firewall_deferred_tang_input_rules": [
                rule(80, tang_sources[0])
            ],
        }
        expectations = {
            "management_services": copy.deepcopy(management),
            "provider_input_rules": {
                "bootstrap": copy.deepcopy(
                    document["hetzner_baremetal_robot_firewall_bootstrap_input_rules"]
                ),
                "hardened": copy.deepcopy(
                    document["hetzner_baremetal_robot_firewall_hardened_input_rules"]
                ),
                "tang": copy.deepcopy(
                    document[
                        "hetzner_baremetal_robot_firewall_deferred_tang_input_rules"
                    ]
                ),
            },
            "tang_access": copy.deepcopy(document["host_firewall_tang_access"]),
            "legacy_aggregate_sources": {"controller": [], "recovery": []},
        }
        MODULE.validate_effective_inventory_access(
            document,
            controller_source_cidr=controller["source_cidr"],
            target_ipv4=target["public_ipv4"],
            expectations=expectations,
        )

        document["host_firewall_management_access"]["openssh"]["sources_ipv4"] = [
            "192.0.2.99/32"
        ]
        with self.assertRaisesRegex(MODULE.ContractError, "do not equal"):
            MODULE.validate_effective_inventory_access(
                document,
                controller_source_cidr=controller["source_cidr"],
                target_ipv4=target["public_ipv4"],
                expectations=expectations,
            )
        document["host_firewall_management_access"] = copy.deepcopy(management)
        document["hetzner_baremetal_robot_firewall_hardened_input_rules"].append(
            {
                "ip_version": "ipv4",
                "protocol": "tcp",
                "dst_ip": target["public_ipv4"],
                "action": "accept",
            }
        )
        with self.assertRaisesRegex(MODULE.ContractError, "pinned contract"):
            MODULE.validate_effective_inventory_access(
                document,
                controller_source_cidr=controller["source_cidr"],
                target_ipv4=target["public_ipv4"],
                expectations=expectations,
            )
        document["hetzner_baremetal_robot_firewall_hardened_input_rules"].pop()
        document["hetzner_baremetal_robot_firewall_deferred_tang_input_rules"][0][
            "src_ip"
        ] = "192.0.2.98/32"
        with self.assertRaisesRegex(MODULE.ContractError, "pinned contract"):
            MODULE.validate_effective_inventory_access(
                document,
                controller_source_cidr=controller["source_cidr"],
                target_ipv4=target["public_ipv4"],
                expectations=expectations,
            )

    def test_typed_artifact_rejects_extra_fields_and_target_mismatch(self):
        target = sample_manifest("f" * 64)["target"]
        action = {
            "artifact_schema": {
                "schema_id": "test.target-plan.v1",
                "fields": {
                    "identity.fqdn": {"type": "string", "binding": "fqdn"},
                    "checks": {"type": "integer"},
                },
            }
        }
        payload = {"identity": {"fqdn": target["fqdn"]}, "checks": 3}
        artifact = MODULE.validate_typed_artifact(
            payload, "target_plan", action, "WBX-EXE-321-A001", target
        )
        self.assertEqual(artifact["target"], target)
        with self.assertRaises(MODULE.ContractError):
            MODULE.validate_typed_artifact(
                {**payload, "unexpected": True},
                "target_plan",
                action,
                "WBX-EXE-321-A001",
                target,
            )
        payload["identity"]["fqdn"] = "other.example.test"
        with self.assertRaisesRegex(MODULE.ContractError, "target binding"):
            MODULE.validate_typed_artifact(
                payload,
                "target_plan",
                action,
                "WBX-EXE-321-A001",
                target,
            )

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
        with tempfile.TemporaryDirectory() as directory:
            runtime = Path(directory) / "runtime"
            runtime.mkdir(mode=0o700)
            with mock.patch.dict(os.environ, {"PATH": "/usr/bin"}, clear=True):
                environment = MODULE.make_environment(
                    manifest,
                    "target_plan",
                    {
                        **sample_policy()["actions"]["target_plan"],
                        "impact": "local_validation",
                    },
                    container_engine=sample_container_engine(),
                    runtime_root=runtime,
                )
        self.assertEqual(environment["ANSIBLE_TOOLBOX_PULL_POLICY"], "never")
        self.assertIn("@sha256:", environment["ANSIBLE_TOOLBOX_RUN_EE_IMAGE"])
        self.assertNotIn("VAULT_TOKEN", environment)

    def test_environment_rejects_ambient_vault_password_transport(self):
        manifest = sample_manifest("f" * 64)
        with tempfile.TemporaryDirectory() as directory:
            runtime = Path(directory) / "runtime"
            runtime.mkdir(mode=0o700)
            with mock.patch.dict(
                os.environ,
                {
                    "PATH": "/usr/bin",
                    "ANSIBLE_VAULT_PASSWORD_FILE": "/private/unrelated-vault-file",
                },
                clear=True,
            ):
                with self.assertRaisesRegex(
                    MODULE.ContractError, "forbidden secret-bearing environment"
                ):
                    MODULE.make_environment(
                        manifest,
                        "target_plan",
                        {
                            **sample_policy()["actions"]["target_plan"],
                            "impact": "local_validation",
                        },
                        container_engine=sample_container_engine(),
                        runtime_root=runtime,
                    )

    def test_live_environment_binds_one_owner_only_private_key_directory(self):
        manifest = sample_manifest("f" * 64)
        action = sample_policy()["actions"]["target_plan"]
        with tempfile.TemporaryDirectory() as directory:
            ssh_source = Path(directory) / "ssh"
            ssh_source.mkdir(mode=0o700)
            private_key = ssh_source / "id_test"
            private_key.write_bytes(b"test-private-key-material\n")
            private_key.chmod(0o600)
            known_hosts = ssh_source / "known_hosts_test"
            known_hosts.write_bytes(b"host.example.test ssh-ed25519 AAAAtest\n")
            known_hosts.chmod(0o400)
            manifest["controller"]["ssh"] = {
                "source_directory": str(ssh_source),
                "private_key_name": private_key.name,
                "private_key_sha256": MODULE.sha256_file(private_key),
                "known_hosts_name": known_hosts.name,
                "known_hosts_sha256": MODULE.sha256_file(known_hosts),
            }
            runtime = Path(directory) / "runtime"
            runtime.mkdir(mode=0o700)
            sealed = MODULE.seal_controller_ssh_inputs(
                manifest, action, runtime / "controller-ssh"
            )
            with mock.patch.dict(os.environ, {"PATH": "/usr/bin"}, clear=True):
                environment = MODULE.make_environment(
                    manifest,
                    "target_plan",
                    action,
                    container_engine=sample_container_engine(),
                    sealed_ssh_directory=sealed,
                    runtime_root=runtime,
                )
        self.assertEqual(environment["ANSIBLE_TOOLBOX_MOUNT_SSH"], "false")
        self.assertEqual(
            Path(environment["ANSIBLE_TOOLBOX_SSH_PRIVATE_KEY_FILE"]).name,
            "id_selected",
        )
        self.assertEqual(
            environment["ANSIBLE_TOOLBOX_SSH_PRIVATE_KEY_SHA256"],
            manifest["controller"]["ssh"]["private_key_sha256"],
        )
        self.assertEqual(
            environment["ANSIBLE_TOOLBOX_SSH_KNOWN_HOSTS_SHA256"],
            manifest["controller"]["ssh"]["known_hosts_sha256"],
        )

    def test_agent_bound_action_fails_before_start_without_socket(self):
        action = {
            **sample_policy()["actions"]["target_plan"],
            "requires_ssh_private_key": False,
            "requires_ssh_agent": True,
        }
        with tempfile.TemporaryDirectory() as directory:
            runtime = Path(directory) / "runtime"
            runtime.mkdir(mode=0o700)
            with mock.patch.dict(os.environ, {"PATH": "/usr/bin"}, clear=True):
                with self.assertRaises(MODULE.ContractError):
                    MODULE.make_environment(
                        sample_manifest("f" * 64),
                        "target_plan",
                        action,
                        container_engine=sample_container_engine(),
                        runtime_root=runtime,
                    )


if __name__ == "__main__":
    unittest.main()
