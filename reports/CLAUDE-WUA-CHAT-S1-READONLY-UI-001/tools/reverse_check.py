"""Prove the change inventory without Git: undo exactly the edits this task describes and compare with stage 0.

For every changed file the listed inverse operations are applied to the current bytes in memory; the result must
have the stage-0 SHA-256 recorded in evidence/preflight_base.json (equal to the published base). If any other byte
had changed, the hash would differ. Nothing is written except the JSON record. CRLF files are handled as text with
their own line ending. Usage: reverse_check.py <out.json>
"""
import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
PREFLIGHT = Path(__file__).resolve().parents[1] / "evidence" / "preflight_base.json"
CUT = "cut"  # remove from the start marker up to and including the end marker
REPLACE = "replace"  # current text -> original text

OPERATIONS = {
    "context_storage.py": [
        (REPLACE, "import shutil\nimport stat\nimport uuid\nfrom dataclasses import dataclass\nfrom datetime",
         "import shutil\nimport uuid\nfrom datetime"),
        (CUT, "\n\n# ---------------------------------------------------------------------------\n"
              "# Bounded read-only access for the web shell", None),
    ],
    "web_alarm/server.py": [
        (REPLACE, "from .ui import INDEX_HTML\nfrom .ultra_chat import ULTRA_CHAT_CAPABILITY_PATH, UltraChatAccess, "
                  "UltraChatError, UltraChatService\n", "from .ui import INDEX_HTML\n"),
        (REPLACE,
         "    def _require_local_ui_origin(self, code: str, label: str) -> None:\n"
         "        # Shared by the folder picker and Ultra Chat: loopback peer and bind, one exact Host, and Origin /\n"
         "        # Sec-Fetch-Site only when they match it. Each capability keeps its own token check.\n"
         "        port = self.server.server_port\n",
         "    def _folder_picker_request(self, path: str) -> None:\n"
         "        # This capability is local UI transport, never a WebAlarmApi authority route.\n"
         "        port = self.server.server_port\n"),
        (REPLACE, "            raise ApiError(403, code, f'{label} requires its exact local origin')\n",
         "            raise ApiError(403, 'folder_picker_forbidden', 'Folder picker requires its exact local origin')\n"),
        (REPLACE,
         "            raise ApiError(403, code, 'Foreign or opaque origins are not allowed')\n\n"
         "    def _folder_picker_request(self, path: str) -> None:\n"
         "        # This capability is local UI transport, never a WebAlarmApi authority route.\n"
         "        self._require_local_ui_origin('folder_picker_forbidden', 'Folder picker')\n"
         "        origins = self.headers.get_all('Origin', [])\n",
         "            raise ApiError(403, 'folder_picker_forbidden', 'Foreign or opaque origins are not allowed')\n"),
        (CUT, "    def _ultra_chat_request(self, path: str) -> None:\n", "        self._send_json(200, payload)\n\n"),
        (REPLACE,
         "                self._folder_picker_request(path)\n                return\n"
         "            if path == ULTRA_CHAT_CAPABILITY_PATH or path == '/ultra/chat' or path.startswith('/ultra/chat/'):\n"
         "                self._ultra_chat_request(path)\n                return\n",
         "                self._folder_picker_request(path)\n                return\n"),
        (REPLACE, "    folder_picker_timeout: float = 120,\n    enable_ultra_chat: bool = True,\n",
         "    folder_picker_timeout: float = 120,\n"),
        (CUT, "    # Independent of the folder picker: own token, loopback only, off with --disable-ultra-chat.\n",
         "    server.web_alarm_ultra_chat = UltraChatService(api.registry)  # type: ignore[attr-defined]\n"),
        (CUT, "    parser.add_argument(\"--disable-ultra-chat\"", "the operator panel and EVM keep working\")\n"),
        (REPLACE, "            enable_ultra_chat=not args.disable_ultra_chat,\n", ""),
    ],
    "web_alarm/ui.py": [
        (CUT, "/* Ultra Chat (programme No.37 stage 1): read-only history of the shared Ultra core; the default view. */\n",
         ".chat-composer .row{justify-content:space-between;flex-wrap:nowrap}\n"),
        (CUT, "@media(max-width:850px){.chat-layout{", ".chat-composer .row{flex-wrap:wrap}}\n"),
        (REPLACE, '<a class="skip" id="skipLink" href="#chatMain">К истории диалога</a>',
         '<a class="skip" href="#main">К состоянию TASK</a>'),
        (REPLACE, '<button type="button" id="viewChat" aria-pressed="true" aria-controls="chatView" title="Сохранённые '
                  'диалоги Ultra, только чтение">Ultra Chat</button>\n<button type="button" id="viewOperator" '
                  'aria-pressed="false" aria-controls="layout">',
         '<button type="button" id="viewOperator" aria-pressed="true" aria-controls="layout">'),
        (REPLACE, 'aria-controls="workspacesPanel" hidden>', 'aria-controls="workspacesPanel">'),
        (REPLACE, 'aria-controls="tasksPanel" hidden>', 'aria-controls="tasksPanel">'),
        (CUT, '<section id="chatView" class="chat-view" aria-labelledby="chatHeading">\n', "</div>\n</section>\n"),
        (REPLACE, '<div class="layout" id="layout" hidden>', '<div class="layout" id="layout">'),
        (REPLACE, "const evm={epoch:0,busy:false,data:null,view:'chat'};", "const evm={epoch:0,busy:false,data:null,view:'operator'};"),
        (CUT, "// Three sections: Ultra Chat (default), the operator panel and EVM.", "function showView(name,initial=false){\n"),
        (CUT, "  if(!VIEWS[name])name='chat';evm.view=name;\n", "  if(!initial)$('main').focus()\n}\n"),
        (REPLACE, "function validEvm(data){",
         "function showView(name){\n"
         "  const isEvm=name==='evm';evm.view=isEvm?'evm':'operator';\n"
         "  $('layout').hidden=isEvm;$('evmView').hidden=!isEvm;\n"
         "  $('viewEvm').setAttribute('aria-pressed',String(isEvm));$('viewOperator').setAttribute('aria-pressed',String(!isEvm));\n"
         "  $('showWorkspaces').hidden=isEvm;$('showTasks').hidden=isEvm;\n"
         "  if(isEvm){$('evmHeading').focus();return loadEvm()}\n"
         "  $('main').focus()\n"
         "}\nfunction validEvm(data){"),
        (CUT, "// Ultra Chat (programme No.37 stage 1): saved dialogues of the shared Ultra core, read-only.",
         "$('chatComposer').onsubmit=e=>e.preventDefault();\n"),
        (REPLACE, "showView(initialView(),true);\nrefresh();", "refresh();"),
    ],
    "test_web_alarm_evm_ui.js": [
        (CUT, "test('E1 Ultra Chat is the default view;", "  assert.equal(h.el('viewEvm').getAttribute('aria-pressed'), 'false');\n});\n"),
        (REPLACE, "\n\ntest('E2 opening EVM",
         "\ntest('E1 the operator panel stays the default view and nothing is asked about connections at load', async () => {\n"
         "  const h = harness(); await settle();\n"
         "  assert.equal(h.evmCalls().length, 0);\n"
         "  assert.equal(h.el('evmView').hidden, true);\n"
         "  assert.equal(h.el('layout').hidden, false);\n"
         "  assert.equal(h.el('viewOperator').getAttribute('aria-pressed'), 'true');\n"
         "  assert.equal(h.el('viewEvm').getAttribute('aria-pressed'), 'false');\n"
         "});\n\ntest('E2 opening EVM"),
        (REPLACE,
         "  assert.equal(h.calls.filter(c => c.url === '/ultra/connections').length, 2);\n"
         "  const before = h.evmCalls().length;  // stage 1: the default Ultra Chat already read the chat badge at load\n",
         "  assert.equal(h.evmCalls().length, 2);\n"),
        (REPLACE, "  assert.equal(h.el('evmView').hidden, true);\n  assert.equal(h.el('chatView').hidden, true);\n"
                  "  assert.equal(h.el('viewOperator').getAttribute('aria-pressed'), 'true');\n  assert.equal(h.el('showWorkspaces').hidden, false);\n"
                  "  assert.equal(h.evmCalls().length, before, 'returning to the operator panel asked the /ultra/ API');\n",
         "  assert.equal(h.el('evmView').hidden, true);\n"
         "  assert.equal(h.el('viewOperator').getAttribute('aria-pressed'), 'true');\n  assert.equal(h.el('showWorkspaces').hidden, false);\n"
         "  assert.equal(h.evmCalls().length, 2, 'returning to the operator panel asked the connections API');\n"),
    ],
}


