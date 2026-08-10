#!/usr/bin/env python3
"""Classify a 1Password item-tag dry-run without exposing item content."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--op", required=True)
    parser.add_argument("--account-id", required=True)
    parser.add_argument("--vault-id", required=True)
    parser.add_argument("--item-id", required=True)
    parser.add_argument("--tags", required=True)
    parser.add_argument("--timeout", type=int, default=30)
    return parser


def _minimal_environment() -> dict[str, str]:
    forbidden = ("OP_SERVICE_ACCOUNT_TOKEN", "OP_CONNECT_HOST", "OP_CONNECT_TOKEN")
    if any(os.environ.get(name) for name in forbidden):
        raise RuntimeError("forbidden_auth_environment")
    if any(name.startswith("OP_SESSION_") and value for name, value in os.environ.items()):
        raise RuntimeError("forbidden_session_environment")
    environment = {
        name: os.environ[name]
        for name in ("HOME", "PATH", "TMPDIR", "LANG", "LC_ALL")
        if os.environ.get(name)
    }
    if not environment.get("HOME"):
        raise RuntimeError("missing_home")
    return environment


def _classify(stderr: bytes) -> dict[str, bool]:
    text = stderr.decode("utf-8", errors="replace").lower()
    return {
        "authorization": "authorization" in text,
        "already": "already" in text,
        "cannot": "cannot" in text or "can't" in text,
        "change": "change" in text,
        "detected": "detect" in text,
        "dry_run": "dry-run" in text or "dry run" in text,
        "edit": "edit" in text,
        "error": "error" in text,
        "failed": "fail" in text,
        "input": "input" in text,
        "invalid_json": "invalid json" in text,
        "invalid": "invalid" in text,
        "interactive": "interactive" in text,
        "must": "must" in text,
        "not_found": "not found" in text,
        "nothing": "nothing" in text or "no changes" in text,
        "permission": "permission" in text,
        "read": "read" in text,
        "required": "required" in text,
        "signed_in": "signed in" in text,
        "stdin": "stdin" in text,
        "terminal": "terminal" in text or "tty" in text,
        "timeout": "timeout" in text or "timed out" in text,
        "unexpected": "unexpected" in text,
        "unknown_flag": "unknown flag" in text,
        "unsupported": "unsupported" in text or "not supported" in text,
    }


def _sanitize(stderr: bytes, redactions: tuple[str, ...]) -> str:
    if len(stderr) > 256:
        return "WITHHELD_OVERSIZE"
    try:
        text = stderr.decode("ascii", errors="strict")
    except UnicodeDecodeError:
        return "WITHHELD_NON_ASCII"
    for value in redactions:
        text = text.replace(value, "<redacted-id>")
    text = re.sub(
        r"\b\d{4}/\d{2}/\d{2}\s+\d{2}:\d{2}:\d{2}\b",
        "<timestamp>",
        text,
    )
    forbidden_terms = (
        "begin ",
        "credential",
        "key",
        "password",
        "private",
        "schema_version",
        "secret",
        "ssh-",
        "subject",
        "token",
    )
    for term in forbidden_terms:
        text = re.sub(
            re.escape(term),
            "<sensitive-term>",
            text,
            flags=re.IGNORECASE,
        )
    if re.search(r"[A-Za-z0-9+/=]{20,}", text):
        return "WITHHELD_LONG_TOKEN"
    return " ".join(text.split())


def main() -> int:
    args = _parser().parse_args()
    op_path = Path(args.op)
    if not op_path.is_absolute() or not op_path.is_file() or op_path.is_symlink():
        raise RuntimeError("invalid_op_path")
    master_fd = -1
    slave_fd = -1
    try:
        master_fd, slave_fd = os.openpty()
        completed = subprocess.run(
            [
                str(op_path),
                "item",
                "edit",
                args.item_id,
                "--account",
                args.account_id,
                "--vault",
                args.vault_id,
                "--tags",
                args.tags,
                "--dry-run",
                "--format",
                "json",
            ],
            stdin=slave_fd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            env=_minimal_environment(),
            check=False,
            timeout=args.timeout,
        )
        stderr = completed.stderr
        result = {
            "schema_version": 1,
            "operation": "onepassword_item_tag_dry_run",
            "returncode": completed.returncode,
            "stderr_length": len(stderr),
            "stderr_sha256": hashlib.sha256(stderr).hexdigest(),
            "classification": _classify(stderr),
            "sanitized_stderr": _sanitize(
                stderr,
                (args.account_id, args.vault_id, args.item_id),
            ),
        }
        sys.stdout.write(json.dumps(result, sort_keys=True) + "\n")
        return 0
    finally:
        for descriptor in (slave_fd, master_fd):
            if descriptor >= 0:
                try:
                    os.close(descriptor)
                except OSError:
                    pass


if __name__ == "__main__":
    raise SystemExit(main())
