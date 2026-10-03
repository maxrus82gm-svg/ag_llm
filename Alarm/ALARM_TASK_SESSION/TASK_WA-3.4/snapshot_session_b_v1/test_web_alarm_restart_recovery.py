import hashlib
import json
import subprocess
import sys
import tempfile
import threading
import unittest
import urllib.request
from pathlib import Path

from web_alarm.operation_store import OperationStore
from web_alarm.server import WebAlarmApi, create_server
from web_alarm.state_machine import ServerStateMachine
from web_alarm.task_store import TaskStore
from web_alarm.workspace_registry import WorkspaceRegistry


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class RestartRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.storage = self.root / "state"
        self.project = self.root / "project"
        self.project.mkdir()
        self.target = self.project / "file.txt"
        self.before = b"before"
        self.target.write_bytes(self.before)

        workspace = WorkspaceRegistry(self.storage).register(
            "Project",
            self.project,
            workspace_id="ws_restart",
        )
        tasks = TaskStore(self.storage)
        self.task = tasks.create_task(
            workspace.workspace_id,
            "Restart Recovery",
            "RAW TASK",
            "Prove recovery survives Chat/Server restart.",
            task_id="task_restart",
        )
        self.micro = tasks.create_microtask(
            self.task.task_id,
            "M1",
            "Restart recovery",
            microtask_id="m1",
        )
        ServerStateMachine(self.storage).prepare_microtask(
            self.task.task_id,
            self.micro.microtask_id,
            [("file.txt", "edit")],
            operation_id="prepare_m1",
        )
        operations = OperationStore(self.storage)
        operations.begin(
            self.task.task_id,
            self.micro.microtask_id,
            "write",
            "file.txt",
            operation_id="op_write",
            expected_precondition_sha256=sha256(self.before),
            request_payload={"content": "after"},
        )
        operations.transition(
            self.task.task_id,
            "op_write",
            "STARTED",
        )
        operations.transition(
            self.task.task_id,
            "op_write",
            "UNKNOWN_AFTER_DISCONNECT",
        )
        self.repo_root = Path(__file__).resolve().parent

    def tearDown(self):
        self.tempdir.cleanup()

    @staticmethod
    def recovery_signature(pack):
        reconciliation = pack["RECONCILIATION"]
        return {
            "task_id": pack["TASK"]["task_id"],
            "current_microtask": pack["CURRENT_MICROTASK"],
            "current_status": pack["CURRENT_STATUS"],
            "snapshot_status": pack["SNAPSHOT_STATUS"],
            "last_operation": pack["LAST_OPERATION"],
            "next_safe_action": pack["NEXT_SAFE_ACTION"],
            "recovery_decision": reconciliation["DECISION"]["decision"],
            "reason_code": reconciliation["DECISION"]["reason_code"],
            "fingerprint": reconciliation["DECISION"]["evidence_fingerprint"],
        }

    def subprocess_http_json(self, url):
        script = (
            "import json,sys,urllib.request;"
            "r=urllib.request.urlopen(sys.argv[1],timeout=5);"
            "print(json.dumps(json.loads(r.read().decode('utf-8')),ensure_ascii=False))"
        )
        completed = subprocess.run(
            [sys.executable, "-B", "-c", script, url],
            cwd=self.repo_root,
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
        return json.loads(completed.stdout)

    def test_new_chat_process_reads_same_checkpoint_while_server_stays_alive(self):
        api = WebAlarmApi(self.storage)
        server = create_server(api, host="127.0.0.1", port=0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        host, port = server.server_address[:2]
        url = f"http://{host}:{port}/tasks/{self.task.task_id}/context"
        original = self.target.read_bytes()

        try:
            with urllib.request.urlopen(url, timeout=5) as response:
                baseline = json.loads(response.read().decode("utf-8"))

            new_chat = self.subprocess_http_json(url)

            self.assertEqual(
                self.recovery_signature(new_chat),
                self.recovery_signature(baseline),
            )
            self.assertEqual(
                new_chat["RECONCILIATION"],
                baseline["RECONCILIATION"],
            )
            self.assertEqual(self.target.read_bytes(), original)
            self.assertTrue(thread.is_alive())
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


if __name__ == "__main__":
    unittest.main()
