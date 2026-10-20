"""Synthetic forensic sample for CLAUDE-WA4-R-TRANSPORT-TAIL-RECOVERY-001 (TEMP storage only, no live data).

Builds a synthetic storage root in TEMP, writes 3 transport events with the real store, simulates a process
death inside a 4th append (record cut without LF), then runs the real operator CLI:
`inspect` (dry run) and `apply` with the printed fingerprint. Copies the CLI outputs, the archive
(original.bin, tail.bin, plan.json, receipt.json) and the repaired log into forensic_sample/ with machine paths
replaced by <TEMP>, and writes verification.json with independent byte checks.
Usage: make_forensic_sample.py <python>
"""
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(r"M:\GitHub\ag_llm")
HERE = Path(__file__).resolve().parent.parent
OUT = HERE / "forensic_sample"
sys.path.insert(0, str(REPO))
from web_alarm.transport_event_store import TransportEventStore  # noqa: E402

sha = lambda data: hashlib.sha256(data).hexdigest()
if OUT.exists():
    raise SystemExit("refused: forensic_sample/ already exists (never overwritten)")
base = Path(tempfile.mkdtemp(prefix="wa_tailrec_sample_"))
root = base / "state"
temp_token = str(base)


def clean(text: str) -> str:
    for form in (temp_token, temp_token.replace("\\", "\\\\"), temp_token.replace("\\", "/")):
        text = text.replace(form, "<TEMP>")
    return text


try:
    store = TransportEventStore(root)
    for index, kind in enumerate(("REMOTE_ONLINE", "RESULT_DELIVERY_FAILED", "REMOTE_RECOVERED")):
        store.append(kind, event_id=f"sample-{index}", task_id="task_synthetic", payload={"note": "synthetic"})
    prefix = store.events_path.read_bytes()
    lost = (b'{"event_id":"sample-3","event_type":"PROCESS_RESTARTED","task_id":"task_synthetic",'
            b'"payload":{"note":"synthetic, cut by a simulated crash"')
    with store.events_path.open("ab") as handle:
        handle.write(lost)  # the process "died" inside this single write
    original = store.events_path.read_bytes()

    def cli(*args):
        proc = subprocess.run([sys.executable, "-B", "-m", "web_alarm.transport_event_recovery", *args],
                              cwd=REPO, capture_output=True, timeout=60)
        return proc.returncode, proc.stdout.decode("utf-8")

    inspect_code, inspect_out = cli("inspect", "--storage-root", str(root))
    plan = json.loads(inspect_out)
    apply_code, apply_out = cli("apply", "--storage-root", str(root), "--plan-fingerprint", plan["plan_fingerprint"],
                                "--reason", "synthetic sample: process died inside an append")
    receipt = json.loads(apply_out)
    repeat_code, repeat_out = cli("apply", "--storage-root", str(root), "--plan-fingerprint", plan["plan_fingerprint"],
                                  "--reason", "synthetic sample: repeated confirmation")
    attempt = root / Path(receipt["archive"]["original.bin"]["path"]).parent
    repaired = store.events_path.read_bytes()
    OUT.mkdir()
    (OUT / "transport_events.before.jsonl.bin").write_bytes(original)
    (OUT / "transport_events.after.jsonl").write_bytes(repaired)
    for name in ("original.bin", "tail.bin"):
        (OUT / f"archive_{name}").write_bytes((attempt / name).read_bytes())
    for name in ("plan.json", "receipt.json"):
        (OUT / f"archive_{name}").write_bytes(clean((attempt / name).read_text(encoding="ascii")).encode("ascii"))
    (OUT / "cli_inspect.json").write_text(clean(inspect_out), encoding="utf-8", newline="\n")
    (OUT / "cli_apply.json").write_text(clean(apply_out), encoding="utf-8", newline="\n")
    (OUT / "cli_apply_repeat.json").write_text(clean(repeat_out), encoding="utf-8", newline="\n")
    offset = plan["prefix"]["bytes"]
    checks = {
        "inspect_exit": inspect_code, "apply_exit": apply_code, "repeat_exit": repeat_code,
        "verdict": plan["verdict"], "tail_kind": plan["tail"]["kind"],
        "original_bytes_sha256": [len(original), sha(original)],
        "archive_original_equals_original": (attempt / "original.bin").read_bytes() == original,
        "archive_tail_equals_original_from_offset": (attempt / "tail.bin").read_bytes() == original[offset:],
        "tail_equals_lost_bytes": original[offset:] == lost,
        "repaired_equals_original_prefix": repaired == original[:offset] == prefix,
        "repaired_event_ids": [r.event_id for r in TransportEventStore(root).read_events()],
        "repeat_outcome": json.loads(repeat_out)["outcome"],
        "archive_files_readonly": sorted(p.name for p in attempt.iterdir() if not (p.stat().st_mode & 0o200)),
    }
    (OUT / "verification.json").write_text(json.dumps(checks, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(checks, indent=1))
finally:
    for path in base.rglob("*"):
        try:
            path.chmod(0o666)
        except OSError:
            pass
    shutil.rmtree(base, ignore_errors=True)
