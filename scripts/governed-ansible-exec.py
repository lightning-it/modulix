#!/usr/bin/env python3
"""Execute one policy-bound Ansible action and create candidate evidence.

The recorder is deliberately generic.  Environment-specific target identity,
gate state, approvals, repository commits, and runtime image digests are read
from a signed manifest supplied by a private validation adapter.  The recorder
does not accept an arbitrary command line and never treats caller prose as an
authorization boundary.

The recorder keeps its subprocess capture bounded in memory.  Ansible Runner's
unavoidable raw artifacts are redirected into one owner-only private runtime
tree and the final record reports them as absent only after verified cleanup.
A started journal is written before governed process creation and a separate
final record is written afterwards.  Both are local integrity artifacts;
independent review and an external hash/signature anchor remain required for
acceptance.
"""

from __future__ import annotations

import argparse
import base64
import binascii
import datetime as dt
import hashlib
import hmac
import ipaddress
import json
import os
from pathlib import Path
import re
import selectors
import shlex
import shutil
import signal
import stat
import struct
import subprocess
import sys
import tempfile
import time
import unicodedata
from typing import Any, Callable, Iterable


SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
GIT_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
BRANCH_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,199}$")
ACTION_ID_RE = re.compile(r"^[a-z][a-z0-9_]{2,79}$")
RECORD_PREFIX_RE = re.compile(r"^[0-9]{3}$")
JIRA_RE = re.compile(r"^[A-Z][A-Z0-9]+-[0-9]+$")
IMAGE_DIGEST_RE = re.compile(r"^[^\s@]+@sha256:[0-9a-f]{64}$")
SSH_FINGERPRINT_RE = re.compile(r"^SHA256:[A-Za-z0-9+/]{43}$")
EVENT_PREFIX = "LIT_GOVERNED_EVENT="
CONTROLLER_TRUST_DESCRIPTOR = Path(
    "/Library/Application Support/Lightning IT/Governed Ansible/controller-trust.json"
)
SYSTEM_GIT = Path("/usr/bin/git")
FOUNDATIONAL_APPROVAL_NAMESPACE = "lit-onepassword-approval-v1"
MAX_APPROVAL_SECONDS = 900
MAX_CLOCK_SKEW_SECONDS = 60
MAX_SNAPSHOT_FILES = 100_000
MAX_SNAPSHOT_BYTES = 256 * 1024 * 1024
MAX_SNAPSHOT_FILE_BYTES = 64 * 1024 * 1024
MAX_GIT_LISTING_BYTES = 64 * 1024 * 1024
MAX_GIT_TREE_DEPTH = 64
SECRET_KEY_RE = re.compile(
    r"(?i)(?:password|passphrase|token|secret|private[_-]?key|credential|"
    r"recovery[_-]?key|unseal|root[_-]?token)"
)
URI_CREDENTIAL_RE = re.compile(r"(?:^|=)[a-z][a-z0-9+.-]*://[^/@\s]+:[^/@\s]+@", re.I)
FORBIDDEN_EXECUTION_ENV_RE = re.compile(
    r"(?i)^(?:VAULT_TOKEN|RH_AUTOMATION_HUB_TOKEN|OP_CONNECT_TOKEN|"
    r"OP_SERVICE_ACCOUNT_TOKEN|OP_SESSION_.+|ANSIBLE_.+(?:PASSWORD|PASSPHRASE|"
    r"TOKEN|SECRET|PRIVATE_KEY|CREDENTIAL).*)$"
)
FORBIDDEN_OVERRIDE_KEYS = {
    "ansible_host",
    "ansible_limit",
    "inventory_hostname",
    "hetzner_baremetal_server_id",
    "hetzner_baremetal_expected_server_number",
    "hetzner_installimage_expected_disks",
    "hetzner_installimage_expected_identity",
}
ALLOWED_IMPACTS = {
    "local_validation",
    "controller_read",
    "target_read",
    "security_relevant",
    "availability",
    "destructive",
    "recovery",
}
LIVE_IMPACTS = ALLOWED_IMPACTS - {"local_validation", "controller_read"}
ALLOWED_GATE_STATES = {"NOT_STARTED", "IN_PROGRESS", "ACCEPTED", "BLOCKED"}
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
APPROVAL_AUTHORITY_KEYS = {
    "schema_version",
    "identity",
    "namespace",
    "fingerprint",
    "allowed_signers_path",
    "allowed_signers_sha256",
    "ssh_keygen_path",
    "ssh_keygen_sha256",
    "replay_directory",
}
SIGNATURE_TRUST_KEYS = {
    "identity",
    "namespace",
    "allowed_signers_path",
    "allowed_signers_sha256",
    "ssh_keygen_path",
    "ssh_keygen_sha256",
}
CONTROLLER_TRUST_KEYS = {
    "schema_version",
    "policy",
    "execution_anchor",
    "replay_broker",
    "container_engine",
    "manifest_signature",
    "runtime_attestation_signature",
    "approval_authority",
}
EXECUTION_ANCHOR_KEYS = {
    "launcher",
    "interpreter",
    "recorder",
    "acceptance_receipt",
}
REPLAY_BROKER_KEYS = {"kind", "path", "sha256", "store_id"}
ANCHOR_RECEIPT_KEYS = {
    "schema_version",
    "status",
    "launcher_sha256",
    "interpreter_sha256",
    "recorder_sha256",
    "replay_broker_sha256",
    "container_engine_sha256",
    "negative_replay_test",
    "controller_readback_test",
}
PINNED_FILE_KEYS = {"path", "sha256"}
PINNED_EXECUTABLE_KEYS = {"kind", "path", "sha256"}
CONTAINER_ENGINE_KEYS = PINNED_EXECUTABLE_KEYS | {
    "backend_uri",
    "backend_identity_sha256",
}
MANIFEST_KEYS = {
    "schema_version",
    "manifest_status",
    "policy_sha256",
    "safety_hold",
    "target",
    "controller",
    "runtime",
    "gates",
    "repositories",
    "authorizations",
}
TARGET_KEYS = {"target_id", "fqdn", "public_ipv4", "provider_id"}
CONTROLLER_KEYS = {"device_id", "source_cidr", "ssh"}
CONTROLLER_SSH_KEYS = {
    "source_directory",
    "private_key_name",
    "private_key_sha256",
    "known_hosts_name",
    "known_hosts_sha256",
}
RUNTIME_KEYS = {
    "toolbox_image",
    "run_ee_image",
    "attestation_path",
    "attestation_sha256",
    "attestation_signature_path",
}
RUNTIME_ATTESTATION_KEYS = {"schema_version", "toolbox", "run_ee"}
RUNTIME_PROVENANCE_KEYS = {
    "schema_version",
    "image_role",
    "image",
    "loader",
    "collections",
}
RUNTIME_LOADER_KEYS = {"collection_paths", "scan_sys_path"}
EXPECTED_RUNTIME_LOADER = {
    "collection_paths": [
        "/usr/share/ansible/collections",
        "/usr/share/automation-controller/collections",
    ],
    "scan_sys_path": False,
}
INVENTORY_PROJECTION_PATHS = [
    "hostname_fqdn",
    "hostname_etc_hosts_ip",
    "hetzner_robot_server_number",
    "hetzner_baremetal_root_of_trust.schema_version",
    "hetzner_baremetal_root_of_trust.selection_scope",
    "hetzner_baremetal_root_of_trust.inventory_hostname",
    "hetzner_baremetal_root_of_trust.controller_ipv4_cidr",
    "hetzner_baremetal_root_of_trust.server_lifecycle.status",
    "hetzner_baremetal_root_of_trust.server_lifecycle.cancelled",
    "wunderbox_inventory_contract.controller_access.management_services",
    "host_firewall_management_access",
    "host_firewall_tang_access",
    "host_firewall_controller_source_cidrs",
    "host_firewall_recovery_source_cidrs",
    "hetzner_baremetal_robot_firewall_bootstrap_input_rules",
    "hetzner_baremetal_robot_firewall_hardened_input_rules",
    "hetzner_baremetal_robot_firewall_deferred_tang_input_rules",
]
COLLECTION_PROVENANCE_KEYS = {
    "fqcn",
    "version",
    "source_commit",
    "installed_tree_sha256",
}
PROBE_COLLECTION_KEYS = {"fqcn", "version", "installed_tree_sha256"}
AUTHORIZATION_BASE_KEYS = {
    "status",
    "approval_reference",
    "approval_sha256",
    "not_before_utc",
    "expires_utc",
    "execution_approval",
    "consumer_approval_contracts",
}
APPROVAL_CONTRACT_KEYS = {"operation", "target", "binding"}
POLICY_KEYS = {
    "schema_version",
    "policy_id",
    "required_repositories",
    "required_collections",
    "collection_repositories",
    "target_contract",
    "actions",
}
ARTIFACT_SCHEMA_KEYS = {"schema_id", "fields"}
ARTIFACT_FIELD_TYPES = {
    "string",
    "integer",
    "boolean",
    "mapping",
    "sequence",
    "sha256",
    "ssh_fingerprint",
    "ipv4",
}


class ContractError(RuntimeError):
    """Raised before execution or when produced output violates the contract."""


def utc_now() -> str:
    return (
        dt.datetime.now(dt.timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )


def parse_utc(value: str, label: str) -> dt.datetime:
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise ContractError(f"{label} must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise ContractError(f"{label} must include a timezone")
    return parsed.astimezone(dt.timezone.utc)


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")


def require_exact_keys(value: dict[str, Any], expected: set[str], label: str) -> None:
    if set(value) != expected:
        missing = sorted(expected - set(value))
        unexpected = sorted(set(value) - expected)
        raise ContractError(
            f"{label} has an invalid exact-key schema; "
            f"missing={missing}, unexpected={unexpected}"
        )


def _validate_trusted_parent_chain(
    path: Path, label: str, trusted_uids: set[int]
) -> None:
    current = path
    while True:
        status = os.lstat(current)
        if not stat.S_ISDIR(status.st_mode) or stat.S_ISLNK(status.st_mode):
            raise ContractError(f"a parent of {label} is not a real directory")
        if status.st_uid not in trusted_uids:
            raise ContractError(f"a parent of {label} has an untrusted owner")
        if status.st_mode & 0o022:
            raise ContractError(f"a parent of {label} is group/world writable")
        if current.parent == current:
            break
        current = current.parent


def read_trusted_file(
    path: Path,
    label: str,
    *,
    trusted_uids: set[int],
    expected_sha256: str | None = None,
    maximum_size: int = 2 * 1024 * 1024,
    executable: bool = False,
) -> tuple[Path, bytes]:
    raw = str(path)
    if (
        not path.is_absolute()
        or os.path.normpath(raw) != raw
        or any(character in raw for character in "\x00\r\n")
    ):
        raise ContractError(f"{label} must use one normalized absolute path")
    try:
        resolved = path.resolve(strict=True)
    except OSError as exc:
        raise ContractError(f"{label} does not exist") from exc
    if resolved != path:
        raise ContractError(f"{label} path or parent chain contains a symbolic link")
    _validate_trusted_parent_chain(resolved.parent, label, trusted_uids)
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(resolved, flags)
    except OSError as exc:
        raise ContractError(
            f"{label} could not be opened without following links"
        ) from exc
    payload = bytearray()
    try:
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_nlink != 1
            or before.st_uid not in trusted_uids
            or before.st_mode & 0o022
        ):
            raise ContractError(f"{label} has unsafe ownership, type, links, or mode")
        if executable and not before.st_mode & 0o111:
            raise ContractError(f"{label} is not executable")
        if before.st_size <= 0 or before.st_size > maximum_size:
            raise ContractError(f"{label} is empty or exceeds its size boundary")
        while chunk := os.read(descriptor, min(1024 * 1024, maximum_size + 1)):
            payload.extend(chunk)
            if len(payload) > maximum_size:
                raise ContractError(f"{label} exceeds its size boundary")
        after = os.fstat(descriptor)
        identity_before = (
            before.st_dev,
            before.st_ino,
            before.st_size,
            before.st_mtime_ns,
            before.st_ctime_ns,
        )
        identity_after = (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
            after.st_ctime_ns,
        )
        if identity_before != identity_after:
            raise ContractError(f"{label} changed while it was inspected")
    finally:
        os.close(descriptor)
    observed = sha256_bytes(bytes(payload))
    if expected_sha256 is not None and not hmac.compare_digest(
        observed, expected_sha256
    ):
        raise ContractError(f"{label} does not match its pinned SHA-256")
    return resolved, bytes(payload)


def _ed25519_fingerprint(public_key: str) -> str:
    fields = public_key.split()
    if len(fields) != 2 or fields[0] != "ssh-ed25519":
        raise ContractError("approval authority must use one Ed25519 public key")
    try:
        blob = base64.b64decode(fields[1], validate=True)
        algorithm_length = struct.unpack(">I", blob[0:4])[0]
        algorithm = blob[4 : 4 + algorithm_length]
        offset = 4 + algorithm_length
        key_length = struct.unpack(">I", blob[offset : offset + 4])[0]
        key = blob[offset + 4 :]
    except (binascii.Error, ValueError, struct.error) as exc:
        raise ContractError(
            "approval authority public-key encoding is invalid"
        ) from exc
    if algorithm != b"ssh-ed25519" or key_length != 32 or len(key) != 32:
        raise ContractError("approval authority Ed25519 key blob is invalid")
    digest = base64.b64encode(hashlib.sha256(blob).digest()).decode("ascii")
    return f"SHA256:{digest.rstrip('=')}"


def parse_allowed_signers(
    payload: bytes, identity: str, expected_fingerprint: str
) -> dict[str, str]:
    try:
        rows = payload.decode("ascii").splitlines()
    except UnicodeDecodeError as exc:
        raise ContractError("allowed signers must contain ASCII") from exc
    entries = [
        row.strip() for row in rows if row.strip() and not row.lstrip().startswith("#")
    ]
    if len(entries) != 1:
        raise ContractError("allowed signers must contain exactly one signer")
    fields = entries[0].split()
    if len(fields) not in {3, 4}:
        raise ContractError("allowed signer entry is invalid or contains options")
    principal, key_type, encoded_key = fields[:3]
    if principal != identity or any(character in principal for character in "*,!"):
        raise ContractError("allowed signer principal does not match its pin")
    if key_type != "ssh-ed25519":
        raise ContractError("allowed signer must use Ed25519")
    fingerprint = _ed25519_fingerprint(f"ssh-ed25519 {encoded_key}")
    if not hmac.compare_digest(fingerprint, expected_fingerprint):
        raise ContractError("allowed signer fingerprint does not match its pin")
    return {
        "fingerprint": fingerprint,
        "entry_sha256": sha256_bytes(entries[0].encode("ascii")),
    }


def require_controller_replay_directory(
    path: Path, label: str
) -> tuple[Path, os.stat_result]:
    raw = str(path)
    if not path.is_absolute() or os.path.normpath(raw) != raw:
        raise ContractError(f"{label} must be one canonical absolute path")
    resolved = path.resolve(strict=True)
    if resolved != path or path.is_symlink():
        raise ContractError(f"{label} must not contain symbolic links")
    status = os.lstat(path)
    if (
        not stat.S_ISDIR(status.st_mode)
        or status.st_uid != os.geteuid()
        or stat.S_IMODE(status.st_mode) != 0o700
    ):
        raise ContractError(f"{label} must be an effective-user-owned 0700 directory")
    _validate_trusted_parent_chain(path.parent, label, {0, os.geteuid()})
    return resolved, status


def validate_signature_trust(
    value: Any, label: str, *, trusted_uids: set[int]
) -> dict[str, Any]:
    trust = require_mapping(value, label)
    require_exact_keys(trust, SIGNATURE_TRUST_KEYS, label)
    identity = str(trust["identity"])
    namespace = str(trust["namespace"])
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._@+-]{0,127}", identity):
        raise ContractError(f"{label} identity is invalid")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", namespace):
        raise ContractError(f"{label} namespace is invalid")
    for key in ("allowed_signers_sha256", "ssh_keygen_sha256"):
        if not SHA256_RE.fullmatch(str(trust[key])):
            raise ContractError(f"{label} {key} is invalid")
    signers_path, signers_payload = read_trusted_file(
        Path(str(trust["allowed_signers_path"])),
        f"{label} allowed signers",
        trusted_uids=trusted_uids,
        expected_sha256=str(trust["allowed_signers_sha256"]),
        maximum_size=65536,
    )
    verifier_path, _verifier_payload = read_trusted_file(
        Path(str(trust["ssh_keygen_path"])),
        f"{label} ssh-keygen",
        trusted_uids=trusted_uids,
        expected_sha256=str(trust["ssh_keygen_sha256"]),
        maximum_size=16 * 1024 * 1024,
        executable=True,
    )
    return {
        **trust,
        "allowed_signers_path": str(signers_path),
        "ssh_keygen_path": str(verifier_path),
        "_allowed_signers_payload": signers_payload,
        "_trusted_uids": frozenset(trusted_uids),
    }


def validate_approval_authority(
    value: Any, *, trusted_uids: set[int]
) -> dict[str, Any]:
    authority = require_mapping(value, "approval authority")
    require_exact_keys(authority, APPROVAL_AUTHORITY_KEYS, "approval authority")
    if authority.get("schema_version") != 1:
        raise ContractError("approval authority schema_version must be 1")
    if authority.get("namespace") != FOUNDATIONAL_APPROVAL_NAMESPACE:
        raise ContractError(
            "approval authority namespace is not the Foundational contract"
        )
    signature_trust = validate_signature_trust(
        {key: authority[key] for key in SIGNATURE_TRUST_KEYS},
        "approval authority",
        trusted_uids=trusted_uids,
    )
    fingerprint = str(authority["fingerprint"])
    if not SSH_FINGERPRINT_RE.fullmatch(fingerprint):
        raise ContractError("approval authority fingerprint is invalid")
    signer = parse_allowed_signers(
        signature_trust["_allowed_signers_payload"],
        str(authority["identity"]),
        fingerprint,
    )
    replay_directory, replay_status = require_controller_replay_directory(
        Path(str(authority["replay_directory"])), "approval authority replay directory"
    )
    return {
        **authority,
        **signature_trust,
        "fingerprint": signer["fingerprint"],
        "allowed_signers_entry_sha256": signer["entry_sha256"],
        "replay_directory": str(replay_directory),
        "_replay_directory_device": replay_status.st_dev,
        "_replay_directory_inode": replay_status.st_ino,
    }


