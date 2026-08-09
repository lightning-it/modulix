#!/usr/bin/env python3
"""Execute one policy-bound Ansible action and create candidate evidence.

The recorder is deliberately generic.  Environment-specific target identity,
gate state, approvals, repository commits, and runtime image digests are read
from a signed manifest supplied by a private validation adapter.  The recorder
does not accept an arbitrary command line and never treats caller prose as an
authorization boundary.

Raw subprocess output is bounded in memory and is never written to disk.  A
started journal is written before process creation and a separate final record
is written afterwards.  Both are local integrity artifacts; independent
review and an external hash/signature anchor are still required for acceptance.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import re
import selectors
import shlex
import signal
import stat
import subprocess
import sys
import time
from typing import Any, Callable, Iterable


SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
GIT_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
BRANCH_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,199}$")
ACTION_ID_RE = re.compile(r"^[a-z][a-z0-9_]{2,79}$")
RECORD_PREFIX_RE = re.compile(r"^[0-9]{3}$")
JIRA_RE = re.compile(r"^[A-Z][A-Z0-9]+-[0-9]+$")
IMAGE_DIGEST_RE = re.compile(r"^[^\s@]+@sha256:[0-9a-f]{64}$")
EVENT_PREFIX = "LIT_GOVERNED_EVENT="
SECRET_KEY_RE = re.compile(
    r"(?i)(?:password|passphrase|token|secret|private[_-]?key|credential|"
    r"recovery[_-]?key|unseal|root[_-]?token)"
)
URI_CREDENTIAL_RE = re.compile(
    r"(?:^|=)[a-z][a-z0-9+.-]*://[^/@\s]+:[^/@\s]+@", re.I
)
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


class ContractError(RuntimeError):
    """Raised before execution or when produced output violates the contract."""


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="milliseconds").replace(
        "+00:00", "Z"
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


def require_mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ContractError(f"{label} must be a mapping")
    return value


def require_sequence(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise ContractError(f"{label} must be a list")
    return value


def read_json_object(path: Path, label: str, max_bytes: int = 2 * 1024 * 1024) -> tuple[dict[str, Any], bytes]:
    resolved = path.expanduser().resolve()
    file_stat = resolved.stat()
    if not stat.S_ISREG(file_stat.st_mode) or file_stat.st_size <= 0:
        raise ContractError(f"{label} must be a nonempty regular file")
    if file_stat.st_size > max_bytes:
        raise ContractError(f"{label} exceeds {max_bytes} bytes")
    payload = resolved.read_bytes()
    try:
        parsed = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ContractError(f"{label} must contain UTF-8 JSON") from exc
    return require_mapping(parsed, label), payload


def require_private_file(path: Path, label: str, *, allow_readonly: bool = True) -> Path:
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


def run_git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return completed.stdout.strip()


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
    status = run_git(repo, "status", "--porcelain=v1")
    expected_branch = str(expected.get("branch", ""))
    expected_commit = str(expected.get("commit", ""))
    if not BRANCH_RE.fullmatch(expected_branch) or not GIT_SHA_RE.fullmatch(
        expected_commit
    ):
        raise ContractError(f"manifest repository {name} is not frozen")
    if branch != expected_branch or commit != expected_commit:
        raise ContractError(f"repository {name} does not match the signed freeze")
    if status:
        raise ContractError(f"repository {name} is dirty")
    return {
        "name": name,
        "path": str(repo),
        "branch": branch,
        "commit": commit,
        "clean_at_start": True,
    }


def verify_repositories_after(states: list[dict[str, Any]]) -> None:
    for state in states:
        repo = Path(state["path"])
        if run_git(repo, "rev-parse", "HEAD") != state["commit"]:
            raise ContractError(f"repository {state['name']} commit changed during execution")
        if run_git(repo, "status", "--porcelain=v1"):
            raise ContractError(f"repository {state['name']} became dirty during execution")


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
    allowed_multiline_paths: frozenset[str] = frozenset(),
    depth: int = 0,
) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if not isinstance(key, str):
                raise ContractError(f"{label} contains a non-string key")
            if SECRET_KEY_RE.search(key) and not (
                depth == 0 and key in allowed_top_level_secret_names
            ):
                raise ContractError(f"{label}.{key} is a forbidden secret-bearing key")
            recursively_reject_secret_fields(
                child,
                f"{label}.{key}",
                allowed_top_level_secret_names=allowed_top_level_secret_names,
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
                allowed_multiline_paths=allowed_multiline_paths,
                depth=depth + 1,
            )
        return
    if isinstance(value, str):
        if label not in allowed_multiline_paths:
            validate_no_secret_scalar(value, label)


def validate_policy(policy: dict[str, Any]) -> None:
    if policy.get("schema_version") != 1:
        raise ContractError("policy schema_version must be 1")
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
    signing = require_mapping(policy.get("signing"), "policy signing")
    if not signing.get("identity") or not signing.get("namespace"):
        raise ContractError("policy signing identity and namespace are required")
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
        if implementation_status == "blocked" and not str(
            action.get("implementation_blocker", "")
        ).strip():
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
        for transport_flag in ("requires_ssh_private_key", "requires_ssh_agent"):
            if transport_flag in action and not isinstance(
                action[transport_flag], bool
            ):
                raise ContractError(
                    f"action {action_id} has an invalid {transport_flag} flag"
                )
        if action.get("mode") != "inventory_projection" and not action.get(
            "playbook"
        ):
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
        allowed_extra_vars = require_sequence(
            action.get("allowed_extra_vars", []),
            f"action {action_id} allowed_extra_vars",
        )
        required_extra_vars = require_sequence(
            action.get("required_extra_vars", []),
            f"action {action_id} required_extra_vars",
        )
        if (
            len(allowed_extra_vars) != len(set(allowed_extra_vars))
            or not set(required_extra_vars).issubset(allowed_extra_vars)
        ):
            raise ContractError(f"action {action_id} has an invalid extra-vars contract")
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
                if "value" not in binding:
                    raise ContractError(f"action {action_id} has an empty literal binding")
            elif kind == "target_confirmation":
                if not re.fullmatch(r"[A-Z][A-Z0-9_]{1,39}", str(binding.get("prefix", ""))):
                    raise ContractError(f"action {action_id} has an invalid confirmation prefix")
            elif kind == "authorization_field":
                if not re.fullmatch(r"[a-z][a-z0-9_]{1,79}", str(binding.get("field", ""))):
                    raise ContractError(f"action {action_id} has an invalid authorization binding")
            elif kind == "signed_approval_transport":
                if not re.fullmatch(r"[a-z][a-z0-9_]{1,79}", str(binding.get("field", ""))):
                    raise ContractError(f"action {action_id} has an invalid signed approval binding")
            elif kind == "target_and_authorization_confirmation":
                if not re.fullmatch(r"[A-Z][A-Z0-9_]{1,39}", str(binding.get("prefix", ""))):
                    raise ContractError(f"action {action_id} has an invalid confirmation prefix")
                if not re.fullmatch(r"[a-z][a-z0-9_]{1,79}", str(binding.get("field", ""))):
                    raise ContractError(f"action {action_id} has an invalid authorization binding")
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
    if manifest.get("schema_version") != 1:
        raise ContractError("gate manifest schema_version must be 1")
    if manifest.get("policy_sha256") != policy_digest:
        raise ContractError("gate manifest does not bind the current policy")
    if manifest.get("manifest_status") != "APPROVED":
        raise ContractError("gate manifest is not approved")
    target = require_mapping(manifest.get("target"), "manifest target")
    if not target.get("target_id") or not re.fullmatch(
        r"(?=.{1,253}$)(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+[A-Za-z]{2,63}",
        str(target.get("fqdn", "")),
    ):
        raise ContractError("manifest target identity is incomplete")
    target_contract = policy["target_contract"]
    if re.fullmatch(
        str(target_contract["target_id_pattern"]), str(target["target_id"])
    ) is None or re.fullmatch(
        str(target_contract["fqdn_pattern"]), str(target["fqdn"])
    ) is None:
        raise ContractError("manifest target is outside the policy target contract")
    controller = require_mapping(manifest.get("controller"), "manifest controller")
    try:
        target_ip = ipaddress.ip_address(str(target.get("public_ipv4", "")))
        source = ipaddress.ip_network(str(controller["source_cidr"]), strict=True)
    except (KeyError, TypeError, ValueError) as exc:
        raise ContractError("manifest target/controller network identity is invalid") from exc
    if target_ip.version != 4 or source.version != 4 or source.prefixlen != 32:
        raise ContractError("controller source must be one exact IPv4 /32")
    if not str(target.get("provider_id", "")).strip() or not str(
        controller.get("device_id", "")
    ).strip():
        raise ContractError("manifest provider/controller identity is incomplete")
    controller_ssh = require_mapping(
        controller.get("ssh"), "manifest controller ssh"
    )
    if not str(controller_ssh.get("source_directory", "")).startswith("/"):
        raise ContractError("controller SSH source directory must be absolute")
    if not re.fullmatch(
        r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}",
        str(controller_ssh.get("private_key_name", "")),
    ) or not SHA256_RE.fullmatch(str(controller_ssh.get("private_key_sha256", ""))):
        raise ContractError("controller SSH key binding is incomplete")
    runtime = require_mapping(manifest.get("runtime"), "manifest runtime")
    for key in ("toolbox_image", "run_ee_image"):
        if not IMAGE_DIGEST_RE.fullmatch(str(runtime.get(key, ""))):
            raise ContractError(f"runtime {key} must use an immutable digest")
    if not SHA256_RE.fullmatch(str(runtime.get("attestation_sha256", ""))):
        raise ContractError("runtime attestation SHA-256 is required")
    collections = require_mapping(runtime.get("collections"), "runtime collections")
    if set(collections) != set(policy["required_collections"]):
        raise ContractError("runtime collection set does not match policy")
    for name, raw_collection in collections.items():
        collection = require_mapping(raw_collection, f"runtime collection {name}")
        if not str(collection.get("version", "")).strip() or not GIT_SHA_RE.fullmatch(
            str(collection.get("source_commit", ""))
        ):
            raise ContractError(f"runtime collection {name} is not source-bound")
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
    for action_id, raw_authorization in authorizations.items():
        authorization = require_mapping(
            raw_authorization, f"manifest authorization {action_id}"
        )
        if authorization.get("status") not in {"APPROVED", "NOT_APPROVED"}:
            raise ContractError(f"authorization {action_id} has an invalid status")
    if not isinstance(manifest.get("safety_hold"), bool):
        raise ContractError("manifest safety_hold must be a boolean")


def verify_manifest_signature(
    manifest_payload: bytes,
    signature: Path,
    allowed_signers: Path,
    identity: str,
    namespace: str,
    runner: Callable[..., subprocess.CompletedProcess[bytes]] = subprocess.run,
) -> None:
    signature_path = require_private_file(signature, "gate manifest signature")
    signers_path = require_private_file(allowed_signers, "allowed signers")
    completed = runner(
        [
            "ssh-keygen",
            "-Y",
            "verify",
            "-f",
            str(signers_path),
            "-I",
            identity,
            "-n",
            namespace,
            "-s",
            str(signature_path),
        ],
        input=manifest_payload,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        raise ContractError("gate manifest signature verification failed")


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
    if not start <= now <= end or end <= start:
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
            f"extra_vars.{variable}.signature"
            for variable in signed_approval_variables
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
                raise ContractError("approval-bound extra-vars require an authorization")
            field = str(binding["field"])
            expected = authorization.get(field)
            if field.endswith("sha256") and not SHA256_RE.fullmatch(
                str(expected or "")
            ):
                raise ContractError(f"authorization field {field} is not a SHA-256")
            if field.endswith("fingerprint") and re.fullmatch(
                r"SHA256:[A-Za-z0-9+/]{43}", str(expected or "")
            ) is None:
                raise ContractError(f"authorization field {field} is not a fingerprint")
        elif kind == "signed_approval_transport":
            if manifest is None or authorization is None or execution_id is None:
                raise ContractError(
                    "signed approval transport requires manifest authorization and execution ID"
                )
            field = str(binding["field"])
            expected = authorization.get(field)
            validate_signed_approval_transport(
                expected, manifest, authorization, execution_id
            )
        elif kind == "target_and_authorization_confirmation":
            if manifest is None or authorization is None:
                raise ContractError("approval-bound confirmation requires authorization")
            field = str(binding["field"])
            bound_value = authorization.get(field)
            if field.endswith("sha256") and not SHA256_RE.fullmatch(
                str(bound_value or "")
            ):
                raise ContractError(f"authorization field {field} is not a SHA-256")
            expected = (
                f"{binding['prefix']}:{manifest['target']['fqdn']}:"
                f"{bound_value}"
            )
        else:  # validate_policy rejects this before execution.
            raise ContractError(f"unsupported extra-vars binding for {key}")
        if expected is None or parsed.get(key) != expected:
            raise ContractError(f"extra-vars value for {key} violates its binding")
    return parsed, sha256_bytes(payload), source


def validate_signed_approval_transport(
    value: Any,
    manifest: dict[str, Any],
    authorization: dict[str, Any],
    execution_id: str,
) -> dict[str, Any]:
    """Validate a plugin approval only as signed-manifest transport metadata."""
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
        raise ContractError("signed approval transport does not bind the frozen repositories")
    if not re.fullmatch(r"[0-9a-f]{64}", str(approval.get("nonce", ""))):
        raise ContractError("signed approval transport nonce is invalid")
    issued_text = str(approval.get("issued_at", ""))
    expires_text = str(approval.get("expires_at", ""))
    if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z", issued_text) or not re.fullmatch(
        r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z", expires_text
    ):
        raise ContractError("signed approval transport timestamps must use whole-second UTC")
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
        and (expires - issued).total_seconds() <= 900
    ):
        raise ContractError(
            "signed approval transport is outside the signed authorization window"
        )
    signature = approval.get("signature")
    if (
        not isinstance(signature, str)
        or not signature.isascii()
        or len(signature) > 16384
        or "\x00" in signature
        or not signature.startswith("-----BEGIN SSH SIGNATURE-----\n")
        or not signature.endswith("-----END SSH SIGNATURE-----\n")
    ):
        raise ContractError("signed approval transport signature is malformed")
    require_private_directory(
        Path(str(approval.get("replay_directory", ""))),
        "signed approval replay directory",
    )
    return approval


def claim_signed_approval_transports(
    extra_vars: dict[str, Any],
    action: dict[str, Any],
    execution_id: str,
) -> list[dict[str, str]]:
    """Consume signed approval nonces once across all targets and operations."""
    claims = []
    for variable, raw_binding in action.get("extra_var_bindings", {}).items():
        binding = require_mapping(raw_binding, f"extra-vars binding {variable}")
        if binding.get("kind") != "signed_approval_transport":
            continue
        approval = require_mapping(
            extra_vars.get(variable), f"signed approval transport {variable}"
        )
        nonce = str(approval["nonce"])
        replay_directory = require_private_directory(
            Path(str(approval["replay_directory"])),
            "signed approval replay directory",
        )
        marker = replay_directory / f"{nonce}.recorder-used.json"
        try:
            digest = write_new_json(
                marker,
                {
                    "schema_version": 1,
                    "execution_id": execution_id,
                    "claim_basis": "SIGNED_GATE_MANIFEST",
                    "nonce_sha256": sha256_bytes(nonce.encode("ascii")),
                },
            )
        except FileExistsError as exc:
            raise ContractError(
                "signed approval nonce has already been consumed by the recorder"
            ) from exc
        claims.append(
            {
                "variable": variable,
                "nonce_sha256": sha256_bytes(nonce.encode("ascii")),
                "marker": str(marker),
                "marker_sha256": digest,
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
    if wrapper != expected_wrapper or not wrapper.is_file():
        raise ContractError("canonical ansible-nav wrapper is missing")
    inventory_relative = str(action.get("inventory", "inventories/pub/inventory.yml"))
    inventory_path = (inventory_repo / inventory_relative).resolve()
    if inventory_repo not in inventory_path.parents or not inventory_path.is_file():
        raise ContractError("action inventory path escapes the inventory repository")
    runtime_inventory = "/runner/project/inventories/" + inventory_relative.split(
        "inventories/", 1
    )[-1]
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
            raise ContractError("policy playbook is missing or escapes the automation tree")
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
            runtime_extra = f"/runner/project/.tmp/governed-exec/{execution_id}.json"
            command.extend(["--extra-vars", f"@{runtime_extra}"])
    return command, {
        "inventory_path": str(inventory_path),
        "inventory_relative_path": inventory_relative,
        "playbook": playbook or "ansible-inventory",
        "limit": target["fqdn"] if mode == "playbook" else None,
        "tags": action.get("tags", []),
        "skip_tags": action.get("skip_tags", []),
        "check_mode": bool(action.get("check_mode")),
        "diff_mode": bool(action.get("diff_mode")),
    }


def make_environment(
    manifest: dict[str, Any],
    action_id: str,
    action: dict[str, Any],
    repos: dict[str, Path] | None = None,
) -> dict[str, str]:
    for name in os.environ:
        if (
            FORBIDDEN_EXECUTION_ENV_RE.fullmatch(name)
            and name != "ANSIBLE_VAULT_PASSWORD_FILE"
        ):
            raise ContractError(f"forbidden secret-bearing environment variable is set: {name}")
    environment: dict[str, str] = {}
    for name in ("PATH", "HOME", "TMPDIR", "SSH_AUTH_SOCK", "ANSIBLE_VAULT_PASSWORD_FILE"):
        value = os.environ.get(name)
        if value:
            environment[name] = value
    if "ANSIBLE_VAULT_PASSWORD_FILE" in environment:
        require_private_file(
            Path(environment["ANSIBLE_VAULT_PASSWORD_FILE"]),
            "ANSIBLE_VAULT_PASSWORD_FILE",
        )
    if repos is not None:
        environment["ANSIBLE_TOOLBOX_INVENTORY_SOURCE"] = str(
            (repos["inventory"] / "inventories").resolve()
        )
    requires_private_key = action.get(
        "requires_ssh_private_key", action["impact"] in LIVE_IMPACTS
    )
    requires_ssh_agent = action.get("requires_ssh_agent", False)
    if requires_private_key:
        ssh_contract = manifest["controller"]["ssh"]
        ssh_source = require_private_directory(
            Path(ssh_contract["source_directory"]), "controller SSH source"
        )
        private_key = require_private_file(
            ssh_source / ssh_contract["private_key_name"],
            "controller SSH private key",
            allow_readonly=False,
        )
        if sha256_file(private_key) != ssh_contract["private_key_sha256"]:
            raise ContractError("controller SSH private key hash mismatch")
        environment["ANSIBLE_TOOLBOX_SSH_SOURCE"] = str(ssh_source)
        environment["ANSIBLE_TOOLBOX_MOUNT_SSH"] = "true"
        environment["ANSIBLE_TOOLBOX_MOUNT_SSH_AGENT"] = "false"
    else:
        environment["ANSIBLE_TOOLBOX_MOUNT_SSH"] = "false"
        environment["ANSIBLE_TOOLBOX_MOUNT_SSH_AGENT"] = "false"
    if requires_ssh_agent:
        ssh_agent = environment.get("SSH_AUTH_SOCK")
        if (
            not ssh_agent
            or not Path(ssh_agent).exists()
            or not stat.S_ISSOCK(Path(ssh_agent).stat().st_mode)
        ):
            raise ContractError("action requires a live SSH agent socket")
        environment["ANSIBLE_TOOLBOX_MOUNT_SSH_AGENT"] = "true"
    runtime = manifest["runtime"]
    environment.update(
        {
            "ANSIBLE_TOOLBOX_IMAGE": runtime["toolbox_image"],
            "ANSIBLE_TOOLBOX_RUN_EE_IMAGE": runtime["run_ee_image"],
            "ANSIBLE_TOOLBOX_PULL_POLICY": "never",
            "ANSIBLE_TOOLBOX_RUNTIME_MODE": "disconnected",
            "ANSIBLE_TOOLBOX_RUN_EE_PRELOAD": "true",
            "ANSIBLE_TOOLBOX_RH_COLLECTIONS_MODE": "never",
            "ANSIBLE_TOOLBOX_AUTO_COLLECTIONS": "false",
            "ANSIBLE_TOOLBOX_EE_ONLY_COLLECTIONS": "true",
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
    return environment


def terminate_process(process: subprocess.Popen[bytes], sig: int = signal.SIGTERM) -> None:
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
                if sum(totals.values()) > max_output_bytes and termination_reason is None:
                    termination_reason = "output_limit"
                    termination_started = time.monotonic()
                    terminate_process(process)
                remaining = max_output_bytes - sum(len(item) for item in buffers.values())
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


def parse_events(stdout: bytes, action_id: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    recaps: list[dict[str, Any]] = []
    artifacts: list[dict[str, Any]] = []
    for raw_line in stdout.decode("utf-8", errors="replace").splitlines():
        line = raw_line.strip()
        if not line.startswith(EVENT_PREFIX):
            continue
        try:
            event = json.loads(line[len(EVENT_PREFIX) :])
        except json.JSONDecodeError as exc:
            raise ContractError("governed callback emitted invalid JSON") from exc
        event = require_mapping(event, "governed event")
        if event.get("schema_version") != 1 or event.get("action_id") != action_id:
            raise ContractError("governed callback event identity mismatch")
        if event.get("type") == "recap":
            recaps.append(event)
        elif event.get("type") == "artifact":
            recursively_reject_secret_fields(event.get("payload"), "artifact")
            artifacts.append(event)
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
        not isinstance(value, int) or value < 0 for value in counts.values()
    ):
        raise ContractError("target recap counters are invalid")
    if counts["failed"] or counts["unreachable"]:
        raise ContractError("target recap contains failed or unreachable tasks")
    if counts["rescued"] and not action.get("allow_rescued", False):
        raise ContractError("target recap contains unapproved rescued tasks")
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


def write_artifact(path: Path, artifact_type: str, payload: Any) -> dict[str, Any]:
    recursively_reject_secret_fields(payload, artifact_type)
    document = {
        "schema_version": 1,
        "artifact_type": artifact_type,
        "payload": payload,
    }
    digest = write_new_json(path, document)
    return {"path": str(path), "sha256": digest, "artifact_type": artifact_type}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", required=True, type=Path)
    parser.add_argument("--gate-manifest", required=True, type=Path)
    parser.add_argument("--gate-signature", required=True, type=Path)
    parser.add_argument("--allowed-signers", required=True, type=Path)
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

    policy, policy_payload = read_json_object(args.policy, "execution policy")
    gate_manifest_path = require_private_file(
        args.gate_manifest, "signed gate manifest"
    )
    manifest, manifest_payload = read_json_object(
        gate_manifest_path, "signed gate manifest"
    )
    policy_digest = sha256_bytes(policy_payload)
    validate_policy(policy)
    validate_manifest(manifest, policy, policy_digest)
    verify_manifest_signature(
        manifest_payload,
        args.gate_signature,
        args.allowed_signers,
        policy["signing"]["identity"],
        policy["signing"]["namespace"],
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
    repos = dict(repo_pairs)
    repository_states = [
        collect_repository_state(name, repos[name], manifest["repositories"][name])
        for name in policy["required_repositories"]
    ]

    extra_vars, extra_vars_digest, extra_vars_source = validate_extra_vars(
        args.extra_vars, action, manifest, authorization, execution_id
    )
    sealed_extra_vars: Path | None = None
    sealed_extra_vars_created = False
    executed_extra_vars_digest: str | None = None
    canonical_extra_vars: bytes | None = None
    if extra_vars_source is not None:
        temp_root = repos["automation"] / "ansible" / ".tmp" / "governed-exec"
        temp_root.mkdir(mode=0o700, parents=True, exist_ok=True)
        os.chmod(temp_root, 0o700)
        sealed_extra_vars = temp_root / f"{execution_id}.json"
        canonical_extra_vars = (
            json.dumps(extra_vars, sort_keys=True, separators=(",", ":")) + "\n"
        ).encode("utf-8")
        executed_extra_vars_digest = sha256_bytes(canonical_extra_vars)

    command, command_metadata = build_command(
        action, manifest["target"], repos, execution_id, sealed_extra_vars
    )
    environment = make_environment(manifest, args.action_id, action, repos)
    started_record = {
        "schema_version": 1,
        "execution_id": execution_id,
        "invocation_status": "STARTED",
        "evidence_status": "CANDIDATE",
        "gate_effect": "NONE_PENDING_REVIEW",
        "action_id": args.action_id,
        "impact": action["impact"],
        "gate": action["gate"],
        "target": manifest["target"],
        "controller": {
            **manifest["controller"],
            "claim_basis": "SIGNED_MANIFEST_NOT_LIVE_OBSERVATION",
        },
        "operator": {"value": args.operator, "claim_basis": "DECLARED"},
        "reviewer": {"value": args.reviewer, "claim_basis": "DECLARED"},
        "purpose": args.purpose,
        "jira": args.jira,
        "approval": {
            "reference": authorization["approval_reference"],
            "sha256": authorization["approval_sha256"],
            "claim_basis": "SIGNED_GATE_MANIFEST",
        },
        "policy": {"path": str(args.policy.resolve()), "sha256": policy_digest},
        "gate_manifest": {
            "path": str(args.gate_manifest.resolve()),
            "sha256": sha256_bytes(manifest_payload),
            "signature_verified": True,
        },
        "repositories": repository_states,
        "runtime": {
            **manifest["runtime"],
            "collection_claim_basis": "SIGNED_RUNTIME_ATTESTATION",
        },
        "command": {
            "argv": command,
            "copyable": shlex.join(command),
            **command_metadata,
            "extra_variable_names": sorted(extra_vars),
            "source_extra_vars_sha256": extra_vars_digest,
            "executed_extra_vars_sha256": executed_extra_vars_digest,
        },
        "required_evidence_references": {
            key: authorization[key]
            for key in action.get("required_evidence_references", [])
        },
        "started_utc": utc_now(),
        "local_integrity_claim": (
            "Owner-only append-on-create records with SHA-256 sidecars; external "
            "signature/hash anchoring and independent acceptance remain required."
        ),
    }
    started_digest = write_new_json(started_path, started_record)

    result: dict[str, Any]
    contract_failure: str | None = None
    produced_artifact: dict[str, Any] | None = None
    signed_approval_claims: list[dict[str, str]] = []
    try:
        signed_approval_claims = claim_signed_approval_transports(
            extra_vars, action, execution_id
        )
        if sealed_extra_vars is not None and canonical_extra_vars is not None:
            descriptor = os.open(
                sealed_extra_vars, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600
            )
            sealed_extra_vars_created = True
            try:
                with os.fdopen(descriptor, "wb", closefd=False) as stream:
                    stream.write(canonical_extra_vars)
                    stream.flush()
                    os.fsync(stream.fileno())
            finally:
                os.close(descriptor)
            if sha256_file(sealed_extra_vars) != executed_extra_vars_digest:
                raise ContractError("sealed extra-vars copy failed verification")
        result = run_bounded(
            command,
            environment,
            repos["automation"] / "ansible",
            int(action.get("timeout_seconds", 1800)),
            int(action.get("max_output_bytes", 8 * 1024 * 1024)),
        )
        try:
            verify_repositories_after(repository_states)
            if sealed_extra_vars is not None and sha256_file(sealed_extra_vars) != sha256_bytes(
                (json.dumps(extra_vars, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
            ):
                raise ContractError("sealed extra-vars changed during execution")
            recaps, artifacts = parse_events(result["stdout"], args.action_id)
            recap = validate_target_recap(
                recaps, manifest["target"]["fqdn"], action
            )
            if result["exit_code"] != 0 or result["termination_reason"]:
                raise ContractError("subprocess did not complete successfully")
            expected_artifact = action.get("expected_artifact")
            if action["mode"] == "inventory_projection":
                try:
                    inventory_document = json.loads(result["stdout"].decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                    raise ContractError("ansible-inventory stdout is not one JSON object") from exc
                inventory_document = require_mapping(
                    inventory_document, "inventory host document"
                )
                projection = select_projection(
                    inventory_document, action.get("projection_paths", [])
                )
                produced_artifact = write_artifact(
                    evidence_dir / f"{execution_id.lower()}.inventory-projection.json",
                    "inventory_projection",
                    projection,
                )
            elif expected_artifact:
                matching = [
                    event for event in artifacts if event.get("artifact_type") == expected_artifact
                ]
                if len(matching) != 1:
                    raise ContractError("expected exactly one governed artifact event")
                artifact_payload = require_mapping(
                    matching[0]["payload"], "governed artifact payload"
                )
                projection = select_projection(
                    artifact_payload, action.get("artifact_projection_paths", [])
                )
                produced_artifact = write_artifact(
                    evidence_dir / f"{execution_id.lower()}.{expected_artifact}.json",
                    str(expected_artifact),
                    projection,
                )
            elif artifacts:
                raise ContractError("action emitted an unexpected governed artifact")
        except ContractError as exc:
            contract_failure = str(exc)
            recap = None
    except ContractError as exc:
        result = {
            "start_utc": started_record["started_utc"],
            "end_utc": utc_now(),
            "duration_seconds": 0,
            "exit_code": 126,
            "termination_reason": "pre_process_contract",
            "stdout": b"",
            "stderr": b"",
            "stdout_sha256": sha256_bytes(b""),
            "stderr_sha256": sha256_bytes(b""),
            "stdout_bytes": 0,
            "stderr_bytes": 0,
        }
        recap = None
        contract_failure = str(exc)
    except OSError as exc:
        result = {
            "start_utc": started_record["started_utc"],
            "end_utc": utc_now(),
            "duration_seconds": 0,
            "exit_code": 127,
            "termination_reason": "process_start",
            "stdout": b"",
            "stderr": b"",
            "stdout_sha256": sha256_bytes(b""),
            "stderr_sha256": sha256_bytes(b""),
            "stdout_bytes": 0,
            "stderr_bytes": 0,
        }
        recap = None
        contract_failure = f"process start failed: {type(exc).__name__}"
    finally:
        if sealed_extra_vars is not None and sealed_extra_vars_created:
            try:
                sealed_extra_vars.unlink()
            except FileNotFoundError:
                pass

    if contract_failure:
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
        },
        "output": {
            "raw_retained": False,
            "stdout_sha256": result["stdout_sha256"],
            "stderr_sha256": result["stderr_sha256"],
            "stdout_bytes": result["stdout_bytes"],
            "stderr_bytes": result["stderr_bytes"],
            "claim_basis": "BOUNDED_IN_MEMORY_CAPTURE",
        },
        "produced_artifact": produced_artifact,
        "signed_approval_transport": {
            "transport_authority": "SIGNED_GATE_MANIFEST",
            "transport_mapping_is_approval_authority": False,
            "plugin_signature_verification": (
                "DELEGATED_TO_FOUNDATIONAL_ACTION_PLUGIN_AT_CONSUMER"
            ),
            "claims": signed_approval_claims,
        },
        "claims": {
            "technical": [
                "target/command/gate/repository/runtime contract validated before start",
                "execution attempt reserved before process creation",
                "raw output not persisted by the recorder",
            ],
            "declarative_pending_review": [
                "operator and reviewer identity",
                "controller source is approved but not live-observed by this recorder",
                "readback, rollback, findings, risk and gate effect references",
                "action semantics derive from reviewed policy and are not inferred from CLI",
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
