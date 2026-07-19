#!/usr/bin/env python3
"""Remove terminal escapes, local paths, and token-shaped values from a log."""

from __future__ import annotations

import argparse
from pathlib import Path
import re


ANSI_ESCAPE = re.compile(r"\x1b(?:\[[0-?]*[ -/]*[@-~]|\][^\x07]*(?:\x07|\x1b\\))")
TOKEN_SHAPES = [
    re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,})\b"),
    re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    re.compile(r"\bhvs\.[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b"),
]
PRIVATE_KEY_BLOCK = re.compile(
    r"-----BEGIN (?:[A-Z0-9 ]+ )?PRIVATE KEY-----.*?"
    r"-----END (?:[A-Z0-9 ]+ )?PRIVATE KEY-----",
    re.DOTALL,
)
CREDENTIAL_ASSIGNMENT = re.compile(
    r"(?i)(\b(?:password|passwd|token|secret|client_secret)\b"
    r"\s*[:=]\s*['\"]?)[^\s'\"]{16,}"
)


def main() -> int:
    """Write a deterministic sanitized copy of one acceptance log."""
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--replace", action="append", default=[])
    args = parser.parse_args()

    content = args.source.read_text(encoding="utf-8", errors="replace")
    content = ANSI_ESCAPE.sub("", content)
    for value in sorted(filter(None, args.replace), key=len, reverse=True):
        content = content.replace(value, "<LOCAL_PATH>")
    content = PRIVATE_KEY_BLOCK.sub("<REDACTED_PRIVATE_KEY>", content)
    content = CREDENTIAL_ASSIGNMENT.sub(r"\1<REDACTED_CREDENTIAL>", content)
    for pattern in TOKEN_SHAPES:
        content = pattern.sub("<REDACTED_CREDENTIAL>", content)
    args.destination.write_text(content, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
