"""Contract tests for the controller-side CIS audit normalizer."""

from __future__ import annotations

import json
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest


ANSIBLE_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ANSIBLE_ROOT / "scripts" / "cis-audit-normalize"
DEFAULT_MANIFEST = (
    ANSIBLE_ROOT / "scripts" / "cis-audit-ubuntu24-v1.0.0-manifest.json"
)
FIXTURES = Path(__file__).parent / "fixtures" / "cis-audit"


class CisAuditNormalizeTests(unittest.TestCase):
    def run_normalizer(self, fixture: str, *extra: str) -> subprocess.CompletedProcess[str]:
        command = [
            sys.executable,
            str(SCRIPT),
            "--raw",
            str(FIXTURES / fixture),
            "--profile",
            "level1-server",
            "--manifest",
            str(FIXTURES / "manifest.json"),
            *extra,
        ]
        return subprocess.run(command, check=False, capture_output=True, text=True)

    def test_pass_is_normalized(self) -> None:
        result = self.run_normalizer("pass.json")
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["controls"][0]["status"], "pass")
        self.assertEqual(len(report["raw_evidence"]["sha256"]), 64)

    def test_unexplained_failure_fails_gate(self) -> None:
        result = self.run_normalizer("fail.json")
        self.assertEqual(result.returncode, 2, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["status"], "fail")
        self.assertEqual(
            report["unexplained_failures_or_skips"][0]["status"], "fail"
        )

    def test_unexplained_skip_fails_gate(self) -> None:
        result = self.run_normalizer("skip.json")
        self.assertEqual(result.returncode, 2, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["status"], "fail")
        self.assertEqual(
            report["unexplained_failures_or_skips"][0]["status"], "skip"
        )

    def test_missing_profile_metadata_is_contract_error(self) -> None:
        result = self.run_normalizer("missing-metadata.json")
        self.assertEqual(result.returncode, 3)
        self.assertIn("meta.workstation is required", result.stderr)
        self.assertEqual(result.stdout, "")

    def test_explicit_exception_classifies_failure(self) -> None:
        result = self.run_normalizer(
            "fail.json", "--exceptions", str(FIXTURES / "exceptions.json")
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["controls"][0]["status"], "intentional_exception")
        self.assertEqual(report["unexplained_failures_or_skips"], [])

    def test_reviewed_supplement_resolves_unreliable_raw_failure(self) -> None:
        command = [
            sys.executable,
            str(SCRIPT),
            "--raw",
            str(FIXTURES / "fail.json"),
            "--profile",
            "level1-server",
            "--manifest",
            str(FIXTURES / "manifest-supplemental.json"),
            "--supplemental-results",
            str(FIXTURES / "supplemental-pass.json"),
        ]
        result = subprocess.run(command, check=False, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["status"], "pass")
        self.assertEqual(len(report["explained_unreliable_producer_results"]), 1)
        self.assertEqual(
            report["known_coverage_gaps"][0]["resolution"], "supplemental_pass"
        )

    def test_output_is_owner_only(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "normalized.json"
            result = self.run_normalizer("pass.json", "--output", str(output))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(stat.S_IMODE(output.stat().st_mode), 0o600)
            self.assertEqual(json.loads(output.read_text()), json.loads(result.stdout))

    def test_declared_workstation_system_type_defect_is_visible(self) -> None:
        command = [
            sys.executable,
            str(SCRIPT),
            "--raw",
            str(FIXTURES / "pass.json"),
            "--profile",
            "level1-workstation",
            "--manifest",
            str(FIXTURES / "manifest.json"),
        ]
        result = subprocess.run(command, check=False, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(
            report["benchmark_metadata_defects"][0]["field"], "host_system_type"
        )
        self.assertEqual(
            report["benchmark_metadata_defects"][0]["emitted_value"], "Server"
        )

    def test_reviewed_manifest_counts_and_pins(self) -> None:
        manifest = json.loads(DEFAULT_MANIFEST.read_text())
        self.assertEqual(
            manifest["benchmark"]["remediation_role"]["commit"],
            "c893ca6836fb32b1ea067d4a63c341e39693074b",
        )
        self.assertEqual(
            manifest["benchmark"]["audit"]["commit"],
            "87efcc6d409d1a998a7cb809c5ce5a6afedf84c7",
        )
        self.assertEqual(
            manifest["expected_controls"]["counts"],
            {
                "level1-server": 267,
                "level1-workstation": 257,
                "common": 255,
            },
        )
        server_gap_ids = {
            gap["control_id"]
            for gap in manifest["coverage_gaps"]
            if "level1-server" in gap["profiles"]
        }
        workstation_gap_ids = {
            gap["control_id"]
            for gap in manifest["coverage_gaps"]
            if "level1-workstation" in gap["profiles"]
        }
        self.assertEqual(len(server_gap_ids), 45)
        self.assertEqual(len(workstation_gap_ids), 46)

    def test_reviewed_effective_context_is_enforced(self) -> None:
        command = [
            sys.executable,
            str(SCRIPT),
            "--raw",
            str(FIXTURES / "pass.json"),
            "--profile",
            "level1-server",
            "--manifest",
            str(DEFAULT_MANIFEST),
            "--context",
            str(FIXTURES / "default-context.json"),
        ]
        result = subprocess.run(command, check=False, capture_output=True, text=True)
        self.assertEqual(result.returncode, 2, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["tagged_expected_control_count"], 267)
        self.assertEqual(report["effective_expected_control_count"], 228)
        self.assertEqual(
            {item["key"]: item["value"] for item in report["effective_context"]},
            {
                "time_sync_tool": "systemd-timesyncd",
                "firewall_mode": "disabled",
                "syslog_service": "journald",
                "ipv6_mode": "required",
            },
        )


if __name__ == "__main__":
    unittest.main()
