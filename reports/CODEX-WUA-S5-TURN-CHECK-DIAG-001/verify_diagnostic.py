"""Four bounded in-memory diagnostic probes plus syntax checks; no live sessions/storage writes.

Run from repo root: python -B -X utf8 reports/CODEX-WUA-S5-TURN-CHECK-DIAG-001/verify_diagnostic.py
Output is JSON on stdout. This is report evidence, not a new product test/implementation.
"""
import ast
import copy
import json
from pathlib import Path
import re
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from web_alarm import ultra_chat as chat


def main():
    records = []
    user = dict(message_id="msg_diag_user", role="user", created_at=1,
                text="S5_IN_MEMORY_UNANSWERED", task_block_id="block_diag")
    tasks = {"block_diag": {"runs": ["run_diag"]}}
    active = chat._classify([user], {"run_diag": {"run_status": "RUNNING"}}, tasks)
    assert len(active) == 1 and active[0]["outcome"] == "interrupted"
    records.append({"id": "D1", "result": "PASS", "observed": "RUNNING + no assistant is classified interrupted", "scope": "real classifier, synthetic in-memory data"})
    unknown = chat._classify([user], {"run_diag": {"run_status": "UNKNOWN"}}, tasks)
    assert len(unknown) == 1 and unknown[0]["outcome"] == "no_answer"
    records.append({"id": "D2", "result": "PASS", "observed": "UNKNOWN unanswered user is retained as no_answer", "scope": "classifier only; no assertion of real cancellation persistence"})

    completed_user = dict(message_id="msg_completed_user", role="user", text="COMPLETED_QUESTION")
    assistant = dict(message_id="msg_completed_assistant", role="assistant", text="COMPLETED_ANSWER",
                     producer={"kind": "offline_chat_fixture", "run_id": "run_completed"})
    history = {"excluded": {}, "messages": [completed_user, assistant, user]}
    original = copy.deepcopy(history)
    core = SimpleNamespace(read_chat_history_bounded=lambda root, chat_id: history)
    turn = {"state": "SUCCEEDED", "user_message_id": completed_user["message_id"],
            "assistant_message_id": assistant["message_id"]}
    turns = SimpleNamespace(get=lambda *args: turn)
    with patch.object(chat, "_core", return_value=core):
        context = chat.OfflineUltraChatService._context(None, "unused", "workspace", "chat_diag", turns)
    assert [m["content"] for m in context] == ["TEST offline chat chat_diag", "COMPLETED_QUESTION", "COMPLETED_ANSWER"]
    assert history == original
    records.append({"id": "D3", "result": "PASS", "observed": "completed pair included; later unanswered user omitted from next context; input history unchanged", "scope": "real context selector; core/turn reads replaced by in-memory stubs"})
    history = {"excluded": {}, "messages": [user]}
    with patch.object(chat, "_core", return_value=core):
        context = chat.OfflineUltraChatService._context(None, "unused", "workspace", "chat_diag", turns)
    assert context == [{"role": "system", "content": "TEST offline chat chat_diag"}]
    assert history["messages"] == [user]
    records.append({"id": "D4", "result": "PASS", "observed": "only unanswered RAW yields system-only context without modifying input history", "scope": "context projection only; no disk persistence tested"})

    source = (ROOT / "web_alarm/ui.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    html = next(ast.literal_eval(node.value) for node in tree.body if isinstance(node, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == "INDEX_HTML" for t in node.targets))
    assert '<button type="button" id="chatTurnCheck" title="Если ответ не появился или связь прервалась, проверьте состояние отправленного запроса.">Проверить состояние запроса</button>' in html
    scripts = re.findall(r"<script\b[^>]*>(.*?)</script\s*>", html, re.S | re.I)
    assert len(scripts) == 1
    result = subprocess.run(["node", "--check", "-"], input=scripts[0], text=True,
                            capture_output=True, encoding="utf-8", cwd=ROOT)
    assert result.returncode == 0, result.stderr
    version = subprocess.run(["node", "--version"], capture_output=True, text=True, check=True).stdout.strip()
    print(json.dumps({"status": "BOUNDED_DIAGNOSTIC_CHECKS_COMPLETE", "python": sys.version,
                      "node": version, "diagnostic_cases": records,
                      "counts": {"diagnostic_cases": 4, "passed": 4, "failed": 0},
                      "syntax": {"python_ast": "PASS", "inline_js_node_check": "PASS", "scripts": 1},
                      "prior_wording_present": True,
                      "not_run": ["browser replay", "real cancel/F5", "raw persistence test", "race proof", "full regression", "real providers"],
                      "product_verdict": "PARTIAL; successful probes do not imply product PASS"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
