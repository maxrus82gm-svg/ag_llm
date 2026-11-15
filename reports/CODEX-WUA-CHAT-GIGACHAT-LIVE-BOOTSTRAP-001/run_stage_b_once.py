"""Single-use Stage B operator run for the explicit 15.11.2026 USER GO.

Only the existing Web Alarm server submits the one Turn. This script never
prints/saves credentials, local capability tokens, OAuth data, or bearer tokens.
"""
import http.client
import json
import os
from pathlib import Path
import secrets
import ssl
import sys
import threading
import time
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import context_storage as core
from gigachat_runtime import LiveApproval, ModelContract
from ultra_budget_ledger import BudgetLedger
from web_alarm.live_bootstrap import _verified_workspace, serve_one_inference
from web_alarm.server import WebAlarmApi
from web_alarm.ultra_chat import UltraChatService


HERE = Path(__file__).resolve().parent
EVIDENCE = HERE / "evidence"
ATTEMPT = EVIDENCE / "stage_b_attempt.json"
RESULT = EVIDENCE / "stage_b_result.json"
WA_ID = "ws_49c3d0f2e269471ab181bddf4db3c329"
WID = "ws_e6c65b696ee348ca83eda85e4f9606f6"
CHAT_ID = "chat_09c134a891a148ffa44b7963208120fa"
RELATIVE_ROOT = Path("WebAlarmWorkspace/live_bootstrap/probe_83e64481d2dd49fb8bcabea3a4206707")
TEXT = "Ответь одним словом: готово"
PORT = 8765


def http_json(method, path, body=None, headers=None, *, timeout=15):
    connection = http.client.HTTPConnection("127.0.0.1", PORT, timeout=timeout)
    try:
        wire = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
        connection.request(method, path, wire, {"Content-Type": "application/json", **(headers or {})})
        response = connection.getresponse()
        data = response.read()
        if not response.getheader("Content-Type", "").startswith("application/json"):
            return response.status, None
        return response.status, json.loads(data)
    finally:
        connection.close()


def safe_result(root, grant_id, *, result=None, page=None, latest=None, error=None):
    record_path = root / ".ultra" / "provider_sessions" / (grant_id + ".json")
    try:
        record = json.loads(record_path.read_text(encoding="utf-8"))
        counts = {key: record["counts"][key] for key in ("oauth", "catalog", "inference", "liability")}
        grant_state = record["state"]
    except (OSError, ValueError, KeyError, TypeError):
        counts, grant_state = None, "UNVERIFIED"
    try:
        ledger = BudgetLedger(root, WID).recover()
        ledger_summary = {"events": ledger.event_count, "attempts": len(ledger.attempts),
                          "states": [attempt.state for attempt in ledger.attempts]}
    except Exception:
        ledger_summary = {"state": "UNVERIFIED"}
    messages = page.get("messages", []) if type(page) is dict else []
    raw_verified = False
    if len(messages) == 2:
        try:
            raw_verified = all(core.load_raw_message(root, CHAT_ID, m["message_id"])["original_text"] == m["text"]
                               for m in messages)
        except Exception:
            pass
    output = {
        "status": "SUCCESS" if type(result) is dict and result.get("state") == "SUCCEEDED" and raw_verified
                    and counts is not None and counts.get("inference") == 1 else "STOPPED",
        "error_code": error,
        "grant_id": grant_id,
        "committed_call_counts": counts,
        "grant_state": grant_state,
        "turn_state": result.get("state") if type(result) is dict else None,
        "answer": result.get("answer") if type(result) is dict and result.get("state") == "SUCCEEDED" else None,
        "response_model": result.get("response_model") if type(result) is dict else None,
        "usage": result.get("usage") if type(result) is dict else None,
        "latest_turn_matches": type(latest) is dict and latest.get("turn") == result,
        "history_roles": [m.get("role") for m in messages],
        "history_text": [m.get("text") for m in messages] if type(result) is dict and result.get("state") == "SUCCEEDED" else None,
        "raw_verified": raw_verified,
        "usage_summary": page.get("usage_summary") if type(page) is dict else None,
        "ledger": ledger_summary,
        "authorization_material_saved": False,
    }
    RESULT.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output