def load_controller_trust(
    path: Path = CONTROLLER_TRUST_DESCRIPTOR,
    *,
    trusted_uids: set[int] | None = None,
) -> tuple[dict[str, Any], dict[str, Any], bytes]:
    effective_trusted_uids = {0} if trusted_uids is None else set(trusted_uids)
    descriptor_path, descriptor_payload = read_trusted_file(
        path,
        "controller trust descriptor",
        trusted_uids=effective_trusted_uids,
        maximum_size=256 * 1024,
    )
    descriptor = require_mapping(
        strict_json_loads(descriptor_payload, "controller trust descriptor"),
        "controller trust descriptor",
    )
    require_exact_keys(descriptor, CONTROLLER_TRUST_KEYS, "controller trust descriptor")
    if descriptor.get("schema_version") != 1:
        raise ContractError("controller trust descriptor schema_version must be 1")
    policy_pin = require_mapping(descriptor["policy"], "controller policy pin")
    require_exact_keys(policy_pin, PINNED_FILE_KEYS, "controller policy pin")
    if not SHA256_RE.fullmatch(str(policy_pin["sha256"])):
        raise ContractError("controller policy pin SHA-256 is invalid")
    policy_path, policy_payload = read_trusted_file(
        Path(str(policy_pin["path"])),
        "execution policy",
        trusted_uids=effective_trusted_uids,
        expected_sha256=str(policy_pin["sha256"]),
    )
    policy = require_mapping(
        strict_json_loads(policy_payload, "execution policy"), "execution policy"
    )
    engine_pin = require_mapping(
        descriptor["container_engine"], "controller container engine pin"
    )
    require_exact_keys(
        engine_pin, CONTAINER_ENGINE_KEYS, "controller container engine pin"
    )
    backend_uri = str(engine_pin.get("backend_uri", ""))
    if (
        engine_pin.get("kind") != "podman"
        or not SHA256_RE.fullmatch(str(engine_pin.get("sha256", "")))
        or not SHA256_RE.fullmatch(str(engine_pin.get("backend_identity_sha256", "")))
        or not re.fullmatch(r"(?:unix|ssh)://[^\s]+", backend_uri)
        or URI_CREDENTIAL_RE.search(backend_uri)
    ):
        raise ContractError("controller container engine pin is invalid")
    engine_path, _engine_payload = read_trusted_file(
        Path(str(engine_pin["path"])),
        "controller container engine",
        trusted_uids=effective_trusted_uids,
        expected_sha256=str(engine_pin["sha256"]),
        maximum_size=256 * 1024 * 1024,
        executable=True,
    )
    replay_pin = require_mapping(
        descriptor["replay_broker"], "controller replay broker pin"
    )
    require_exact_keys(replay_pin, REPLAY_BROKER_KEYS, "controller replay broker pin")
    if (
        replay_pin.get("kind") != "root-brokered-append-only-v1"
        or not SHA256_RE.fullmatch(str(replay_pin.get("sha256", "")))
        or not re.fullmatch(
            r"[A-Za-z0-9][A-Za-z0-9._:-]{2,127}",
            str(replay_pin.get("store_id", "")),
        )
    ):
        raise ContractError("controller replay broker pin is invalid")
    replay_path, _replay_payload = read_trusted_file(
        Path(str(replay_pin["path"])),
        "controller replay broker",
        trusted_uids=effective_trusted_uids,
        expected_sha256=str(replay_pin["sha256"]),
        maximum_size=64 * 1024 * 1024,
        executable=True,
    )
    anchor = require_mapping(descriptor["execution_anchor"], "execution anchor")
    require_exact_keys(anchor, EXECUTION_ANCHOR_KEYS, "execution anchor")
    normalized_anchor: dict[str, dict[str, str]] = {}
    for key in ("launcher", "interpreter", "recorder"):
        pin = require_mapping(anchor[key], f"execution anchor {key}")
        require_exact_keys(pin, PINNED_FILE_KEYS, f"execution anchor {key}")
        if not SHA256_RE.fullmatch(str(pin.get("sha256", ""))):
            raise ContractError(f"execution anchor {key} digest is invalid")
        pinned_path, _payload = read_trusted_file(
            Path(str(pin["path"])),
            f"execution anchor {key}",
            trusted_uids=effective_trusted_uids,
            expected_sha256=str(pin["sha256"]),
            maximum_size=256 * 1024 * 1024,
            executable=True,
        )
        normalized_anchor[key] = {
            "path": str(pinned_path),
            "sha256": str(pin["sha256"]),
        }
    receipt_pin = require_mapping(
        anchor["acceptance_receipt"], "execution anchor acceptance receipt"
    )
    require_exact_keys(
        receipt_pin, PINNED_FILE_KEYS, "execution anchor acceptance receipt"
    )
    receipt_path, receipt_payload = read_trusted_file(
        Path(str(receipt_pin["path"])),
        "execution anchor acceptance receipt",
        trusted_uids=effective_trusted_uids,
        expected_sha256=str(receipt_pin["sha256"]),
        maximum_size=128 * 1024,
    )
    receipt = require_mapping(
        strict_json_loads(receipt_payload, "execution anchor acceptance receipt"),
        "execution anchor acceptance receipt",
    )
    require_exact_keys(receipt, ANCHOR_RECEIPT_KEYS, "execution anchor receipt")
    expected_receipt = {
        "schema_version": 1,
        "status": "ACCEPTED",
        "launcher_sha256": normalized_anchor["launcher"]["sha256"],
        "interpreter_sha256": normalized_anchor["interpreter"]["sha256"],
        "recorder_sha256": normalized_anchor["recorder"]["sha256"],
        "replay_broker_sha256": str(replay_pin["sha256"]),
        "container_engine_sha256": str(engine_pin["sha256"]),
        "negative_replay_test": True,
        "controller_readback_test": True,
    }
    if receipt != expected_receipt:
        raise ContractError("execution anchor acceptance receipt is not accepted")
    normalized_anchor["acceptance_receipt"] = {
        "path": str(receipt_path),
        "sha256": str(receipt_pin["sha256"]),
    }
    descriptor["_descriptor_path"] = str(descriptor_path)
    descriptor["_descriptor_sha256"] = sha256_bytes(descriptor_payload)
    descriptor["_trusted_uids"] = frozenset(effective_trusted_uids)
    descriptor["policy"] = {
        "path": str(policy_path),
        "sha256": str(policy_pin["sha256"]),
    }
    descriptor["container_engine"] = {
        "kind": "podman",
        "path": str(engine_path),
        "sha256": str(engine_pin["sha256"]),
        "backend_uri": backend_uri,
        "backend_identity_sha256": str(engine_pin["backend_identity_sha256"]),
    }
    descriptor["replay_broker"] = {
        "kind": "root-brokered-append-only-v1",
        "path": str(replay_path),
        "sha256": str(replay_pin["sha256"]),
        "store_id": str(replay_pin["store_id"]),
    }
    descriptor["execution_anchor"] = normalized_anchor
    descriptor["manifest_signature"] = validate_signature_trust(
        descriptor["manifest_signature"],
        "manifest signature trust",
        trusted_uids=effective_trusted_uids,
    )
    descriptor["runtime_attestation_signature"] = validate_signature_trust(
        descriptor["runtime_attestation_signature"],
        "runtime attestation signature trust",
        trusted_uids=effective_trusted_uids,
    )
    descriptor["approval_authority"] = validate_approval_authority(
        descriptor["approval_authority"], trusted_uids=effective_trusted_uids
    )
    return descriptor, policy, policy_payload


def public_signature_trust(trust: dict[str, Any]) -> dict[str, Any]:
    return {key: trust[key] for key in SIGNATURE_TRUST_KEYS}


def revalidate_controller_trust(expected: dict[str, Any]) -> dict[str, Any]:
    observed, observed_policy, observed_policy_payload = load_controller_trust(
        Path(expected["_descriptor_path"]),
        trusted_uids=set(expected.get("_trusted_uids", {0})),
    )
    if observed["_descriptor_sha256"] != expected["_descriptor_sha256"]:
        raise ContractError("controller trust descriptor changed before execution")
    if sha256_bytes(observed_policy_payload) != expected["policy"]["sha256"]:
        raise ContractError("controller execution policy changed before execution")
    if observed["container_engine"] != expected["container_engine"]:
        raise ContractError("controller container engine changed before execution")
    if observed["replay_broker"] != expected["replay_broker"]:
        raise ContractError("controller replay broker changed before execution")
    if observed["execution_anchor"] != expected["execution_anchor"]:
        raise ContractError("controller execution anchor changed before execution")
    if observed_policy != strict_json_loads(
        observed_policy_payload, "execution policy"
    ):
        raise ContractError("controller execution policy revalidation failed")
    for key in ("manifest_signature", "runtime_attestation_signature"):
        if public_signature_trust(observed[key]) != public_signature_trust(
            expected[key]
        ):
            raise ContractError(f"controller {key} trust changed before execution")
    if public_approval_authority(
        observed["approval_authority"]
    ) != public_approval_authority(expected["approval_authority"]):
        raise ContractError("controller approval authority changed before execution")
    return observed


def validate_execution_anchor_runtime(
    trust: dict[str, Any],
    *,
    recorder_path: Path | None = None,
    interpreter_path: Path | None = None,
    isolated: bool | None = None,
    safe_path: bool | None = None,
    launcher_path: str | None = None,
    python_environment: dict[str, str] | None = None,
) -> dict[str, str]:
    anchor = trust["execution_anchor"]
    actual_recorder = (recorder_path or Path(__file__)).resolve(strict=True)
    actual_interpreter = (interpreter_path or Path(sys.executable)).resolve(strict=True)
    actual_isolated = bool(sys.flags.isolated) if isolated is None else isolated
    actual_safe_path = bool(sys.flags.safe_path) if safe_path is None else safe_path
    actual_launcher = (
        os.environ.get("LIT_GOVERNED_LAUNCHER_PATH", "")
        if launcher_path is None
        else launcher_path
    )
    if (
        str(actual_recorder) != anchor["recorder"]["path"]
        or sha256_file(actual_recorder) != anchor["recorder"]["sha256"]
    ):
        raise ContractError(
            "running recorder is not the root-pinned installed recorder"
        )
    if (
        str(actual_interpreter) != anchor["interpreter"]["path"]
        or sha256_file(actual_interpreter) != anchor["interpreter"]["sha256"]
    ):
        raise ContractError("running Python interpreter is not root-pinned")
    if not actual_isolated or not actual_safe_path:
        raise ContractError("recorder Python must run with isolated safe imports")
    if actual_launcher != anchor["launcher"]["path"]:
        raise ContractError("recorder was not entered through the root-owned launcher")
    inherited = os.environ if python_environment is None else python_environment
    forbidden = {
        name
        for name in inherited
        if name == "PYTHONPATH"
        or name == "PYTHONHOME"
        or name.startswith("PYTHONUSERBASE")
    }
    if forbidden:
        raise ContractError("recorder inherited a Python import override")
    return {
        "launcher_path": anchor["launcher"]["path"],
        "launcher_sha256": anchor["launcher"]["sha256"],
        "interpreter_path": anchor["interpreter"]["path"],
        "interpreter_sha256": anchor["interpreter"]["sha256"],
        "recorder_path": anchor["recorder"]["path"],
        "recorder_sha256": anchor["recorder"]["sha256"],
        "acceptance_receipt_sha256": anchor["acceptance_receipt"]["sha256"],
        "python_mode": "ISOLATED_SAFE_PATH",
    }


def require_mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ContractError(f"{label} must be a mapping")
    return value


def require_sequence(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise ContractError(f"{label} must be a list")
    return value


def strict_json_loads(payload: bytes, label: str) -> Any:
    def reject_constant(value: str) -> None:
        raise ContractError(f"{label} contains a non-finite JSON number: {value}")

    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ContractError(f"{label} contains duplicate key {key!r}")
            result[key] = value
        return result

    try:
        return json.loads(
            payload.decode("utf-8"),
            parse_constant=reject_constant,
            object_pairs_hook=reject_duplicates,
        )
    except UnicodeDecodeError as exc:
        raise ContractError(f"{label} must contain UTF-8 JSON") from exc
    except json.JSONDecodeError as exc:
        raise ContractError(f"{label} must contain valid JSON") from exc


def read_json_object(
    path: Path, label: str, max_bytes: int = 2 * 1024 * 1024
) -> tuple[dict[str, Any], bytes]:
    resolved = path.expanduser().resolve()
    file_stat = resolved.stat()
    if not stat.S_ISREG(file_stat.st_mode) or file_stat.st_size <= 0:
        raise ContractError(f"{label} must be a nonempty regular file")
    if file_stat.st_size > max_bytes:
        raise ContractError(f"{label} exceeds {max_bytes} bytes")
    payload = resolved.read_bytes()
    parsed = strict_json_loads(payload, label)
    return require_mapping(parsed, label), payload


def require_private_file(
    path: Path, label: str, *, allow_readonly: bool = True
) -> Path:
    candidate = path.expanduser()
    if candidate.is_symlink():
        raise ContractError(f"{label} must not be a symbolic link")
    resolved = candidate.resolve(strict=True)
    file_stat = resolved.stat()
    if not stat.S_ISREG(file_stat.st_mode) or file_stat.st_nlink != 1:
        raise ContractError(f"{label} must be a single-link regular file")
    if file_stat.st_uid != os.geteuid():
        raise ContractError(f"{label} must be owned by the effective user")
    mode = stat.S_IMODE(file_stat.st_mode)
    allowed = {0o400, 0o600} if allow_readonly else {0o600}
    if mode not in allowed:
        raise ContractError(f"{label} must have mode 0400 or 0600")
    return resolved


def require_evidence_directory(path: Path) -> Path:
    candidate = path.expanduser()
    if candidate.exists() and candidate.is_symlink():
        raise ContractError("evidence directory must not be a symbolic link")
    candidate.mkdir(mode=0o700, parents=True, exist_ok=True)
    resolved = candidate.resolve(strict=True)
    directory_stat = resolved.stat()
    if not stat.S_ISDIR(directory_stat.st_mode):
        raise ContractError("evidence path is not a directory")
    if directory_stat.st_uid != os.geteuid():
        raise ContractError("evidence directory must be owned by the effective user")
    if stat.S_IMODE(directory_stat.st_mode) != 0o700:
        raise ContractError("evidence directory must have mode 0700")
    return resolved


def require_private_directory(path: Path, label: str) -> Path:
    candidate = path.expanduser()
    if candidate.is_symlink():
        raise ContractError(f"{label} must not be a symbolic link")
    resolved = candidate.resolve(strict=True)
    directory_stat = resolved.stat()
    if not stat.S_ISDIR(directory_stat.st_mode):
        raise ContractError(f"{label} must be a directory")
    if directory_stat.st_uid != os.geteuid():
        raise ContractError(f"{label} must be owned by the effective user")
    if stat.S_IMODE(directory_stat.st_mode) != 0o700:
        raise ContractError(f"{label} must have mode 0700")
    return resolved


def fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def write_new_json(path: Path, payload: dict[str, Any]) -> str:
    """Create one record and sidecar without overwriting either name."""
    recursively_reject_secret_fields(payload, "record")
    serialized = (
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    ).encode("utf-8")
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o400)
    try:
        with os.fdopen(descriptor, "wb", closefd=False) as stream:
            stream.write(serialized)
            stream.flush()
            os.fsync(stream.fileno())
    finally:
        os.close(descriptor)
    digest = sha256_bytes(serialized)
    sidecar = path.with_suffix(f"{path.suffix}.sha256")
    sidecar_payload = f"{digest}  {path.name}\n".encode("ascii")
    try:
        sidecar_descriptor = os.open(
            sidecar, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o400
        )
        try:
            with os.fdopen(sidecar_descriptor, "wb", closefd=False) as stream:
                stream.write(sidecar_payload)
                stream.flush()
                os.fsync(stream.fileno())
        finally:
            os.close(sidecar_descriptor)
    except Exception:
        # Preserve the primary journal: absence of the sidecar is itself an
        # observable incomplete-evidence state and must not free the ID.
        raise
    fsync_directory(path.parent)
    return digest


def git_environment() -> dict[str, str]:
    """Return a non-interactive Git environment without local trust overlays."""
    return {
        "PATH": "/usr/bin:/bin",
        "LANG": "C",
        "LC_ALL": "C",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_ATTR_NOSYSTEM": "1",
        "GIT_NO_REPLACE_OBJECTS": "1",
        "GIT_OPTIONAL_LOCKS": "0",
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_NO_LAZY_FETCH": "1",
        "GIT_CONFIG_COUNT": "4",
        "GIT_CONFIG_KEY_0": "core.attributesFile",
        "GIT_CONFIG_VALUE_0": "/dev/null",
        "GIT_CONFIG_KEY_1": "fsck.skipList",
        "GIT_CONFIG_VALUE_1": "/dev/null",
        "GIT_CONFIG_KEY_2": "core.hooksPath",
        "GIT_CONFIG_VALUE_2": "/dev/null",
        "GIT_CONFIG_KEY_3": "core.replaceRefs",
        "GIT_CONFIG_VALUE_3": "false",
    }


