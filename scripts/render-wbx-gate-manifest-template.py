#!/usr/bin/env python3
"""Render a complete, deliberately non-approved Recorder-v3 manifest."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "policies" / "wunderbox" / "root-of-trust-policy.json"
TEMPLATE_PATH = ROOT / "policies" / "wunderbox" / "gate-manifest.template.json"


def _authorization_field_placeholder(field: str) -> str:
    if field.endswith("sha256"):
        return "REPLACE_WITH_64_HEX"
    if field.endswith("fingerprint"):
        return "REPLACE_WITH_SSH_SHA256_FINGERPRINT"
    return f"REPLACE_WITH_{field.upper()}"


def _execution_approval(
    authorization_template: dict, action_id: str, repositories: list[str]
) -> dict:
    approval = copy.deepcopy(authorization_template["execution_approval"])
    approval["execution_id"] = (
        f"REPLACE_WITH_EXACT_{action_id.upper()}_RECORDER_EXECUTION_ID"
    )
    approval["commit_shas"] = {
        repository: "REPLACE_WITH_FULL_GIT_SHA" for repository in repositories
    }
    # This deterministic placeholder is not an approval secret.  It makes
    # accidental approval reuse structurally visible while TEMPLATE status and
    # the deliberately invalid signature keep the skeleton non-executable.
    approval["nonce"] = hashlib.sha256(
        f"wunderbox-template:execution:{action_id}".encode("utf-8")
    ).hexdigest()
    approval["signature"] = (
        f"REPLACE_WITH_REAL_{action_id.upper()}_EXECUTION_APPROVAL_SIGNATURE"
    )
    return approval


def _consumer_contracts(action: dict) -> dict:
    contracts = {}
    for variable, binding in action.get("extra_var_bindings", {}).items():
        if binding.get("kind") != "signed_approval_transport":
            continue
        contracts[variable] = {
            "operation": binding["operation"],
            "target": "REPLACE_WITH_EXACT_TARGET_FQDN",
            "binding": binding["contract_binding"],
        }
    return contracts


def render() -> dict:
    policy_bytes = POLICY_PATH.read_bytes()
    policy = json.loads(policy_bytes)
    template = json.loads(TEMPLATE_PATH.read_text(encoding="utf-8"))
    authorization_template = template["authorizations"].pop(
        "REPLACE_WITH_EACH_POLICY_ACTION_ID"
    )
    template["policy_sha256"] = hashlib.sha256(policy_bytes).hexdigest()
    template["authorizations"] = {}
    for action_id, action in policy["actions"].items():
        authorization = copy.deepcopy(authorization_template)
        authorization["approval_reference"] = (
            f"REPLACE_WITH_IMMUTABLE_{action_id.upper()}_APPROVAL_REFERENCE"
        )
        authorization["execution_approval"] = _execution_approval(
            authorization_template,
            action_id,
            policy["required_repositories"],
        )
        authorization["consumer_approval_contracts"] = _consumer_contracts(action)
        for reference in action.get("required_evidence_references", []):
            authorization[reference] = f"REPLACE_WITH_{reference.upper()}"
        for binding in action.get("extra_var_bindings", {}).values():
            if binding.get("kind") not in {
                "authorization_field",
                "target_and_authorization_confirmation",
            }:
                continue
            field = binding["field"]
            authorization[field] = _authorization_field_placeholder(field)
        template["authorizations"][action_id] = authorization
    return template


def main() -> int:
    print(json.dumps(render(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
