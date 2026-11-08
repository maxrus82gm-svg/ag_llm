"""Documentation arithmetic only: AST literals and saved evidence, no runtime/test imports."""
import ast
from collections import Counter, defaultdict
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path

P = Path(__file__).resolve().parent
ROOT = P.parents[1]
E = P / "evidence"


def sha(raw): return hashlib.sha256(raw).hexdigest()
def write(path, value): path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def simple(node):
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "dict" and not node.args:
        assert all(k.arg is not None for k in node.keywords)
        return {k.arg: simple(k.value) for k in node.keywords}
    if isinstance(node, ast.Dict): return {simple(k): simple(v) for k, v in zip(node.keys, node.values)}
    return ast.literal_eval(node)


def constants(path):
    return {n.targets[0].id: n.value for n in ast.parse(path.read_text(encoding="utf-8")).body
            if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name)}


def main():
    test = ROOT / "test_rt002_s2_budget_policy.py"
    source = constants(test)
    rows, legacy, outputs = [simple(source[name]) for name in ("ROWS", "CANDIDATES", "ROUTE_MAX_TOKENS")]
    digest = sha(json.dumps([list(r) for r in rows], ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
    assert digest == simple(source["DATASET_SHA256"])
    route_roles = {"executor": "executor", "audit_diagnostic": "executor", "planner_session": "planner", "planner_direct": "planner",
        "verifier_final": "dredd", "verifier_permission": "dredd", "planner_review": "dredd", "compressor": "compressor", "mcp_chat": "mcp"}
    grouped = defaultdict(list)
    for r in rows:
        if type(r[6]) is int and r[6] + (r[7] or 0) > 0: grouped[(r[3], route_roles[r[2]])].append(r)
    stats = []
    for (model, role), group in sorted(grouped.items()):
        ratios = sorted(Fraction(r[4], r[6] + (r[7] or 0)) for r in group)
        floor = ratios[0]
        stats.append({"provider_model_id": model, "profile_key": role, "samples": len(group),
            "unknown_precached_samples": sum(r[7] is None for r in group),
            "min_bytes_per_processed_input": float(floor), "median_bytes_per_processed_input": float(ratios[len(ratios)//2]),
            "legacy_divisors": {str(m): math.floor(float(floor)/(1+m)*10000)/10000 for m in (0.0,0.1,0.2)},
            "ordinary_chat_samples": 0, "note": "S2 calibration denominator uses precached or 0; not an Ordinary Chat profile"})
    old_result = json.loads((ROOT / "reports/CODEX-RT002-B2-S2-ISOLATION-ORACLE-REPAIR-001/evidence/s2.result.json").read_text(encoding="utf-8"))
    historical = {key: old_result["observations"][key] for key in ("bytes_div_4", "leave_one_out", "candidate_blocks")}
    audit_rows = [r for r in rows if r[2] == "verifier_final"]
    audits = []
    dredd = next(s for s in stats if s["profile_key"] == "dredd")
    divisor = dredd["legacy_divisors"]["0.1"]
    for run in ("project/20261001_004240_a734f1", "project/20261001_004705_96dc2e"):
        r = next(r for r in audit_rows if r[0] == run)
        d = Fraction.from_float(divisor)
        estimate = -(-(r[4] * d.denominator)//d.numerator)
        audits.append({"run": "R-029" if "004240" in run else "R-030", "wire_bytes": r[4],
            "legacy_input_estimate": estimate, "output_reserve": outputs["verifier_final"], "liability_estimate": estimate+outputs["verifier_final"],
            "role": "dredd", "not_ordinary_chat": True})
    write(E / "calibration_facts.json", {"method": "AST extraction + arithmetic; no policy/test module execution",
        "source_sha256": sha(test.read_bytes()), "dataset_sha256": digest, "rows": len(rows),
        "known_prompt_rows": sum(type(r[6]) is int for r in rows), "run_locators": len({r[0] for r in rows}),
        "models_in_rows": dict(Counter(r[3] for r in rows)), "ordinary_chat_rows": 0, "groups": stats,
        "historical_author_observations_not_rerun": historical, "large_final_audits": audits,
        "legacy_candidates_NOT_DEFAULTS": legacy})

    candidates = {}
    for label, max_input, multiplier in [("A",16000,Fraction(1,2)),("B",32000,Fraction(1)),("C",64000,Fraction(2))]:
        old = legacy[label]
        output = int(outputs["verifier_final"] * multiplier)
        limits = {"max_request_bytes": old["max_request_bytes"]//4, "max_request_input_tokens_est": max_input,
            "max_output_tokens": output, "output_reserve": "EXACT_REQUEST_MAX_TOKENS", "max_session_liability_tokens": old["max_run_liability_tokens"]//2,
            "max_session_attempts": old["max_run_attempts"]//2}
        limits["max_workspace_ordinary_liability_tokens"] = limits["max_session_liability_tokens"]
        limits["max_workspace_ordinary_attempts"] = limits["max_session_attempts"]
        limits["max_inflight_per_chat"] = 1
        full = max_input + output
        scenarios = []
        for bpt in (1.0,2.4,4.1076):
            fraction = Fraction.from_float(bpt)
            estimate = -(-(limits["max_request_bytes"]*fraction.denominator)//fraction.numerator)
            effective = min(limits["max_request_bytes"], (max_input*fraction.numerator)//fraction.denominator)
            scenarios.append({"illustrative_divisor_NOT_PROFILE": bpt, "input_estimate_at_bytes_cap": estimate,
                "request_allowed_by_input_cap_alone": estimate <= max_input,
                "effective_wire_bytes_under_both_caps": effective})
        candidates[label] = {"name": {"A":"Консервативный","B":"Сбалансированный","C":"Исследовательский"}[label],
            "limits_proposed": limits, "status": "USER_DECISION_REQUIRED / UNCALIBRATED / NOT_ACTIVE",
            "numeric_origin": {"bytes": "legacy S2 candidate " + label + " max_request_bytes / 4; design downscale, not observed optimum",
                "input_tokens": "legacy A 48000 / 3" if label=="A" else "legacy B 96000 / 3" if label=="B" else "2 * proposed B 32000; below legacy C 200000/3",
                "output": str(multiplier) + " * existing verifier_final max_tokens 2048; UX hypothesis, no ordinary output evidence",
                "session_liability": "legacy " + label + " max_run_liability_tokens / 2; separate grant, no transfer from RUN reserve",
                "session_attempts": "legacy " + label + " max_run_attempts / 2; proposal only",
                "workspace": "same cap as session, shared across ALL Ordinary Chat sessions in this Workspace epoch; no new-chat multiplier",
                "inflight": "one outstanding physical call per Chat: serialization proposal, not benchmark-derived"},
            "confidence": "high arithmetic/provenance; low Ordinary Chat suitability; no production calibration",
            "illustrations_only": {"reserve_at_full_input_and_output": full,
                "worst_full_UNKNOWNs_fitting_session_liability": limits["max_session_liability_tokens"]//full,
                "typical_events_at_attempt_cap": 3*limits["max_session_attempts"],
                "sum_raw_wire_bytes_at_attempt_cap": limits["max_session_attempts"]*limits["max_request_bytes"],
                "divisor_scenarios": scenarios}}
    write(P / "policy_candidates.json", {"document_type": "NON_PRODUCTION_POLICY_PROPOSAL", "active": False, "user_approved": False,
        "approval_status": "PARTIAL DESIGN APPROVAL ONLY; numeric candidate PENDING",
        "approved_design_constraints": [{"id": "CHAT-A01", "topic": "workspace_ordinary_envelope_equals_selected_session_limits",
            "status": "USER APPROVED", "source": "chat_amendment_01.md", "implementation_authorized": False}],
        "task_id": P.name, "route_proposed": "ordinary_chat", "role_proposed": "ordinary_chat", "scope_proposed": "ORDINARY_CHAT_SESSION",
        "recommendation": "B for discussion; activation HOLD until approval and accepted implementation/calibration",
        "accepted_by_current_policy_schema": False, "price_or_currency_budget": None,
        "calibration_proposed": {"bytes_per_token": None, "ordinary_chat_samples_available": 0, "margin": 0.2, "min_samples": 20,
            "missing_profile": "DENY", "fallback": "NONE by default; HARD_BOUND only by separate explicit approval, conditional not guaranteed",
            "origin": "margin 0.2 tested by legacy S2 LOO; min_samples20 = 4 * legacy analysis5, a design choice not a confidence guarantee",
            "require_complete_cached_usage": True, "allow_legacy_role_profile_alias": False}, "candidates": candidates})
    print(json.dumps({"dataset_rows":len(rows),"ordinary_chat_rows":0,"groups":stats,"audits":audits,
        "candidate_caps":{k:v["limits_proposed"] for k,v in candidates.items()}},ensure_ascii=False,indent=2))


if __name__ == "__main__": main()
