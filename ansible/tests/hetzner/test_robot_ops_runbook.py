"""Safety contract for target-bound Hetzner Robot operations."""

from pathlib import Path
import unittest

import yaml


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
RUNBOOK = (
    REPOSITORY_ROOT
    / "ansible"
    / "runbooks"
    / "10-compute"
    / "baremetal"
    / "hetzner"
    / "09-robot-ops.yml"
)


class HetznerRobotOpsRunbookTests(unittest.TestCase):
    """Keep every Robot boot/reset request bound to one numeric asset."""

    def test_robot_ops_requires_and_forwards_numeric_server_identity(self):
        with RUNBOOK.open(encoding="utf-8") as stream:
            play = yaml.safe_load(stream)[0]

        target_guard = play["pre_tasks"][0]
        conditions = "\n".join(target_guard["ansible.builtin.assert"]["that"])
        self.assertIn("ansible_play_hosts_all | length == 1", conditions)
        self.assertIn("ansible_limit | string | trim == inventory_hostname", conditions)
        self.assertIn("hetzner_robot_server_number is defined", conditions)
        self.assertIn("hetzner_robot_server_number is integer", conditions)
        self.assertIn("hetzner_robot_server_number | int > 0", conditions)

        robot_role = play["roles"][0]
        self.assertEqual(robot_role["role"], "lit.foundational.hetzner_robot_ops")
        self.assertEqual(
            robot_role["hetzner_robot_ops_server_number"],
            "{{ hetzner_robot_server_number }}",
        )
        self.assertEqual(
            robot_role["hetzner_robot_ops_server_ip"],
            "{{ ansible_host }}",
        )


if __name__ == "__main__":
    unittest.main()
