"""Independent, read-only audit of the published R-006 package (no production imports, no Git, no network).

Does not reuse Codex verify_package.py logic: recomputes every hash from bytes, re-derives run counts from the
original results.json members inside evidence.zip, compares local source bytes with pinned SHA-256 (raw and
LF-normalised), and cross-checks checks.json / versions.json / manifest.json / raw-index.jsonl against each other.
"""
import hashlib
import json
import sys
import zipfile
from collections import Counter
from pathlib import Path

REPO = Path(r"M:\GitHub\ag_llm")
PKG = REPO / "reports" / "CODEX-WA4-R-006-WINDOWS-F1F2F3-LOCAL-GATE"
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else None


def sha(data):
    return hashlib.sha256(data).hexdigest()


def strict(data):
    def pairs(items):
        out = {}
        for k, v in items:
            if k in out:
                raise ValueError("duplicate key " + k)
            out[k] = v
        return out
    return json.loads(data, object_pairs_hook=pairs, parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def eol(data):
    crlf, lf = data.count(b"\r\n"), data.count(b"\n")
    return "NONE" if not lf else ("CRLF" if crlf == lf else ("LF" if not crlf else "MIXED"))


findings = []
report = {}

# 1. manifest: every published file, byte-exact (and LF-normalised fallback to classify transport only)
manifest_bytes = (PKG / "manifest.json").read_bytes()
manifest = strict(manifest_bytes)
report["manifest_sha256"] = sha(manifest_bytes)
report["manifest_bytes"] = len(manifest_bytes)
actual = sorted(p.relative_to(PKG).as_posix() for p in PKG.rglob("*") if p.is_file() and p.name != "manifest.json")
listed = sorted(manifest["files"])
report["manifest_listed"] = len(listed)
report["manifest_unlisted_local"] = sorted(set(actual) - set(listed))
report["manifest_missing_local"] = sorted(set(listed) - set(actual))
exact, lf_only, bad = 0, [], []
for name, pin in manifest["files"].items():
    path = PKG / name
    if not path.exists():
        continue
    data = path.read_bytes()
    if len(data) == pin["bytes"] and sha(data) == pin["sha256"]:
        exact += 1
    elif sha(data.replace(b"\r\n", b"\n")) == pin["sha256"] or sha(data.replace(b"\n", b"\r\n")) == pin["sha256"]:
        lf_only.append(name)
    else:
        bad.append(name)
report["manifest_exact"] = exact
report["manifest_eol_only_mismatch"] = lf_only
report["manifest_content_mismatch"] = bad
report["manifest_source_section"] = {k: v for k, v in manifest.items() if k != "files"}

# 2. evidence.zip byte-safe: whole-file pin, CRC of every member, inventory equality
prov = strict((PKG / "provenance.json").read_bytes())
checks = strict((PKG / "checks.json").read_bytes())
versions = strict((PKG / "versions.json").read_bytes())
zbytes = (PKG / "evidence.zip").read_bytes()
report["zip"] = {"bytes": len(zbytes), "sha256": sha(zbytes),
                 "pin_match": len(zbytes) == prov["archive"]["bytes"] and sha(zbytes) == prov["archive"]["sha256"]}
with zipfile.ZipFile(PKG / "evidence.zip") as zf:
    report["zip"]["testzip_first_bad"] = zf.testzip()
    names = zf.namelist()
    report["zip"]["members"] = len(names)
    report["zip"]["inventory_equal"] = names == [i["member"] for i in prov["archive"]["inventory"]]
    report["zip"]["dup_members"] = [n for n, c in Counter(names).items() if c > 1]
    report["zip"]["unsafe_names"] = [n for n in names if n.startswith("/") or ".." in n.split("/") or ":" in n]
    inv_bad = []
    for item in prov["archive"]["inventory"]:
        d = zf.read(item["member"])
        if len(d) != item["bytes"] or sha(d) != item["sha256"]:
            inv_bad.append(item["member"])
    report["zip"]["inventory_hash_mismatch"] = inv_bad
    report["zip"]["member_list"] = [(i.filename, i.file_size) for i in zf.infolist()]

    # 3. runs: recount from original results.json, not from checks.json
    runs = []
    for run in checks["runs"]:
        raw = zf.read(run["member"])
        res = strict(raw)
        tests = res["tests"]
        cnt = Counter(t["status"] for t in tests)
        ids = [t["test"] for t in tests]
        row = {"attempt": run["attempt"], "member_sha_ok": sha(raw) == run["member_sha256"],
               "tests_run": res["tests_run"], "len_tests": len(tests), "unique_ids": len(set(ids)),
               "PASS": cnt.get("PASS", 0), "FAIL": cnt.get("FAIL", 0), "ERROR": cnt.get("ERROR", 0),
               "SKIP": cnt.get("SKIP", 0), "other_status": sorted(set(cnt) - {"PASS", "FAIL", "ERROR", "SKIP"}),
               "result_keys": sorted(k for k in res if k != "tests"),
               "exit_in_result": res.get("exit", res.get("exit_code")),
               "claimed": [run["tests_run"], run["passed"], run["failures"], run["errors"], run["skips"], run["exit"]],
               "ids_match_checks": ids == run["test_ids"] or sorted(ids) == sorted(run["test_ids"]),
               "elapsed": res.get("elapsed_seconds"), "claimed_elapsed": run["elapsed_seconds"],
               "python": res.get("python"), "platform": res.get("platform")}
        row["counts_consistent"] = (row["PASS"] == run["passed"] and row["FAIL"] == run["failures"]
                                    and row["ERROR"] == run["errors"] and row["SKIP"] == run["skips"]
                                    and len(tests) == run["tests_run"] == res["tests_run"])
        if run["attempt"] == "full-release":
            report["full_release_skips"] = [(t["test"], t.get("message") or t.get("reason") or t.get("detail"))
                                            for t in tests if t["status"] == "SKIP"]
            report["full_release_by_module"] = Counter(t["test"].split(".")[0] for t in tests)
            full_ids = set(ids)
            full_status = {t["test"]: t["status"] for t in tests}
            report["full_test_record_keys"] = sorted(tests[0].keys())
        runs.append(row)
    report["runs"] = runs
    focused = checks["focused_within_full"]["test_ids"]
    report["focused"] = {"n": len(focused), "unique": len(set(focused)),
                         "all_in_full": all(i in full_ids for i in focused),
                         "all_pass_in_full": all(full_status.get(i) == "PASS" for i in focused),
                         "modules": Counter(i.split(".")[0] for i in focused)}

    # 4. RAW records equal to the pointed original test record
    entries = [strict(l) for l in (PKG / "raw-index.jsonl").read_bytes().splitlines() if l.strip()]
    raw_rows = []
    for e in entries:
        data = (PKG / e["file"]).read_bytes()
        val = strict(data)
        member = zf.read(e["member"])
        orig = strict(member)["tests"][int(e["pointer"].split("/")[-1])]
        raw_rows.append({"id": e["id"], "attempt": e.get("attempt"), "text_ok": sha(data) == e["text_sha256"],
                         "raw_equal": canonical(val["raw"]) == canonical(orig),
                         "canon_ok": sha(canonical(orig)) == e["canonical_record_sha256"],
                         "status": orig["status"], "claimed": e["original_status"],
                         "selector_ok": orig["test"] == e["selector"],
                         "origin_ok": val.get("origin") == {k: v for k, v in e.items()
                                                            if k not in ("text_bytes", "text_sha256")}})
    report["raw_records"] = len(raw_rows)
    report["raw_bad"] = [r for r in raw_rows if not all(r[k] for k in ("text_ok", "raw_equal", "canon_ok",
                                                                         "selector_ok", "origin_ok"))
                         or r["status"] != r["claimed"]]
    report["raw_status"] = Counter(r["status"] for r in raw_rows)

# 5. local source bytes vs pins (final full source map, 102 files)
pins_c = checks["final_full_source_sha256"]
pins_v = versions["final_full_source_sha256"]
report["source_pins_checks_eq_versions"] = pins_c == pins_v
src_exact, src_eol, src_bad, src_missing = [], [], [], []
for name, digest in sorted(pins_c.items()):
    path = REPO / name
    if not path.exists():
        src_missing.append(name)
        continue
    data = path.read_bytes()
    if sha(data) == digest:
        src_exact.append(name)
    elif sha(data.replace(b"\r\n", b"\n")) == digest or sha(data.replace(b"\n", b"\r\n")) == digest:
        src_eol.append((name, eol(data)))
    else:
        src_bad.append(name)
report["source"] = {"pinned": len(pins_c), "exact": len(src_exact), "eol_only": src_eol, "content_mismatch": src_bad,
                    "missing": src_missing}
key = ["web_alarm/task_store.py", "web_alarm/event_checkpoint_store.py", "web_alarm/operation_store.py",
       "test_web_alarm_wa4r006_local_gate.py"]
report["key_files"] = {k: {"pinned": pins_c.get(k), "local": sha((REPO / k).read_bytes()), "eol": eol((REPO / k).read_bytes())}
                       for k in key}
report["versions_changes"] = versions["changes"]
report["versions_meta"] = {k: versions[k] for k in ("supplied_github_baseline", "git_equivalence", "environment",
                                                     "frozen_card_sha256", "source_frozen_after_full")}
# web_alarm/*.py files that exist locally but are not in the pinned source map (unpinned code reachable by tests)
local_wa = sorted(p.relative_to(REPO).as_posix() for p in (REPO / "web_alarm").rglob("*.py") if "__pycache__" not in p.parts)
report["web_alarm_unpinned_local"] = [p for p in local_wa if p not in pins_c]
local_tests = sorted(p.name for p in REPO.glob("test_web_alarm*.py"))
report["web_alarm_tests_unpinned_local"] = [p for p in local_tests if p not in pins_c]

text = json.dumps(report, ensure_ascii=False, indent=1, default=str)
if OUT:
    OUT.write_text(text, encoding="utf-8", newline="\n")
print(text)
