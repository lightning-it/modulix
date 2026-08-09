"""Static guards for the external 1Password root-of-trust bootstrap path."""

from pathlib import Path
import unittest

import yaml


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
HETZNER_DIRECTORY = (
    REPOSITORY_ROOT / "ansible" / "runbooks" / "10-compute" / "baremetal" / "hetzner"
)
UBUNTU_DIRECTORY = (
    REPOSITORY_ROOT
    / "ansible"
    / "runbooks"
    / "30-operating-systems"
    / "ubuntu"
    / "24"
)


def load_yaml(path: Path):
    """Load one repository YAML document."""
    with path.open(encoding="utf-8") as stream:
        return yaml.safe_load(stream)


class OnePasswordRootOfTrustTests(unittest.TestCase):
    """Keep secret creation, public-key staging, and consumption fail closed."""

    def test_creation_returns_only_pinnable_identity_metadata(self):
        path = HETZNER_DIRECTORY / "08-recovery-secrets.yml"
        content = path.read_text(encoding="utf-8")

        self.assertIn("lit.foundational.onepassword_secret_item", content)
        self.assertIn("lit.foundational.onepassword_ssh_key_item", content)
        self.assertIn("password_item.item_version", content)
        self.assertIn("ssh_key_item.item_version", content)
        self.assertIn("ssh_key_item.expected_fingerprint", content)
        self.assertIn("ssh_keygen_path", content)
        self.assertIn("Report safe 1Password identity metadata", content)
        self.assertNotIn("onepassword_read_secret", content)

    def test_dropbear_hook_uses_only_the_verified_public_key(self):
        plays = load_yaml(UBUNTU_DIRECTORY / "09-prepare-installimage.yml")
        play = plays[0]
        verify_task = next(
            task
            for task in play["pre_tasks"]
            if task["name"]
            == "Verify the pinned Dropbear public key and its Agent capability"
        )
        self.assertEqual(
            verify_task["lit.foundational.onepassword_ssh_key_item"]["operation"],
            "verify_agent",
        )
        role_task = next(
            task
            for task in play["tasks"]
            if task["name"] == "Stage the secret-free Ubuntu Dropbear hook"
        )
        self.assertEqual(
            role_task["vars"]["luks_unlock_dropbear_authorized_keys"],
            ["{{ _luks_unlock_dropbear_public_identity.public_key }}"],
        )

    def test_unlock_has_no_ansible_secret_fact_or_generic_resolver(self):
        path = UBUNTU_DIRECTORY / "10-bootstrap-unlock.yml"
        content = path.read_text(encoding="utf-8")
        plays = load_yaml(path)
        play = plays[0]
        unlock_task = next(
            task
            for task in play["tasks"]
            if task["name"].startswith("Submit the exact pinned 1Password")
        )
        arguments = unlock_task["lit.foundational.onepassword_ssh_secret_stdin"]

        self.assertIs(unlock_task["no_log"], True)
        self.assertEqual(arguments["remote_command"], "/bin/cryptroot-unlock")
        self.assertIn("password_item_version", arguments)
        self.assertIn("ssh_item_version", arguments)
        self.assertIn("ssh_expected_fingerprint", arguments)
        self.assertIn("ssh_keygen_path", arguments)
        self.assertNotIn("register", unlock_task)
        self.assertNotIn("resolve-recovery-secret.yml", content)
        self.assertNotIn("_hetzner_baremetal_recovery_passphrase", content)
        self.assertNotIn("ansible.builtin.set_fact", content)
        self.assertNotIn("ansible.builtin.command", content)

    def test_first_boot_explicitly_accepts_the_external_backend(self):
        content = (UBUNTU_DIRECTORY / "10-first-encrypted-boot.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("'onepassword_cli'", content)
        self.assertIn("non-interactive SSH stdin", content)
        self.assertNotIn("under no_log", content)


if __name__ == "__main__":
    unittest.main()
