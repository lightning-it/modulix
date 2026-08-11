"""Behavior tests for governed execution support files."""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import types
from types import SimpleNamespace
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]


def ensure_ansible_test_runtime() -> None:
    try:
        from ansible import constants  # noqa: F401
        from ansible.plugins.callback import CallbackBase  # noqa: F401

        return
    except ImportError:
        pass

    ansible_module = sys.modules.get("ansible") or types.ModuleType("ansible")
    plugins_module = types.ModuleType("ansible.plugins")
    callback_module = types.ModuleType("ansible.plugins.callback")
    constants_module = types.ModuleType("ansible.constants")

    class CallbackBase:
        def __init__(self) -> None:
            self._display = SimpleNamespace(display=lambda _message: None)

    callback_module.CallbackBase = CallbackBase
    constants_module.COLLECTIONS_PATHS = ()
    constants_module.COLLECTIONS_SCAN_SYS_PATH = False
    ansible_module.constants = constants_module
    ansible_module.plugins = plugins_module
    plugins_module.callback = callback_module
    sys.modules.update(
        {
            "ansible": ansible_module,
            "ansible.constants": constants_module,
            "ansible.plugins": plugins_module,
            "ansible.plugins.callback": callback_module,
        }
    )


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ensure_ansible_test_runtime()
RECORDER = load_module(
    "governed_ansible_exec_runtime_test", ROOT / "scripts" / "governed-ansible-exec.py"
)
CALLBACK = load_module(
    "lit_governed_evidence_runtime_test",
    ROOT / "ansible" / "callback_plugins" / "lit_governed_evidence.py",
)
PROVENANCE = load_module(
    "runtime_collection_provenance_test",
    ROOT / "ansible" / "scripts" / "runtime-collection-provenance.py",
)


def emitted_event(callback) -> dict:
    payload = callback._display.display.call_args.args[0]
    prefix = "LIT_GOVERNED_EVENT="
    if not payload.startswith(prefix):
        raise AssertionError("callback did not emit a governed event")
    return json.loads(payload[len(prefix) :])


class CallbackBehaviorTests(unittest.TestCase):
    def make_callback(self):
        environment = {
            "LIT_GOVERNED_ACTION_ID": "test_action",
            "LIT_GOVERNED_EXECUTION_ID": "execution-1",
            "LIT_GOVERNED_SAFE_TASKS": json.dumps({"safe task": "readback"}),
        }
        with mock.patch.dict(os.environ, environment, clear=True):
            callback = CALLBACK.CallbackModule()
        callback._display.display = mock.Mock()
        return callback

    def test_safe_artifact_is_emitted_with_bound_identity(self) -> None:
        callback = self.make_callback()
        result = SimpleNamespace(
            _task=SimpleNamespace(get_name=lambda: "safe task"),
            _result={"msg": {"status": "ok", "count": 1}},
        )
        callback.v2_runner_on_ok(result)
        self.assertEqual(
            emitted_event(callback),
            {
                "schema_version": 1,
                "action_id": "test_action",
                "execution_id": "execution-1",
                "type": "artifact",
                "artifact_type": "readback",
                "task": "safe task",
                "payload": {"status": "ok", "count": 1},
            },
        )

    def test_secret_named_artifact_is_rejected_without_payload(self) -> None:
        callback = self.make_callback()
        result = SimpleNamespace(
            _task=SimpleNamespace(get_name=lambda: "safe task"),
            _result={"msg": {"nested": {"access_token": "must-not-emit"}}},
        )
        callback.v2_runner_on_ok(result)
        event = emitted_event(callback)
        self.assertEqual(event["type"], "artifact_rejected")
        self.assertNotIn("payload", event)
        self.assertNotIn("must-not-emit", json.dumps(event))

    def test_unallowlisted_task_emits_nothing(self) -> None:
        callback = self.make_callback()
        result = SimpleNamespace(
            _task=SimpleNamespace(get_name=lambda: "other task"),
            _result={"msg": {"status": "ok"}},
        )
        callback.v2_runner_on_ok(result)
        callback._display.display.assert_not_called()

    def test_recap_is_sorted_and_counter_only(self) -> None:
        callback = self.make_callback()
        stats = SimpleNamespace(
            processed={"z-host": object(), "a-host": object()},
            summarize=lambda host: {
                "ok": 1 if host == "a-host" else 2,
                "changed": 0,
                "unreachable": 0,
                "failures": 0,
                "skipped": 0,
                "rescued": 0,
                "ignored": 0,
            },
        )
        callback.v2_playbook_on_stats(stats)
        event = emitted_event(callback)
        self.assertEqual(event["type"], "recap")
        self.assertEqual(list(event["hosts"]), ["a-host", "z-host"])
        self.assertEqual(
            set(event["hosts"]["a-host"]),
            {"ok", "changed", "unreachable", "failed", "skipped", "rescued", "ignored"},
        )


class ProvenanceBehaviorTests(unittest.TestCase):
    def test_tree_digest_is_stable_and_rejects_symbolic_links(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "payload.txt").write_text("payload\n", encoding="utf-8")
            first = PROVENANCE.tree_sha256(root)
            self.assertEqual(first, PROVENANCE.tree_sha256(root))
            (root / "link").symlink_to(root / "payload.txt")
            with self.assertRaisesRegex(RuntimeError, "symbolic link"):
                PROVENANCE.tree_sha256(root)

    def test_loader_contract_is_exact_and_sys_path_closed(self) -> None:
        expected = tuple(path.parent for path in PROVENANCE.SYSTEM_COLLECTION_ROOTS)
        with mock.patch.object(
            PROVENANCE.ansible_constants,
            "COLLECTIONS_PATHS",
            tuple(str(path) for path in expected),
        ), mock.patch.object(
            PROVENANCE.ansible_constants, "COLLECTIONS_SCAN_SYS_PATH", False
        ):
            self.assertEqual(
                PROVENANCE.effective_loader_contract(),
                {
                    "collection_paths": [str(path) for path in expected],
                    "scan_sys_path": False,
                },
            )
            PROVENANCE.ansible_constants.COLLECTIONS_SCAN_SYS_PATH = True
            with self.assertRaisesRegex(RuntimeError, "sys.path scanning"):
                PROVENANCE.effective_loader_contract()

    def test_unpinned_image_is_rejected_before_measurement(self) -> None:
        argv = [
            "runtime-collection-provenance.py",
            "--image-role",
            "toolbox",
            "--image",
            "image:tag",
        ]
        with mock.patch.object(sys, "argv", argv):
            with self.assertRaisesRegex(RuntimeError, "immutable digest"):
                PROVENANCE.main()


class ExecutionAnchorBehaviorTests(unittest.TestCase):
    def test_local_launcher_copy_fails_closed(self) -> None:
        launcher = ROOT / "ansible" / "scripts" / "governed-ansible-root-launcher"
        result = subprocess.run(
            [str(launcher)],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
        self.assertEqual(result.returncode, 126)
        self.assertIn("root-owned installed launcher", result.stderr)

    def test_real_product_policy_passes_generic_closed_schema(self) -> None:
        policy = json.loads(
            (ROOT / "policies" / "wunderbox" / "root-of-trust-policy.json").read_text(
                encoding="utf-8"
            )
        )
        RECORDER.validate_policy(policy)


if __name__ == "__main__":
    unittest.main()