def run_git(repo: Path, *args: str) -> str:
    if not SYSTEM_GIT.is_file():
        raise ContractError(f"required system Git is missing: {SYSTEM_GIT}")
    try:
        completed = subprocess.run(
            [str(SYSTEM_GIT), "--no-replace-objects", "-C", str(repo), *args],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=120,
            env=git_environment(),
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise ContractError("system Git verification failed") from exc
    if completed.returncode != 0:
        raise ContractError("system Git verification failed")
    return completed.stdout.strip()


def run_git_bytes(
    repo: Path,
    *args: str,
    input_payload: bytes | None = None,
    maximum_output_bytes: int = MAX_GIT_LISTING_BYTES,
) -> bytes:
    if not SYSTEM_GIT.is_file():
        raise ContractError(f"required system Git is missing: {SYSTEM_GIT}")
    try:
        completed = subprocess.run(
            [str(SYSTEM_GIT), "--no-replace-objects", "-C", str(repo), *args],
            input=input_payload,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=300,
            env=git_environment(),
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise ContractError("system Git object read failed") from exc
    if completed.returncode != 0 or len(completed.stdout) > maximum_output_bytes:
        raise ContractError("system Git object read failed or exceeded its boundary")
    return completed.stdout


def parse_repo(value: str) -> tuple[str, Path]:
    name, separator, raw_path = value.partition("=")
    if not separator or not re.fullmatch(r"[a-z][a-z0-9_-]{1,39}", name):
        raise argparse.ArgumentTypeError("--repo must use NAME=PATH")
    path = Path(raw_path).expanduser().resolve()
    if not path.is_dir() or not (path / ".git").exists():
        raise argparse.ArgumentTypeError(f"repository does not exist: {path}")
    return name, path


def collect_repository_state(
    name: str, repo: Path, expected: dict[str, Any]
) -> dict[str, Any]:
    branch = run_git(repo, "branch", "--show-current")
    commit = run_git(repo, "rev-parse", "HEAD")
    status = run_git(
        repo,
        "status",
        "--porcelain=v1",
        "--untracked-files=all",
        "--ignored=matching",
    )
    expected_branch = str(expected.get("branch", ""))
    expected_commit = str(expected.get("commit", ""))
    if not BRANCH_RE.fullmatch(expected_branch) or not GIT_SHA_RE.fullmatch(
        expected_commit
    ):
        raise ContractError(f"manifest repository {name} is not frozen")
    if branch != expected_branch or commit != expected_commit:
        raise ContractError(f"repository {name} does not match the signed freeze")
    if status:
        raise ContractError(
            f"repository {name} contains modified, untracked, or ignored paths"
        )
    commit_type = run_git(repo, "cat-file", "-t", expected_commit)
    if commit_type != "commit":
        raise ContractError(f"repository {name} freeze does not name a commit")
    return {
        "name": name,
        "path": str(repo),
        "branch": branch,
        "commit": commit,
        "clean_at_start": True,
        "ignored_paths_rejected": True,
    }


def git_object_sha1(object_type: str, payload: bytes) -> str:
    header = f"{object_type} {len(payload)}\0".encode("ascii")
    digest = hashlib.sha1(usedforsecurity=False)
    digest.update(header)
    digest.update(payload)
    return digest.hexdigest()


def read_git_object(repo: Path, object_id: str, object_type: str) -> bytes:
    if not GIT_SHA_RE.fullmatch(object_id) or object_type not in {
        "blob",
        "commit",
        "tree",
    }:
        raise ContractError("Git object request is not exact")
    payload = run_git_bytes(
        repo,
        "cat-file",
        object_type,
        object_id,
        maximum_output_bytes=(
            MAX_SNAPSHOT_FILE_BYTES if object_type == "blob" else MAX_GIT_LISTING_BYTES
        ),
    )
    if git_object_sha1(object_type, payload) != object_id:
        raise ContractError("Git object content does not match its object ID")
    return payload


def parse_commit_root_tree(repo: Path, commit: str) -> str:
    payload = read_git_object(repo, commit, "commit")
    first_line, separator, _remainder = payload.partition(b"\n")
    if not separator or not first_line.startswith(b"tree "):
        raise ContractError("frozen Git commit has no canonical root tree")
    try:
        root_tree = first_line.removeprefix(b"tree ").decode("ascii")
    except UnicodeDecodeError as exc:
        raise ContractError("frozen Git commit root tree is malformed") from exc
    if not GIT_SHA_RE.fullmatch(root_tree):
        raise ContractError("frozen Git commit root tree is malformed")
    return root_tree


def safe_git_component(raw_name: bytes, parent: tuple[str, ...]) -> str:
    try:
        name = raw_name.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ContractError("Git tree path is not UTF-8") from exc
    if (
        not name
        or name in {".", ".."}
        or "/" in name
        or "\\" in name
        or any(ord(character) < 32 or ord(character) == 127 for character in name)
        or unicodedata.normalize("NFC", name) != name
    ):
        raise ContractError("Git tree path is unsafe or non-canonical")
    full_path = Path(*parent, name)
    if full_path.is_absolute() or ".." in full_path.parts:
        raise ContractError("Git tree path escapes its snapshot")
    return name


def parse_git_tree(payload: bytes) -> list[tuple[str, bytes, str]]:
    entries: list[tuple[str, bytes, str]] = []
    offset = 0
    while offset < len(payload):
        space = payload.find(b" ", offset)
        nul = payload.find(b"\0", space + 1)
        if space <= offset or nul < 0 or nul + 21 > len(payload):
            raise ContractError("Git tree object is malformed")
        try:
            mode = payload[offset:space].decode("ascii")
        except UnicodeDecodeError as exc:
            raise ContractError("Git tree mode is malformed") from exc
        name = payload[space + 1 : nul]
        object_id = payload[nul + 1 : nul + 21].hex()
        entries.append((mode, name, object_id))
        offset = nul + 21
    return entries


def create_snapshot_directory(path: Path) -> None:
    try:
        path.mkdir(mode=0o700)
    except FileExistsError:
        pass
    status = os.lstat(path)
    if (
        not stat.S_ISDIR(status.st_mode)
        or stat.S_ISLNK(status.st_mode)
        or status.st_uid != os.geteuid()
        or stat.S_IMODE(status.st_mode) != 0o700
    ):
        raise ContractError("repository snapshot directory is unsafe")


def write_snapshot_blob(path: Path, payload: bytes, executable: bool) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    flags |= getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags, 0o700 if executable else 0o600)
    except OSError as exc:
        raise ContractError(
            "repository snapshot file could not be created safely"
        ) from exc
    try:
        view = memoryview(payload)
        offset = 0
        while offset < len(view):
            written = os.write(descriptor, view[offset:])
            if written <= 0:
                raise ContractError("repository snapshot file write was incomplete")
            offset += written
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def materialize_git_tree(repo: Path, commit: str, destination: Path) -> dict[str, int]:
    root_tree = parse_commit_root_tree(repo, commit)
    counters = {"files": 0, "bytes": 0, "trees": 0}
    collision_keys: set[str] = set()
    active_trees: set[str] = set()

    def walk(tree_id: str, parent: tuple[str, ...], depth: int) -> None:
        if depth > MAX_GIT_TREE_DEPTH or tree_id in active_trees:
            raise ContractError("Git tree depth or recursion exceeds its boundary")
        active_trees.add(tree_id)
        counters["trees"] += 1
        if counters["trees"] > MAX_SNAPSHOT_FILES:
            raise ContractError("Git snapshot exceeds its tree-count boundary")
        try:
            entries = parse_git_tree(read_git_object(repo, tree_id, "tree"))
            local_names: set[str] = set()
            for mode, raw_name, object_id in entries:
                name = safe_git_component(raw_name, parent)
                local_key = unicodedata.normalize("NFC", name).casefold()
                if local_key in local_names:
                    raise ContractError("Git tree has a filesystem-colliding path")
                local_names.add(local_key)
                relative_parts = (*parent, name)
                collision_key = "/".join(relative_parts).casefold()
                if collision_key in collision_keys:
                    raise ContractError("Git tree has a filesystem-colliding path")
                collision_keys.add(collision_key)
                target = destination.joinpath(*relative_parts)
                if mode == "40000":
                    create_snapshot_directory(target)
                    walk(object_id, relative_parts, depth + 1)
                    continue
                if mode not in {"100644", "100755"}:
                    raise ContractError("Git tree contains an unsupported entry type")
                payload = read_git_object(repo, object_id, "blob")
                counters["files"] += 1
                counters["bytes"] += len(payload)
                if (
                    counters["files"] > MAX_SNAPSHOT_FILES
                    or counters["bytes"] > MAX_SNAPSHOT_BYTES
                    or len(payload) > MAX_SNAPSHOT_FILE_BYTES
                ):
                    raise ContractError("Git snapshot exceeds its size boundary")
                write_snapshot_blob(target, payload, mode == "100755")
        finally:
            active_trees.remove(tree_id)

    walk(root_tree, (), 0)
    return counters


def snapshot_tree_sha256(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*"), key=lambda candidate: candidate.as_posix()):
        relative = path.relative_to(root).as_posix().encode("utf-8")
        status = os.lstat(path)
        if stat.S_ISLNK(status.st_mode):
            raise ContractError("repository snapshot contains a symbolic link")
        if stat.S_ISDIR(status.st_mode):
            digest.update(b"D\0" + relative + b"\0")
            continue
        if not stat.S_ISREG(status.st_mode):
            raise ContractError("repository snapshot contains a non-regular entry")
        executable = b"1" if status.st_mode & 0o111 else b"0"
        digest.update(b"F\0" + relative + b"\0" + executable + b"\0")
        with path.open("rb") as source:
            while chunk := source.read(1024 * 1024):
                digest.update(chunk)
    return digest.hexdigest()


def make_snapshot_read_only(root: Path) -> None:
    paths = sorted(root.rglob("*"), key=lambda path: len(path.parts), reverse=True)
    for path in paths:
        status = os.lstat(path)
        if stat.S_ISDIR(status.st_mode):
            os.chmod(path, 0o500)
        elif stat.S_ISREG(status.st_mode):
            os.chmod(path, 0o500 if status.st_mode & 0o111 else 0o400)
        else:
            raise ContractError("repository snapshot contains an unsafe entry")
    os.chmod(root, 0o500)


def create_repository_snapshots(
    states: list[dict[str, Any]], runtime_root: Path
) -> tuple[dict[str, Path], list[dict[str, Any]]]:
    snapshots_root = runtime_root / "snapshots"
    snapshots_root.mkdir(mode=0o700)
    snapshots: dict[str, Path] = {}
    evidence: list[dict[str, Any]] = []
    for state in states:
        name = str(state["name"])
        source_repo = Path(str(state["path"]))
        destination = snapshots_root / name
        destination.mkdir(mode=0o700)
        materialized = materialize_git_tree(
            source_repo, str(state["commit"]), destination
        )
        tree_sha256 = snapshot_tree_sha256(destination)
        make_snapshot_read_only(destination)
        snapshots[name] = destination
        evidence.append(
            {
                "name": name,
                "source_commit": str(state["commit"]),
                "snapshot_tree_sha256": tree_sha256,
                "read_only": True,
                "tracked_objects_only": True,
                "git_object_integrity_verified": True,
                "replace_refs_disabled": True,
                "file_count": materialized["files"],
                "byte_count": materialized["bytes"],
            }
        )
    os.chmod(snapshots_root, 0o500)
    return snapshots, evidence


def verify_repository_snapshots(
    snapshots: dict[str, Path], expected: list[dict[str, Any]]
) -> None:
    evidence_keys = {
        "name",
        "source_commit",
        "snapshot_tree_sha256",
        "read_only",
        "tracked_objects_only",
        "git_object_integrity_verified",
        "replace_refs_disabled",
        "file_count",
        "byte_count",
    }
    for entry in expected:
        require_exact_keys(entry, evidence_keys, "repository snapshot evidence")
    expected_by_name = {entry["name"]: entry for entry in expected}
    if len(expected_by_name) != len(expected) or set(snapshots) != set(
        expected_by_name
    ):
        raise ContractError("repository snapshot set changed")
    for name, root in snapshots.items():
        evidence = expected_by_name[name]
        if (
            evidence["read_only"] is not True
            or evidence["tracked_objects_only"] is not True
            or evidence["git_object_integrity_verified"] is not True
            or evidence["replace_refs_disabled"] is not True
            or not isinstance(evidence["file_count"], int)
            or isinstance(evidence["file_count"], bool)
            or not isinstance(evidence["byte_count"], int)
            or isinstance(evidence["byte_count"], bool)
        ):
            raise ContractError("repository snapshot evidence is not fail-closed")
        root_status = os.lstat(root)
        if (
            not stat.S_ISDIR(root_status.st_mode)
            or root_status.st_uid != os.geteuid()
            or stat.S_IMODE(root_status.st_mode) != 0o500
        ):
            raise ContractError(f"repository snapshot {name} is not read-only")
        observed_files = 0
        observed_bytes = 0
        for path in root.rglob("*"):
            status = os.lstat(path)
            if status.st_uid != os.geteuid() or stat.S_ISLNK(status.st_mode):
                raise ContractError(
                    f"repository snapshot {name} has unsafe ownership or links"
                )
            if stat.S_ISDIR(status.st_mode):
                expected_mode = 0o500
            elif stat.S_ISREG(status.st_mode) and status.st_nlink == 1:
                expected_mode = 0o500 if status.st_mode & 0o111 else 0o400
            else:
                raise ContractError(
                    f"repository snapshot {name} has an unsafe entry type"
                )
            if stat.S_IMODE(status.st_mode) != expected_mode:
                raise ContractError(f"repository snapshot {name} permissions changed")
            if stat.S_ISREG(status.st_mode):
                observed_files += 1
                observed_bytes += status.st_size
        if (
            observed_files != evidence["file_count"]
            or observed_bytes != evidence["byte_count"]
        ):
            raise ContractError(f"repository snapshot {name} inventory changed")
        if snapshot_tree_sha256(root) != expected_by_name[name]["snapshot_tree_sha256"]:
            raise ContractError(f"repository snapshot {name} changed")


def verify_external_anchor_sources(
    trust: dict[str, Any], snapshots: dict[str, Path]
) -> None:
    expected = {
        snapshots["automation"]
        / "scripts"
        / "governed-ansible-exec.py": trust["execution_anchor"]["recorder"]["sha256"],
        snapshots["automation"]
        / "ansible"
        / "scripts"
        / "governed-ansible-root-launcher": trust["execution_anchor"]["launcher"][
            "sha256"
        ],
        snapshots["validation"]
        / "policies"
        / "wunderbox"
        / "root-of-trust-policy.json": trust["policy"]["sha256"],
    }
    for source, digest in expected.items():
        if not source.is_file() or source.is_symlink() or sha256_file(source) != digest:
            raise ContractError(
                "root-owned execution anchor does not match the frozen reviewed source"
            )


def remove_private_runtime_tree(root: Path) -> bool:
    try:
        for path in sorted(
            root.rglob("*"), key=lambda item: len(item.parts), reverse=True
        ):
            if path.is_symlink():
                path.unlink()
            elif path.is_dir():
                os.chmod(path, 0o700)
            elif path.exists():
                os.chmod(path, 0o600)
        os.chmod(root, 0o700)
        shutil.rmtree(root)
    except OSError:
        return False
    return not root.exists()


def validate_no_secret_scalar(value: str, label: str) -> None:
    if "\n" in value or "\r" in value or "\x00" in value:
        raise ContractError(f"{label} must be a single-line scalar")
    if URI_CREDENTIAL_RE.search(value):
        raise ContractError(f"{label} contains URI credentials")
    if re.search(
        r"(?i)(?:password|passphrase|token|secret|private[_-]?key|credential)\s*=",
        value,
    ):
        raise ContractError(f"{label} contains an inline secret assignment")


def recursively_reject_secret_fields(
    value: Any,
    label: str = "payload",
    *,
    allowed_top_level_secret_names: frozenset[str] = frozenset(),
    allowed_secret_names: frozenset[str] = frozenset(),
    allowed_secret_paths: frozenset[str] = frozenset(),
    allowed_multiline_paths: frozenset[str] = frozenset(),
    depth: int = 0,
) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if not isinstance(key, str):
                raise ContractError(f"{label} contains a non-string key")
            child_label = f"{label}.{key}"
            if SECRET_KEY_RE.search(key) and not (
                (depth == 0 and key in allowed_top_level_secret_names)
                or key in allowed_secret_names
                or child_label in allowed_secret_paths
            ):
                raise ContractError(f"{child_label} is a forbidden secret-bearing key")
            recursively_reject_secret_fields(
                child,
                child_label,
                allowed_top_level_secret_names=allowed_top_level_secret_names,
                allowed_secret_names=allowed_secret_names,
                allowed_secret_paths=allowed_secret_paths,
                allowed_multiline_paths=allowed_multiline_paths,
                depth=depth + 1,
            )
        return
    if isinstance(value, list):
        for index, child in enumerate(value):
            recursively_reject_secret_fields(
                child,
                f"{label}[{index}]",
                allowed_top_level_secret_names=allowed_top_level_secret_names,
                allowed_secret_names=allowed_secret_names,
                allowed_secret_paths=allowed_secret_paths,
                allowed_multiline_paths=allowed_multiline_paths,
                depth=depth + 1,
            )
        return
    if isinstance(value, str):
        if label not in allowed_multiline_paths:
            validate_no_secret_scalar(value, label)


def validate_policy(policy: dict[str, Any]) -> None:
    require_exact_keys(policy, POLICY_KEYS, "execution policy")
    if policy.get("schema_version") != 2:
        raise ContractError("policy schema_version must be 2")
    if not re.fullmatch(r"[a-z][a-z0-9-]{2,79}", str(policy.get("policy_id", ""))):
        raise ContractError("policy_id is invalid")
    required_repositories = require_sequence(
        policy.get("required_repositories"), "policy required_repositories"
    )
    if len(required_repositories) != len(set(required_repositories)):
        raise ContractError("policy repository names must be unique")
    required_collections = require_sequence(
        policy.get("required_collections"), "policy required_collections"
    )
    if not required_collections or len(required_collections) != len(
        set(required_collections)
    ):
        raise ContractError("policy collection names must be nonempty and unique")
    collection_repositories = require_mapping(
        policy.get("collection_repositories"), "policy collection repositories"
    )
    if set(collection_repositories) != set(required_collections) or any(
        repository not in required_repositories
        for repository in collection_repositories.values()
    ):
        raise ContractError("policy collection-to-repository mapping is invalid")
    target_contract = require_mapping(
        policy.get("target_contract"), "policy target_contract"
    )
    try:
        re.compile(str(target_contract["target_id_pattern"]))
        re.compile(str(target_contract["fqdn_pattern"]))
    except (KeyError, re.error) as exc:
        raise ContractError("policy target contract contains invalid patterns") from exc
    actions = require_mapping(policy.get("actions"), "policy actions")
    record_prefixes: set[str] = set()
    for action_id, raw_action in actions.items():
        if not ACTION_ID_RE.fullmatch(action_id):
            raise ContractError(f"invalid action ID: {action_id}")
        action = require_mapping(raw_action, f"action {action_id}")
        prefix = str(action.get("record_prefix", ""))
        if not RECORD_PREFIX_RE.fullmatch(prefix) or prefix in record_prefixes:
            raise ContractError(f"action {action_id} has an invalid/duplicate prefix")
        record_prefixes.add(prefix)
        if action.get("impact") not in ALLOWED_IMPACTS:
            raise ContractError(f"action {action_id} has an invalid impact")
        implementation_status = action.get("implementation_status", "ready")
        if implementation_status not in {"ready", "blocked"}:
            raise ContractError(
                f"action {action_id} has an invalid implementation status"
            )
        if (
            implementation_status == "blocked"
            and not str(action.get("implementation_blocker", "")).strip()
        ):
            raise ContractError(
                f"action {action_id} must declare its implementation blocker"
            )
        if not re.fullmatch(r"WBX-G[0-5]", str(action.get("gate", ""))):
            raise ContractError(f"action {action_id} has an invalid gate")
        if action.get("mode") not in {
            "inventory_projection",
            "syntax_check",
            "playbook",
        }:
            raise ContractError(f"action {action_id} has an invalid mode")
        if (
            action.get("mode") == "inventory_projection"
            and action.get("projection_paths") != INVENTORY_PROJECTION_PATHS
        ):
            raise ContractError(
                f"action {action_id} must pin the complete effective-access projection"
            )
        for transport_flag in ("requires_ssh_private_key", "requires_ssh_agent"):
            if transport_flag in action and not isinstance(
                action[transport_flag], bool
            ):
                raise ContractError(
                    f"action {action_id} has an invalid {transport_flag} flag"
                )
        if action.get(
            "requires_ssh_private_key", action["impact"] in LIVE_IMPACTS
        ) and action.get("requires_ssh_agent", False):
            raise ContractError(
                f"action {action_id} cannot combine SSH key and agent transport"
            )
        if action.get("mode") != "inventory_projection" and not action.get("playbook"):
            raise ContractError(f"action {action_id} must pin one playbook")
        artifact_tasks = require_mapping(
            action.get("safe_artifact_tasks", {}),
            f"action {action_id} safe_artifact_tasks",
        )
        if any(
            not isinstance(task_name, str)
            or not task_name.strip()
            or artifact_type not in {"plan", "readback"}
            for task_name, artifact_type in artifact_tasks.items()
        ):
            raise ContractError(f"action {action_id} has an invalid artifact task")
        expected_artifact = action.get("expected_artifact")
        if expected_artifact is not None and expected_artifact not in set(
            artifact_tasks.values()
        ):
            raise ContractError(
                f"action {action_id} cannot produce its expected artifact"
            )
        artifact_projection_paths = require_sequence(
            action.get("artifact_projection_paths", []),
            f"action {action_id} artifact_projection_paths",
        )
        if expected_artifact is not None and not artifact_projection_paths:
            raise ContractError(
                f"action {action_id} must define a sanitized artifact projection"
            )
        artifact_schema = action.get("artifact_schema")
        if expected_artifact is not None:
            schema = require_mapping(
                artifact_schema, f"action {action_id} artifact schema"
            )
            require_exact_keys(
                schema,
                ARTIFACT_SCHEMA_KEYS,
                f"action {action_id} artifact schema",
            )
            if not re.fullmatch(
                r"[a-z][a-z0-9_.-]{2,127}", str(schema.get("schema_id", ""))
            ):
                raise ContractError(f"action {action_id} artifact schema ID is invalid")
            fields = require_mapping(
                schema.get("fields"), f"action {action_id} artifact fields"
            )
            if set(fields) != set(artifact_projection_paths):
                raise ContractError(
                    f"action {action_id} artifact schema must type every projection path"
                )
            for field_path, raw_field in fields.items():
                field = require_mapping(
                    raw_field, f"action {action_id} artifact field {field_path}"
                )
                if not set(field).issubset({"type", "binding", "allowed_values"}):
                    raise ContractError(
                        f"action {action_id} artifact field {field_path} has unknown keys"
                    )
                if field.get("type") not in ARTIFACT_FIELD_TYPES:
                    raise ContractError(
                        f"action {action_id} artifact field {field_path} has an invalid type"
                    )
                binding = field.get("binding")
                if binding is not None and binding not in TARGET_KEYS:
                    raise ContractError(
                        f"action {action_id} artifact field {field_path} has an invalid target binding"
                    )
                allowed_values = field.get("allowed_values")
                if allowed_values is not None and (
                    not isinstance(allowed_values, list) or not allowed_values
                ):
                    raise ContractError(
                        f"action {action_id} artifact field {field_path} has invalid allowed values"
                    )
        elif artifact_schema is not None:
            raise ContractError(
                f"action {action_id} cannot define a schema without an expected artifact"
            )
        allowed_extra_vars = require_sequence(
            action.get("allowed_extra_vars", []),
            f"action {action_id} allowed_extra_vars",
        )
        required_extra_vars = require_sequence(
            action.get("required_extra_vars", []),
            f"action {action_id} required_extra_vars",
        )
        if len(allowed_extra_vars) != len(set(allowed_extra_vars)) or not set(
            required_extra_vars
        ).issubset(allowed_extra_vars):
            raise ContractError(
                f"action {action_id} has an invalid extra-vars contract"
            )
        nonsecret_secret_names = set(
            require_sequence(
                action.get("nonsecret_secret_named_vars", []),
                f"action {action_id} nonsecret_secret_named_vars",
            )
        )
        if not nonsecret_secret_names.issubset(allowed_extra_vars):
            raise ContractError(
                f"action {action_id} has an invalid secret-named metadata allowlist"
            )
        allowed_values = require_mapping(
            action.get("extra_var_allowed_values", {}),
            f"action {action_id} extra_var_allowed_values",
        )
        if not set(allowed_values).issubset(allowed_extra_vars):
            raise ContractError(f"action {action_id} constrains an unknown extra var")
        raw_bindings = require_mapping(
            action.get("extra_var_bindings", {}),
            f"action {action_id} extra_var_bindings",
        )
        structurally_bound_nonsecret_names = {
            variable
            for variable, raw_binding in raw_bindings.items()
            if isinstance(raw_binding, dict)
            and raw_binding.get("kind") == "signed_approval_transport"
        }
        if not nonsecret_secret_names.issubset(
            set(allowed_values) | structurally_bound_nonsecret_names
        ):
            raise ContractError(
                f"action {action_id} must constrain or structurally bind every secret-named metadata value"
            )
        bindings = raw_bindings
        if set(bindings) != set(required_extra_vars):
            raise ContractError(
                f"action {action_id} must bind every required extra var"
            )
        for variable, raw_binding in bindings.items():
            binding = require_mapping(
                raw_binding, f"action {action_id} binding {variable}"
            )
            kind = binding.get("kind")
            if kind == "literal":
                require_exact_keys(
                    binding, {"kind", "value"}, f"action {action_id} binding {variable}"
                )
                if "value" not in binding:
                    raise ContractError(
                        f"action {action_id} has an empty literal binding"
                    )
            elif kind == "target_confirmation":
                require_exact_keys(
                    binding,
                    {"kind", "prefix"},
                    f"action {action_id} binding {variable}",
                )
                if not re.fullmatch(
                    r"[A-Z][A-Z0-9_]{1,39}", str(binding.get("prefix", ""))
                ):
                    raise ContractError(
                        f"action {action_id} has an invalid confirmation prefix"
                    )
            elif kind == "authorization_field":
                require_exact_keys(
                    binding,
                    {"kind", "field"},
                    f"action {action_id} binding {variable}",
                )
                if not re.fullmatch(
                    r"[a-z][a-z0-9_]{1,79}", str(binding.get("field", ""))
                ):
                    raise ContractError(
                        f"action {action_id} has an invalid authorization binding"
                    )
            elif kind == "signed_approval_transport":
                require_exact_keys(
                    binding,
                    {"kind", "operation", "contract_binding"},
                    f"action {action_id} binding {variable}",
                )
                if not re.fullmatch(
                    r"[a-z][a-z0-9-]{2,79}", str(binding.get("operation", ""))
                ):
                    raise ContractError(
                        f"action {action_id} has an invalid signed approval operation"
                    )
                canonical_approval_binding(
                    binding.get("contract_binding"),
                    f"action {action_id} signed approval binding",
                )
                recursively_reject_secret_fields(
                    binding.get("contract_binding"),
                    f"action.{action_id}.binding.{variable}.contract_binding",
                    allowed_secret_names=frozenset(
                        {
                            "onepassword",
                            "password_item",
                            "password_recipe",
                            "password_length",
                        }
                    ),
                )
            elif kind == "target_and_authorization_confirmation":
                require_exact_keys(
                    binding,
                    {"kind", "prefix", "field"},
                    f"action {action_id} binding {variable}",
                )
                if not re.fullmatch(
                    r"[A-Z][A-Z0-9_]{1,39}", str(binding.get("prefix", ""))
                ):
                    raise ContractError(
                        f"action {action_id} has an invalid confirmation prefix"
                    )
                if not re.fullmatch(
                    r"[a-z][a-z0-9_]{1,79}", str(binding.get("field", ""))
                ):
                    raise ContractError(
                        f"action {action_id} has an invalid authorization binding"
                    )
            else:
                raise ContractError(f"action {action_id} has an invalid binding kind")
        timeout = action.get("timeout_seconds", 1800)
        output_limit = action.get("max_output_bytes", 8 * 1024 * 1024)
        if not isinstance(timeout, int) or not 1 <= timeout <= 21600:
            raise ContractError(f"action {action_id} has an invalid timeout")
        if not isinstance(output_limit, int) or not 1024 <= output_limit <= 16777216:
            raise ContractError(f"action {action_id} has an invalid output limit")


def validate_manifest(
    manifest: dict[str, Any], policy: dict[str, Any], policy_digest: str
) -> None:
    require_exact_keys(manifest, MANIFEST_KEYS, "gate manifest")
    if manifest.get("schema_version") != 2:
        raise ContractError("gate manifest schema_version must be 2")
    if manifest.get("policy_sha256") != policy_digest:
        raise ContractError("gate manifest does not bind the current policy")
    if manifest.get("manifest_status") != "APPROVED":
        raise ContractError("gate manifest is not approved")
    target = require_mapping(manifest.get("target"), "manifest target")
    require_exact_keys(target, TARGET_KEYS, "manifest target")
    if not target.get("target_id") or not re.fullmatch(
        r"(?=.{1,253}$)(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+[A-Za-z]{2,63}",
        str(target.get("fqdn", "")),
    ):
        raise ContractError("manifest target identity is incomplete")
    target_contract = policy["target_contract"]
    if (
        re.fullmatch(
            str(target_contract["target_id_pattern"]), str(target["target_id"])
        )
        is None
        or re.fullmatch(str(target_contract["fqdn_pattern"]), str(target["fqdn"]))
        is None
    ):
        raise ContractError("manifest target is outside the policy target contract")
    controller = require_mapping(manifest.get("controller"), "manifest controller")
    require_exact_keys(controller, CONTROLLER_KEYS, "manifest controller")
    try:
        target_ip = ipaddress.ip_address(str(target.get("public_ipv4", "")))
        source = ipaddress.ip_network(str(controller["source_cidr"]), strict=True)
    except (KeyError, TypeError, ValueError) as exc:
        raise ContractError(
            "manifest target/controller network identity is invalid"
        ) from exc
    if target_ip.version != 4 or source.version != 4 or source.prefixlen != 32:
        raise ContractError("controller source must be one exact IPv4 /32")
    if (
        not str(target.get("provider_id", "")).strip()
        or not str(controller.get("device_id", "")).strip()
    ):
        raise ContractError("manifest provider/controller identity is incomplete")
    controller_ssh = require_mapping(controller.get("ssh"), "manifest controller ssh")
    require_exact_keys(controller_ssh, CONTROLLER_SSH_KEYS, "manifest controller ssh")
    if not str(controller_ssh.get("source_directory", "")).startswith("/"):
        raise ContractError("controller SSH source directory must be absolute")
    if not re.fullmatch(
        r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}",
        str(controller_ssh.get("private_key_name", "")),
    ) or not SHA256_RE.fullmatch(str(controller_ssh.get("private_key_sha256", ""))):
        raise ContractError("controller SSH key binding is incomplete")
    if not re.fullmatch(
        r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}",
        str(controller_ssh.get("known_hosts_name", "")),
    ) or not SHA256_RE.fullmatch(str(controller_ssh.get("known_hosts_sha256", ""))):
        raise ContractError("controller SSH known-hosts binding is incomplete")
    runtime = require_mapping(manifest.get("runtime"), "manifest runtime")
    require_exact_keys(runtime, RUNTIME_KEYS, "manifest runtime")
    for key in ("toolbox_image", "run_ee_image"):
        if not IMAGE_DIGEST_RE.fullmatch(str(runtime.get(key, ""))):
            raise ContractError(f"runtime {key} must use an immutable digest")
    if not SHA256_RE.fullmatch(str(runtime.get("attestation_sha256", ""))):
        raise ContractError("runtime attestation SHA-256 is required")
    for key in ("attestation_path", "attestation_signature_path"):
        path = Path(str(runtime.get(key, "")))
        if not path.is_absolute() or os.path.normpath(str(path)) != str(path):
            raise ContractError(f"runtime {key} must be a normalized absolute path")
    gates = require_mapping(manifest.get("gates"), "manifest gates")
    expected_gates = {f"WBX-G{number}" for number in range(6)}
    if set(gates) != expected_gates:
        raise ContractError("manifest must declare exactly WBX-G0 through WBX-G5")
    if any(value not in ALLOWED_GATE_STATES for value in gates.values()):
        raise ContractError("manifest contains an invalid gate state")
    repositories = require_mapping(
        manifest.get("repositories"), "manifest repositories"
    )
    if set(repositories) != set(policy["required_repositories"]):
        raise ContractError("manifest repository set does not match policy")
    authorizations = require_mapping(
        manifest.get("authorizations"), "manifest authorizations"
    )
    if set(authorizations) != set(policy["actions"]):
        raise ContractError("manifest authorization matrix does not match policy")
    execution_ids: set[str] = set()
    execution_nonces: set[str] = set()
    for action_id, raw_authorization in authorizations.items():
        authorization = require_mapping(
            raw_authorization, f"manifest authorization {action_id}"
        )
        action = require_mapping(policy["actions"][action_id], f"action {action_id}")
        authorization_fields = {
            str(binding.get("field"))
            for binding in action.get("extra_var_bindings", {}).values()
            if isinstance(binding, dict)
            and binding.get("kind")
            in {
                "authorization_field",
                "target_and_authorization_confirmation",
            }
        }
        expected_authorization_keys = (
            AUTHORIZATION_BASE_KEYS
            | set(action.get("required_evidence_references", []))
            | authorization_fields
        )
        require_exact_keys(
            authorization,
            expected_authorization_keys,
            f"manifest authorization {action_id}",
        )
        if authorization.get("status") not in {"APPROVED", "NOT_APPROVED"}:
            raise ContractError(f"authorization {action_id} has an invalid status")
        if (
            action.get("implementation_status", "ready") == "blocked"
            and authorization.get("status") != "NOT_APPROVED"
        ):
            raise ContractError(f"blocked action {action_id} cannot be approved")
        execution_approval = require_mapping(
            authorization.get("execution_approval"),
            f"manifest authorization {action_id} execution approval",
        )
        if set(execution_approval) != SIGNED_APPROVAL_KEYS:
            raise ContractError(
                f"authorization {action_id} execution approval schema is invalid"
            )
        execution_id = str(execution_approval.get("execution_id", ""))
        validate_approval_transport_shape(
            execution_approval, manifest, authorization, execution_id
        )
        nonce = str(execution_approval["nonce"])
        if execution_id in execution_ids or nonce in execution_nonces:
            raise ContractError(
                "each action authorization must use a distinct execution approval"
            )
        execution_ids.add(execution_id)
        execution_nonces.add(nonce)
        consumer_contracts = require_mapping(
            authorization.get("consumer_approval_contracts"),
            f"manifest authorization {action_id} consumer approval contracts",
        )
        expected_consumer_variables = {
            variable
            for variable, binding in action.get("extra_var_bindings", {}).items()
            if isinstance(binding, dict)
            and binding.get("kind") == "signed_approval_transport"
        }
        if set(consumer_contracts) != expected_consumer_variables:
            raise ContractError(
                f"authorization {action_id} consumer approval contract set is invalid"
            )
        for variable, raw_contract in consumer_contracts.items():
            contract = require_mapping(
                raw_contract,
                f"authorization {action_id} consumer contract {variable}",
            )
            policy_binding = require_mapping(
                action["extra_var_bindings"][variable],
                f"action {action_id} consumer binding {variable}",
            )
            require_exact_keys(
                contract,
                APPROVAL_CONTRACT_KEYS,
                f"authorization {action_id} consumer contract {variable}",
            )
            if (
                contract["operation"] != policy_binding["operation"]
                or contract["target"] != target["fqdn"]
                or canonical_approval_binding(contract["binding"])
                != canonical_approval_binding(policy_binding["contract_binding"])
            ):
                raise ContractError(
                    f"authorization {action_id} consumer contract {variable} is not policy- and target-bound"
                )
            recursively_reject_secret_fields(
                contract["binding"],
                f"manifest.authorizations.{action_id}.consumer_approval_contracts.{variable}.binding",
                allowed_secret_names=frozenset(
                    {
                        "onepassword",
                        "password_item",
                        "password_recipe",
                        "password_length",
                    }
                ),
            )
    if not isinstance(manifest.get("safety_hold"), bool):
        raise ContractError("manifest safety_hold must be a boolean")
    manifest_without_authorizations = dict(manifest)
    manifest_without_authorizations.pop("authorizations")
    recursively_reject_secret_fields(
        manifest_without_authorizations,
        "manifest",
        allowed_secret_paths=frozenset(
            {
                "manifest.controller.ssh.private_key_name",
                "manifest.controller.ssh.private_key_sha256",
            }
        ),
        allowed_secret_names=frozenset(
            {"onepassword", "password_item", "password_recipe", "password_length"}
        ),
    )
    # Action IDs are trusted identifiers from the root-owned policy and can
    # legitimately describe secret-handling checks.  Do not mistake that map
    # key for persisted secret material; scan each exact-schema authorization
    # value without incorporating its action ID into the data path.
    for authorization in authorizations.values():
        recursively_reject_secret_fields(
            authorization,
            "manifest.authorization",
            allowed_secret_names=frozenset(
                {"onepassword", "password_item", "password_recipe", "password_length"}
            ),
            allowed_multiline_paths=frozenset(
                {"manifest.authorization.execution_approval.signature"}
            ),
        )


