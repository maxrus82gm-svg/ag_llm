"""Evidence for CLAUDE-WA4-R-CRASH-CONSISTENCY-REPAIR-001 (read-only over TEMP attempt outputs).

For every attempt: copies results.json and summary.json into runs/<label>/ with machine paths replaced
by placeholders (<TEMP>, <REPO>, <USER>) so the raw per-test outcomes can be published, keeps the
SHA-256 of the original and of the sanitized copy, and writes a per-method census plus the source map
check against source-final.json (the repaired bytes; mirror runs differ by design). Writes evidence.json.
Usage: collect_evidence.py <label>=<attempt base dir> [...]
"""
import hashlib
import json
import sys
import tempfile
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
TEMP = str(Path(tempfile.gettempdir()).resolve())
REPO = r"M:\GitHub\ag_llm"
HOME = str(Path.home())
SEP = {chr(code): chr(92) + "u" + format(code, "04x") for code in (0x85, 0x2028, 0x2029)}
gate = json.loads((HERE / "source-final.json").read_bytes())["source_sha256_all"]  # repaired bytes (Gate E)
sha = lambda data: hashlib.sha256(data).hexdigest()


def sanitize(text: str) -> str:
    for raw, token in ((TEMP, "<TEMP>"), (REPO, "<REPO>"), (HOME, "<USER>")):
        for form in (raw, raw.replace("\\", "\\\\"), raw.replace("\\", "/")):
            text = text.replace(form, token)
    return text.translate(str.maketrans(SEP))


attempts = []
for arg in sys.argv[1:]:
    label, base = arg.split("=", 1)
    base = Path(base)
    target = HERE / "runs" / label
    target.mkdir(parents=True, exist_ok=True)
    row = {"label": label}
    for name in ("results.json", "summary.json"):
        source = base / "out" / name if name == "results.json" else base / name
        raw = source.read_bytes()
        clean = sanitize(raw.decode("utf-8")).replace("\r\n", "\n")
        json.loads(clean)  # still valid JSON
        (target / name).write_bytes(clean.encode("utf-8"))
        row[name] = {"original_sha256": sha(raw), "published_sha256": sha(clean.encode("utf-8")),
                     "published_path": (target / name).relative_to(HERE).as_posix()}
    res = json.loads((base / "out" / "results.json").read_bytes())
    methods = {}
    for t in res["tests"]:
        methods.setdefault(t["test"].split(" [", 1)[0], set()).add(t["status"])
    row.update(
        tests_run=res["tests_run"], exit=json.loads((base / "summary.json").read_bytes())["exit"],
        elapsed_seconds=res.get("elapsed_seconds"), python=res.get("python"), platform=res.get("platform"),
        isolation_violations=len(res.get("isolation_violations", [])),
        method_status={m: ("PASS" if s <= {"PASS"} else "+".join(sorted(s))) for m, s in sorted(methods.items())},
        method_counts=dict(Counter("PASS" if s <= {"PASS"} else "+".join(sorted(s)) for s in methods.values())),
        source_map_files=len(res.get("source_sha256", {})),
        source_map_diff_vs_gate=sorted(k for k, v in res.get("source_sha256", {}).items()
                                       if k in gate and gate[k] != v),
    )
    attempts.append(row)
(HERE / "evidence.json").write_text(json.dumps({"task": "CLAUDE-WA4-R-CRASH-CONSISTENCY-REPAIR-001",
                                                "attempts": attempts}, ensure_ascii=False, indent=1) + "\n",
                                    encoding="utf-8", newline="\n")
for a in attempts:
    print(a["label"], a["exit"], a["tests_run"], a["method_counts"], "iso", a["isolation_violations"],
          "srcdiff", a["source_map_diff_vs_gate"], a["source_map_files"])
