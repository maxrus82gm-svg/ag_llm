"""Tk contour of stage 2 and the ui_smoke_test of No.36.3, in isolated child processes (no real Workspace or state).

Every child gets LOCALAPPDATA / APPDATA / USERPROFILE / HOME and its working folder in a fresh TEMP folder, and checks
before importing the Tk shell that ui_state and the Tk runtime folder resolve there; otherwise it stops.
1. ui_smoke_test: the child code of server._agent_ui_smoke_test (UltraApp(), withdraw(), update_idletasks()), started
   as there with -E -B; the repository is put on sys.path explicitly because the working folder is TEMP.
2. Tk contour (matrix item 1): the real Tk handlers and the real web server of one synthetic Workspace -
   Tk creates the Workspace and its first chat (folder dialog answered by the script); the web creates and renames a
   chat over HTTP with the write capability; the Tk sidebar shows both; Tk renames the web chat; a Tk rename whose
   dialog was open while the web renamed the chat is refused and shown; Tk creates another chat that the web lists;
   a RAW saved by the shared writer is shown by the Tk chat view and by the web history. No LLM, no network.
Usage: tk_contour_check.py <out.json>
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(os.environ.get("S2_MIRROR") or Path(__file__).resolve().parents[3])  # a mutant mirror, or the working tree

ISOLATION = """
import os, sys
from pathlib import Path
base = Path(os.environ['S2_BASE']).resolve()
sys.path.insert(0, os.environ['S2_REPO'])
import ui_state
assert base in ui_state.STATE_DIR.parents, 'ui_state outside TEMP'
import ultra_ui
assert base in ultra_ui._RUNTIME_DIR.parents, 'Tk runtime outside TEMP'
"""

SMOKE = """
import ultra_ui
app = None
try:
    app = ultra_ui.UltraApp()
    app.withdraw()
    app.update_idletasks()
    print("OK: UltraApp constructed")
finally:
    if app is not None:
        app.destroy()
"""

CONTOUR = r"""
import http.client, json, threading
from unittest.mock import patch
import context_storage as cs
from web_alarm.server import WebAlarmApi, create_server

result = {}
ws = base / 'ws'
ws.mkdir()
api = WebAlarmApi(base / 'storage')
server = create_server(api, port=0)
threading.Thread(target=server.serve_forever, daemon=True).start()
host = f'127.0.0.1:{server.server_port}'

def call(method, path, body=None, headers=None):
    conn = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=20)
    raw = json.dumps(body, ensure_ascii=False).encode() if body is not None else None
    sent = {'Host': host, **(headers or {})}
    if raw is not None:
        sent.update({'Origin': 'http://' + host, 'Content-Type': 'application/json', 'Content-Length': str(len(raw))})
    conn.request(method, path, body=raw, headers=sent)
    response = conn.getresponse()
    data = json.loads(response.read())
    conn.close()
    return response.status, data

read_token = call('GET', '/ui/ultra-chat/capability')[1]['ultra_chat']['token']
write_token = call('GET', '/ui/ultra-chat/write-capability')[1]['ultra_chat_write']['token']
def web_titles(wa):
    data = call('GET', f'/ultra/chat/workspaces/{wa}/chats', headers={'X-WebAlarm-Ultra-Chat-Token': read_token})[1]
    return {c['chat_id']: c.get('title') for c in data['chats']}
def web_post(path, body):
    return call('POST', path, body, {'X-WebAlarm-Ultra-Chat-Write-Token': write_token})