def _write_private_bytes(path: Path, payload: bytes) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    flags |= getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags, 0o600)
    try:
        view = memoryview(payload)
        offset = 0
        while offset < len(view):
            written = os.write(descriptor, view[offset:])
            if written <= 0:
                raise ContractError(
                    "signature verification input was not written completely"
                )
            offset += written
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def verify_ssh_signature(
    payload: bytes,
    signature_payload: bytes,
    trust: dict[str, Any],
    *,
    runner: Callable[..., subprocess.CompletedProcess[bytes]] = subprocess.run,
) -> None:
    trusted_uids = set(trust.get("_trusted_uids", {0}))
    verifier_path, _verifier_payload = read_trusted_file(
        Path(str(trust["ssh_keygen_path"])),
        "signature verifier",
        trusted_uids=trusted_uids,
        expected_sha256=str(trust["ssh_keygen_sha256"]),
        maximum_size=16 * 1024 * 1024,
        executable=True,
    )
    _signers_path, signers_payload = read_trusted_file(
        Path(str(trust["allowed_signers_path"])),
        "signature allowed signers",
        trusted_uids=trusted_uids,
        expected_sha256=str(trust["allowed_signers_sha256"]),
        maximum_size=65536,
    )
    if (
        not signature_payload.isascii()
        or len(signature_payload) > 16384
        or not signature_payload.startswith(b"-----BEGIN SSH SIGNATURE-----\n")
        or not signature_payload.endswith(b"-----END SSH SIGNATURE-----\n")
    ):
        raise ContractError("detached SSH signature is malformed")
    temporary_root = Path(tempfile.mkdtemp(prefix="lit-governed-signature-"))
    os.chmod(temporary_root, 0o700)
    signers_copy = temporary_root / "allowed_signers"
    signature_copy = temporary_root / "signature"
    try:
        _write_private_bytes(signers_copy, signers_payload)
        _write_private_bytes(signature_copy, signature_payload)
        try:
            completed = runner(
                [
                    str(verifier_path),
                    "-Y",
                    "verify",
                    "-f",
                    str(signers_copy),
                    "-I",
                    str(trust["identity"]),
                    "-n",
                    str(trust["namespace"]),
                    "-s",
                    str(signature_copy),
                ],
                input=payload,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
                timeout=30,
                env={"PATH": "/usr/bin:/bin", "LANG": "C", "LC_ALL": "C"},
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise ContractError("SSH signature verifier failed to execute") from exc
        if completed.returncode != 0:
            raise ContractError("detached SSH signature verification failed")
    finally:
        signature_copy.unlink(missing_ok=True)
        signers_copy.unlink(missing_ok=True)
        temporary_root.rmdir()


def verify_manifest_signature(
    manifest_payload: bytes,
    signature: Path,
    trust: dict[str, Any],
    *,
    runner: Callable[..., subprocess.CompletedProcess[bytes]] = subprocess.run,
) -> None:
    signature_path = require_private_file(signature, "gate manifest signature")
    verify_ssh_signature(
        manifest_payload, signature_path.read_bytes(), trust, runner=runner
    )


def validate_authorization(
    action_id: str,
    action: dict[str, Any],
    manifest: dict[str, Any],
    now: dt.datetime,
) -> dict[str, Any]:
    if action.get("implementation_status", "ready") != "ready":
        raise ContractError(
            f"action {action_id} implementation is blocked: "
            f"{action.get('implementation_blocker', 'unspecified')}"
        )
    gates = manifest["gates"]
    for prerequisite in action.get("prerequisite_gates", []):
        if gates.get(prerequisite) != "ACCEPTED":
            raise ContractError(f"prerequisite gate {prerequisite} is not accepted")
    if gates.get(action["gate"]) not in {"IN_PROGRESS", "ACCEPTED"}:
        raise ContractError(f"action gate {action['gate']} is not active")
    if manifest.get("safety_hold") is True and not action.get(
        "allowed_under_safety_hold", False
    ):
        raise ContractError("safety hold blocks this action")
    authorization = require_mapping(
        manifest.get("authorizations", {}).get(action_id),
        f"authorization {action_id}",
    )
    if authorization.get("status") != "APPROVED":
        raise ContractError(f"action {action_id} is not approved")
    if not authorization.get("approval_reference") or not SHA256_RE.fullmatch(
        str(authorization.get("approval_sha256", ""))
    ):
        raise ContractError("authorization reference/hash is incomplete")
    start = parse_utc(str(authorization.get("not_before_utc", "")), "not_before_utc")
    end = parse_utc(str(authorization.get("expires_utc", "")), "expires_utc")
    if not start <= now < end or end <= start:
        raise ContractError("authorization is outside its approved time window")
    for field in action.get("required_evidence_references", []):
        if not str(authorization.get(field, "")).strip():
            raise ContractError(f"authorization is missing {field}")
    return authorization


def validate_extra_vars(
    path: Path | None,
    action: dict[str, Any],
    manifest: dict[str, Any] | None = None,
    authorization: dict[str, Any] | None = None,
    execution_id: str | None = None,
) -> tuple[dict[str, Any], str | None, Path | None]:
    allowed = set(action.get("allowed_extra_vars", []))
    required = set(action.get("required_extra_vars", []))
    if path is None:
        if required:
            raise ContractError("this action requires an extra-vars JSON file")
        return {}, None, None
    source = require_private_file(path, "extra-vars file")
    parsed, payload = read_json_object(source, "extra-vars file", 128 * 1024)
    keys = set(parsed)
    if not required.issubset(keys) or not keys.issubset(allowed):
        raise ContractError("extra-vars keys do not match the action allowlist")
    if keys & FORBIDDEN_OVERRIDE_KEYS:
        raise ContractError("extra-vars attempts to override a protected identity")
    nonsecret_secret_names = frozenset(action.get("nonsecret_secret_named_vars", []))
    signed_approval_variables = frozenset(
        variable
        for variable, raw_binding in action.get("extra_var_bindings", {}).items()
        if isinstance(raw_binding, dict)
        and raw_binding.get("kind") == "signed_approval_transport"
    )
    recursively_reject_secret_fields(
        parsed,
        "extra_vars",
        allowed_top_level_secret_names=nonsecret_secret_names,
        allowed_multiline_paths=frozenset(
            f"extra_vars.{variable}.signature" for variable in signed_approval_variables
        ),
    )
    for key, values in action.get("extra_var_allowed_values", {}).items():
        allowed_values = require_sequence(values, f"allowed values for {key}")
        if key in parsed and parsed[key] not in allowed_values:
            raise ContractError(f"extra-vars value for {key} is outside the allowlist")
    for key, raw_binding in action.get("extra_var_bindings", {}).items():
        binding = require_mapping(raw_binding, f"extra-vars binding {key}")
        kind = binding["kind"]
        if kind == "literal":
            expected = binding["value"]
        elif kind == "target_confirmation":
            if manifest is None:
                raise ContractError("target-bound extra-vars require a manifest")
            expected = f"{binding['prefix']}:{manifest['target']['fqdn']}"
        elif kind == "authorization_field":
            if authorization is None:
                raise ContractError(
                    "approval-bound extra-vars require an authorization"
                )
            field = str(binding["field"])
            expected = authorization.get(field)
            if field.endswith("sha256") and not SHA256_RE.fullmatch(
                str(expected or "")
            ):
                raise ContractError(f"authorization field {field} is not a SHA-256")
            if (
                field.endswith("fingerprint")
                and re.fullmatch(r"SHA256:[A-Za-z0-9+/]{43}", str(expected or ""))
                is None
            ):
                raise ContractError(f"authorization field {field} is not a fingerprint")
        elif kind == "signed_approval_transport":
            if manifest is None or authorization is None or execution_id is None:
                raise ContractError(
                    "signed approval transport requires manifest authorization and execution ID"
                )
            validate_approval_transport_shape(
                parsed.get(key), manifest, authorization, execution_id
            )
            expected = parsed.get(key)
        elif kind == "target_and_authorization_confirmation":
            if manifest is None or authorization is None:
                raise ContractError(
                    "approval-bound confirmation requires authorization"
                )
            field = str(binding["field"])
            bound_value = authorization.get(field)
            if field.endswith("sha256") and not SHA256_RE.fullmatch(
                str(bound_value or "")
            ):
                raise ContractError(f"authorization field {field} is not a SHA-256")
            expected = (
                f"{binding['prefix']}:{manifest['target']['fqdn']}:" f"{bound_value}"
            )
        else:  # validate_policy rejects this before execution.
            raise ContractError(f"unsupported extra-vars binding for {key}")
        if expected is None or parsed.get(key) != expected:
            raise ContractError(f"extra-vars value for {key} violates its binding")
    return parsed, sha256_bytes(payload), source


def canonical_approval_binding(value: Any, label: str = "approval binding") -> Any:
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, list):
        return [canonical_approval_binding(item, label) for item in value]
    if isinstance(value, dict):
        normalized: dict[str, Any] = {}
        for key, child in value.items():
            if not isinstance(key, str) or not key:
                raise ContractError(f"{label} contains an invalid key")
            normalized[key] = canonical_approval_binding(child, label)
        return normalized
    raise ContractError(f"{label} contains a non-canonical JSON value")


def public_approval_authority(authority: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": authority["schema_version"],
        "identity": authority["identity"],
        "namespace": authority["namespace"],
        "fingerprint": authority["fingerprint"],
        "allowed_signers_path": authority["allowed_signers_path"],
        "allowed_signers_sha256": authority["allowed_signers_sha256"],
        "allowed_signers_entry_sha256": authority["allowed_signers_entry_sha256"],
        "ssh_keygen_path": authority["ssh_keygen_path"],
        "ssh_keygen_sha256": authority["ssh_keygen_sha256"],
        "replay_directory": authority["replay_directory"],
    }


def validate_approval_transport_shape(
    value: Any,
    manifest: dict[str, Any],
    authorization: dict[str, Any],
    execution_id: str,
) -> dict[str, Any]:
    approval = require_mapping(value, "signed approval transport")
    if set(approval) != SIGNED_APPROVAL_KEYS or approval.get("schema_version") != 1:
        raise ContractError("signed approval transport has an invalid schema")
    if approval.get("execution_id") != execution_id:
        raise ContractError("signed approval transport is not bound to this attempt")
    expected_commits = {
        name: repository["commit"]
        for name, repository in manifest["repositories"].items()
    }
    if approval.get("commit_shas") != expected_commits:
        raise ContractError(
            "signed approval transport does not bind the frozen repositories"
        )
    if not re.fullmatch(r"[0-9a-f]{64}", str(approval.get("nonce", ""))):
        raise ContractError("signed approval transport nonce is invalid")
    issued_text = str(approval.get("issued_at", ""))
    expires_text = str(approval.get("expires_at", ""))
    timestamp_pattern = r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z"
    if not re.fullmatch(timestamp_pattern, issued_text) or not re.fullmatch(
        timestamp_pattern, expires_text
    ):
        raise ContractError("signed approval timestamps must use whole-second UTC")
    issued = parse_utc(issued_text, "signed approval issued_at")
    expires = parse_utc(expires_text, "signed approval expires_at")
    authorization_start = parse_utc(
        str(authorization["not_before_utc"]), "authorization not_before_utc"
    )
    authorization_end = parse_utc(
        str(authorization["expires_utc"]), "authorization expires_utc"
    )
    if not (
        authorization_start <= issued < expires <= authorization_end
        and (expires - issued).total_seconds() <= MAX_APPROVAL_SECONDS
    ):
        raise ContractError("signed approval is outside the outer authorization window")
    signature = approval.get("signature")
    if (
        not isinstance(signature, str)
        or not signature.isascii()
        or len(signature) > 16384
        or "\x00" in signature
        or not signature.startswith("-----BEGIN SSH SIGNATURE-----\n")
        or not signature.endswith("-----END SSH SIGNATURE-----\n")
    ):
        raise ContractError("signed approval signature is malformed")
    return approval


def normalize_and_verify_approval(
    value: Any,
    manifest: dict[str, Any],
    authorization: dict[str, Any],
    execution_id: str,
    authority: dict[str, Any],
    *,
    operation: str,
    target: str,
    binding: Any,
    now: dt.datetime,
    allow_existing_marker: bool = False,
    runner: Callable[..., subprocess.CompletedProcess[bytes]] = subprocess.run,
) -> dict[str, Any]:
    approval = validate_approval_transport_shape(
        value, manifest, authorization, execution_id
    )
    replay_directory, replay_status = require_controller_replay_directory(
        Path(str(approval["replay_directory"])), "approval replay directory"
    )
    if replay_directory != Path(str(authority["replay_directory"])) or (
        replay_status.st_dev != authority["_replay_directory_device"]
        or replay_status.st_ino != authority["_replay_directory_inode"]
    ):
        raise ContractError("approval replay directory does not match its authority")
    issued = parse_utc(str(approval["issued_at"]), "approval issued_at")
    expires = parse_utc(str(approval["expires_at"]), "approval expires_at")
    if now.tzinfo is None:
        raise ContractError("approval validation time must be timezone-aware")
    now = now.astimezone(dt.timezone.utc)
    if now < issued and (issued - now).total_seconds() > MAX_CLOCK_SKEW_SECONDS:
        raise ContractError("approval is not yet valid")
    if now >= expires:
        raise ContractError("approval has expired")
    if not operation or not target:
        raise ContractError("approval operation and target are required")
    normalized_binding = canonical_approval_binding(binding)
    payload_document = {
        "schema_version": 1,
        "authority": public_approval_authority(authority),
        "execution_id": approval["execution_id"],
        "commit_shas": dict(sorted(approval["commit_shas"].items())),
        "nonce": approval["nonce"],
        "issued_at": approval["issued_at"],
        "expires_at": approval["expires_at"],
        "replay_directory": str(replay_directory),
        "operation": operation,
        "target": target,
        "binding": normalized_binding,
    }
    payload = canonical_json_bytes(payload_document)
    verify_ssh_signature(
        payload, approval["signature"].encode("ascii"), authority, runner=runner
    )
    approval_digest = sha256_bytes(payload)
    replay_identity = {
        "schema_version": 1,
        "authority_identity": authority["identity"],
        "authority_namespace": authority["namespace"],
        "authority_fingerprint": authority["fingerprint"],
        "execution_id": execution_id,
        "nonce": approval["nonce"],
    }
    replay_digest = sha256_bytes(canonical_json_bytes(replay_identity))
    marker = replay_directory / f"{replay_digest}.used"
    if os.path.lexists(marker) and not allow_existing_marker:
        raise ContractError("approval has already been consumed")
    return {
        "execution_id": execution_id,
        "commit_shas": dict(sorted(approval["commit_shas"].items())),
        "issued_at": approval["issued_at"],
        "expires_at": approval["expires_at"],
        "approval_digest": approval_digest,
        "replay_digest": replay_digest,
        "authority_identity": authority["identity"],
        "authority_namespace": authority["namespace"],
        "authority_fingerprint": authority["fingerprint"],
        "_nonce": approval["nonce"],
        "_signature": approval["signature"],
        "_operation": operation,
        "_target": target,
        "_binding": normalized_binding,
        "_replay_directory": str(replay_directory),
        "_replay_directory_device": replay_status.st_dev,
        "_replay_directory_inode": replay_status.st_ino,
        "_marker": str(marker),
    }


