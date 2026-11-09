"""Read-only source/scope checks and exact test collection; no Git operations."""
from pathlib import Path
import difflib
import hashlib
import json
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
PACKAGE = Path(__file__).resolve().parent
baseline = json.loads((PACKAGE / "evidence/baseline.json").read_text(encoding="utf-8"))
modified = [name for name, expected in baseline["source_sha256"].items()
            if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != expected]
allowed = {"web_alarm/ultra_chat.py", "web_alarm/turn_service.py", "web_alarm/server.py",
           "Документация/000_Задачи Codex.md"}
assert set(modified) <= allowed, modified
run = json.loads((PACKAGE / "evidence/regression.result.json").read_text(encoding="utf-8"))
assert run["exit_code"] == 0
for name, expected in run["source_sha256"].items():
    assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected, name
names = run["command"][run["command"].index("unittest") + 1:]
suite = unittest.defaultTestLoader.loadTestsFromNames(names)

def collect(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from collect(item)
        else:
            yield item.id()

ids = list(collect(suite))
assert len(ids) == len(set(ids)) == 109
(PACKAGE / "evidence/collection.json").write_text(json.dumps(ids, indent=2) + "\n", encoding="utf-8")
changes = []
for name in ("web_alarm/ultra_chat.py", "web_alarm/turn_service.py", "web_alarm/server.py"):
    before = (PACKAGE / "before" / (name.replace("/", "__") + ".txt")).read_text(encoding="utf-8")
    after = (ROOT / name).read_text(encoding="utf-8")
    changes.extend(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
                                      fromfile="before/" + name, tofile=name))
(PACKAGE / "evidence/source_diff.txt").write_text("".join(changes), encoding="utf-8")
card = ROOT / "Документация/000_Задачи Codex.md"
before = (PACKAGE / "before/Документация__000_Задачи Codex.md.txt").read_bytes()
now = card.read_bytes()
marker = "# БЛОК 2".encode("utf-8")
assert before[before.index(marker):] == now[now.index(marker):]
launcher = {name: {"sha256": hashlib.sha256((ROOT / name).read_bytes()).hexdigest(),
                   "source": (ROOT / name).read_text(encoding="utf-8")}
            for name in ("Start_WebAlarm_Standard.cmd", "Start_WebAlarm_Test.cmd", "web_alarm/launch_test_config.json")}
(PACKAGE / "evidence/launcher_source.json").write_text(json.dumps(launcher, ensure_ascii=False, indent=2), encoding="utf-8")
result = {"source_scope": "PASS", "changed_existing": modified,
          "new_code": ["web_alarm/ordinary_chat_bridge.py", "test_web_alarm_ordinary_core_bridge.py"],
          "regression_source_pins": "PASS", "collection_count": len(ids),
          "card_blocks_2_to_4_unchanged": True, "git": "NOT USED",
          "launcher_validation": "SOURCE ONLY; real STANDARD/TEST launch NOT RUN",
          "ignore_check": "Root .gitignore has no matching new task exclusion; authoritative Git check deferred to user (Git forbidden)."}
(PACKAGE / "evidence/package_check.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(result, ensure_ascii=False))
