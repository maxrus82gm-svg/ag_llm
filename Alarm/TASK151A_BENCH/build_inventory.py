from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REQUIRED_STARTED = {
    "provider_attempt_id", "logical_call_id", "role", "mode",
    "request_context_schema_version", "request_blocks",
    "context_chars", "context_utf8_bytes", "context_token_estimate",
    "request_snapshot_sha256",
}


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_records(run_dir: Path):
    records = []
    for name in ("planner.jsonl", "executor.jsonl", "dredd.jsonl"):
        path = run_dir / name
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                records.append(json.loads(line))
    return records


rows = []
for summary_path in sorted(ROOT.glob("*/.ultra/audit/direct/*/summary.json")):
    run_dir = summary_path.parent
    profile = summary_path.parents[4].name
    summary = load_json(summary_path)
    task = load_json(run_dir / "task.json")
    records = load_records(run_dir)
    started = [r["payload"] for r in records if r.get("event") == "provider_attempt_started"]
    terminal = [r["payload"] for r in records if r.get("event") == "provider_attempt_terminal"]
    started_ids = [x.get("provider_attempt_id") for x in started]
    terminal_ids = [x.get("provider_attempt_id") for x in terminal]
    context_ok = all(REQUIRED_STARTED <= set(x) and isinstance(x.get("request_blocks"), list) for x in started)
    max_context = {}
    for item in started:
        role = item.get("role", "unknown")
        max_context[role] = max(max_context.get(role, 0), int(item.get("context_chars") or 0))
    usage = summary.get("usage", {}).get("total", {})
    rows.append({
        "profile": profile,
        "run_id": summary.get("run_id"),
        "status": summary.get("run_status"),
        "final_audit": summary.get("final_audit"),
        "api_requests": summary.get("api_requests"),
        "tool_calls": summary.get("tool_calls"),
        "provider_attempts_started": len(started),
        "provider_attempts_terminal": len(terminal),
        "attempt_identity_complete": sorted(started_ids) == sorted(terminal_ids),
        "context_accounting_complete": context_ok,
        "usage_complete": usage.get("complete"),
        "unknown_usage_calls": usage.get("unknown_usage_calls"),
        "total_tokens": usage.get("total_tokens"),
        "known_total_tokens": usage.get("known_total_tokens"),
        "max_context_chars_by_role": max_context,
        "raw_task": task.get("raw_task"),
    })

(ROOT / "benchmark_inventory.json").write_text(
    json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8"
)
lines = ["# TASK151A benchmark inventory", "", "| Profile | Run | Status / Audit | Attempts | Tools | Tokens | Accounting |",
         "|---|---|---|---:|---:|---:|---|"]
for r in rows:
    acct = f"id={'OK' if r['attempt_identity_complete'] else 'FAIL'}, ctx={'OK' if r['context_accounting_complete'] else 'FAIL'}, usage={r['usage_complete']}, unknown={r['unknown_usage_calls']}"
    lines.append(f"| {r['profile']} | {r['run_id']} | {r['status']} / {r['final_audit']} | {r['provider_attempts_started']}/{r['provider_attempts_terminal']} | {r['tool_calls']} | {r['total_tokens'] if r['total_tokens'] is not None else 'UNKNOWN'} | {acct} |")
lines += ["", "## Max context chars by role"]
for r in rows:
    lines.append(f"- {r['profile']} / {r['run_id']}: {r['max_context_chars_by_role']}")
(ROOT / "benchmark_inventory.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"RUNS={len(rows)}")
print(f"ALL_IDENTITY_OK={all(r['attempt_identity_complete'] for r in rows)}")
print(f"ALL_CONTEXT_OK={all(r['context_accounting_complete'] for r in rows)}")
