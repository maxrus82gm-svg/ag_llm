"""Consistency check of this TASK's report package (read-only; does not import the checks it verifies).

manifest   every listed file exists with the listed bytes / SHA-256 / EOL; no unlisted file; no CR byte anywhere
           (LF policy - a CRLF file can never match its published blob); the changed repository files match.
runs-map   every published run file has a row with its SHA-256; every runs/ file (except the generated runs-map.json
           and census.json) has a row; with --private: each raw copy matches raw_sha256 and LF(sanitize(raw))
           reproduces the published bytes exactly.
evidence   the final source hashes in evidence.json are the actual files; every "runs/..." path named in
           evidence.json or report.md exists; the run counts in evidence.json["finalize"]["runs"] equal census.json.
Exit 0 = consistent, 1 = problems (printed as counts with relative ids only).
--self-test copies the package into TEMP, injects one defect per copy and requires each to be reported, and a
clean copy to pass.
Usage: check_package.py [--private <raw dir>] [--self-test]
"""
import hashlib
import json
import re
import shutil
import sys
import tempfile
from collections import Counter
from pathlib import Path

TASK_DIR = Path(__file__).resolve().parents[1]
REPO = Path(__file__).resolve().parents[4]
GENERATED = {"runs-map.json", "census.json"}
sha = lambda data: hashlib.sha256(data).hexdigest()


def eol_of(data: bytes) -> str:
    crlf = data.count(b"\r\n")
    lf = data.count(b"\n") - crlf
    return "NONE" if not (crlf or lf) else "CRLF" if crlf and not lf else "LF" if lf and not crlf else "MIXED"


def check(task_dir: Path, private: Path | None) -> Counter:
    problems = Counter()
    manifest = json.loads((task_dir / "manifest.json").read_bytes())
    for rel, e in manifest["files"].items():
        path = task_dir / rel
        if not path.is_file():
            problems["manifest-incomplete"] += 1
            continue
        data = path.read_bytes()
        if (sha(data), len(data), eol_of(data)) != (e["sha256"], e["bytes"], e["eol"]):
            problems["manifest-entry-mismatch"] += 1
    on_disk = {p.relative_to(task_dir).as_posix() for p in task_dir.rglob("*") if p.is_file()}
    if on_disk - set(manifest["files"]) - {"manifest.json"}:
        problems["manifest-incomplete"] += len(on_disk - set(manifest["files"]) - {"manifest.json"})
    problems["cr-in-file"] += sum(1 for rel in on_disk if b"\r" in (task_dir / rel).read_bytes())
    for rel, e in manifest.get("repository_files_changed", {}).items():
        if sha((REPO / rel).read_bytes()) != e["sha256"]:
            problems["repo-file-mismatch"] += 1

    runs_map = json.loads((task_dir / "runs" / "runs-map.json").read_bytes())
    rows = {row["id"]: row for row in runs_map["files"]}
    if private is not None:
        sys.path.insert(0, str(REPO))
        from web_alarm import evidence_sanitizer as es
        policy, identity = es.Policy(("ag_llm",)), es.identity_pattern(es.local_identity_tokens())
    for rel, row in rows.items():
        published = task_dir / "runs" / rel
        if row["published_sha256"] is not None:
            if not published.is_file() or sha(published.read_bytes()) != row["published_sha256"]:
                problems["runs-map-published-mismatch"] += 1
                continue
        if private is not None:
            raw_path = private / rel
            if not raw_path.is_file() or sha(raw_path.read_bytes()) != row["raw_sha256"]:
                problems["runs-map-raw-mismatch"] += 1
                continue
            result = es.process_bytes(rel, raw_path.read_bytes(), policy, identity)
            expected = result.output.replace(b"\r\n", b"\n") if result.output is not None else None
            if (expected is None) != (row["published_sha256"] is None) or \
                    (expected is not None and expected != published.read_bytes()):
                problems["runs-map-not-reproducible"] += 1
    runs_files = {p.relative_to(task_dir / "runs").as_posix() for p in (task_dir / "runs").rglob("*") if p.is_file()}
    unmapped = runs_files - GENERATED - {rel for rel, row in rows.items() if row["published_sha256"]}
    if unmapped:
        problems["runs-map-incomplete"] += len(unmapped)

    evidence = json.loads((task_dir / "evidence.json").read_bytes())
    actual = {rel: sha((REPO / rel).read_bytes())
              for rel in ("web_alarm/evidence_sanitizer.py", "test_web_alarm_evidence_sanitizer.py")}
    final = evidence["source"]
    if (final.get("final_module_sha256"), final.get("final_tests_sha256")) != \
            (actual["web_alarm/evidence_sanitizer.py"], actual["test_web_alarm_evidence_sanitizer.py"]):
        problems["evidence-final-sha-mismatch"] += 1
    text = (task_dir / "evidence.json").read_text(encoding="utf-8") + (task_dir / "report.md").read_text(encoding="utf-8")
    for ref in sorted(set(re.findall(r"runs/[A-Za-z0-9_./-]+\.(?:json|txt)", text))):
        if not (task_dir / ref).is_file():
            problems["dangling-reference"] += 1
    census = json.loads((task_dir / "runs" / "census.json").read_bytes())["runs"]
    for label, claim in evidence.get("finalize", {}).get("runs", {}).items():
        got = census.get(label)
        if got is None or got["tests_run"] != claim["tests_run"] or got["method_counts"] != claim["method_counts"] \
                or got["isolation_violations"] != claim["isolation"]:
            problems["census-mismatch"] += 1
    return +problems