def safe_approval_metadata(normalized: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        **{
            key: normalized[key]
            for key in (
                "execution_id",
                "commit_shas",
                "issued_at",
                "expires_at",
                "approval_digest",
                "replay_digest",
                "authority_identity",
                "authority_namespace",
                "authority_fingerprint",
            )
        },
    }


def revalidate_approval(
    normalized: dict[str, Any],
    authority: dict[str, Any],
    now: dt.datetime,
    *,
    require_unclaimed: bool,
    verify_local_claim: bool = True,
    runner: Callable[..., subprocess.CompletedProcess[bytes]] = subprocess.run,
) -> None:
    reconstructed = {
        "schema_version": 1,
        "execution_id": normalized["execution_id"],
        "commit_shas": normalized["commit_shas"],
        "nonce": normalized["_nonce"],
        "issued_at": normalized["issued_at"],
        "expires_at": normalized["expires_at"],
        "replay_directory": normalized["_replay_directory"],
        "signature": normalized["_signature"],
    }
    verified = normalize_and_verify_approval(
        reconstructed,
        {
            "repositories": {
                name: {"commit": commit}
                for name, commit in normalized["commit_shas"].items()
            }
        },
        {
            "not_before_utc": normalized["issued_at"],
            "expires_utc": normalized["expires_at"],
        },
        normalized["execution_id"],
        authority,
        operation=normalized["_operation"],
        target=normalized["_target"],
        binding=normalized["_binding"],
        now=now,
        allow_existing_marker=not require_unclaimed,
        runner=runner,
    )
    if verified["approval_digest"] != normalized["approval_digest"]:
        raise ContractError("approval contract changed during revalidation")
    marker_exists = os.path.lexists(normalized["_marker"])
    if require_unclaimed and marker_exists:
        raise ContractError("approval was claimed before its authorized boundary")
    if not require_unclaimed and verify_local_claim:
        verify_claimed_approval_marker(normalized, "claimed approval")


def invoke_replay_broker(
    operation: str,
    normalized: dict[str, Any],
    broker: dict[str, str],
    *,
    runner: Callable[..., subprocess.CompletedProcess[bytes]] = subprocess.run,
) -> dict[str, str]:
    if operation not in {"claim", "verify"}:
        raise ContractError("replay broker operation is invalid")
    request = {
        "schema_version": 1,
        "store_id": broker["store_id"],
        "operation": operation,
        "execution_id": normalized["execution_id"],
        "approval_digest": normalized["approval_digest"],
        "replay_digest": normalized["replay_digest"],
    }
    try:
        completed = runner(
            [broker["path"], operation],
            input=canonical_json_bytes(request),
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
            timeout=30,
            env={"PATH": "/usr/bin:/bin", "LANG": "C", "LC_ALL": "C"},
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise ContractError("root-brokered replay store failed") from exc
    if completed.returncode != 0 or len(completed.stdout) > 64 * 1024:
        raise ContractError("root-brokered replay store rejected the request")
    response = require_mapping(
        strict_json_loads(completed.stdout, "replay broker response"),
        "replay broker response",
    )
    expected = {
        **request,
        "status": "CLAIMED",
    }
    if response != expected:
        raise ContractError("root-brokered replay response is not exact")
    return {
        "store_id": broker["store_id"],
        "approval_digest": normalized["approval_digest"],
        "replay_digest": normalized["replay_digest"],
        "claim_status": (
            "CLAIMED_BY_ROOT_BROKER"
            if operation == "claim"
            else "ROOT_BROKER_CLAIM_VERIFIED"
        ),
    }


def revalidate_brokered_execution_approval(
    normalized: dict[str, Any],
    authority: dict[str, Any],
    broker: dict[str, str],
    claim: dict[str, str],
    now: dt.datetime,
) -> None:
    revalidate_approval(
        normalized,
        authority,
        now,
        require_unclaimed=False,
        verify_local_claim=False,
    )
    verified = invoke_replay_broker("verify", normalized, broker)
    if (
        claim.get("store_id") != verified["store_id"]
        or claim.get("approval_digest") != verified["approval_digest"]
        or claim.get("replay_digest") != verified["replay_digest"]
    ):
        raise ContractError("root-brokered execution claim changed")


def verify_claimed_approval_marker(
    normalized: dict[str, Any], label: str
) -> dict[str, str]:
    """Read back one claimed marker through its pinned ledger directory."""
    replay_directory, replay_status = require_controller_replay_directory(
        Path(str(normalized["_replay_directory"])), f"{label} replay directory"
    )
    if (
        replay_status.st_dev != normalized["_replay_directory_device"]
        or replay_status.st_ino != normalized["_replay_directory_inode"]
    ):
        raise ContractError(f"{label} replay directory identity changed")
    marker_name = f"{normalized['replay_digest']}.used"
    expected_marker = replay_directory / marker_name
    if str(expected_marker) != str(normalized["_marker"]):
        raise ContractError(f"{label} marker path is not ledger-bound")

    directory_flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    directory_flags |= getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    marker_flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0)
    marker_flags |= getattr(os, "O_NOFOLLOW", 0)
    directory_descriptor = -1
    marker_descriptor = -1
    try:
        directory_descriptor = os.open(replay_directory, directory_flags)
        observed_directory = os.fstat(directory_descriptor)
        if (
            observed_directory.st_uid != os.geteuid()
            or stat.S_IMODE(observed_directory.st_mode) != 0o700
            or observed_directory.st_dev != normalized["_replay_directory_device"]
            or observed_directory.st_ino != normalized["_replay_directory_inode"]
        ):
            raise ContractError(f"{label} replay directory changed before readback")
        marker_descriptor = os.open(
            marker_name, marker_flags, dir_fd=directory_descriptor
        )
        marker_status = os.fstat(marker_descriptor)
        if (
            not stat.S_ISREG(marker_status.st_mode)
            or marker_status.st_uid != os.geteuid()
            or marker_status.st_nlink != 1
            or stat.S_IMODE(marker_status.st_mode) != 0o600
        ):
            raise ContractError(f"{label} ledger marker metadata is unsafe")
        chunks = bytearray()
        while len(chunks) <= 64 * 1024:
            chunk = os.read(marker_descriptor, min(8192, 64 * 1024 + 1 - len(chunks)))
            if not chunk:
                break
            chunks.extend(chunk)
        if len(chunks) > 64 * 1024:
            raise ContractError(f"{label} ledger marker is too large")
    except FileNotFoundError as exc:
        raise ContractError(f"{label} ledger marker is missing") from exc
    except OSError as exc:
        raise ContractError(f"{label} ledger marker readback failed") from exc
    finally:
        if marker_descriptor >= 0:
            os.close(marker_descriptor)
        if directory_descriptor >= 0:
            os.close(directory_descriptor)

    document = require_mapping(
        strict_json_loads(bytes(chunks), f"{label} ledger marker"),
        f"{label} ledger marker",
    )
    if document != safe_approval_metadata(normalized):
        raise ContractError(f"{label} ledger marker is invalid")
    return {
        "approval_digest": normalized["approval_digest"],
        "replay_digest": normalized["replay_digest"],
        "claim_status": "CLAIMED_AND_VERIFIED",
    }


def validate_ledger_integrity(directory: Path) -> None:
    replay_directory, _status = require_controller_replay_directory(
        directory, "approval ledger"
    )
    for entry in replay_directory.iterdir():
        if not re.fullmatch(r"[0-9a-f]{64}\.used", entry.name):
            raise ContractError("approval ledger contains an unexpected entry")
        if entry.is_symlink():
            raise ContractError("approval ledger contains a symbolic link")
        status = os.lstat(entry)
        if (
            not stat.S_ISREG(status.st_mode)
            or status.st_uid != os.geteuid()
            or status.st_nlink != 1
            or status.st_mode & 0o077
        ):
            raise ContractError("approval ledger entry has unsafe metadata")
        payload = entry.read_bytes()
        document = require_mapping(
            strict_json_loads(payload, "approval ledger entry"),
            "approval ledger entry",
        )
        expected_keys = {
            "schema_version",
            "execution_id",
            "commit_shas",
            "issued_at",
            "expires_at",
            "approval_digest",
            "replay_digest",
            "authority_identity",
            "authority_namespace",
            "authority_fingerprint",
        }
        require_exact_keys(document, expected_keys, "approval ledger entry")
        if (
            document.get("schema_version") != 1
            or document.get("replay_digest") != entry.stem
        ):
            raise ContractError("approval ledger entry identity is invalid")
        if not SHA256_RE.fullmatch(str(document.get("approval_digest", ""))):
            raise ContractError("approval ledger entry digest is invalid")


def _claim_local_approval_marker_for_test(
    normalized: dict[str, Any], now: dt.datetime
) -> dict[str, str]:
    issued = parse_utc(str(normalized["issued_at"]), "approval issued_at")
    expires = parse_utc(str(normalized["expires_at"]), "approval expires_at")
    now = now.astimezone(dt.timezone.utc)
    if now < issued and (issued - now).total_seconds() > MAX_CLOCK_SKEW_SECONDS:
        raise ContractError("approval is not yet valid at claim time")
    if now >= expires:
        raise ContractError("approval expired before claim")
    replay_directory = Path(str(normalized["_replay_directory"]))
    validate_ledger_integrity(replay_directory)
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    flags |= getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    directory_descriptor = os.open(replay_directory, flags)
    marker_descriptor = -1
    marker_name = f"{normalized['replay_digest']}.used"
    try:
        status = os.fstat(directory_descriptor)
        if (
            status.st_uid != os.geteuid()
            or stat.S_IMODE(status.st_mode) != 0o700
            or status.st_dev != normalized["_replay_directory_device"]
            or status.st_ino != normalized["_replay_directory_inode"]
        ):
            raise ContractError("approval ledger identity or permissions changed")
        marker_flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        marker_flags |= getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
        try:
            marker_descriptor = os.open(
                marker_name, marker_flags, 0o600, dir_fd=directory_descriptor
            )
        except FileExistsError as exc:
            raise ContractError("approval has already been consumed") from exc
        evidence = canonical_json_bytes(safe_approval_metadata(normalized))
        offset = 0
        while offset < len(evidence):
            written = os.write(marker_descriptor, evidence[offset:])
            if written <= 0:
                raise ContractError("approval ledger claim was not written completely")
            offset += written
        os.fsync(marker_descriptor)
        os.fsync(directory_descriptor)
    finally:
        if marker_descriptor >= 0:
            os.close(marker_descriptor)
        os.close(directory_descriptor)
    marker = replay_directory / marker_name
    if marker.read_bytes() != canonical_json_bytes(safe_approval_metadata(normalized)):
        raise ContractError("approval ledger claim failed readback verification")
    validate_ledger_integrity(replay_directory)
    return {
        "replay_digest": normalized["replay_digest"],
        "approval_digest": normalized["approval_digest"],
        "claim_status": "CLAIMED_AND_FSYNCED",
    }


def execution_approval_binding(
    action_id: str,
    action: dict[str, Any],
    manifest: dict[str, Any],
    authorization: dict[str, Any],
) -> dict[str, Any]:
    return {
        "action_id": action_id,
        "gate": action["gate"],
        "impact": action["impact"],
        "policy_sha256": manifest["policy_sha256"],
        "target": manifest["target"],
        "controller": {
            "device_id": manifest["controller"]["device_id"],
            "source_cidr": manifest["controller"]["source_cidr"],
            "ssh": manifest["controller"]["ssh"],
        },
        "runtime": {
            "toolbox_image": manifest["runtime"]["toolbox_image"],
            "run_ee_image": manifest["runtime"]["run_ee_image"],
            "attestation_sha256": manifest["runtime"]["attestation_sha256"],
        },
        "manifest_state": {
            "manifest_status": manifest["manifest_status"],
            "safety_hold": manifest["safety_hold"],
            "gates": manifest["gates"],
        },
        "outer_authorization": {
            "reference": authorization["approval_reference"],
            "sha256": authorization["approval_sha256"],
        },
    }