def main():
    if ATTEMPT.exists():
        print(json.dumps({"status": "DENIED_ALREADY_ATTEMPTED"}), flush=True)
        return 2
    if os.getenv("GIGACHAT_SCOPE") != "GIGACHAT_API_PERS" or not os.getenv("GIGACHAT_CREDENTIALS"):
        print(json.dumps({"status": "DENIED_ENV_NOT_READY"}), flush=True)
        return 2
    api = WebAlarmApi()
    root, wid = _verified_workspace(api, WA_ID)
    if root != Path(os.environ["LOCALAPPDATA"]) / RELATIVE_ROOT or wid != WID:
        print(json.dumps({"status": "DENIED_WORKSPACE_MISMATCH"}), flush=True)
        return 2
    if BudgetLedger(root, wid).recover().event_count != 0:
        print(json.dumps({"status": "DENIED_LEDGER_NOT_EMPTY"}), flush=True)
        return 2
    if UltraChatService(api.registry).messages(WA_ID, CHAT_ID, None, 50)["messages"]:
        print(json.dumps({"status": "DENIED_CHAT_NOT_EMPTY"}), flush=True)
        return 2
    tls = ssl.create_default_context()
    if tls.verify_mode != ssl.CERT_REQUIRED or not tls.check_hostname or not tls.get_ca_certs():
        print(json.dumps({"status": "DENIED_TLS_NOT_READY"}), flush=True)
        return 2

    grant_id = "First" + secrets.token_hex(16)
    approval = LiveApproval(
        grant_id=grant_id,
        user_go="CODEX-WUA-CHAT-GIGACHAT-LIVE-BOOTSTRAP-001 / USER GO STAGE B 2026-11-15",
        independent_review="H38 OFFLINE suite 37 PASS; guarded S1 69 PASS; S2 73 PASS; amendment reviewed",
        account_id="existing-windows-gigachat-pers-account",
        scope="GIGACHAT_API_PERS",
        expires_at=time.time() + 180,
        contracts=(ModelContract(
            model_id="gigachat_2", context_tokens=128000, output_tokens=32,
            response_models=(), provider_output_cap_tokens=None,
            version_mode="DISCOVER_GIGACHAT_2",
            evidence="Official GigaChat-2 model docs: 128000 context; official chat API max_tokens definition; explicit USER GO STAGE B 2026-11-15 operator limit 32",),),
        max_oauth=1, max_catalog=1, max_inference=1,
        max_liability_tokens=1056, max_request_bytes=1024, max_answer_tokens=32,
    )
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    with ATTEMPT.open("x", encoding="utf-8") as handle:
        json.dump({"grant_id": grant_id, "status": "STARTED", "wa_workspace_id": WA_ID}, handle)
        handle.write("\n")

    server_errors = []
    def serve():
        try:
            serve_one_inference(api, WA_ID, approval, tls_context=tls, port=PORT)
        except Exception as exc:
            server_errors.append(type(exc).__name__)
    worker = threading.Thread(target=serve, daemon=False)
    worker.start()
    result = page = latest = None
    error = None
    try:
        capability = None
        for _ in range(120):
            if server_errors or not worker.is_alive():
                break
            try:
                status, candidate = http_json("GET", "/ui/ultra-chat/capability", timeout=2)
                if status == 200 and type(candidate) is dict and candidate.get("turn_test", {}).get("real_available"):
                    capability = candidate["turn_test"]
                    break
            except (OSError, ValueError, TypeError):
                pass
            time.sleep(0.25)
        if capability is None or not any(m.get("model_id") == "gigachat_2" and m.get("availability") == "AVAILABLE"
                                         for m in capability.get("models", [])):
            error = "catalog_or_server_unavailable"
        else:
            print(json.dumps({"status": "SERVER_READY", "port": PORT, "grant_id": grant_id}), flush=True)
            status, token_reply = http_json("GET", "/ui/ultra-chat/write-capability")
            if status != 200:
                raise RuntimeError("local_write_capability_unavailable")
            token = token_reply["ultra_chat_write"]
            write = {token["header"]: token["token"], "Origin": f"http://127.0.0.1:{PORT}"}
            status, token_reply = http_json("GET", "/ui/ultra-chat/capability")
            if status != 200:
                raise RuntimeError("local_read_capability_unavailable")
            token = token_reply["ultra_chat"]
            read = {token["header"]: token["token"]}
            base = f"/ultra/chat/workspaces/{WA_ID}/chats/{CHAT_ID}"
            status, selected = http_json("POST", base + "/model", {"model_ref": "gigachat_2"}, write)
            if status != 200 or selected.get("model_ref") != "gigachat_2":
                raise RuntimeError("model_selection_failed")
            body = {"idempotency_key": uuid4().hex, "model_ref": "gigachat_2", "text": TEXT}
            # THE ONLY LOCAL TURN POST. Its provider path is bounded by the grant.
            try:
                status, result = http_json("POST", base + "/turns", body, write, timeout=100)
            except Exception:
                error = "turn_post_outcome_unknown"
            else:
                if status != 200 or type(result) is not dict:
                    error = "turn_http_or_body_invalid"
            try:
                status, latest = http_json("GET", base + "/turns/latest", headers=read)
                if status != 200:
                    latest = None
                status, page = http_json("GET", base + "/messages?limit=50", headers=read)
                if status != 200:
                    page = None
            except Exception:
                error = error or "local_readback_failed"
    except Exception as exc:
        error = error or "exception_" + type(exc).__name__
    output = safe_result(root, grant_id, result=result, page=page, latest=latest, error=error)
    print(json.dumps({"status": output["status"], "turn_state": output["turn_state"],
                      "answer": output["answer"], "response_model": output["response_model"],
                      "counts": output["committed_call_counts"], "error_code": error}, ensure_ascii=False), flush=True)
    worker.join(timeout=max(1, approval.expires_at - time.time() + 5))
    output = safe_result(root, grant_id, result=result, page=page, latest=latest,
                         error=error or ("server_" + server_errors[0] if server_errors else None))
    return 0 if output["status"] == "SUCCESS" and output["grant_state"] == "CLOSED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