def self_test(private: Path | None) -> dict:
    base = Path(tempfile.mkdtemp(prefix="claude-esrep-checkpkg-"))

    def fresh(name):
        target = base / name / TASK_DIR.name
        shutil.copytree(TASK_DIR, target)
        return target

    def first_run_file(task):
        return sorted(p for p in (task / "runs").rglob("*.json") if p.name not in GENERATED)[0]

    def drop_row(task):
        path = task / "runs" / "runs-map.json"
        doc = json.loads(path.read_bytes())
        doc["files"] = doc["files"][1:]
        path.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")

    def tamper_published(task):
        path = first_run_file(task)
        path.write_bytes(path.read_bytes() + b" ")

    def crlf(task):
        path = task / "scope.md"
        path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))

    def stale_evidence(task):
        path = task / "evidence.json"
        doc = json.loads(path.read_bytes())
        doc["source"]["final_module_sha256"] = "f1a98cc4b5c5f01f77fe9636d4517cb7d5d6b3804c06eef301400fdbb1c22cb9"
        path.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")

    def unlisted(task):
        (task / "runs" / "stray.json").write_text("{}\n", encoding="utf-8", newline="\n")

    def missing_listed(task):
        (task / "block3-closeout.md").unlink()

    def census_claim(task):
        path = task / "evidence.json"
        doc = json.loads(path.read_bytes())
        label = next(iter(doc["finalize"]["runs"]))
        doc["finalize"]["runs"][label]["tests_run"] += 1
        path.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")

    cases = {"drop-runs-map-row": (drop_row, "runs-map-incomplete"),
             "tampered-published-file": (tamper_published, "runs-map-published-mismatch"),
             "crlf-file": (crlf, "cr-in-file"), "stale-evidence-sha": (stale_evidence, "evidence-final-sha-mismatch"),
             "unlisted-file": (unlisted, "manifest-incomplete"), "listed-file-missing": (missing_listed,
                                                                                         "manifest-incomplete"),
             "census-claim": (census_claim, "census-mismatch")}
    outcome = {"clean": "PASS" if not check(fresh("clean"), private) else "FAIL"}
    for name, (damage, expected) in cases.items():
        task = fresh(name)
        damage(task)
        found = check(task, private)
        outcome[name] = "DETECTED" if expected in found else "MISSED:" + ",".join(sorted(found))
    shutil.rmtree(base, ignore_errors=True)
    return outcome


args = sys.argv[1:]
private = Path(args[args.index("--private") + 1]) if "--private" in args else None
if "--self-test" in args:
    result = self_test(private)
    print(json.dumps(result, indent=1))
    sys.exit(0 if result["clean"] == "PASS" and all(v == "DETECTED" for k, v in result.items() if k != "clean") else 1)
found = check(TASK_DIR, private)
print(json.dumps({"problems": dict(sorted(found.items())), "verdict": "CONSISTENT" if not found else "INCONSISTENT"},
                 indent=1))
sys.exit(0 if not found else 1)