def prepare_approvals(
    action_id: str,
    action: dict[str, Any],
    manifest: dict[str, Any],
    authorization: dict[str, Any],
    execution_id: str,
    extra_vars: dict[str, Any],
    authority: dict[str, Any],
    now: dt.datetime,
    *,
    runner: Callable[..., subprocess.CompletedProcess[bytes]] = subprocess.run,
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    execution = normalize_and_verify_approval(
        authorization["execution_approval"],
        manifest,
        authorization,
        execution_id,
        authority,
        operation="governed-ansible-action",
        target=manifest["target"]["fqdn"],
        binding=execution_approval_binding(action_id, action, manifest, authorization),
        now=now,
        runner=runner,
    )
    consumers: dict[str, dict[str, Any]] = {}
    for variable, binding in action.get("extra_var_bindings", {}).items():
        if binding.get("kind") != "signed_approval_transport":
            continue
        contract = authorization["consumer_approval_contracts"][variable]
        consumers[variable] = normalize_and_verify_approval(
            extra_vars[variable],
            manifest,
            authorization,
            execution_id,
            authority,
            operation=contract["operation"],
            target=contract["target"],
            binding=contract["binding"],
            now=now,
            runner=runner,
        )
    all_approvals = [execution, *consumers.values()]
    if len({approval["_nonce"] for approval in all_approvals}) != len(all_approvals):
        raise ContractError("execution and consumer approvals must use distinct nonces")
    if len({approval["replay_digest"] for approval in all_approvals}) != len(
        all_approvals
    ):
        raise ContractError(
            "execution and consumer approvals must use distinct replay identities"
        )
    return execution, consumers


def verify_consumer_claims(
    consumers: dict[str, dict[str, Any]]
) -> list[dict[str, str]]:
    claims: list[dict[str, str]] = []
    for variable, normalized in consumers.items():
        verified = verify_claimed_approval_marker(
            normalized, f"consumer approval {variable}"
        )
        claims.append(
            {
                "variable": variable,
                "approval_digest": verified["approval_digest"],
                "replay_digest": verified["replay_digest"],
                "claim_status": "CLAIMED_BY_FOUNDATIONAL_CONSUMER",
            }
        )
    return claims


def build_command(
    action: dict[str, Any],
    target: dict[str, Any],
    repos: dict[str, Path],
    execution_id: str,
    sealed_extra_vars: Path | None,
) -> tuple[list[str], dict[str, Any]]:
    automation = repos["automation"]
    inventory_repo = repos["inventory"]
    wrapper = (automation / "ansible" / "scripts" / "ansible-nav").resolve()
    expected_wrapper = (automation / "ansible" / "scripts" / "ansible-nav").resolve()
    if wrapper != expected_wrapper or not wrapper.is_file() or wrapper.is_symlink():
        raise ContractError("canonical ansible-nav wrapper is missing")
    inventory_relative = str(action.get("inventory", "inventories/pub/inventory.yml"))
    inventory_path = (inventory_repo / inventory_relative).resolve()
    if inventory_repo not in inventory_path.parents or not inventory_path.is_file():
        raise ContractError("action inventory path escapes the inventory repository")
    runtime_inventory = (
        "/runner/project/inventories/" + inventory_relative.split("inventories/", 1)[-1]
    )
    mode = action["mode"]
    playbook = action.get("playbook")
    if mode != "inventory_projection":
        playbook_path = (automation / "ansible" / str(playbook)).resolve()
        ansible_root = (automation / "ansible").resolve()
        if (
            playbook_path == ansible_root
            or ansible_root not in playbook_path.parents
            or not playbook_path.is_file()
        ):
            raise ContractError(
                "policy playbook is missing or escapes the automation tree"
            )
    if mode == "inventory_projection":
        command = [
            str(wrapper),
            "exec",
            "--",
            "ansible-inventory",
            "-i",
            runtime_inventory,
            "--host",
            target["fqdn"],
        ]
    elif mode == "syntax_check":
        command = [
            str(wrapper),
            "exec",
            "--",
            "ansible-playbook",
            str(playbook),
            "-i",
            runtime_inventory,
            "--syntax-check",
        ]
    else:
        command = [
            str(wrapper),
            "run",
            str(playbook),
            "-i",
            str(inventory_path),
            "--limit",
            target["fqdn"],
        ]
        tags = action.get("tags", [])
        if tags:
            command.extend(["--tags", ",".join(tags)])
        skip_tags = action.get("skip_tags", [])
        if skip_tags:
            command.extend(["--skip-tags", ",".join(skip_tags)])
        if action.get("check_mode"):
            command.append("--check")
        if action.get("diff_mode"):
            command.append("--diff")
        if sealed_extra_vars is not None:
            runtime_extra = "/runner/governed-input/extra-vars.json"
            command.extend(["--extra-vars", f"@{runtime_extra}"])
    return command, {
        "launcher_path": str(wrapper),
        "launcher_sha256": sha256_file(wrapper),
        "inventory_path": str(inventory_path),
        "inventory_relative_path": inventory_relative,
        "playbook": playbook or "ansible-inventory",
        "limit": target["fqdn"] if mode == "playbook" else None,
        "tags": action.get("tags", []),
        "skip_tags": action.get("skip_tags", []),
        "check_mode": bool(action.get("check_mode")),
        "diff_mode": bool(action.get("diff_mode")),
    }


def build_pre_live_projection_command(
    action: dict[str, Any], target: dict[str, Any], repos: dict[str, Path]
) -> list[str]:
    if action["impact"] not in LIVE_IMPACTS:
        raise ContractError("pre-live projection requested for a non-live action")
    automation = repos["automation"]
    inventory_repo = repos["inventory"]
    wrapper = automation / "ansible" / "scripts" / "ansible-nav"
    inventory_relative = str(action.get("inventory", "inventories/pub/inventory.yml"))
    inventory_path = (inventory_repo / inventory_relative).resolve()
    if inventory_repo not in inventory_path.parents or not inventory_path.is_file():
        raise ContractError(
            "pre-live inventory path is missing or escapes its snapshot"
        )
    runtime_inventory = (
        "/runner/project/inventories/" + inventory_relative.split("inventories/", 1)[-1]
    )
    return [
        str(wrapper),
        "exec",
        "--",
        "ansible-inventory",
        "-i",
        runtime_inventory,
        "--host",
        target["fqdn"],
    ]


def build_runtime_provenance_commands(repos: dict[str, Path]) -> dict[str, list[str]]:
    wrapper = repos["automation"] / "ansible" / "scripts" / "ansible-nav"
    if not wrapper.is_file() or wrapper.is_symlink():
        raise ContractError("runtime provenance wrapper is missing")
    return {
        "toolbox": [str(wrapper), "provenance-toolbox"],
        "run_ee": [str(wrapper), "provenance-run-ee"],
    }


def make_environment(
    manifest: dict[str, Any],
    action_id: str,
    action: dict[str, Any],
    repos: dict[str, Path] | None = None,
    *,
    container_engine: dict[str, str],
    sealed_ssh_directory: Path | None = None,
    execution_id: str | None = None,
    runtime_root: Path | None = None,
    runner_artifact_directory: Path | None = None,
    governed_input_directory: Path | None = None,
) -> dict[str, str]:
    for name in os.environ:
        if FORBIDDEN_EXECUTION_ENV_RE.fullmatch(name):
            raise ContractError(
                f"forbidden secret-bearing environment variable is set: {name}"
            )
    environment: dict[str, str] = {
        "PATH": "/usr/bin:/bin:/usr/sbin:/sbin",
    }
    if (
        set(container_engine) != CONTAINER_ENGINE_KEYS
        or container_engine.get("kind") != "podman"
        or not Path(str(container_engine.get("path", ""))).is_absolute()
        or not SHA256_RE.fullmatch(str(container_engine.get("sha256", "")))
    ):
        raise ContractError("container engine trust is incomplete")
    environment["ANSIBLE_TOOLBOX_ENGINE_BINARY"] = str(container_engine["path"])
    environment["CONTAINER_HOST"] = str(container_engine["backend_uri"])
    if runtime_root is not None:
        runtime_tmp = runtime_root / "tmp"
        runtime_tmp.mkdir(mode=0o700, exist_ok=True)
        runtime_home = runtime_root / "controller-home"
        runtime_home.mkdir(mode=0o700, exist_ok=True)
        runtime_config = runtime_root / "controller-config"
        runtime_config.mkdir(mode=0o700, exist_ok=True)
        runtime_cache = runtime_root / "controller-cache"
        runtime_cache.mkdir(mode=0o700, exist_ok=True)
        environment["TMPDIR"] = str(runtime_tmp)
        environment["HOME"] = str(runtime_home)
        environment["XDG_CONFIG_HOME"] = str(runtime_config)
        environment["XDG_CACHE_HOME"] = str(runtime_cache)
    else:
        raise ContractError("governed execution requires an isolated runtime home")
    if repos is not None:
        environment["ANSIBLE_TOOLBOX_INVENTORY_SOURCE"] = str(
            (repos["inventory"] / "inventories").resolve()
        )
    if runner_artifact_directory is not None:
        require_private_directory(
            runner_artifact_directory, "ephemeral Runner artifact directory"
        )
        environment["ANSIBLE_TOOLBOX_RUNNER_ARTIFACT_SOURCE"] = str(
            runner_artifact_directory
        )
    if governed_input_directory is not None:
        require_private_directory(governed_input_directory, "governed input directory")
        environment["ANSIBLE_TOOLBOX_GOVERNED_INPUT_SOURCE"] = str(
            governed_input_directory
        )
    requires_private_key = action.get(
        "requires_ssh_private_key", action["impact"] in LIVE_IMPACTS
    )
    requires_ssh_agent = action.get("requires_ssh_agent", False)
    if requires_private_key and requires_ssh_agent:
        raise ContractError("an action cannot combine an SSH key and SSH agent")
    if requires_private_key:
        ssh_contract = manifest["controller"]["ssh"]
        if sealed_ssh_directory is None:
            raise ContractError("live action is missing sealed controller SSH inputs")
        ssh_source = require_private_directory(
            sealed_ssh_directory, "sealed controller SSH inputs"
        )
        private_key = require_private_file(
            ssh_source / "id_selected",
            "sealed controller SSH private key",
        )
        if sha256_file(private_key) != ssh_contract["private_key_sha256"]:
            raise ContractError("controller SSH private key hash mismatch")
        known_hosts = require_private_file(
            ssh_source / "known_hosts",
            "sealed controller SSH known-hosts file",
        )
        if sha256_file(known_hosts) != ssh_contract["known_hosts_sha256"]:
            raise ContractError("controller SSH known-hosts hash mismatch")
        environment["ANSIBLE_TOOLBOX_SSH_PRIVATE_KEY_FILE"] = str(private_key)
        environment["ANSIBLE_TOOLBOX_SSH_KNOWN_HOSTS_FILE"] = str(known_hosts)
        environment["ANSIBLE_TOOLBOX_SSH_PRIVATE_KEY_SHA256"] = str(
            ssh_contract["private_key_sha256"]
        )
        environment["ANSIBLE_TOOLBOX_SSH_KNOWN_HOSTS_SHA256"] = str(
            ssh_contract["known_hosts_sha256"]
        )
        environment["ANSIBLE_TOOLBOX_MOUNT_SSH"] = "false"
        environment["ANSIBLE_TOOLBOX_MOUNT_SSH_AGENT"] = "false"
    else:
        environment["ANSIBLE_TOOLBOX_MOUNT_SSH"] = "false"
        environment["ANSIBLE_TOOLBOX_MOUNT_SSH_AGENT"] = "false"
    if requires_ssh_agent:
        ssh_agent = os.environ.get("SSH_AUTH_SOCK")
        if (
            not ssh_agent
            or not Path(ssh_agent).exists()
            or not stat.S_ISSOCK(Path(ssh_agent).stat().st_mode)
        ):
            raise ContractError("action requires a live SSH agent socket")
        environment["SSH_AUTH_SOCK"] = ssh_agent
        environment["ANSIBLE_TOOLBOX_MOUNT_SSH_AGENT"] = "true"
    runtime = manifest["runtime"]
    environment.update(
        {
            "ANSIBLE_TOOLBOX_IMAGE": runtime["toolbox_image"],
            "ANSIBLE_TOOLBOX_RUN_EE_IMAGE": runtime["run_ee_image"],
            "ANSIBLE_TOOLBOX_ENGINE": "podman",
            "ANSIBLE_TOOLBOX_PULL_POLICY": "never",
            "ANSIBLE_TOOLBOX_RUNTIME_MODE": "disconnected",
            "ANSIBLE_TOOLBOX_RUN_EE_PRELOAD": "true",
            "ANSIBLE_TOOLBOX_RH_COLLECTIONS_MODE": "never",
            "ANSIBLE_TOOLBOX_AUTO_COLLECTIONS": "false",
            "ANSIBLE_TOOLBOX_EE_ONLY_COLLECTIONS": "true",
            "ANSIBLE_COLLECTIONS_SCAN_SYS_PATH": "False",
            "ANSIBLE_NOCOLOR": "1",
            "ANSIBLE_DISPLAY_ARGS_TO_STDOUT": "False",
            "ANSIBLE_STDOUT_CALLBACK": "lit_governed_evidence",
            "ANSIBLE_CALLBACK_PLUGINS": "/runner/project/callback_plugins",
            "LIT_GOVERNED_ACTION_ID": action_id,
            "LIT_GOVERNED_SAFE_TASKS": json.dumps(
                action.get("safe_artifact_tasks", []), separators=(",", ":")
            ),
        }
    )
    if execution_id is not None:
        environment["LIT_GOVERNED_EXECUTION_ID"] = execution_id
    return environment


def seal_controller_ssh_inputs(
    manifest: dict[str, Any], action: dict[str, Any], destination: Path
) -> Path | None:
    requires_private_key = action.get(
        "requires_ssh_private_key", action["impact"] in LIVE_IMPACTS
    )
    if not requires_private_key:
        return None
    contract = manifest["controller"]["ssh"]
    source = require_private_directory(
        Path(contract["source_directory"]), "controller SSH source"
    )
    trusted_uids = {0, os.geteuid()}
    _key_path, key_payload = read_trusted_file(
        source / contract["private_key_name"],
        "controller SSH private key",
        trusted_uids=trusted_uids,
        expected_sha256=contract["private_key_sha256"],
        maximum_size=1024 * 1024,
    )
    _known_hosts_path, known_hosts_payload = read_trusted_file(
        source / contract["known_hosts_name"],
        "controller SSH known-hosts file",
        trusted_uids=trusted_uids,
        expected_sha256=contract["known_hosts_sha256"],
        maximum_size=1024 * 1024,
    )
    destination.mkdir(mode=0o700)
    _write_private_bytes(destination / "id_selected", key_payload)
    _write_private_bytes(destination / "known_hosts", known_hosts_payload)
    verify_sealed_ssh_inputs(destination, manifest, action)
    return destination


def verify_sealed_ssh_inputs(
    directory: Path | None, manifest: dict[str, Any], action: dict[str, Any]
) -> None:
    requires_private_key = action.get(
        "requires_ssh_private_key", action["impact"] in LIVE_IMPACTS
    )
    if not requires_private_key:
        if directory is not None:
            raise ContractError("non-SSH action received sealed SSH inputs")
        return
    if directory is None:
        raise ContractError("live action is missing sealed SSH inputs")
    sealed = require_private_directory(directory, "sealed controller SSH inputs")
    contract = manifest["controller"]["ssh"]
    if (
        sha256_file(
            require_private_file(sealed / "id_selected", "sealed SSH private key")
        )
        != contract["private_key_sha256"]
    ):
        raise ContractError("sealed controller SSH private key changed")
    if (
        sha256_file(
            require_private_file(sealed / "known_hosts", "sealed SSH known-hosts")
        )
        != contract["known_hosts_sha256"]
    ):
        raise ContractError("sealed controller SSH known-hosts changed")


def load_and_verify_runtime_attestation(
    manifest: dict[str, Any],
    policy: dict[str, Any],
    signature_trust: dict[str, Any],
    *,
    runner: Callable[..., subprocess.CompletedProcess[bytes]] = subprocess.run,
) -> tuple[dict[str, Any], bytes]:
    runtime = manifest["runtime"]
    attestation_path = require_private_file(
        Path(runtime["attestation_path"]), "runtime attestation"
    )
    payload = attestation_path.read_bytes()
    if sha256_bytes(payload) != runtime["attestation_sha256"]:
        raise ContractError("runtime attestation hash mismatch")
    signature_path = require_private_file(
        Path(runtime["attestation_signature_path"]), "runtime attestation signature"
    )
    verify_ssh_signature(
        payload, signature_path.read_bytes(), signature_trust, runner=runner
    )
    document = require_mapping(
        strict_json_loads(payload, "runtime attestation"), "runtime attestation"
    )
    require_exact_keys(document, RUNTIME_ATTESTATION_KEYS, "runtime attestation")
    if document.get("schema_version") != 1:
        raise ContractError("runtime attestation schema_version must be 1")
    expected_images = {
        "toolbox": runtime["toolbox_image"],
        "run_ee": runtime["run_ee_image"],
    }
    for role in ("toolbox", "run_ee"):
        provenance = require_mapping(document[role], f"runtime attestation {role}")
        require_exact_keys(
            provenance, RUNTIME_PROVENANCE_KEYS, f"runtime attestation {role}"
        )
        if (
            provenance.get("schema_version") != 1
            or provenance.get("image_role") != role
        ):
            raise ContractError(f"runtime attestation {role} identity is invalid")
        if provenance.get("image") != expected_images[role]:
            raise ContractError(f"runtime attestation {role} image digest mismatch")
        loader = require_mapping(
            provenance.get("loader"), f"runtime attestation {role} loader"
        )
        require_exact_keys(
            loader, RUNTIME_LOADER_KEYS, f"runtime attestation {role} loader"
        )
        if loader != EXPECTED_RUNTIME_LOADER:
            raise ContractError(
                f"runtime attestation {role} collection loader is not fail-closed"
            )
        collections = require_mapping(
            provenance.get("collections"), f"runtime attestation {role} collections"
        )
        if set(collections) != set(policy["required_collections"]):
            raise ContractError(f"runtime attestation {role} collection set mismatch")
        for name, raw_collection in collections.items():
            collection = require_mapping(
                raw_collection, f"runtime attestation {role} collection {name}"
            )
            require_exact_keys(
                collection,
                COLLECTION_PROVENANCE_KEYS,
                f"runtime attestation {role} collection {name}",
            )
            if collection["fqcn"] != f"lit.{name}":
                raise ContractError(
                    f"runtime attestation {role} collection {name} FQCN mismatch"
                )
            if not str(collection["version"]).strip() or not SHA256_RE.fullmatch(
                str(collection["installed_tree_sha256"])
            ):
                raise ContractError(
                    f"runtime attestation {role} collection {name} is incomplete"
                )
            repository = policy["collection_repositories"][name]
            if (
                collection["source_commit"]
                != manifest["repositories"][repository]["commit"]
            ):
                raise ContractError(
                    f"runtime attestation {role} collection {name} source commit mismatch"
                )
    recursively_reject_secret_fields(document, "runtime_attestation")
    return document, payload


def validate_runtime_probe(
    payload: bytes,
    role: str,
    expected: dict[str, Any],
    policy: dict[str, Any],
) -> dict[str, Any]:
    probe = require_mapping(
        strict_json_loads(payload, f"{role} runtime probe"), f"{role} runtime probe"
    )
    require_exact_keys(probe, RUNTIME_PROVENANCE_KEYS, f"{role} runtime probe")
    if (
        probe.get("schema_version") != 1
        or probe.get("image_role") != role
        or probe.get("image") != expected["image"]
    ):
        raise ContractError(f"{role} runtime probe identity mismatch")
    loader = require_mapping(probe.get("loader"), f"{role} runtime probe loader")
    require_exact_keys(loader, RUNTIME_LOADER_KEYS, f"{role} runtime probe loader")
    if loader != expected.get("loader") or loader != EXPECTED_RUNTIME_LOADER:
        raise ContractError(f"{role} runtime collection loader is not fail-closed")
    collections = require_mapping(
        probe.get("collections"), f"{role} runtime probe collections"
    )
    if set(collections) != set(policy["required_collections"]):
        raise ContractError(f"{role} runtime probe collection set mismatch")
    for name, raw_collection in collections.items():
        collection = require_mapping(
            raw_collection, f"{role} runtime probe collection {name}"
        )
        require_exact_keys(
            collection, PROBE_COLLECTION_KEYS, f"{role} runtime probe collection {name}"
        )
        expected_collection = expected["collections"][name]
        for key in PROBE_COLLECTION_KEYS:
            if collection[key] != expected_collection[key]:
                raise ContractError(f"{role} runtime collection {name} {key} mismatch")
    recursively_reject_secret_fields(probe, f"{role}_runtime_probe")
    return probe


def run_runtime_provenance_probes(
    commands: dict[str, list[str]],
    environment: dict[str, str],
    cwd: Path,
    attestation: dict[str, Any],
    policy: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    allowed_environment = {
        "PATH",
        "TMPDIR",
        "XDG_CONFIG_HOME",
        "XDG_CACHE_HOME",
        "CONTAINER_HOST",
        "ANSIBLE_TOOLBOX_ENGINE_BINARY",
        "ANSIBLE_TOOLBOX_IMAGE",
        "ANSIBLE_TOOLBOX_RUN_EE_IMAGE",
        "ANSIBLE_TOOLBOX_ENGINE",
        "ANSIBLE_TOOLBOX_PULL_POLICY",
        "ANSIBLE_TOOLBOX_RUNTIME_MODE",
        "ANSIBLE_TOOLBOX_RUN_EE_PRELOAD",
        "ANSIBLE_TOOLBOX_RH_COLLECTIONS_MODE",
        "ANSIBLE_TOOLBOX_AUTO_COLLECTIONS",
        "ANSIBLE_TOOLBOX_EE_ONLY_COLLECTIONS",
        "ANSIBLE_COLLECTIONS_SCAN_SYS_PATH",
        "ANSIBLE_NOCOLOR",
    }
    probe_environment = {
        name: value
        for name, value in environment.items()
        if name in allowed_environment
    }
    runtime_tmp = probe_environment.get("TMPDIR")
    if runtime_tmp is None:
        raise ContractError("runtime provenance requires a private runtime TMPDIR")
    runtime_root = Path(runtime_tmp).parent
    probe_home = runtime_root / "provenance-home"
    probe_home.mkdir(mode=0o700, exist_ok=True)
    probe_home_status = probe_home.stat()
    if (
        probe_home.is_symlink()
        or probe_home_status.st_uid != os.geteuid()
        or stat.S_IMODE(probe_home_status.st_mode) != 0o700
    ):
        raise ContractError("runtime provenance home is not an owner-only directory")
    probe_environment["HOME"] = str(probe_home)
    probe_environment.update(
        {
            "ANSIBLE_TOOLBOX_MOUNT_INVENTORIES": "false",
            "ANSIBLE_TOOLBOX_MOUNT_SSH": "false",
            "ANSIBLE_TOOLBOX_MOUNT_SSH_AGENT": "false",
        }
    )
    evidence: dict[str, dict[str, Any]] = {}
    for role in ("toolbox", "run_ee"):
        result = run_bounded(
            commands[role],
            probe_environment,
            cwd,
            timeout_seconds=300,
            max_output_bytes=1024 * 1024,
        )
        if result["exit_code"] != 0 or result["termination_reason"]:
            raise ContractError(f"{role} runtime provenance probe failed")
        probe = validate_runtime_probe(
            result["stdout"], role, attestation[role], policy
        )
        evidence[role] = {
            "probe_sha256": sha256_bytes(canonical_json_bytes(probe)),
            "stdout_sha256": result["stdout_sha256"],
            "stderr_sha256": result["stderr_sha256"],
            "collections": probe["collections"],
        }
    return evidence


def normalized_container_backend_identity(
    document: Any, engine: dict[str, str]
) -> dict[str, Any]:
    """Select only stable Podman backend identity fields.

    The full ``podman info`` document contains uptime, capacity, memory and
    object counters.  Those values are operational state, not backend
    identity, and would make a pre/post identity pin change merely because the
    governed containers ran.
    """
    root = require_mapping(document, "container backend identity")
    host = require_mapping(root.get("host"), "container backend host identity")
    store = require_mapping(root.get("store"), "container backend store identity")
    version = require_mapping(root.get("version"), "container backend version identity")
    remote_socket = require_mapping(
        host.get("remoteSocket"), "container backend remote socket identity"
    )

    def text_field(mapping: dict[str, Any], key: str, label: str) -> str:
        value = mapping.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ContractError(f"{label} is missing")
        validate_no_secret_scalar(value, label)
        return value

    service_is_remote = host.get("serviceIsRemote")
    if not isinstance(service_is_remote, bool):
        raise ContractError("container backend remote-service identity is missing")
    identity = {
        "schema_version": 1,
        "backend_uri": engine["backend_uri"],
        "client_sha256": engine["sha256"],
        "host": {
            "arch": text_field(host, "arch", "container backend architecture"),
            "os": text_field(host, "os", "container backend operating system"),
            "hostname": text_field(host, "hostname", "container backend hostname"),
            "service_is_remote": service_is_remote,
            "remote_socket_path": text_field(
                remote_socket,
                "path",
                "container backend remote socket path",
            ),
        },
        "store": {
            "graph_driver_name": text_field(
                store, "graphDriverName", "container backend graph driver"
            ),
            "graph_root": text_field(
                store, "graphRoot", "container backend graph root"
            ),
            "run_root": text_field(store, "runRoot", "container backend run root"),
        },
        "version": {
            "api_version": text_field(
                version, "APIVersion", "container backend API version"
            ),
            "version": text_field(version, "Version", "container backend version"),
        },
    }
    recursively_reject_secret_fields(identity, "container_backend_identity")
    return identity


def measure_container_backend_identity(
    environment: dict[str, str], engine: dict[str, str], cwd: Path
) -> dict[str, str]:
    backend_environment = {
        name: environment[name]
        for name in (
            "PATH",
            "HOME",
            "TMPDIR",
            "XDG_CONFIG_HOME",
            "XDG_CACHE_HOME",
            "CONTAINER_HOST",
        )
    }
    result = run_bounded(
        [str(engine["path"]), "info", "--format", "json"],
        backend_environment,
        cwd,
        timeout_seconds=30,
        max_output_bytes=2 * 1024 * 1024,
    )
    if result["exit_code"] != 0 or result["termination_reason"]:
        raise ContractError("pinned container backend identity readback failed")
    document = strict_json_loads(result["stdout"], "container backend identity")
    identity = normalized_container_backend_identity(document, engine)
    digest = sha256_bytes(canonical_json_bytes(identity))
    if digest != engine["backend_identity_sha256"]:
        raise ContractError("container backend identity does not match its root pin")
    return {
        "backend_uri": engine["backend_uri"],
        "identity_sha256": digest,
        "identity": identity,
        "stdout_sha256": result["stdout_sha256"],
    }


def make_pre_live_environment(environment: dict[str, str]) -> dict[str, str]:
    allowed = {
        "PATH",
        "HOME",
        "TMPDIR",
        "XDG_CONFIG_HOME",
        "XDG_CACHE_HOME",
        "CONTAINER_HOST",
        "ANSIBLE_TOOLBOX_ENGINE_BINARY",
        "ANSIBLE_TOOLBOX_INVENTORY_SOURCE",
        "ANSIBLE_TOOLBOX_IMAGE",
        "ANSIBLE_TOOLBOX_RUN_EE_IMAGE",
        "ANSIBLE_TOOLBOX_ENGINE",
        "ANSIBLE_TOOLBOX_PULL_POLICY",
        "ANSIBLE_TOOLBOX_RUNTIME_MODE",
        "ANSIBLE_TOOLBOX_RUN_EE_PRELOAD",
        "ANSIBLE_TOOLBOX_RH_COLLECTIONS_MODE",
        "ANSIBLE_TOOLBOX_AUTO_COLLECTIONS",
        "ANSIBLE_TOOLBOX_EE_ONLY_COLLECTIONS",
        "ANSIBLE_COLLECTIONS_SCAN_SYS_PATH",
        "ANSIBLE_NOCOLOR",
    }
    minimal = {name: value for name, value in environment.items() if name in allowed}
    minimal.update(
        {
            "ANSIBLE_TOOLBOX_MOUNT_INVENTORIES": "true",
            "ANSIBLE_TOOLBOX_MOUNT_SSH": "false",
            "ANSIBLE_TOOLBOX_MOUNT_SSH_AGENT": "false",
        }
    )
    forbidden = {
        "SSH_AUTH_SOCK",
        "ANSIBLE_VAULT_PASSWORD_FILE",
        "ANSIBLE_TOOLBOX_SSH_PRIVATE_KEY_FILE",
        "ANSIBLE_TOOLBOX_SSH_KNOWN_HOSTS_FILE",
        "ANSIBLE_TOOLBOX_GOVERNED_INPUT_SOURCE",
        "ANSIBLE_TOOLBOX_RUNNER_ARTIFACT_SOURCE",
    }
    if forbidden & set(minimal):
        raise ContractError("pre-live environment retained a protected payload input")
    return minimal


def terminate_process(
    process: subprocess.Popen[bytes], sig: int = signal.SIGTERM
) -> None:
    try:
        os.killpg(process.pid, sig)
    except ProcessLookupError:
        return


def run_bounded(
    command: list[str],
    environment: dict[str, str],
    cwd: Path,
    timeout_seconds: int,
    max_output_bytes: int,
    popen_factory: Callable[..., subprocess.Popen[bytes]] = subprocess.Popen,
) -> dict[str, Any]:
    """Run without a TTY and retain only bounded stdout/stderr in memory."""
    started = utc_now()
    monotonic_start = time.monotonic()
    process = popen_factory(
        command,
        cwd=str(cwd),
        env=environment,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    if process.stdout is None or process.stderr is None:
        raise ContractError("subprocess pipes were not created")
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ, "stdout")
    selector.register(process.stderr, selectors.EVENT_READ, "stderr")
    buffers = {"stdout": bytearray(), "stderr": bytearray()}
    hashes = {"stdout": hashlib.sha256(), "stderr": hashlib.sha256()}
    totals = {"stdout": 0, "stderr": 0}
    termination_reason: str | None = None
    termination_started: float | None = None
    interrupted_signal: int | None = None
    previous_handlers: dict[int, Any] = {}

    def forward_signal(signum: int, _frame: Any) -> None:
        nonlocal interrupted_signal
        interrupted_signal = signum
        terminate_process(process, signum)

    for signum in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
        previous_handlers[signum] = signal.signal(signum, forward_signal)
    try:
        while selector.get_map():
            elapsed = time.monotonic() - monotonic_start
            if elapsed > timeout_seconds and termination_reason is None:
                termination_reason = "timeout"
                termination_started = time.monotonic()
                terminate_process(process)
            for key, _mask in selector.select(timeout=0.2):
                chunk = os.read(key.fileobj.fileno(), 65536)
                if not chunk:
                    selector.unregister(key.fileobj)
                    continue
                stream_name = key.data
                totals[stream_name] += len(chunk)
                hashes[stream_name].update(chunk)
                if (
                    sum(totals.values()) > max_output_bytes
                    and termination_reason is None
                ):
                    termination_reason = "output_limit"
                    termination_started = time.monotonic()
                    terminate_process(process)
                remaining = max_output_bytes - sum(
                    len(item) for item in buffers.values()
                )
                if remaining > 0:
                    buffers[stream_name].extend(chunk[:remaining])
            if (
                termination_started is not None
                and process.poll() is None
                and time.monotonic() - termination_started > 5
            ):
                terminate_process(process, signal.SIGKILL)
        try:
            return_code = process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            termination_reason = termination_reason or "closed_pipes_process_alive"
            terminate_process(process, signal.SIGKILL)
            return_code = process.wait(timeout=5)
    finally:
        for signum, handler in previous_handlers.items():
            signal.signal(signum, handler)
        selector.close()
        process.stdout.close()
        process.stderr.close()
    ended = utc_now()
    if interrupted_signal is not None:
        termination_reason = f"signal_{interrupted_signal}"
    return {
        "start_utc": started,
        "end_utc": ended,
        "duration_seconds": round(time.monotonic() - monotonic_start, 3),
        "exit_code": return_code,
        "termination_reason": termination_reason,
        "stdout": bytes(buffers["stdout"]),
        "stderr": bytes(buffers["stderr"]),
        "stdout_sha256": hashes["stdout"].hexdigest(),
        "stderr_sha256": hashes["stderr"].hexdigest(),
        "stdout_bytes": totals["stdout"],
        "stderr_bytes": totals["stderr"],
    }


def parse_events(
    stdout: bytes,
    action_id: str,
    action: dict[str, Any] | None = None,
    execution_id: str | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    recaps: list[dict[str, Any]] = []
    artifacts: list[dict[str, Any]] = []
    for raw_line in stdout.decode("utf-8", errors="replace").splitlines():
        line = raw_line.strip()
        if not line.startswith(EVENT_PREFIX):
            continue
        try:
            event = strict_json_loads(
                line[len(EVENT_PREFIX) :].encode("utf-8"), "governed callback event"
            )
        except UnicodeEncodeError as exc:
            raise ContractError("governed callback event is not UTF-8 safe") from exc
        event = require_mapping(event, "governed event")
        if (
            event.get("schema_version") != 1
            or event.get("action_id") != action_id
            or (execution_id is not None and event.get("execution_id") != execution_id)
        ):
            raise ContractError("governed callback event identity mismatch")
        if event.get("type") == "recap":
            require_exact_keys(
                event,
                {"schema_version", "action_id", "execution_id", "type", "hosts"},
                "governed recap event",
            )
            recaps.append(event)
        elif event.get("type") == "artifact":
            require_exact_keys(
                event,
                {
                    "schema_version",
                    "action_id",
                    "execution_id",
                    "type",
                    "artifact_type",
                    "task",
                    "payload",
                },
                "governed artifact event",
            )
            if action is not None:
                safe_tasks = action.get("safe_artifact_tasks", {})
                if safe_tasks.get(event.get("task")) != event.get("artifact_type"):
                    raise ContractError("governed artifact task/type binding mismatch")
            recursively_reject_secret_fields(event.get("payload"), "artifact")
            artifacts.append(event)
        elif event.get("type") == "artifact_rejected":
            raise ContractError("governed callback rejected an artifact payload")
        else:
            raise ContractError("governed callback emitted an unsupported event")
    return recaps, artifacts


def validate_target_recap(
    recaps: list[dict[str, Any]], target: str, action: dict[str, Any]
) -> dict[str, Any] | None:
    if action["mode"] != "playbook":
        if recaps:
            raise ContractError("non-playbook action emitted an unexpected recap")
        return None
    if len(recaps) != 1:
        raise ContractError("live playbook requires exactly one governed recap")
    hosts = require_mapping(recaps[0].get("hosts"), "recap hosts")
    if set(hosts) != {target}:
        raise ContractError("recap host set does not equal the approved target")
    counts = require_mapping(hosts[target], "target recap")
    expected_keys = {
        "ok",
        "changed",
        "unreachable",
        "failed",
        "skipped",
        "rescued",
        "ignored",
    }
    if set(counts) != expected_keys or any(
        not isinstance(value, int) or isinstance(value, bool) or value < 0
        for value in counts.values()
    ):
        raise ContractError("target recap counters are invalid")
    if counts["failed"] or counts["unreachable"]:
        raise ContractError("target recap contains failed or unreachable tasks")
    if counts["rescued"] and not action.get("allow_rescued", False):
        raise ContractError("target recap contains unapproved rescued tasks")
    if counts["ignored"]:
        raise ContractError("target recap contains ignored task failures")
    if (
        action["impact"] in {"local_validation", "controller_read", "target_read"}
        and counts["changed"]
    ):
        raise ContractError("read-only action reported changes")
    return counts


def select_projection(source: dict[str, Any], paths: Iterable[str]) -> dict[str, Any]:
    projection: dict[str, Any] = {}
    for dotted in paths:
        if not re.fullmatch(r"[A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)*", dotted):
            raise ContractError(f"invalid projection path: {dotted}")
        value: Any = source
        for component in dotted.split("."):
            if not isinstance(value, dict) or component not in value:
                raise ContractError(f"inventory projection path is missing: {dotted}")
            value = value[component]
        target = projection
        components = dotted.split(".")
        for component in components[:-1]:
            target = target.setdefault(component, {})
        target[components[-1]] = value
    recursively_reject_secret_fields(projection, "inventory_projection")
    return projection


def leaf_paths(value: Any, prefix: str = "") -> set[str]:
    if isinstance(value, dict):
        paths: set[str] = set()
        for key, child in value.items():
            child_prefix = f"{prefix}.{key}" if prefix else str(key)
            paths.update(leaf_paths(child, child_prefix))
        return paths
    return {prefix}


def dotted_value(value: dict[str, Any], path: str) -> Any:
    current: Any = value
    for component in path.split("."):
        if not isinstance(current, dict) or component not in current:
            raise ContractError(f"typed artifact is missing {path}")
        current = current[component]
    return current


def validate_artifact_field_type(value: Any, field_type: str, label: str) -> None:
    valid = False
    if field_type == "string":
        valid = isinstance(value, str)
    elif field_type == "integer":
        valid = isinstance(value, int) and not isinstance(value, bool)
    elif field_type == "boolean":
        valid = isinstance(value, bool)
    elif field_type == "mapping":
        valid = isinstance(value, dict)
    elif field_type == "sequence":
        valid = isinstance(value, list)
    elif field_type == "sha256":
        valid = isinstance(value, str) and SHA256_RE.fullmatch(value) is not None
    elif field_type == "ssh_fingerprint":
        valid = (
            isinstance(value, str) and SSH_FINGERPRINT_RE.fullmatch(value) is not None
        )
    elif field_type == "ipv4":
        try:
            valid = isinstance(value, str) and ipaddress.ip_address(value).version == 4
        except ValueError:
            valid = False
    if not valid:
        raise ContractError(f"typed artifact field {label} has the wrong type")


def validate_typed_artifact(
    payload: dict[str, Any],
    action_id: str,
    action: dict[str, Any],
    execution_id: str,
    target: dict[str, Any],
) -> dict[str, Any]:
    schema = action["artifact_schema"]
    fields = schema["fields"]
    observed_paths = leaf_paths(payload)
    if observed_paths != set(fields):
        raise ContractError(
            "governed artifact fields do not exactly match the typed schema"
        )
    for path, field in fields.items():
        value = dotted_value(payload, path)
        validate_artifact_field_type(value, field["type"], path)
        if "allowed_values" in field and value not in field["allowed_values"]:
            raise ContractError(f"typed artifact field {path} is outside its allowlist")
        binding = field.get("binding")
        if binding is not None and value != target[binding]:
            raise ContractError(f"typed artifact field {path} violates target binding")
    recursively_reject_secret_fields(payload, "typed_artifact")
    return {
        "schema_id": schema["schema_id"],
        "action_id": action_id,
        "execution_id": execution_id,
        "target": dict(target),
        "payload": payload,
    }


def canonical_ipv4_host_cidr(value: Any, label: str) -> str:
    if not isinstance(value, str):
        raise ContractError(f"{label} must be one canonical IPv4 /32")
    try:
        network = ipaddress.ip_network(value, strict=True)
    except ValueError as exc:
        raise ContractError(f"{label} must be one canonical IPv4 /32") from exc
    if network.version != 4 or network.prefixlen != 32 or str(network) != value:
        raise ContractError(f"{label} must be one canonical IPv4 /32")
    return value


def validate_effective_inventory_access(
    document: dict[str, Any], *, controller_source_cidr: str, target_ipv4: str
) -> dict[str, Any]:
    """Project the complete resolved, secret-free access semantics.

    This deliberately validates the independently rendered host variables,
    rather than trusting a single declarative source object.  The management
    contract, host-firewall consumption and provider rules must agree exactly.
    """
    approved_controller = canonical_ipv4_host_cidr(
        controller_source_cidr, "approved controller source"
    )
    inventory_contract = require_mapping(
        document.get("wunderbox_inventory_contract"), "inventory target contract"
    )
    controller_access = require_mapping(
        inventory_contract.get("controller_access"),
        "inventory controller access contract",
    )
    management = require_mapping(
        controller_access.get("management_services"),
        "inventory management-services contract",
    )
    host_management = require_mapping(
        document.get("host_firewall_management_access"),
        "resolved host-firewall management access",
    )
    service_specs = {
        "bootstrap_ssh": {"port": 22, "modes": ["bootstrap"]},
        "openssh": {"port": 1905, "modes": ["bootstrap", "hardened"]},
        "dropbear": {"port": 2222, "modes": ["bootstrap", "hardened"]},
    }
    if set(management) != set(service_specs) or host_management != management:
        raise ContractError(
            "resolved host-firewall management services do not equal the canonical contract"
        )
    normalized_management: dict[str, Any] = {}
    for name, spec in service_specs.items():
        service = require_mapping(management[name], f"management service {name}")
        require_exact_keys(
            service,
            {"port", "modes", "sources_ipv4", "sources_ipv6"},
            f"management service {name}",
        )
        sources_ipv4 = require_sequence(
            service["sources_ipv4"], f"management service {name} IPv4 sources"
        )
        sources_ipv6 = require_sequence(
            service["sources_ipv6"], f"management service {name} IPv6 sources"
        )
        if (
            service["port"] != spec["port"]
            or service["modes"] != spec["modes"]
            or sources_ipv4 != [approved_controller]
            or sources_ipv6 != []
        ):
            raise ContractError(
                f"management service {name} is not port-, mode- and source-exact"
            )
        canonical_ipv4_host_cidr(sources_ipv4[0], f"management service {name} source")
        normalized_management[name] = {
            "protocol": "tcp",
            "port": spec["port"],
            "modes": list(spec["modes"]),
            "sources_ipv4": list(sources_ipv4),
            "sources_ipv6": [],
        }

    bootstrap_rules = require_sequence(
        document.get("hetzner_baremetal_robot_firewall_bootstrap_input_rules"),
        "provider bootstrap firewall rules",
    )
    hardened_rules = require_sequence(
        document.get("hetzner_baremetal_robot_firewall_hardened_input_rules"),
        "provider hardened firewall rules",
    )
    phase_rules = {"bootstrap": bootstrap_rules, "hardened": hardened_rules}
    provider_rule_phases = {
        "bootstrap_ssh": "bootstrap",
        "openssh": "hardened",
        "dropbear": "hardened",
    }
    management_ports = {spec["port"] for spec in service_specs.values()}
    all_management_rules: list[tuple[str, dict[str, Any]]] = []
    for phase, raw_rules in phase_rules.items():
        for index, raw_rule in enumerate(raw_rules, start=1):
            rule = require_mapping(raw_rule, f"provider {phase} rule {index}")
            try:
                port = int(str(rule.get("dst_port", "")))
            except ValueError:
                continue
            if port in management_ports:
                all_management_rules.append((phase, rule))
    normalized_provider: dict[str, Any] = {}
    for name, phase in provider_rule_phases.items():
        port = service_specs[name]["port"]
        matches = [
            rule
            for observed_phase, rule in all_management_rules
            if observed_phase == phase and int(str(rule.get("dst_port"))) == port
        ]
        if len(matches) != 1:
            raise ContractError(
                f"provider management rule {name} is missing or ambiguous"
            )
        rule = matches[0]
        source = canonical_ipv4_host_cidr(
            rule.get("src_ip"), f"provider management rule {name} source"
        )
        if (
            rule.get("ip_version") != "ipv4"
            or rule.get("protocol") != "tcp"
            or rule.get("action") != "accept"
            or str(rule.get("dst_port")) != str(port)
            or source != approved_controller
            or str(rule.get("dst_ip")) != target_ipv4
        ):
            raise ContractError(
                f"provider management rule {name} is not target- and source-exact"
            )
        normalized_provider[name] = {
            "protocol": "tcp",
            "port": port,
            "sources_ipv4": [source],
            "sources_ipv6": [],
        }
    if len(all_management_rules) != len(provider_rule_phases):
        raise ContractError("provider firewall contains extra management-port rules")
    for phase, raw_rules in phase_rules.items():
        for index, raw_rule in enumerate(raw_rules, start=1):
            rule = require_mapping(raw_rule, f"provider {phase} rule {index}")
            try:
                port = int(str(rule.get("dst_port", "")))
            except ValueError:
                port = None
            if port in management_ports:
                continue
            if (
                rule.get("ip_version") != "ipv4"
                or rule.get("action") != "accept"
                or str(rule.get("dst_ip", target_ipv4)) != target_ipv4
            ):
                raise ContractError(
                    f"provider {phase} residual rule {index} is not target-bound"
                )
            protocol = rule.get("protocol")
            if protocol == "tcp":
                if (
                    str(rule.get("tcp_flags", "")).lower() != "ack"
                    or str(rule.get("dst_port")) != "32768-65535"
                    or rule.get("src_ip") is not None
                ):
                    raise ContractError(
                        "provider firewall contains an unprojected inbound TCP rule"
                    )
            elif protocol == "udp":
                if (
                    str(rule.get("src_port")) not in {"53", "123"}
                    or str(rule.get("dst_port")) != "32768-65535"
                ):
                    raise ContractError(
                        "provider firewall contains an unapproved UDP response rule"
                    )
            elif protocol != "icmp":
                raise ContractError(
                    "provider firewall contains an unapproved residual protocol"
                )

    host_tang = require_mapping(
        document.get("host_firewall_tang_access"), "resolved host-firewall Tang access"
    )
    require_exact_keys(
        host_tang,
        {"port", "sources_ipv4", "sources_ipv6"},
        "resolved host-firewall Tang access",
    )
    host_tang_sources = require_sequence(
        host_tang["sources_ipv4"], "host-firewall Tang IPv4 sources"
    )
    if host_tang["port"] != 80 or host_tang.get("sources_ipv6") != []:
        raise ContractError("host-firewall Tang access is not TCP/80 IPv4-only")
    canonical_host_tang_sources = [
        canonical_ipv4_host_cidr(source, "host-firewall Tang source")
        for source in host_tang_sources
    ]
    if len(canonical_host_tang_sources) != len(set(canonical_host_tang_sources)):
        raise ContractError("host-firewall Tang sources are not unique")

    provider_tang_rules = require_sequence(
        document.get("hetzner_baremetal_robot_firewall_deferred_tang_input_rules"),
        "provider deferred Tang rules",
    )
    provider_tang_sources: list[str] = []
    for index, raw_rule in enumerate(provider_tang_rules, start=1):
        rule = require_mapping(raw_rule, f"provider Tang rule {index}")
        source = canonical_ipv4_host_cidr(
            rule.get("src_ip"), f"provider Tang rule {index} source"
        )
        if (
            rule.get("ip_version") != "ipv4"
            or rule.get("protocol") != "tcp"
            or rule.get("action") != "accept"
            or str(rule.get("dst_port")) != "80"
            or str(rule.get("dst_ip")) != target_ipv4
        ):
            raise ContractError(f"provider Tang rule {index} is not target-exact")
        provider_tang_sources.append(source)
    if provider_tang_sources != canonical_host_tang_sources or len(
        provider_tang_sources
    ) != len(set(provider_tang_sources)):
        raise ContractError(
            "provider and host-firewall Tang source contracts do not match"
        )

    legacy_controller = require_sequence(
        document.get("host_firewall_controller_source_cidrs"),
        "legacy controller aggregate sources",
    )
    legacy_recovery = require_sequence(
        document.get("host_firewall_recovery_source_cidrs"),
        "legacy recovery aggregate sources",
    )
    if legacy_controller != [] or legacy_recovery != []:
        raise ContractError("legacy cross-port aggregate sources must remain empty")

    projection = {
        "schema_version": 1,
        "management_services": normalized_management,
        "provider_management_rules": normalized_provider,
        "host_firewall_management_services": normalized_management,
        "tang": {
            "protocol": "tcp",
            "port": 80,
            "provider_sources_ipv4": provider_tang_sources,
            "host_sources_ipv4": canonical_host_tang_sources,
            "sources_ipv6": [],
        },
        "legacy_aggregate_sources": {
            "controller": [],
            "recovery": [],
        },
    }
    recursively_reject_secret_fields(projection, "effective_access")
    return projection


def validate_inventory_target_projection(
    document: dict[str, Any],
    target: dict[str, Any],
    controller: dict[str, Any],
) -> dict[str, Any]:
    root_of_trust = require_mapping(
        document.get("hetzner_baremetal_root_of_trust"),
        "inventory root-of-trust contract",
    )
    lifecycle = require_mapping(
        root_of_trust.get("server_lifecycle"), "inventory server lifecycle"
    )
    inventory_contract = require_mapping(
        document.get("wunderbox_inventory_contract"), "inventory target contract"
    )
    provider = require_mapping(
        inventory_contract.get("provider"), "inventory provider contract"
    )
    public_identity = require_mapping(
        inventory_contract.get("public_identity"), "inventory public identity"
    )
    orchestration = require_mapping(
        document.get("wunderbox_orchestration"), "inventory orchestration contract"
    )
    orchestration_target = require_mapping(
        orchestration.get("target"), "inventory orchestration target"
    )
    observed = {
        "inventory_hostname": target["fqdn"],
        "ansible_host": str(document.get("ansible_host", "")),
        "hostname_fqdn": str(document.get("hostname_fqdn", "")),
        "hostname_etc_hosts_ip": str(document.get("hostname_etc_hosts_ip", "")),
        "hetzner_robot_server_number": str(
            document.get("hetzner_robot_server_number", "")
        ),
        "inventory_contract": {
            "target_id": str(inventory_contract.get("target_id", "")),
            "provider_server_id": str(provider.get("server_id", "")),
            "public_fqdn": str(public_identity.get("fqdn", "")),
            "public_ipv4": str(public_identity.get("ipv4", "")),
        },
        "orchestration_target": {
            "target_id": str(orchestration_target.get("id", "")),
            "fqdn": str(orchestration_target.get("fqdn", "")),
            "ipv4": str(orchestration_target.get("ipv4", "")),
            "provider_id": str(orchestration_target.get("provider_id", "")),
        },
        "root_of_trust": {
            "inventory_hostname": str(root_of_trust.get("inventory_hostname", "")),
            "controller_ipv4_cidr": str(root_of_trust.get("controller_ipv4_cidr", "")),
            "lifecycle_status": str(lifecycle.get("status", "")),
            "cancelled": lifecycle.get("cancelled"),
        },
    }
    expected_fqdn = target["fqdn"]
    expected_ipv4 = target["public_ipv4"]
    expected_provider = str(target["provider_id"])
    expected_target_id = target["target_id"]
    fqdn_values = {
        observed["inventory_hostname"],
        observed["hostname_fqdn"],
        observed["inventory_contract"]["public_fqdn"],
        observed["orchestration_target"]["fqdn"],
        observed["root_of_trust"]["inventory_hostname"],
    }
    ipv4_values = {
        observed["ansible_host"],
        observed["hostname_etc_hosts_ip"],
        observed["inventory_contract"]["public_ipv4"],
        observed["orchestration_target"]["ipv4"],
    }
    provider_values = {
        observed["hetzner_robot_server_number"],
        observed["inventory_contract"]["provider_server_id"],
        observed["orchestration_target"]["provider_id"],
    }
    target_id_values = {
        observed["inventory_contract"]["target_id"],
        observed["orchestration_target"]["target_id"],
    }
    if fqdn_values != {expected_fqdn}:
        raise ContractError("inventory projection FQDN identity mismatch")
    if ipv4_values != {expected_ipv4}:
        raise ContractError("inventory projection public IPv4 mismatch")
    if provider_values != {expected_provider}:
        raise ContractError("inventory projection provider/server identity mismatch")
    if target_id_values != {expected_target_id}:
        raise ContractError("inventory projection assessment target mismatch")
    if observed["root_of_trust"]["controller_ipv4_cidr"] != controller["source_cidr"]:
        raise ContractError("inventory projection controller CIDR mismatch")
    if (
        observed["root_of_trust"]["lifecycle_status"] != "ready"
        or observed["root_of_trust"]["cancelled"] is not False
    ):
        raise ContractError("inventory projection lifecycle is not ready")
    effective_access = validate_effective_inventory_access(
        document,
        controller_source_cidr=str(controller["source_cidr"]),
        target_ipv4=str(target["public_ipv4"]),
    )
    projection = {
        "schema_version": 2,
        "target": dict(target),
        "controller": {"source_cidr": controller["source_cidr"]},
        "observed": observed,
        "effective_access": effective_access,
    }
    recursively_reject_secret_fields(projection, "inventory_projection")
    return projection


def write_artifact(path: Path, artifact_type: str, payload: Any) -> dict[str, Any]:
    recursively_reject_secret_fields(payload, artifact_type)
    document = {
        "schema_version": 1,
        "artifact_type": artifact_type,
        "payload": payload,
    }
    digest = write_new_json(path, document)
    return {"path": str(path), "sha256": digest, "artifact_type": artifact_type}


def process_phase_record(phase: str, result: dict[str, Any]) -> dict[str, Any]:
    return {
        "phase": phase,
        "start_utc": result["start_utc"],
        "end_utc": result["end_utc"],
        "duration_seconds": result["duration_seconds"],
        "exit_code": result["exit_code"],
        "termination_reason": result["termination_reason"],
        "stdout_sha256": result["stdout_sha256"],
        "stderr_sha256": result["stderr_sha256"],
        "stdout_bytes": result["stdout_bytes"],
        "stderr_bytes": result["stderr_bytes"],
    }


def synthetic_process_result(
    started_utc: str, exit_code: int, reason: str
) -> dict[str, Any]:
    return {
        "start_utc": started_utc,
        "end_utc": utc_now(),
        "duration_seconds": 0,
        "exit_code": exit_code,
        "termination_reason": reason,
        "stdout": b"",
        "stderr": b"",
        "stdout_sha256": sha256_bytes(b""),
        "stderr_sha256": sha256_bytes(b""),
        "stdout_bytes": 0,
        "stderr_bytes": 0,
    }


def public_controller_claim(controller: dict[str, Any]) -> dict[str, Any]:
    return {
        "device_id": controller["device_id"],
        "source_cidr": controller["source_cidr"],
        "ssh_transport": {
            "source_directory_bound": True,
            "key_name_bound": True,
            "key_sha256_bound": True,
            "known_hosts_name_bound": True,
            "known_hosts_sha256_bound": True,
            "strict_host_key_checking": True,
            "identities_only": True,
        },
        "claim_basis": "SIGNED_MANIFEST_NOT_LIVE_OBSERVATION",
    }


def revalidate_execution_boundary(
    *,
    trust: dict[str, Any],
    manifest: dict[str, Any],
    policy: dict[str, Any],
    action_id: str,
    action: dict[str, Any],
    execution_approval: dict[str, Any],
    consumer_approvals: dict[str, dict[str, Any]],
    snapshots: dict[str, Path],
    snapshot_evidence: list[dict[str, Any]],
    sealed_ssh_directory: Path | None,
    execution_claim: dict[str, str] | None,
    require_execution_unclaimed: bool,
) -> dict[str, Any]:
    observed_trust = revalidate_controller_trust(trust)
    now = dt.datetime.now(dt.timezone.utc)
    validate_authorization(action_id, action, manifest, now)
    if require_execution_unclaimed:
        if execution_claim is not None:
            raise ContractError("execution approval was claimed before its boundary")
        revalidate_approval(
            execution_approval,
            observed_trust["approval_authority"],
            now,
            require_unclaimed=True,
        )
    else:
        if execution_claim is None:
            raise ContractError("execution approval lacks its root-brokered claim")
        revalidate_brokered_execution_approval(
            execution_approval,
            observed_trust["approval_authority"],
            observed_trust["replay_broker"],
            execution_claim,
            now,
        )
    for consumer in consumer_approvals.values():
        revalidate_approval(
            consumer,
            observed_trust["approval_authority"],
            now,
            require_unclaimed=True,
        )
    verify_repository_snapshots(snapshots, snapshot_evidence)
    verify_sealed_ssh_inputs(sealed_ssh_directory, manifest, action)
    attestation, attestation_payload = load_and_verify_runtime_attestation(
        manifest,
        policy,
        observed_trust["runtime_attestation_signature"],
    )
    return {
        "trust": observed_trust,
        "runtime_attestation": attestation,
        "runtime_attestation_sha256": sha256_bytes(attestation_payload),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gate-manifest", required=True, type=Path)
    parser.add_argument("--gate-signature", required=True, type=Path)
    parser.add_argument("--action-id", required=True)
    parser.add_argument("--attempt", required=True, type=int)
    parser.add_argument("--operator", required=True)
    parser.add_argument("--reviewer", required=True)
    parser.add_argument("--purpose", required=True)
    parser.add_argument("--jira", required=True)
    parser.add_argument("--repo", action="append", type=parse_repo, required=True)
    parser.add_argument("--extra-vars", type=Path)
    parser.add_argument("--evidence-dir", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not ACTION_ID_RE.fullmatch(args.action_id):
        raise SystemExit("invalid --action-id")
    if not 1 <= args.attempt <= 999:
        raise SystemExit("--attempt must be between 1 and 999")
    if not JIRA_RE.fullmatch(args.jira):
        raise SystemExit("invalid --jira reference")
    for label, value in (
        ("operator", args.operator),
        ("reviewer", args.reviewer),
        ("purpose", args.purpose),
    ):
        validate_no_secret_scalar(value, label)

    trust, policy, policy_payload = load_controller_trust()
    execution_anchor_evidence = validate_execution_anchor_runtime(trust)
    policy_digest = sha256_bytes(policy_payload)
    validate_policy(policy)
    gate_manifest_path = require_private_file(
        args.gate_manifest, "signed gate manifest"
    )
    manifest, manifest_payload = read_json_object(
        gate_manifest_path, "signed gate manifest"
    )
    validate_manifest(manifest, policy, policy_digest)
    verify_manifest_signature(
        manifest_payload,
        args.gate_signature,
        trust["manifest_signature"],
    )

    action = require_mapping(policy["actions"].get(args.action_id), "selected action")
    authorization = validate_authorization(
        args.action_id, action, manifest, dt.datetime.now(dt.timezone.utc)
    )
    execution_id = f"WBX-EXE-{action['record_prefix']}-A{args.attempt:03d}"
    evidence_dir = require_evidence_directory(args.evidence_dir)
    started_path = evidence_dir / f"{execution_id.lower()}.started.json"
    final_path = evidence_dir / f"{execution_id.lower()}.result.json"
    if final_path.exists() or final_path.with_suffix(".json.sha256").exists():
        raise SystemExit(f"execution attempt already finalized: {execution_id}")

    repo_pairs = args.repo
    repo_names = [name for name, _path in repo_pairs]
    if len(repo_names) != len(set(repo_names)):
        raise SystemExit("--repo names must be unique")
    if set(repo_names) != set(policy["required_repositories"]):
        raise SystemExit("--repo set does not match policy")
    source_repos = dict(repo_pairs)
    repository_states = [
        collect_repository_state(
            name, source_repos[name], manifest["repositories"][name]
        )
        for name in policy["required_repositories"]
    ]
    runtime_root = Path(
        tempfile.mkdtemp(prefix=f".{execution_id.lower()}-", dir=evidence_dir)
    )
    os.chmod(runtime_root, 0o700)
    started_record: dict[str, Any] | None = None
    started_digest: str | None = None
    result = synthetic_process_result(utc_now(), 126, "pre_process_contract")
    phases: list[dict[str, Any]] = []
    contract_failure: str | None = None
    produced_artifact: dict[str, Any] | None = None
    pre_live_artifact: dict[str, Any] | None = None
    recap: dict[str, Any] | None = None
    execution_claim: dict[str, str] | None = None
    consumer_claims: list[dict[str, str]] = []
    runtime_probe_evidence: dict[str, Any] = {}
    container_backend_evidence: dict[str, Any] = {}
    runtime_cleanup_verified = False
    verified_claims: list[str] = []
    active_process_phase: str | None = None
    try:
        snapshots, snapshot_evidence = create_repository_snapshots(
            repository_states, runtime_root
        )
        verify_external_anchor_sources(trust, snapshots)
        verified_claims.append(
            "execution inputs were materialized from tracked Git objects as private read-only snapshots and matched the installed root-owned recorder, launcher and policy anchors"
        )
        governed_input_directory = runtime_root / "governed-input"
        governed_input_directory.mkdir(mode=0o700)
        runner_artifact_directory = runtime_root / "runner-raw"
        runner_artifact_directory.mkdir(mode=0o700)
        sealed_ssh_directory = seal_controller_ssh_inputs(
            manifest, action, runtime_root / "controller-ssh"
        )

        extra_vars, extra_vars_digest, extra_vars_source = validate_extra_vars(
            args.extra_vars, action, manifest, authorization, execution_id
        )
        sealed_extra_vars: Path | None = None
        executed_extra_vars_digest: str | None = None
        if extra_vars_source is not None:
            canonical_extra_vars = canonical_json_bytes(extra_vars) + b"\n"
            executed_extra_vars_digest = sha256_bytes(canonical_extra_vars)
            sealed_extra_vars = governed_input_directory / "extra-vars.json"
            _write_private_bytes(sealed_extra_vars, canonical_extra_vars)
            if sha256_file(sealed_extra_vars) != executed_extra_vars_digest:
                raise ContractError("sealed extra-vars copy failed verification")

        command, command_metadata = build_command(
            action, manifest["target"], snapshots, execution_id, sealed_extra_vars
        )
        pre_live_command = (
            build_pre_live_projection_command(action, manifest["target"], snapshots)
            if action["impact"] in LIVE_IMPACTS
            else None
        )
        environment = make_environment(
            manifest,
            args.action_id,
            action,
            snapshots,
            container_engine=trust["container_engine"],
            sealed_ssh_directory=sealed_ssh_directory,
            execution_id=execution_id,
            runtime_root=runtime_root,
            runner_artifact_directory=runner_artifact_directory,
            governed_input_directory=governed_input_directory,
        )
        pre_live_environment = make_pre_live_environment(environment)
        container_backend_evidence = {
            "before": measure_container_backend_identity(
                environment,
                trust["container_engine"],
                snapshots["automation"] / "ansible",
            )
        }
        attestation, attestation_payload = load_and_verify_runtime_attestation(
            manifest,
            policy,
            trust["runtime_attestation_signature"],
        )
        provenance_commands = build_runtime_provenance_commands(snapshots)
        execution_approval, consumer_approvals = prepare_approvals(
            args.action_id,
            action,
            manifest,
            authorization,
            execution_id,
            extra_vars,
            trust["approval_authority"],
            dt.datetime.now(dt.timezone.utc),
        )
        started_record = {
            "schema_version": 2,
            "execution_id": execution_id,
            "invocation_status": "STARTED",
            "evidence_status": "CANDIDATE",
            "gate_effect": "NONE_PENDING_INDEPENDENT_REVIEW",
            "action_id": args.action_id,
            "impact": action["impact"],
            "gate": action["gate"],
            "target": manifest["target"],
            "controller": public_controller_claim(manifest["controller"]),
            "operator": {"value": args.operator, "claim_basis": "DECLARED"},
            "reviewer": {"value": args.reviewer, "claim_basis": "DECLARED"},
            "purpose": args.purpose,
            "jira": args.jira,
            "outer_authorization": {
                "reference": authorization["approval_reference"],
                "sha256": authorization["approval_sha256"],
                "not_before_utc": authorization["not_before_utc"],
                "expires_utc": authorization["expires_utc"],
                "claim_basis": "SIGNED_GATE_MANIFEST",
            },
            "execution_approval": safe_approval_metadata(execution_approval),
            "consumer_approvals": {
                variable: safe_approval_metadata(approval)
                for variable, approval in consumer_approvals.items()
            },
            "controller_trust": {
                "descriptor_path": trust["_descriptor_path"],
                "descriptor_sha256": trust["_descriptor_sha256"],
                "policy": trust["policy"],
                "container_engine": trust["container_engine"],
                "execution_anchor": execution_anchor_evidence,
                "replay_broker": trust["replay_broker"],
                "manifest_signature": public_signature_trust(
                    trust["manifest_signature"]
                ),
                "runtime_attestation_signature": public_signature_trust(
                    trust["runtime_attestation_signature"]
                ),
                "approval_authority": public_approval_authority(
                    trust["approval_authority"]
                ),
            },
            "gate_manifest": {
                "path": str(gate_manifest_path),
                "sha256": sha256_bytes(manifest_payload),
                "signature_verified": True,
            },
            "repository_sources": repository_states,
            "repository_snapshots": snapshot_evidence,
            "runtime": {
                "toolbox_image": manifest["runtime"]["toolbox_image"],
                "run_ee_image": manifest["runtime"]["run_ee_image"],
                "attestation_sha256": sha256_bytes(attestation_payload),
                "attestation_verified": True,
                "effective_collection_provenance_before": "PENDING_MEASUREMENT",
                "project_collection_overlays": "EXCLUDED",
            },
            "command": {
                "argv": command,
                "copyable": shlex.join(command),
                **command_metadata,
                "extra_variable_names": sorted(extra_vars),
                "source_extra_vars_sha256": extra_vars_digest,
                "executed_extra_vars_sha256": executed_extra_vars_digest,
            },
            "process_model": (
                "PRE_LIVE_INVENTORY_PROJECTION_THEN_PAYLOAD"
                if pre_live_command is not None
                else "PAYLOAD_ONLY"
            ),
            "required_evidence_references": {
                key: authorization[key]
                for key in action.get("required_evidence_references", [])
            },
            "started_utc": utc_now(),
            "local_integrity_claim": (
                "Owner-only append-on-create candidate records with SHA-256 sidecars; "
                "independent acceptance remains required and this record cannot advance a gate."
            ),
        }
        started_digest = write_new_json(started_path, started_record)

        runtime_probe_evidence["before"] = run_runtime_provenance_probes(
            provenance_commands,
            environment,
            snapshots["automation"] / "ansible",
            attestation,
            policy,
        )
        verified_claims.append(
            "effective toolbox and run-EE collection trees matched the signed runtime attestation before execution"
        )

        boundary = revalidate_execution_boundary(
            trust=trust,
            manifest=manifest,
            policy=policy,
            action_id=args.action_id,
            action=action,
            execution_approval=execution_approval,
            consumer_approvals=consumer_approvals,
            snapshots=snapshots,
            snapshot_evidence=snapshot_evidence,
            sealed_ssh_directory=sealed_ssh_directory,
            execution_claim=None,
            require_execution_unclaimed=True,
        )
        execution_claim = invoke_replay_broker(
            "claim", execution_approval, boundary["trust"]["replay_broker"]
        )
        verified_claims.append(
            "fixed controller trust and signed execution authorization were revalidated and claimed by the root-brokered append-only replay store"
        )

        if pre_live_command is not None:
            boundary = revalidate_execution_boundary(
                trust=boundary["trust"],
                manifest=manifest,
                policy=policy,
                action_id=args.action_id,
                action=action,
                execution_approval=execution_approval,
                consumer_approvals=consumer_approvals,
                snapshots=snapshots,
                snapshot_evidence=snapshot_evidence,
                sealed_ssh_directory=sealed_ssh_directory,
                execution_claim=execution_claim,
                require_execution_unclaimed=False,
            )
            active_process_phase = "PRE_LIVE_INVENTORY_PROJECTION"
            pre_live_result = run_bounded(
                pre_live_command,
                pre_live_environment,
                snapshots["automation"] / "ansible",
                timeout_seconds=300,
                max_output_bytes=2 * 1024 * 1024,
            )
            phases.append(
                process_phase_record("PRE_LIVE_INVENTORY_PROJECTION", pre_live_result)
            )
            active_process_phase = None
            if (
                pre_live_result["exit_code"] != 0
                or pre_live_result["termination_reason"]
            ):
                raise ContractError("pre-live inventory projection failed")
            pre_live_document = require_mapping(
                strict_json_loads(
                    pre_live_result["stdout"], "pre-live inventory projection"
                ),
                "pre-live inventory projection",
            )
            pre_live_projection = validate_inventory_target_projection(
                pre_live_document, manifest["target"], manifest["controller"]
            )
            pre_live_artifact = write_artifact(
                evidence_dir
                / f"{execution_id.lower()}.pre-live-inventory-projection.json",
                "pre_live_inventory_projection",
                pre_live_projection,
            )
            verified_claims.append(
                "live execution used an exact target-bound inventory projection before payload"
            )

        boundary = revalidate_execution_boundary(
            trust=boundary["trust"],
            manifest=manifest,
            policy=policy,
            action_id=args.action_id,
            action=action,
            execution_approval=execution_approval,
            consumer_approvals=consumer_approvals,
            snapshots=snapshots,
            snapshot_evidence=snapshot_evidence,
            sealed_ssh_directory=sealed_ssh_directory,
            execution_claim=execution_claim,
            require_execution_unclaimed=False,
        )
        if (
            sealed_extra_vars is not None
            and sha256_file(sealed_extra_vars) != executed_extra_vars_digest
        ):
            raise ContractError("sealed extra-vars changed before payload execution")
        active_process_phase = "PAYLOAD"
        result = run_bounded(
            command,
            environment,
            snapshots["automation"] / "ansible",
            int(action.get("timeout_seconds", 1800)),
            int(action.get("max_output_bytes", 8 * 1024 * 1024)),
        )
        phases.append(process_phase_record("PAYLOAD", result))
        active_process_phase = None
        if result["exit_code"] != 0 or result["termination_reason"]:
            raise ContractError("payload process did not complete successfully")
        recaps, artifacts = parse_events(
            result["stdout"], args.action_id, action, execution_id
        )
        recap = validate_target_recap(recaps, manifest["target"]["fqdn"], action)

        expected_artifact = action.get("expected_artifact")
        if action["mode"] == "inventory_projection":
            inventory_document = require_mapping(
                strict_json_loads(result["stdout"], "inventory host document"),
                "inventory host document",
            )
            projection = validate_inventory_target_projection(
                inventory_document, manifest["target"], manifest["controller"]
            )
            produced_artifact = write_artifact(
                evidence_dir / f"{execution_id.lower()}.inventory-projection.json",
                "inventory_projection",
                projection,
            )
        elif expected_artifact:
            matching = [
                event
                for event in artifacts
                if event.get("artifact_type") == expected_artifact
            ]
            if len(matching) != 1:
                raise ContractError("expected exactly one governed artifact event")
            artifact_payload = require_mapping(
                matching[0]["payload"], "governed artifact payload"
            )
            projection = select_projection(
                artifact_payload, action.get("artifact_projection_paths", [])
            )
            typed_artifact = validate_typed_artifact(
                projection,
                args.action_id,
                action,
                execution_id,
                manifest["target"],
            )
            produced_artifact = write_artifact(
                evidence_dir / f"{execution_id.lower()}.{expected_artifact}.json",
                str(expected_artifact),
                typed_artifact,
            )
            verified_claims.append(
                "the action artifact matched its exact typed and target-bound schema"
            )
        elif artifacts:
            raise ContractError("action emitted an unexpected governed artifact")

        consumer_claims = verify_consumer_claims(consumer_approvals)
        if consumer_approvals:
            verified_claims.append(
                "every consumer approval was independently claimed by its Foundational consumer"
            )
        verify_repository_snapshots(snapshots, snapshot_evidence)
        final_attestation, final_attestation_payload = (
            load_and_verify_runtime_attestation(
                manifest,
                policy,
                boundary["trust"]["runtime_attestation_signature"],
            )
        )
        if (
            final_attestation != boundary["runtime_attestation"]
            or sha256_bytes(final_attestation_payload)
            != boundary["runtime_attestation_sha256"]
        ):
            raise ContractError("runtime attestation changed during execution")
        runtime_probe_evidence["after"] = run_runtime_provenance_probes(
            provenance_commands,
            environment,
            snapshots["automation"] / "ansible",
            final_attestation,
            policy,
        )
        verified_claims.append(
            "effective toolbox and run-EE collection trees remained attestation-matched after execution"
        )
        container_backend_evidence["after"] = measure_container_backend_identity(
            environment,
            boundary["trust"]["container_engine"],
            snapshots["automation"] / "ansible",
        )
    except ContractError as exc:
        contract_failure = str(exc)
    except OSError as exc:
        result = synthetic_process_result(
            started_record["started_utc"] if started_record else utc_now(),
            127,
            "process_start",
        )
        if active_process_phase is not None:
            phases.append(process_phase_record(active_process_phase, result))
        contract_failure = f"process start failed: {type(exc).__name__}"
    finally:
        if execution_claim is not None:
            try:
                post_action_claim = invoke_replay_broker(
                    "verify", execution_approval, trust["replay_broker"]
                )
                execution_claim["post_action_verification"] = post_action_claim[
                    "claim_status"
                ]
                verified_claims.append(
                    "the execution approval ledger marker remained intact after the action attempt"
                )
            except ContractError as exc:
                post_action_failure = str(exc)
                contract_failure = (
                    f"{contract_failure}; {post_action_failure}"
                    if contract_failure
                    else post_action_failure
                )
        runtime_cleanup_verified = remove_private_runtime_tree(runtime_root)
        if runtime_cleanup_verified:
            verified_claims.append(
                "owner-only raw Runner artifacts and all private runtime inputs were removed with absence verified"
            )
        if not runtime_cleanup_verified:
            contract_failure = (
                f"{contract_failure}; raw Runner artifact cleanup failed"
                if contract_failure
                else "raw Runner artifact cleanup failed"
            )

    if started_record is None or started_digest is None:
        raise ContractError(
            contract_failure or "execution did not reach its journal boundary"
        )
    if not runtime_cleanup_verified:
        execution_status = "RAW_RETENTION_FAILED"
    elif contract_failure:
        execution_status = "CONTRACT_FAILED"
    elif result["termination_reason"]:
        execution_status = str(result["termination_reason"]).upper()
    elif result["exit_code"] == 0:
        execution_status = "SUCCEEDED"
    else:
        execution_status = "FAILED"
    final_record = {
        **started_record,
        "invocation_status": execution_status,
        "started_record": {"path": str(started_path), "sha256": started_digest},
        "result": {
            "start_utc": result["start_utc"],
            "end_utc": result["end_utc"],
            "duration_seconds": result["duration_seconds"],
            "exit_code": result["exit_code"],
            "termination_reason": result["termination_reason"],
            "target_recap": recap,
            "contract_failure": contract_failure,
            "phases": phases,
        },
        "output": {
            "raw_retained": not runtime_cleanup_verified,
            "runtime_cleanup_verified": runtime_cleanup_verified,
            "stdout_sha256": result["stdout_sha256"],
            "stderr_sha256": result["stderr_sha256"],
            "stdout_bytes": result["stdout_bytes"],
            "stderr_bytes": result["stderr_bytes"],
            "claim_basis": "BOUNDED_IN_MEMORY_AND_EPHEMERAL_OWNER_ONLY_RUNNER_ARTIFACTS",
        },
        "pre_live_inventory_artifact": pre_live_artifact,
        "produced_artifact": produced_artifact,
        "runtime_provenance": runtime_probe_evidence,
        "container_backend": container_backend_evidence,
        "execution_approval_claim": execution_claim,
        "consumer_approval_claims": consumer_claims,
        "claims": {
            "technical": verified_claims,
            "declarative_pending_review": [
                "operator and reviewer identity",
                "controller source is approved but not live-observed by this recorder",
                "readback, rollback, findings, risk and gate effect references",
                "candidate evidence requires independent acceptance",
            ],
        },
    }
    final_digest = write_new_json(final_path, final_record)
    print(f"Execution {execution_id}: {execution_status}")
    print(f"Candidate evidence: {final_path}")
    print(f"SHA-256: {final_digest}")
    return 0 if execution_status == "SUCCEEDED" else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ContractError, FileNotFoundError, subprocess.SubprocessError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
