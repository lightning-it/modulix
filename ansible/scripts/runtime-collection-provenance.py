#!/usr/bin/env python3
"""Measure the effective immutable collection trees inside a governed image."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys

from ansible import constants as ansible_constants


COLLECTIONS = {
    "foundational": "lit.foundational",
    "ubuntu": "lit.ubuntu",
}
SYSTEM_COLLECTION_ROOTS = (
    Path("/usr/share/ansible/collections/ansible_collections"),
    Path("/usr/share/automation-controller/collections/ansible_collections"),
)
EXPECTED_COLLECTION_PATHS = tuple(path.parent for path in SYSTEM_COLLECTION_ROOTS)


def tree_sha256(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*"), key=lambda item: item.as_posix()):
        relative = path.relative_to(root).as_posix().encode("utf-8")
        status = os.lstat(path)
        if stat.S_ISLNK(status.st_mode):
            raise RuntimeError(f"collection contains a symbolic link: {relative!r}")
        if stat.S_ISDIR(status.st_mode):
            digest.update(b"D\0" + relative + b"\0")
            continue
        if not stat.S_ISREG(status.st_mode):
            raise RuntimeError(f"collection contains a non-regular entry: {relative!r}")
        executable = b"1" if status.st_mode & 0o111 else b"0"
        digest.update(b"F\0" + relative + b"\0" + executable + b"\0")
        with path.open("rb") as stream:
            while chunk := stream.read(1024 * 1024):
                digest.update(chunk)
    return digest.hexdigest()


def collection_version(root: Path) -> str:
    manifest = root / "MANIFEST.json"
    if not manifest.is_file() or manifest.is_symlink():
        raise RuntimeError(f"installed collection manifest is missing: {manifest}")
    document = json.loads(manifest.read_text(encoding="utf-8"))
    version = document.get("collection_info", {}).get("version")
    if not isinstance(version, str) or not version.strip():
        raise RuntimeError(f"installed collection version is missing: {manifest}")
    return version


def locate_collection(fqcn: str) -> Path:
    namespace, name = fqcn.split(".", 1)
    matches = []
    for root in SYSTEM_COLLECTION_ROOTS:
        candidate = root / namespace / name
        if not candidate.exists():
            continue
        if candidate.is_symlink() or not candidate.is_dir():
            raise RuntimeError(f"effective collection root is unsafe: {candidate}")
        matches.append(candidate)
    if len(matches) != 1:
        raise RuntimeError(f"expected exactly one effective {fqcn} collection")
    return matches[0].resolve(strict=True)


def effective_loader_contract() -> dict[str, object]:
    collection_paths = tuple(
        Path(path).resolve() for path in ansible_constants.COLLECTIONS_PATHS
    )
    scan_sys_path = bool(ansible_constants.COLLECTIONS_SCAN_SYS_PATH)
    if collection_paths != EXPECTED_COLLECTION_PATHS:
        raise RuntimeError(
            "effective Ansible collection paths do not match the governed system roots"
        )
    if scan_sys_path:
        raise RuntimeError("Ansible collection sys.path scanning must be disabled")
    return {
        "collection_paths": [str(path) for path in collection_paths],
        "scan_sys_path": scan_sys_path,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--image-role", choices=("toolbox", "run_ee"), required=True)
    parser.add_argument("--image", required=True)
    args = parser.parse_args()
    if re.fullmatch(r"[^\s@]+@sha256:[0-9a-f]{64}", args.image) is None:
        raise RuntimeError("image must be bound by an immutable digest")
    measured = {}
    loader = effective_loader_contract()
    for name, fqcn in COLLECTIONS.items():
        root = locate_collection(fqcn)
        measured[name] = {
            "fqcn": fqcn,
            "version": collection_version(root),
            "installed_tree_sha256": tree_sha256(root),
        }
    json.dump(
        {
            "schema_version": 1,
            "image_role": args.image_role,
            "image": args.image,
            "loader": loader,
            "collections": measured,
        },
        sys.stdout,
        sort_keys=True,
        separators=(",", ":"),
    )
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
