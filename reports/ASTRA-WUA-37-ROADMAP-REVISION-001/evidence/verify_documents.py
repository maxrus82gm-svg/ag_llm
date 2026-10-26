"""Bounded documentation verification; no application imports, subprocesses or network."""
from pathlib import Path
from collections import Counter
from urllib.parse import unquote
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "reports/ASTRA-WUA-37-ROADMAP-REVISION-001"
TARGET = "Документация/37_Старт перехода - Web Alarm Ultra.md"
BEFORE_SHA = "c86061e1ae1eb00be3e17e75bc3e1f33ce7d43517f0e789d281ae6a2cfbebade"
ANALYSIS_SHA = "7cf81d95be92924dd62a6eb1e623882dd2fa69359c9e31032c19a35ee185d3f5"
EXTS = {".py", ".js", ".md", ".json", ".toml", ".yaml", ".yml", ".bat", ".cmd", ".ps1", ".ini", ".cfg", ".txt"}
checks = []
def check(name, ok, detail):
    checks.append({"name": name, "pass": bool(ok), "detail": detail})
def sha(data):
    return hashlib.sha256(data).hexdigest()
def wiki(text):
    return re.findall(r"\[\[([^\]]+)\]\]", text)
def monitored():
    paths = [p for p in ROOT.iterdir() if p.is_file() and (p.suffix.lower() in EXTS or p.name == ".gitignore")]
    for folder in ["Документация", "web_alarm", ".github"]:
        base = ROOT / folder
        if base.exists():
            paths.extend(p for p in base.rglob("*") if p.is_file() and p.suffix.lower() in EXTS and not any(x in p.parts for x in ("__pycache__", ".obsidian")))
    return {p.relative_to(ROOT).as_posix() for p in paths}

baseline = json.loads((OUT / "evidence/baseline.json").read_text(encoding="utf-8"))["files"]
old_bytes = (OUT / "evidence/37_before.txt").read_bytes()
new_bytes = (ROOT / TARGET).read_bytes()
old = old_bytes.decode("utf-8-sig").replace("\r\n", "\n")
new = new_bytes.decode("utf-8")
rec = (OUT / "recommendations.md").read_text(encoding="utf-8")
check("01_original_recoverable_bytes", len(old_bytes) == 43112 and sha(old_bytes) == BEFORE_SHA, {"bytes": len(old_bytes), "sha256": sha(old_bytes)})
check("02_target_equals_candidate_snapshot", new_bytes == (OUT / "evidence/37_candidate.txt").read_bytes(), {"bytes": len(new_bytes), "sha256": sha(new_bytes)})
check("03_utf8_lf_and_no_replacement_char", not new_bytes.startswith(b"\xef\xbb\xbf") and b"\r" not in new_bytes and "\ufffd" not in new, "UTF-8 without BOM; LF")
check("04_frontmatter_preserved", old.split("---", 2)[1] == new.split("---", 2)[1], "graph_cluster and both aliases")
stages = re.findall(r"^### Этап (\d+)\.", new, re.M)
check("05_exact_eight_stages", stages == list("01234567"), stages)
history = re.findall(r"^\| (H\d\d),", new, re.M)
check("06_unique_history_ids", history == ["H%02d" % i for i in range(1, 24)], history)
check("07_decision_status_vocabulary", all(s in new for s in ["СОХРАНЕНО", "УТОЧНЕНО", "ЗАМЕНЕНО", "ПЕРЕНЕСЕНО", "ТРЕБУЕТ СОГЛАСОВАНИЯ"]), "Five required status labels present")
check("08_outgoing_wiki_multiset", Counter(wiki(old)) == Counter(wiki(new)), {"before": wiki(old), "after": wiki(new)})
missing = [link for link in wiki(new) if not (ROOT / "Документация" / (link.split("|")[0].split("#")[0] + ".md")).is_file()]
check("09_wiki_targets_exist", not missing, missing)
check("10_navigation_preserved", old.split("## Навигация", 1)[1].strip() == new.split("## Навигация", 1)[1].strip(), "Full navigation text compared after EOL normalization")

changed = []
missing_files = []
for name, record in baseline.items():
    p = ROOT / name
    if not p.is_file():
        missing_files.append(name)
    elif sha(p.read_bytes()) != record["sha256"]:
        changed.append(name)
