"""Minimal secret-averse callback for governed execution evidence.

Only final per-host counters and explicitly allowlisted task ``msg`` payloads
are emitted.  Normal task results, arguments, facts, stdout and stderr are never
serialized by this callback.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any

from ansible.plugins.callback import CallbackBase


SECRET_KEY_RE = re.compile(
    r"(?i)(?:password|passphrase|token|secret|private[_-]?key|credential|"
    r"(?:api|access|auth|client|session)[_-]?key|recovery[_-]?key|unseal|"
    r"root[_-]?token)"
)


class CallbackModule(CallbackBase):
    CALLBACK_VERSION = 2.0
    CALLBACK_TYPE = "stdout"
    CALLBACK_NAME = "lit_governed_evidence"
    CALLBACK_NEEDS_WHITELIST = False

    def __init__(self) -> None:
        super().__init__()
        self._action_id = os.environ.get("LIT_GOVERNED_ACTION_ID", "")
        self._execution_id = os.environ.get("LIT_GOVERNED_EXECUTION_ID", "")
        raw_tasks = os.environ.get("LIT_GOVERNED_SAFE_TASKS", "[]")
        try:
            tasks = json.loads(raw_tasks)
        except json.JSONDecodeError:
            tasks = []
        if isinstance(tasks, dict):
            self._safe_tasks = {
                str(task): str(artifact_type)
                for task, artifact_type in tasks.items()
                if isinstance(task, str)
                and task.strip()
                and artifact_type in {"plan", "readback"}
            }
        else:
            self._safe_tasks = {}

    @staticmethod
    def _safe_payload(value: Any) -> bool:
        if isinstance(value, dict):
            return all(
                isinstance(key, str)
                and SECRET_KEY_RE.search(key) is None
                and CallbackModule._safe_payload(child)
                for key, child in value.items()
            )
        if isinstance(value, list):
            return all(CallbackModule._safe_payload(child) for child in value)
        return value is None or isinstance(value, (str, int, float, bool))

    def _emit(self, event: dict[str, Any]) -> None:
        event.update(
            {
                "schema_version": 1,
                "action_id": self._action_id,
                "execution_id": self._execution_id,
            }
        )
        self._display.display(
            "LIT_GOVERNED_EVENT="
            + json.dumps(event, sort_keys=True, separators=(",", ":"))
        )

    def v2_runner_on_ok(self, result: Any) -> None:
        task_name = result._task.get_name().strip()
        if task_name not in self._safe_tasks:
            return
        payload = result._result.get("msg")
        if not self._safe_payload(payload):
            self._emit(
                {
                    "type": "artifact_rejected",
                    "task": task_name,
                    "reason": "payload failed the secret-averse schema",
                }
            )
            return
        artifact_type = self._safe_tasks[task_name]
        self._emit(
            {
                "type": "artifact",
                "artifact_type": artifact_type,
                "task": task_name,
                "payload": payload,
            }
        )

    def v2_playbook_on_stats(self, stats: Any) -> None:
        hosts: dict[str, dict[str, int]] = {}
        for host in sorted(stats.processed):
            summary = stats.summarize(host)
            hosts[host] = {
                "ok": int(summary.get("ok", 0)),
                "changed": int(summary.get("changed", 0)),
                "unreachable": int(summary.get("unreachable", 0)),
                "failed": int(summary.get("failures", 0)),
                "skipped": int(summary.get("skipped", 0)),
                "rescued": int(summary.get("rescued", 0)),
                "ignored": int(summary.get("ignored", 0)),
            }
        self._emit({"type": "recap", "hosts": hosts})
