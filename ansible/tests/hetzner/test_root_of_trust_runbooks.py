"""Static safety contract for generic root-of-trust G0 and G2 runbooks."""

from pathlib import Path
import unittest

import yaml


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
RUNBOOK_DIRECTORY = (
    REPOSITORY_ROOT
    / "ansible"
    / "runbooks"
    / "10-compute"
    / "baremetal"
    / "hetzner"
)
G0_RUNBOOK = RUNBOOK_DIRECTORY / "09-root-of-trust-g0-observe.yml"
G2_RUNBOOK = RUNBOOK_DIRECTORY / "09-root-of-trust-g2-plan.yml"
SELECTION_GUARD = RUNBOOK_DIRECTORY / "tasks" / "require-root-of-trust-selection.yml"


def load_yaml(path: Path):
    """Load one repository YAML document."""
    with path.open(encoding="utf-8") as stream:
        return yaml.safe_load(stream)


class RootOfTrustRunbookTests(unittest.TestCase):
    """Keep G0 read-only, G2 local-only, and both target-exact."""

    def test_both_runbooks_use_the_shared_exact_selection_guard(self):
        for runbook in (G0_RUNBOOK, G2_RUNBOOK):
            with self.subTest(runbook=runbook.name):
                play = load_yaml(runbook)[0]
                self.assertEqual(play["hosts"], "hetzner_baremetal")
                self.assertEqual(play["connection"], "local")
                self.assertEqual(play["serial"], 1)
                self.assertIs(play["any_errors_fatal"], True)
                self.assertIs(play["gather_facts"], False)
                self.assertEqual(
                    play["pre_tasks"][0]["ansible.builtin.import_tasks"],
                    "tasks/require-root-of-trust-selection.yml",
                )

        guard = SELECTION_GUARD.read_text(encoding="utf-8")
        for condition in (
            "== 'single_root_of_trust'",
            "ansible_limit is defined",
            "ansible_limit | string | trim",
            "ansible_play_hosts_all | length == 1",
            "== [hetzner_baremetal_root_of_trust.inventory_hostname]",
            "hetzner_robot_server_number is integer",
            "hetzner_robot_server_number | int > 0",
        ):
            with self.subTest(condition=condition):
                self.assertIn(condition, guard)

    def test_g0_uses_only_the_generic_observation_entrypoint(self):
        play = load_yaml(G0_RUNBOOK)[0]
        credential_task = play["pre_tasks"][1]
        self.assertEqual(
            credential_task["ansible.builtin.include_tasks"],
            "tasks/resolve-robot-credentials.yml",
        )

        observation = play["tasks"][0]
        include_role = observation["ansible.builtin.include_role"]
        self.assertEqual(
            include_role["name"], "lit.foundational.root_of_trust_validate"
        )
        self.assertEqual(include_role["tasks_from"], "g0_observe")
        self.assertIn(
            "hetzner_baremetal_root_of_trust.selection_scope",
            str(observation["vars"]["root_of_trust_validate_selection_scope"]),
        )

        text = G0_RUNBOOK.read_text(encoding="utf-8").lower()
        for forbidden in (
            "ansible.builtin.command",
            "ansible.builtin.shell",
            "ansible.builtin.uri",
            "hetzner_installimage",
            "wunderbox",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, text)

    def test_g2_is_local_only_and_validates_both_exact_firewall_phases(self):
        play = load_yaml(G2_RUNBOOK)[0]
        validation = play["tasks"][0]
        include_role = validation["ansible.builtin.include_role"]
        self.assertEqual(
            include_role["name"], "lit.foundational.root_of_trust_validate"
        )
        self.assertEqual(include_role["tasks_from"], "g2_plan")

        text = G2_RUNBOOK.read_text(encoding="utf-8")
        self.assertIn(
            "hetzner_baremetal_robot_firewall_bootstrap_input_rules", text
        )
        self.assertIn(
            "hetzner_baremetal_robot_firewall_hardened_input_rules", text
        )
        self.assertIn(
            "hetzner_baremetal_robot_firewall_deferred_tang_input_rules", text
        )
        for forbidden in (
            "resolve-robot-credentials",
            "community.hrobot",
            "hetzner_installimage",
            "ansible.builtin.command",
            "ansible.builtin.shell",
            "ansible.builtin.uri",
            "wunderbox",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, text.lower())


if __name__ == "__main__":
    unittest.main()