import ultra_ui
errors = []
app = ultra_ui.UltraApp()
app.withdraw()
try:
    with patch.object(ultra_ui.filedialog, 'askdirectory', return_value=str(ws)), \
            patch.object(ultra_ui.messagebox, 'showerror', side_effect=lambda *a, **k: errors.append(a[-1] if a else '')):
        app._add_workspace_dialog()
    entry = next(e for e in app._workspace_registry if Path(e['path']).resolve() == ws.resolve())
    wid = entry['workspace_id']
    result['tk_created_workspace_and_first_chat'] = [c['title'] for c in cs.list_existing_chats(ws, expected_workspace_id=wid)] == ['Чат 1']
    wa = api.registry.register('Synthetic', ws).workspace_id
    web_chat = 'chat_' + 'ab' * 16
    status_create, created = web_post(f'/ultra/chat/workspaces/{wa}/chats', {'chat_id': web_chat, 'title': 'Создан в вебе'})
    status_rename, _ = web_post(f'/ultra/chat/workspaces/{wa}/chats/{web_chat}/title', {'title': 'Переименован в вебе', 'expected_title': 'Создан в вебе'})
    result['web_create_rename_status'] = [status_create, status_rename]

    def sidebar_labels():
        app._render_workspace_sidebar()
        app.update_idletasks()
        labels, stack = [], list(app.workspace_list_frame.winfo_children())
        while stack:
            widget = stack.pop()
            stack.extend(widget.winfo_children())
            if widget.winfo_class() == 'Label':
                labels.append(widget.cget('text').strip(' •'))
        return labels
    result['tk_sidebar_shows_web_chat'] = 'Переименован в вебе' in sidebar_labels()

    with patch.object(ultra_ui.simpledialog, 'askstring', return_value='Переименован в Tk'), \
            patch.object(ultra_ui.messagebox, 'showerror', side_effect=lambda *a, **k: errors.append(a[-1] if a else '')):
        app._rename_chat_ui(ws, web_chat, wid)
    result['web_sees_tk_rename'] = web_titles(wa).get(web_chat) == 'Переименован в Tk'

    def dialog_while_web_renames(*_a, **_k):
        web_post(f'/ultra/chat/workspaces/{wa}/chats/{web_chat}/title', {'title': 'Веб во время диалога', 'expected_title': 'Переименован в Tk'})
        return 'Tk поверх'
    shown = []
    with patch.object(ultra_ui.simpledialog, 'askstring', side_effect=dialog_while_web_renames), \
            patch.object(ultra_ui.messagebox, 'showerror', side_effect=lambda *a, **k: shown.append(a[-1] if a else '')):
        app._rename_chat_ui(ws, web_chat, wid)
    result['tk_stale_rename_refused_and_shown'] = bool(shown) and 'уже изменено' in shown[0]
    result['web_title_kept'] = web_titles(wa).get(web_chat) == 'Веб во время диалога'

    with patch.object(ultra_ui.messagebox, 'showerror', side_effect=lambda *a, **k: errors.append(a[-1] if a else '')):
        app._create_chat_for_workspace(ws, wid)
    titles = web_titles(wa)
    result['web_lists_tk_chat'] = sorted(titles.values()) == sorted(['Чат 1', 'Чат 2', 'Веб во время диалога'])

    text = 'Сохранено общим writer <b>RAW</b>'
    cs.commit_raw_message(ws, web_chat, 'msg_' + 'cd' * 16, 'user', text)
    app._activate_workspace(ws, preferred_chat_id=web_chat, workspace_id=wid)
    app.update_idletasks()
    result['tk_chat_view_shows_shared_raw'] = text in app.chat.get('1.0', 'end')
    history = call('GET', f'/ultra/chat/workspaces/{wa}/chats/{web_chat}/messages', headers={'X-WebAlarm-Ultra-Chat-Token': read_token})[1]
    result['web_history_shows_shared_raw'] = [m['text'] for m in history['messages']] == [text]
    result['unexpected_error_dialogs'] = len(errors)
finally:
    app.destroy()
    server.shutdown()
    server.server_close()
print(json.dumps(result, ensure_ascii=False))
"""


def run(code: str, extra_flags: list[str]) -> dict:
    base = Path(tempfile.mkdtemp(prefix="s2-tk-")).resolve()
    for name in ("localappdata", "appdata", "home", "cwd"):
        (base / name).mkdir()
    env = {k: v for k, v in os.environ.items() if not k.upper().startswith(("PYTHON", "GIT_"))}
    env.update(LOCALAPPDATA=str(base / "localappdata"), APPDATA=str(base / "appdata"), USERPROFILE=str(base / "home"),
               HOME=str(base / "home"), S2_BASE=str(base), S2_REPO=str(REPO), PYTHONIOENCODING="utf-8",
               PYTHONPYCACHEPREFIX=str(base / "pycache"))
    argv = [sys.executable, *extra_flags, "-B", "-c", ISOLATION + code]
    done = subprocess.run(argv, cwd=base / "cwd", env=env, capture_output=True, timeout=600)
    out = done.stdout.decode("utf-8", "replace").strip().splitlines()
    import shutil
    shutil.rmtree(base, ignore_errors=True)
    return {"exit": done.returncode, "last_line": out[-1] if out else "",
            "stderr_tail_lines": len(done.stderr.decode("utf-8", "replace").splitlines())}


def main():
    smoke = run(SMOKE, [])  # -E would drop the redirected PYTHONPYCACHEPREFIX; sys.path is set by the prelude
    contour = run(CONTOUR, [])
    checks = json.loads(contour["last_line"]) if contour["exit"] == 0 else {}
    record = {
        "task": "CLAUDE-WUA-CHAT-S2-SHARED-STORAGE-001",
        "ui_smoke_test": {"exit": smoke["exit"], "result": smoke["last_line"],
                          "isolation": "LOCALAPPDATA/APPDATA/USERPROFILE/HOME and cwd in TEMP; checked before import"},
        "tk_contour": {"exit": contour["exit"], "checks": checks},
        "passed": smoke["exit"] == 0 and smoke["last_line"] == "OK: UltraApp constructed" and contour["exit"] == 0
        and all(v is True for k, v in checks.items() if k not in {"web_create_rename_status", "unexpected_error_dialogs"})
        and checks.get("web_create_rename_status") == [201, 200] and checks.get("unexpected_error_dialogs") == 0,
        "network": "loopback web server of the child only; no LLM, no provider",
    }
    Path(sys.argv[1]).write_text(json.dumps(record, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"passed": record["passed"], "smoke": smoke["exit"], "contour": contour["exit"], **checks}, ensure_ascii=False))


if __name__ == "__main__":
    main()