def undo(text: str, operations) -> tuple[str, list[str]]:
    problems = []
    for kind, first, second in operations:
        if kind == REPLACE:
            if text.count(first) != 1:
                problems.append(f"replace: expected one occurrence, found {text.count(first)}: {first[:50]!r}")
                continue
            text = text.replace(first, second)
        else:
            start = text.find(first)
            if start < 0 or text.count(first) != 1:
                problems.append(f"cut: start marker count {text.count(first)}: {first[:50]!r}")
                continue
            end = len(text) if second is None else text.find(second, start)
            if end < 0:
                problems.append(f"cut: end marker missing: {second[:50]!r}")
                continue
            text = text[:start] + text[end + (0 if second is None else len(second)):]
    if operations and operations[-1][0] == CUT and operations[-1][2] is None:
        pass
    return text, problems


preflight = json.loads(PREFLIGHT.read_text(encoding="utf-8"))["compared"]
results = {}
for rel, operations in OPERATIONS.items():
    raw = (REPO / rel).read_bytes()
    crlf = b"\r\n" in raw
    text = raw.decode("utf-8").replace("\r\n", "\n") if crlf else raw.decode("utf-8")
    original, problems = undo(text, operations)
    if rel == "context_storage.py":
        original += "\n" if not original.endswith("\n") else ""
    data = (original.replace("\n", "\r\n") if crlf else original).encode("utf-8")
    expected = preflight[rel]["stage0_sha256"]
    results[rel] = {"current_sha256": hashlib.sha256(raw).hexdigest(), "undone_sha256": hashlib.sha256(data).hexdigest(),
                    "stage0_sha256": expected, "inventory_complete": hashlib.sha256(data).hexdigest() == expected,
                    "operations": len(operations), "problems": problems}
record = {"task": "CLAUDE-WUA-CHAT-S1-READONLY-UI-001", "method": "inverse of the described edits applied in memory",
          "files": results, "all_complete": all(r["inventory_complete"] for r in results.values()), "git_used": False}
Path(sys.argv[1]).write_text(json.dumps(record, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
print(json.dumps({rel: (r["inventory_complete"], r["problems"]) for rel, r in results.items()}, ensure_ascii=False))
