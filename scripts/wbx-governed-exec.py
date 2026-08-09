#!/usr/bin/env python3
"""Bind the generic recorder to the Wunderbox Root-of-Trust policy.

This adapter deliberately exposes no policy, signer, target, playbook,
inventory, gate, impact, tags, execution image, or arbitrary command option.
Policy and signer trust come from the recorder's fixed controller trust
descriptor; engagement values come from the separately protected, signed gate
manifest.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
ROOT_OWNED_LAUNCHER = Path(
    "/Library/Application Support/Lightning IT/Governed Ansible/bin/governed-ansible-exec"
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inventory-repo", required=True, type=Path)
    parser.add_argument("--foundational-repo", required=True, type=Path)
    parser.add_argument("--ubuntu-repo", required=True, type=Path)
    parser.add_argument("--validation-repo", required=True, type=Path)
    parser.add_argument("--operations-repo", required=True, type=Path)
    parser.add_argument("--gate-manifest", required=True, type=Path)
    parser.add_argument("--gate-signature", required=True, type=Path)
    parser.add_argument("--action-id", required=True)
    parser.add_argument("--attempt", required=True, type=int)
    parser.add_argument("--operator", required=True)
    parser.add_argument("--reviewer", required=True)
    parser.add_argument("--purpose", required=True)
    parser.add_argument("--jira", required=True)
    parser.add_argument("--extra-vars", type=Path)
    parser.add_argument("--evidence-dir", required=True, type=Path)
    return parser


def build_core_command(args: argparse.Namespace) -> list[str]:
    command = [
        str(ROOT_OWNED_LAUNCHER),
        "--gate-manifest",
        str(args.gate_manifest),
        "--gate-signature",
        str(args.gate_signature),
        "--action-id",
        args.action_id,
        "--attempt",
        str(args.attempt),
        "--operator",
        args.operator,
        "--reviewer",
        args.reviewer,
        "--purpose",
        args.purpose,
        "--jira",
        args.jira,
        "--repo",
        f"automation={REPOSITORY_ROOT}",
        "--repo",
        f"inventory={args.inventory_repo.expanduser().resolve()}",
        "--repo",
        f"foundational={args.foundational_repo.expanduser().resolve()}",
        "--repo",
        f"ubuntu={args.ubuntu_repo.expanduser().resolve()}",
        "--repo",
        f"validation={args.validation_repo.expanduser().resolve()}",
        "--repo",
        f"operations={args.operations_repo.expanduser().resolve()}",
        "--evidence-dir",
        str(args.evidence_dir),
    ]
    if args.extra_vars is not None:
        command.extend(["--extra-vars", str(args.extra_vars)])
    return command


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    command = build_core_command(args)
    os.execv(str(ROOT_OWNED_LAUNCHER), command)
    return 127


if __name__ == "__main__":
    raise SystemExit(main())
