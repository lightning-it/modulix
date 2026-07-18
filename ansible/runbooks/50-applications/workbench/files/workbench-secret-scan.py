#!/usr/bin/env python3
"""Scan acceptance evidence for high-confidence credential material."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys


PATTERNS = {
    "private-key": re.compile(r"-----BEGIN (?:[A-Z0-9 ]+ )?PRIVATE KEY-----"),
    "github-token": re.compile(
        r"\b(?:gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,})\b"
    ),
    "aws-access-key": re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    "vault-token": re.compile(r"\bhvs\.[A-Za-z0-9_-]{20,}\b"),
    "slack-token": re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b"),
    "credential-assignment": re.compile(
        r"(?i)\b(?:password|passwd|token|secret|client_secret)\b"
        r"\s*[:=]\s*['\"]?[^\s'\"]{16,}"
    ),
}


def iter_files(paths: list[Path]):
    """Yield regular, non-symlink files in deterministic order."""
    for path in sorted(paths):
        if path.is_symlink():
            continue
        if path.is_file():
            yield path
        elif path.is_dir():
            for candidate in sorted(path.rglob("*")):
                if candidate.is_file() and not candidate.is_symlink():
                    yield candidate


def main() -> int:
    """Return nonzero without returning matched secret values."""
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+", type=Path)
    args = parser.parse_args()

    findings = []
    scanned_files = 0
    missing_paths = [path for path in args.paths if not path.exists()]
    for path in missing_paths:
        findings.append(
            {
                "file": str(path),
                "line": 0,
                "pattern": "missing-path",
            }
        )

    for path in iter_files(args.paths):
        scanned_files += 1
        try:
            with path.open("r", encoding="utf-8", errors="replace") as stream:
                for line_number, line in enumerate(stream, start=1):
                    for pattern_name, pattern in PATTERNS.items():
                        if pattern.search(line):
                            findings.append(
                                {
                                    "file": str(path),
                                    "line": line_number,
                                    "pattern": pattern_name,
                                }
                            )
        except OSError:
            findings.append(
                {
                    "file": str(path),
                    "line": 0,
                    "pattern": "scan-error",
                }
            )

    if scanned_files == 0 and not missing_paths:
        findings.append(
            {
                "file": "<scan-input>",
                "line": 0,
                "pattern": "empty-scan",
            }
        )

    json.dump(
        {
            "status": "failed" if findings else "passed",
            "scanned_files": scanned_files,
            "findings": findings,
        },
        sys.stdout,
        indent=2,
        sort_keys=True,
    )
    sys.stdout.write("\n")
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
