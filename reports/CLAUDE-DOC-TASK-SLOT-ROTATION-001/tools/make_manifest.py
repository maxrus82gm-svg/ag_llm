"""Build manifest.json for CLAUDE-DOC-TASK-SLOT-ROTATION-001: project files created or changed by the task, proof that
the EVM package sources are unchanged, every package file and the publication scan (must exit 0).
Text files of the package must be LF without unsafe separators.
Usage: make_manifest.py
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[1]
REPO = PACKAGE.parents[1]
TASK = PACKAGE.name
PROJECT = {
    "tools/task_slot_rotate.py": ("NEW", "single rotation script for Claude/Codex cards: check, install-markers, rotate"),
    "tools/test_task_slot_rotate.py": ("NEW", "43 tests: valid cards (LF, CRLF, BOM, separators) and wrong pastes"),
    "Документация/000_Задачи Claude.md": ("CHANGED", "instruction paragraph (+6 lines), four slot markers, "
                                                     "first rotation BLOCK 1 -> BLOCK 1.1"),
    "Документация/000_Задачи Codex.md": ("CHANGED", "instruction paragraph (+6 lines), four slot markers; "
                                                    "its BLOCK 1 text untouched, no rotation"),
    "reports/CLAUDE-WUA-EVM-COMPACT-LAYOUT-001/handoff_task.md": ("NEW", "snapshot of the rotated task written by the script"),
}
sha = lambda data: hashlib.sha256(data).hexdigest()


def facts(path: Path) -> dict:
    data = path.read_bytes()
    eol = "CRLF" if b"\r\n" in data else ("LF" if b"\n" in data else "none")
    return {"bytes": len(data), "sha256": sha(data), "sha256_lf": sha(data.replace(b"\r\n", b"\n")), "eol": eol}


def main():
    problems = []
    project = {rel: {"kind": kind, "role": role, **facts(REPO / rel)} for rel, (kind, role) in PROJECT.items()}
    evm = json.loads((REPO / "reports/CLAUDE-WUA-EVM-COMPACT-LAYOUT-001/manifest.json").read_text(encoding="utf-8"))
    evm_sources = {}
    for rel, row in evm["changed_files"].items():
        data = (REPO / rel).read_bytes()
        lf = data.replace(b"\r\n", b"\n")
        evm_sources[rel] = row["sha256"] in {sha(data), sha(lf), sha(lf.replace(b"\n", b"\r\n"))}
    if not all(evm_sources.values()):
        problems.append("an EVM source file changed")
    rows = []
    for path in sorted(p for p in PACKAGE.rglob("*") if p.is_file() and p.name != "manifest.json"):
        data = path.read_bytes()
        rel = path.relative_to(PACKAGE).as_posix()
        if b"\r" in data:
            problems.append(f"CR in {rel}")
        if any(chr(code) in data.decode("utf-8") for code in (0x85, 0x2028, 0x2029)):
            problems.append(f"unsafe separator in {rel}")
        rows.append({"path": rel, **facts(path)})
    scans = {}
    for folder in (PACKAGE, REPO / "reports/CLAUDE-WUA-EVM-COMPACT-LAYOUT-001"):
        done = subprocess.run([sys.executable, "-B", "-m", "web_alarm.evidence_sanitizer", "--repo-anchor", "ag_llm", "scan",
                               str(folder)], cwd=REPO, capture_output=True, text=True, encoding="utf-8")
        scans[folder.name] = {"exit": done.returncode, "classes": json.loads(done.stdout)["classes"]}
        if done.returncode != 0:
            problems.append(f"scan exit {done.returncode} for {folder.name}")
    if problems:
        sys.exit("manifest refused: " + "; ".join(problems))
    evidence = {}
    for path in sorted((PACKAGE / "evidence").glob("*.json")):
        value = json.loads(path.read_text(encoding="utf-8"))
        keep = ("purpose", "exit", "tests_run", "pass", "fail", "errors", "skips", "mutants", "killed", "verdict", "state")
        evidence[path.name] = {k: value[k] for k in keep if k in value}
        if "protocol" in value:
            evidence[path.name]["result"] = value["protocol"].get("result")
    record = {"task": TASK, "executor": "Claude 008",
              "source": "coordinator's service assignment pasted by the user on 2026-10-29 (no TASK ID given; ID assigned by "
                        "the executor); rule №18 DOC-BLOCK1-SLOT-01@1 (#460)",
              "status": "RESULT READY / AWAITING INDEPENDENT VERIFICATION",
              "rotated_task": {"task_id": "CLAUDE-WUA-EVM-COMPACT-LAYOUT-001", "status": "SUBMITTED / REVIEW PENDING",
                               "independent_acceptance": "NOT DONE (EVM #457 is not accepted)"},
              "project_files": project, "evm_sources_unchanged": evm_sources,
              "not_changed": ["card BLOCKS 2-4", "№001 archives", "№18 and other shared documents", "Ultra Desktop card",
                              "Codex BLOCK 1 text", "Git (not used, not read)"],
              "evidence_summary": evidence, "publication_scans": scans,
              "git_used": False, "network_used": False, "files": rows}
    (PACKAGE / "manifest.json").write_text(json.dumps(record, ensure_ascii=False, indent=1) + "\n", encoding="utf-8",
                                           newline="\n")
    print(json.dumps({"package_files": len(rows), "scans": scans, "evm_sources_unchanged": all(evm_sources.values())}))


if __name__ == "__main__":
    main()
