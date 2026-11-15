"""Single use Stage A operator script for the exact 15.11.2026 USER GO.

No credential, token, raw OAuth body or headers are written or printed.
An exclusive attempt marker makes a second invocation fail before networking.
"""
import json
import os
from pathlib import Path
import re
import secrets
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from gigachat_runtime import LiveApproval
from ordinary_chat_service import PreSendDenied
from web_alarm.live_bootstrap import _verified_workspace, catalog_probe
from web_alarm.server import WebAlarmApi


HERE = Path(__file__).resolve().parent
EVIDENCE = HERE / "evidence"
ATTEMPT = EVIDENCE / "stage_a_attempt.json"
RESULT = EVIDENCE / "stage_a_result.json"
WA_ID = "ws_49c3d0f2e269471ab181bddf4db3c329"
WID = "ws_e6c65b696ee348ca83eda85e4f9606f6"
RELATIVE_ROOT = Path("WebAlarmWorkspace/live_bootstrap/probe_83e64481d2dd49fb8bcabea3a4206707")


def main():
    if ATTEMPT.exists():
        print(json.dumps({"status": "DENIED_ALREADY_ATTEMPTED"}))
        return 2
    if os.getenv("GIGACHAT_SCOPE") != "GIGACHAT_API_PERS" or not os.getenv("GIGACHAT_CREDENTIALS"):
        print(json.dumps({"status": "DENIED_ENV_NOT_READY"}))
        return 2
    api = WebAlarmApi()
    root, wid = _verified_workspace(api, WA_ID)
    if root != Path(os.environ["LOCALAPPDATA"]) / RELATIVE_ROOT or wid != WID:
        print(json.dumps({"status": "DENIED_WORKSPACE_MISMATCH"}))
        return 2

    grant_id = "Probe" + secrets.token_hex(16)
    approval = LiveApproval(
        grant_id=grant_id,
        user_go="CODEX-WUA-CHAT-GIGACHAT-LIVE-BOOTSTRAP-001 / USER GO STAGE A 2026-11-15",
        independent_review="H38 independent OFFLINE review / Windows run 43722871919",
        account_id="existing-windows-gigachat-pers-account",
        scope="GIGACHAT_API_PERS",
        expires_at=time.time() + 300,
        contracts=(),
        max_oauth=1,
        max_catalog=1,
        max_inference=0,
        max_liability_tokens=1,
        max_answer_tokens=1,
    )
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    with ATTEMPT.open("x", encoding="utf-8") as handle:
        json.dump({"grant_id": grant_id, "status": "STARTED", "wa_workspace_id": WA_ID}, handle)
        handle.write("\n")

    status, models, error_code = "ERROR", [], None
    try:
        observed = catalog_probe(api, WA_ID, approval)
        models = sorted(m for m in observed if re.fullmatch(r"[A-Za-z0-9._:-]{1,128}", m))
        status = "PASS" if len(models) == len(observed) else "INVALID_MODEL_ID"
    except PreSendDenied as exc:
        error_code = str(exc) if re.fullmatch(r"[a-z0-9_]{1,80}", str(exc)) else "provider_denied"
    except Exception as exc:
        error_code = "exception_" + type(exc).__name__

    record_path = root / ".ultra" / "provider_sessions" / (grant_id + ".json")
    try:
        record = json.loads(record_path.read_text(encoding="utf-8"))
        counts = {k: record["counts"][k] for k in ("oauth", "catalog", "inference")}
        grant_state = record["state"]
    except (OSError, ValueError, KeyError, TypeError):
        counts, grant_state = None, "UNVERIFIED"
    result = {"status": status, "grant_id": grant_id, "scope": "GIGACHAT_API_PERS",
              "models": models, "error_code": error_code,
              "committed_call_counts": counts, "grant_state": grant_state,
              "raw_authorization_response_saved": False}
    RESULT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    return 0 if status == "PASS" and counts == {"oauth": 1, "catalog": 1, "inference": 0} \
        and grant_state == "CLOSED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
