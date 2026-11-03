"""Exercise the actual HTTP contract using disposable storage, without a browser."""
import json
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from test_web_alarm_ultra_chat_storage import Server, cs, new_id, snapshot


def run():
    with tempfile.TemporaryDirectory(prefix="wua_ui_workspace_") as tmp, patch(
        "web_alarm.folder_picker.subprocess.run", side_effect=AssertionError("folder picker not permitted")
    ):
        base = Path(tmp)
        root = base / "existing"
        root.mkdir()
        cs.ensure_workspace_storage(root)
        original = cs.create_chat(root, "Старый диалог")["chat_id"]
        raw = '<img src=x onerror="alert(1)"> Синтетическая история'
        cs.commit_raw_message(root, original, "msg_" + "1" * 32, "user", raw)
        before = snapshot(root)
        srv = Server(base / "server")
        try:
            status, _, body = srv.request("GET", "/")
            assert status == 200 and b'id="chatRegisterWorkspace"' in body and b'id="chatSend" disabled' in body
            assert srv.read("/ultra/chat/workspaces")[1]["workspaces"] == []
            status, _, body = srv.request("POST", "/workspaces",
                {"Origin": srv.origin, "Content-Type": "application/json"},
                body=json.dumps({"display_name": "Synthetic", "workspace_root": str(root)}).encode())
            assert status == 201, status
            wid = json.loads(body)["workspace"]["workspace_id"]
            assert snapshot(root) == before
            assert srv.read("/ultra/chat/workspaces")[1]["workspaces"][0]["history"] == "ok"
            url = f"/ultra/chat/workspaces/{wid}/chats"
            history = f"{url}/{original}/messages"
            assert srv.read(history)[1]["messages"][0]["text"] == raw
            assert snapshot(root) == before
            cid = new_id(9)
            data = {"chat_id": cid, "title": "Создан через HTTP"}
            assert srv.post(url, data)[0] == 201
            status, _, body = srv.post(url, data)
            assert status == 200 and json.loads(body)["created"] is False
            assert srv.post(f"{url}/{cid}/title", {"expected_title": data["title"], "title": "Переименован"})[0] == 200
            expected = {original: "Старый диалог", cid: "Переименован"}
            assert {c["chat_id"]: c["title"] for c in cs.list_existing_chats(root)} == expected
            assert cs.load_chat_messages(root, cid) == []
        finally:
            srv.stop()
        srv = Server(base / "server")
        try:
            assert {c["chat_id"]: c["title"] for c in srv.read(url)[1]["chats"]} == expected
            assert srv.read(history)[1]["messages"][0]["text"] == raw
        finally:
            srv.stop()
    return {"status": "PASS", "transport": "real loopback HTTP; new server instance on restart",
            "verified": ["served HTML", "existing Workspace registration via POST /workspaces",
                         "registration/read leave original files intact", "RAW roundtrip",
                         "create and idempotent repeat", "rename visible through common core",
                         "catalog and RAW persist on reopen"],
            "browser": "NOT RUN", "tk_gui": "NOT RUN", "llm_requests": 0}


if __name__ == "__main__":
    if sys.argv[1:] == ["--browser"]:
        with tempfile.TemporaryDirectory(prefix="wua_ui_browser_") as tmp, patch(
            "web_alarm.folder_picker.subprocess.run", side_effect=AssertionError("folder picker not permitted")
        ):
            base = Path(tmp)
            root = base / "existing"
            root.mkdir()
            cs.ensure_workspace_storage(root)
            original = cs.create_chat(root, "Старый синтетический диалог")["chat_id"]
            cs.commit_raw_message(root, original, "msg_" + "1" * 32, "user", "<b>Синтетическая история</b>")
            srv = Server(base / "server")
            try:
                srv.api.registry.register("Synthetic browser Workspace", root)
                print(srv.origin, flush=True)
                input()
                print(json.dumps({"titles": [c["title"] for c in cs.list_existing_chats(root)]}, ensure_ascii=True))
            finally:
                srv.stop()
    else:
        print(json.dumps(run(), ensure_ascii=True, indent=2))
