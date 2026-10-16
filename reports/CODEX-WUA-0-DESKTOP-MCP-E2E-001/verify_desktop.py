"""Validate a human-confirmed ordinary Desktop Chat run; never infer host from SDK metadata."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
EXPECTED_TASK = "synthetic_wua_desktop_001"
REQUIRED = {"ping", "list_capabilities", "read_synthetic_context"}


def digest(value):
    data = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def validate(proof, observed):
    checks = []

    def check(name, value):
        checks.append({"id": name, "PASS": bool(value)})

    check("human_confirmed_ordinary_desktop_chat", observed.get("ordinary_desktop_chat_confirmed_by_user") is True
          and observed.get("attestation_source") == "direct_human_reply_in_codex_chat")
    check("synthetic_task_id", proof.get("synthetic") is True and proof.get("task_id") == EXPECTED_TASK
          and observed.get("task_id") == EXPECTED_TASK)
    check("session_id", observed.get("session_id") == proof.get("session_id"))
    check("nonce", isinstance(proof.get("nonce"), str) and len(proof["nonce"]) == 32
          and observed.get("nonce") == proof.get("nonce"))
    expected = proof.get("expected_context_sha256")
    check("context_hash", expected == digest(proof.get("expected_context"))
          and observed.get("context_sha256") == expected)
    check("fixture_unchanged", proof.get("storage_unchanged") is True
          and proof.get("baseline_state_sha256") == proof.get("current_state_sha256"))
    check("no_production_or_models", proof.get("production_access") is False and proof.get("model_api_calls") == 0)
    events = proof.get("events", [])
    starts = {e.get("call_id"): e for e in events if e.get("kind") == "tool_started"}
    successes = [e for e in events if e.get("kind") == "tool_finished" and e.get("status") == "OK"]
    check("three_tools_in_server_receipts", REQUIRED <= {e.get("tool") for e in successes}
          and all(e.get("call_id") in starts for e in successes))
    peers = [e.get("peer_claim") or {} for e in starts.values()]
    check("not_the_local_sdk_regression", bool(peers) and all("SDK Regression" not in str(p.get("client_name", "")) for p in peers))
    # Client-supplied name is only a negative filter, never positive host attestation.
    check("protocol_recorded", bool(peers) and all(p.get("protocol_version") for p in peers))
    check("other_task_denied", observed.get("other_task_error") == "TASK_ID_DENIED"
          and any(e.get("kind") == "tool_finished" and e.get("tool") == "read_synthetic_context"
                  and e.get("status") == "REJECTED" and e.get("error") == "TASK_ID_DENIED" for e in events))
    check("only_get_http", all(e.get("method") == "GET" for e in events if e.get("kind") == "http"))
    guard = proof.get("guard_denials")
    check("normal_run_no_guard_violations", isinstance(guard, dict) and guard == {"network": 0, "file_write": 0, "subprocess": 0})
    return {"status": "PASS" if all(c["PASS"] for c in checks) else "PARTIAL / DESKTOP E2E NOT VERIFIED",
            "checks": checks, "basis": "direct human mode attestation + independent local server proof; peer name is untrusted",
            "independent_acceptance": "NOT CLAIMED"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--session-id", required=True)
    parser.add_argument("--observations", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if not re.fullmatch(r"[0-9a-f]{32}", args.session_id):
        raise SystemExit("INVALID_SESSION_ID")
    observations = args.observations.resolve()
    output = args.output.resolve()
    if not observations.is_relative_to(HERE) or not output.is_relative_to(HERE):
        raise SystemExit("OBSERVATIONS_AND_OUTPUT_MUST_BE_IN_TASK_FOLDER")
    if output.exists():
        raise SystemExit("Refusing to overwrite original Desktop evidence")
    path = HERE / "evidence" / args.session_id / "session.json"
    raw = path.read_bytes()
    result = validate(json.loads(raw), json.loads(observations.read_bytes()))
    if path.read_bytes() != raw:
        result["status"] = "PARTIAL / PROOF CHANGED DURING VALIDATION"
    result.update({"task_id": "CODEX-WUA-0-DESKTOP-MCP-E2E-001", "proof_path": str(path),
                   "proof_sha256": hashlib.sha256(raw).hexdigest(), "observations_path": str(observations)})
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": result["status"], "output": str(output)}, ensure_ascii=False))
    raise SystemExit(0 if result["status"] == "PASS" else 1)