check("11_only_allowed_baseline_target_changed", changed == [TARGET] and not missing_files, {"changed": changed, "missing": missing_files, "unchanged": len(baseline) - len(changed)})
extra = sorted(monitored() - set(baseline))
removed = sorted(set(baseline) - monitored())
check("12_no_new_or_removed_monitored_files", not extra and not removed, {"extra": extra, "removed": removed})
card = ROOT / "Документация/000_Задачи Codex.md"
check("13_task_card_unchanged", card.read_bytes() == (OUT / "evidence/task_card_at_start.txt").read_bytes(), sha(card.read_bytes()))
analysis = ROOT / "Документация/Дополнительная аналитика Астры.md"
check("14_accepted_analysis_pin_unchanged", sha(analysis.read_bytes()) == ANALYSIS_SHA, sha(analysis.read_bytes()))
names = {Path(TARGET).stem, "Web Alarm Ultra — старт перехода", "Старт нового Ultra Chat"}
incoming_selectors = []
for name in baseline:
    if not name.endswith(".md"):
        continue
    p = ROOT / name
    text = p.read_text(encoding="utf-8-sig")
    for lineno, line in enumerate(text.splitlines(), 1):
        for link in wiki(line):
            destination = link.split("|")[0]
            if destination.split("#")[0].removesuffix(".md").split("/")[-1] in names and "#" in destination:
                incoming_selectors.append({"file": name, "line": lineno, "link": destination})
        for target in re.findall(r"\]\(([^)]+)\)", line):
            decoded = unquote(target.strip("<>"))
            if "37_" in decoded and "#" in decoded:
                incoming_selectors.append({"file": name, "line": lineno, "markdown": decoded})
check("15_no_incoming_section_selectors_to_migrate", not incoming_selectors, incoming_selectors)
recommendation_ids = re.findall(r"^### (R\d\d)\.", rec, re.M)
check("16_eleven_recommendation_groups", recommendation_ids == ["R%02d" % i for i in range(1, 12)], recommendation_ids)
check("17_recommendations_have_reason_and_approval", rec.count("**Причина:**") == 11 and rec.count("**Утверждение:**") == 11, {"reasons": rec.count("**Причина:**"), "approval_fields": rec.count("**Утверждение:**")})
report_wiki = {}
for p in OUT.rglob("*.md"):
    links = wiki(p.read_text(encoding="utf-8"))
    if links:
        report_wiki[p.relative_to(OUT).as_posix()] = links
check("18_no_new_wiki_edges_from_reports", not report_wiki, report_wiki)
required_literal_locators = ["evidence/37_before.txt", "evidence/37_candidate.txt", "evidence/baseline.json", "recommendations.md"]
check("19_local_evidence_locators_exist", all((OUT / x).is_file() for x in required_literal_locators), required_literal_locators)
check("20_candidate_and_gate_statements_present", all(s in new for s in ["ПРОГРАММА-КАНДИДАТ", "ОЖИДАЕТ НЕЗАВИСИМОЙ ПРОВЕРКИ", "S13a + S6a", "V-13", "UNKNOWN", "DOC CLOSEOUT INCOMPLETE"]), "Presence check only; does not prove architectural correctness")
check("21_historical_numbering_map_present", all(s in new for s in ["| WUA-3 | **First Blueprint Node**", "| WUA-4 | **Codex Adapter**", "номера программы, не TASK ID"]), "Historical meaning preserved in explicit mapping")

result = {
    "task": "ASTRA-WUA-37-ROADMAP-REVISION-001",
    "kind": "LOCAL DOCUMENT MECHANICAL CHECKS; NOT INDEPENDENT OR RUNTIME TESTS",
    "pass": sum(x["pass"] for x in checks),
    "fail": sum(not x["pass"] for x in checks),
    "checks": checks,
    "scope": {"baseline_files": len(baseline), "outside_target_unchanged": len(baseline) - len(changed), "excluded": [".git", "live storage", ".venv", ".obsidian", "other reports", "unmonitored binary files"]},
}
(OUT / "evidence/verification.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"pass": result["pass"], "fail": result["fail"], "changed": changed, "unchanged": result["scope"]["outside_target_unchanged"], "failed_checks": [x["name"] for x in checks if not x["pass"]]}, ensure_ascii=True))
raise SystemExit(0 if result["fail"] == 0 else 1)

