"""Consistency check of this TASK's report package (read-only; does not import the checks it verifies).

json       manifest.json, runs/runs-map.json, runs/census.json and evidence.json are loaded strictly: a repeated
           object key is a problem (json.loads would silently keep the last value).
manifest   every listed file exists with the listed bytes / SHA-256 / EOL; no unlisted file; no CR byte anywhere
           (LF policy - a CRLF file can never match its published blob); the changed repository files match.
runs-map   every id is unique (also for fully identical records) and a safe relative path inside runs/ - an unsafe
           id is reported and never read; every published run file has a row with its SHA-256; every runs/ file
           (except the generated runs-map.json and census.json) has a row; with --private: each raw copy matches
           raw_sha256 and LF(sanitize(raw)) reproduces the published bytes exactly.
evidence   the final source hashes in evidence.json are the actual files; every "runs/..." path named in
           evidence.json or report.md exists; the run counts in evidence.json["finalize"]["runs"] equal census.json.
Exit 0 = consistent, 1 = problems (printed as counts with relative ids only).
--self-test copies the package into TEMP and injects one defect per copy; the manifest entries of the touched files
are re-hashed, so each defect must be reported by exactly its own check (no checksum side effect may stand in for
it); a clean copy must pass.
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
_UNSAFE = re.compile(r'[\\:*?"<>|\x00-\x1f]')
sha = lambda data: hashlib.sha256(data).hexdigest()


class DuplicateKey(ValueError):
    pass


def _pairs(items):
    keys = [key for key, _ in items]
    if len(keys) != len(set(keys)):
        raise DuplicateKey("repeated object key")
    return dict(items)


def load(path: Path, name: str, problems: Counter):
    """Strict JSON: a repeated key is reported; the lenient parse is then used so the other checks still run."""
    data = path.read_bytes()
    try:
        return json.loads(data, object_pairs_hook=_pairs)
    except DuplicateKey:
        problems[name + "-duplicate-key"] += 1
        return json.loads(data)


def safe_id(rel) -> bool:
    if not isinstance(rel, str) or not rel or rel.startswith("/") or _UNSAFE.search(rel):
        return False
    return all(part not in ("", ".", "..") for part in rel.split("/"))


def eol_of(data: bytes) -> str:
    crlf = data.count(b"\r\n")
    lf = data.count(b"\n") - crlf
    return "NONE" if not (crlf or lf) else "CRLF" if crlf and not lf else "LF" if lf and not crlf else "MIXED"


def check(task_dir: Path, private: Path | None) -> Counter:
    problems = Counter()
    manifest = load(task_dir / "manifest.json", "manifest", problems)
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

    runs_map = load(task_dir / "runs" / "runs-map.json", "runs-map", problems)
    ids = Counter(row.get("id") if isinstance(row, dict) else None for row in runs_map["files"])
    problems["runs-map-duplicate-id"] += sum(count - 1 for count in ids.values() if count > 1)
    rows = {}
    for row in runs_map["files"]:
        rel = row.get("id") if isinstance(row, dict) else None
        if not safe_id(rel):
            problems["runs-map-unsafe-id"] += 1
            continue
        rows.setdefault(rel, row)
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

    evidence = load(task_dir / "evidence.json", "evidence", problems)
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
    census = load(task_dir / "runs" / "census.json", "census", problems)["runs"]
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

    def write_json(path, doc):
        path.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")

    def rehash(task, rel):
        """Bring the manifest entry of a touched file up to date, as a careful forger would."""
        doc = json.loads((task / "manifest.json").read_bytes())
        data = (task / rel).read_bytes()
        doc["files"][rel].update(sha256=sha(data), bytes=len(data), eol=eol_of(data))
        write_json(task / "manifest.json", doc)

    def runs_map(task):
        return json.loads((task / "runs" / "runs-map.json").read_bytes())

    def save_runs_map(task, doc):
        write_json(task / "runs" / "runs-map.json", doc)
        rehash(task, "runs/runs-map.json")

    def edit_evidence(task, change):
        doc = json.loads((task / "evidence.json").read_bytes())
        change(doc)
        write_json(task / "evidence.json", doc)
        rehash(task, "evidence.json")

    def drop_row(task):
        doc = runs_map(task)
        doc["files"] = doc["files"][1:]
        save_runs_map(task, doc)

    def duplicate_identical(task):  # the independent verifier's finding: identical duplicate + re-hashed manifest
        doc = runs_map(task)
        doc["files"].append(dict(doc["files"][0]))
        save_runs_map(task, doc)

    def duplicate_different(task):  # same id, another (still valid) row content
        doc = runs_map(task)
        doc["files"].append(dict(doc["files"][1], id=doc["files"][0]["id"]))
        save_runs_map(task, doc)

    def unsafe_id(task):
        doc = runs_map(task)
        doc["files"].append(dict(doc["files"][0], id="../../outside.json"))
        save_runs_map(task, doc)

    def duplicate_manifest_key(task):
        path = task / "manifest.json"
        text = path.read_text(encoding="utf-8")
        rel = next(iter(json.loads(text)["files"]))
        stale = json.dumps({"bytes": 1, "sha256": "0" * 64, "eol": "LF"})
        path.write_text(text.replace('"files": {', '"files": {' + json.dumps(rel) + ": " + stale + ",", 1),
                        encoding="utf-8", newline="\n")

    def tamper_published(task):
        path = sorted(p for p in (task / "runs").rglob("*.json") if p.name not in GENERATED)[0]
        path.write_bytes(path.read_bytes() + b" ")
        rehash(task, path.relative_to(task).as_posix())

    def crlf(task):
        path = task / "scope.md"
        path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))
        rehash(task, "scope.md")

    def stale_evidence(task):
        edit_evidence(task, lambda doc: doc["source"].update(
            final_module_sha256="f1a98cc4b5c5f01f77fe9636d4517cb7d5d6b3804c06eef301400fdbb1c22cb9"))

    def census_claim(task):
        def change(doc):
            label = next(iter(doc["finalize"]["runs"]))
            doc["finalize"]["runs"][label]["tests_run"] += 1
        edit_evidence(task, change)

    def unlisted(task):
        (task / "stray.json").write_text("{}\n", encoding="utf-8", newline="\n")

    def missing_listed(task):
        (task / "block3-closeout.md").unlink()

    cases = {"drop-runs-map-row": (drop_row, "runs-map-incomplete"),
             "duplicate-runs-map-id-identical": (duplicate_identical, "runs-map-duplicate-id"),
             "duplicate-runs-map-id-different": (duplicate_different, "runs-map-duplicate-id"),
             "unsafe-runs-map-id": (unsafe_id, "runs-map-unsafe-id"),
             "duplicate-manifest-key": (duplicate_manifest_key, "manifest-duplicate-key"),
             "tampered-published-file": (tamper_published, "runs-map-published-mismatch"),
             "crlf-file": (crlf, "cr-in-file"), "stale-evidence-sha": (stale_evidence, "evidence-final-sha-mismatch"),
             "census-claim": (census_claim, "census-mismatch"), "unlisted-file": (unlisted, "manifest-incomplete"),
             "listed-file-missing": (missing_listed, "manifest-incomplete")}
    clean = check(fresh("clean"), private)
    outcome = {"clean": "PASS" if not clean else "FAIL:" + ",".join(sorted(clean))}
    for name, (damage, expected) in cases.items():
        task = fresh(name)
        damage(task)
        found = check(task, private)
        outcome[name] = "DETECTED" if set(found) == {expected} else "WRONG:" + ",".join(sorted(found))
    shutil.rmtree(base, ignore_errors=True)
    return outcome


args = sys.argv[1:]
private = Path(args[args.index("--private") + 1]) if "--private" in args else None
if "--self-test" in args:
    result = self_test(private)
    negatives = [k for k in result if k != "clean"]
    print(json.dumps(result | {"negative_scenarios": len(negatives),
                               "detected": sum(1 for k in negatives if result[k] == "DETECTED")}, indent=1))
    sys.exit(0 if result["clean"] == "PASS" and all(result[k] == "DETECTED" for k in negatives) else 1)
found = check(TASK_DIR, private)
print(json.dumps({"problems": dict(sorted(found.items())), "verdict": "CONSISTENT" if not found else "INCONSISTENT"},
                 indent=1))
sys.exit(0 if not found else 1)
