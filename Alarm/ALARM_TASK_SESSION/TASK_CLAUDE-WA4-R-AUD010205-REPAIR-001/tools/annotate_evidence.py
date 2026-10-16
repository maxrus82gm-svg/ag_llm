"""Add per-attempt source identity (repair files + new test) and the manually aborted full attempt to
evidence.json. Usage: annotate_evidence.py <evidence.json> <aborted attempt dir>"""
import hashlib
import json
import sys
from pathlib import Path

REPO = Path(r"M:\GitHub\ag_llm")
NAMES = ["web_alarm/event_checkpoint_store.py", "web_alarm/operation_store.py", "web_alarm/projection.py",
         "test_web_alarm_aud010205_repair.py"]
final = {n: hashlib.sha256((REPO / n).read_bytes()).hexdigest() for n in NAMES}
path, aborted = Path(sys.argv[1]), Path(sys.argv[2])
evidence = json.loads(path.read_text(encoding="utf-8"))
for attempt in evidence["attempts"]:
    results = json.loads((Path(attempt["temp_base"]) / "out" / "results.json").read_text(encoding="utf-8"))
    ident = {n: results["source_sha256"].get(n) for n in NAMES}
    attempt["repair_source_identity"] = ident
    attempt["on_final_repair_bytes"] = ident == final
stderr = (aborted / "stderr.txt").read_text(encoding="utf-8", errors="replace")
evidence["aborted_attempts"] = [{
    "label": "full (first)", "temp_base": str(aborted), "results_json": "ABSENT (stopped manually)",
    "ok_lines_before_stop": stderr.count(" ... ok"), "fail_or_error_lines": stderr.count(" ... FAIL") + stderr.count(" ... ERROR"),
    "reason": "stopped by the agent after the repair test file gained a test and raw U+2028/U+2029 characters in "
              "event_checkpoint_store.py were replaced by ASCII escapes (AST identical); superseded by full-final; NOT COUNTED",
}]
evidence["final_repair_bytes"] = final
path.write_text(json.dumps(evidence, ensure_ascii=False, indent=1, default=str) + "\n", encoding="utf-8", newline="\n")
for attempt in evidence["attempts"]:
    print(f"{attempt['label']:<18} final_bytes={attempt['on_final_repair_bytes']} "
          f"ecs={str(attempt['repair_source_identity']['web_alarm/event_checkpoint_store.py'])[:12]} "
          f"test={str(attempt['repair_source_identity']['test_web_alarm_aud010205_repair.py'])[:12]}")
print(evidence["aborted_attempts"][0]["ok_lines_before_stop"], evidence["aborted_attempts"][0]["fail_or_error_lines"])
