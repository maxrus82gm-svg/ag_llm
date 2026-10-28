"""TEST-QA for the compact EVM board: each mutant weakens one new rule in a disposable TEMP mirror of the code; the
tests must kill it. The unmodified mirror is the control and must pass every target.

Mirror = top-level *.py and *.js plus web_alarm/*.py of the working tree (no Git metadata, no data). Python targets
run through run_gate.py with CLAUDE_RUNNER_ROOT pointing at the mirror (guarded runner, TEMP isolation); JS targets
run with node --test inside the mirror. Only names, verdicts and counters are published.
Usage: run_mutants.py <absolute python> <out.json> [mutant-name ...]
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
REPO = TOOLS.parents[2]
GATE = REPO / "Alarm" / "ALARM_TASK_SESSION" / "TASK_CLAUDE-WA4-R-AUD010205-REPAIR-001" / "tools" / "run_gate.py"
MC, UI = "web_alarm/model_cards.py", "web_alarm/ui.py"
PY, JS = ("py", ("test_web_alarm_model_cards",)), ("js", ("test_web_alarm_evm_ui.js",))

MUTANTS = {
    # server: order and favourites
    "V01 absent entries dropped on save": (MC, [("            stored[section] = list(order) + [x for x in stored[section] if x not in visible and x not in order]",
                                                  "            stored[section] = list(order)")], PY),
    "V02 incomplete column order accepted": (MC, [(" or (section != \"favorites\" and set(order) != visible):", ":")], PY),
    "V03 column kind not checked": (MC, [("        if section != \"favorites\" and any(x.split(\":\", 1)[0] != BOARD_COLUMNS[section][1] for x in order):",
                                          "        if False:")], PY),
    "V04 board revision not compared": (MC, [("            if body.get(\"base_revision\") != current[\"revision\"]:\n"
                                              "                raise SettingsConflictError(\"the board arrangement changed",
                                              "            if False:\n                raise SettingsConflictError(\"the board arrangement changed")], PY),
    "V05 damaged board file overwritten, not kept": (MC, [("                self._set_aside(self.view_path)\n", "                pass\n")], PY),
    "V06 repeated ids in the stored board accepted": (MC, [(" or len(set(map(str, ids))) != len(ids)", "")], PY),
    "V07 new entries not appended": (MC, [("            sections[section] = kept + [x for x in present[section] if x not in kept]",
                                           "            sections[section] = kept")], PY),
    "V08 favourites of absent entries shown": (MC, [("        sections[\"favorites\"] = [x for x in stored[\"stored\"][\"favorites\"] if x in everywhere]",
                                                     "        sections[\"favorites\"] = list(stored[\"stored\"][\"favorites\"])")], PY),
    # page: board, floating card, order, favourites, description, chat picker
    "U10 hover opens at once": (UI, [("evm.peekTimer=setTimeout(()=>openPeek(id,section,false),PEEK_OPEN_MS)", "openPeek(id,section,false)")], JS),
    "U11 hover replaces a pinned card": (UI, [("  if(same||evm.peek.pinned)return;", "  if(same)return;")], JS),
    "U12 leaving closes a pinned card": (UI, [("if(evm.peek.id&&!evm.peek.pinned)evm.peekTimer=", "if(evm.peek.id)evm.peekTimer=")], JS),
    "U13 the star opens the card": (UI, [("star.onclick=ev=>{ev?.stopPropagation?.();toggleFavorite(id)}", "star.onclick=ev=>{toggleFavorite(id)}")], JS),
    "U14 a drag from the star moves the card": (UI, [("const fromStar=evm.pressOnButton;", "const fromStar=false;")], JS),
    "U15 a card dropped into another column": (UI, [("  if(!evm.drag||evm.drag.section!==section||evm.drag.id===id)return;", "  if(!evm.drag||evm.drag.id===id)return;")], JS),
    "U16 a refused order kept locally": (UI, [("    evm.viewSaving=false;evm.cards.view=before;evm.peekFocus=null;\n    await loadEvm();\n",
                                               "    evm.viewSaving=false;evm.peekFocus=null;\n")], JS),
    "U17 the card measured while hidden": (UI, [("  const box=$('evmPeek');box.hidden=false;  // visible first: the position needs the real height\n  fillPeek();\n",
                                                 "  fillPeek();\n  const box=$('evmPeek');box.hidden=false;\n")], JS),
    "U18 the card placed under the sticky header": (UI, [("top=Math.max(minTop,Math.min(r.top-6,vh-h-12))", "top=Math.max(12,Math.min(r.top-6,vh-h-12))")], JS),
    "U19 «Изменить описание» opens the connection tab": (UI, [("  if(tab)evm.tab=tab;\n", "")], JS),
    "U20 the picker reads the model list at load": (UI, [("    text('chatModelPick',(s.state==='SAVED'", "    api('/ultra/connections');text('chatModelPick',(s.state==='SAVED'")], JS),
    "U21 the picker sends the chat token": (UI, [("api('/ultra/connections/selection',{method:'POST',body:{role:'chat',connection_id:id}});\n    if(r?.selection?.state!=='SAVED'||r.selection.connection_id!==id)throw new Error('Сервер не подтвердил сохранение выбора');\n    closePicker(true)",
                                                  "api('/ultra/connections/selection',{method:'POST',body:{role:'chat',connection_id:id},headers:{'X-WebAlarm-Ultra-Chat-Token':String(chat.token)}});\n    if(r?.selection?.state!=='SAVED'||r.selection.connection_id!==id)throw new Error('Сервер не подтвердил сохранение выбора');\n    closePicker(true)")], JS),
    "U22 the star nested in the card button": (UI, [("  open.append(body);el.append(grip,open,star);", "  open.append(body,star);el.append(grip,open);")], JS),
}


def mirror(edits, file_name) -> Path:
    dest = Path(tempfile.mkdtemp(prefix="claude-evmcompact-mirror-"))
    for path in list(REPO.glob("*.py")) + list(REPO.glob("*.js")):
        shutil.copy2(path, dest / path.name)
    (dest / "web_alarm").mkdir()
    for path in (REPO / "web_alarm").glob("*.py"):
        shutil.copy2(path, dest / "web_alarm" / path.name)
    if file_name:
        target = dest / file_name
        raw = target.read_bytes()
        crlf = b"\r\n" in raw
        text = raw.decode("utf-8").replace("\r\n", "\n") if crlf else raw.decode("utf-8")
        for old, new in edits:
            if text.count(old) != 1:
                shutil.rmtree(dest)
                sys.exit(f"pattern occurs {text.count(old)} times in {file_name}: {old[:60]!r}")
            text = text.replace(old, new)
        target.write_bytes((text.replace("\n", "\r\n") if crlf else text).encode("utf-8"))
    return dest


def run(python, dest, kind, targets):
    if kind == "js":
        done = subprocess.run(["node", "--test", *targets], cwd=dest, capture_output=True, text=True, encoding="utf-8")
        failed = sorted({line.split(" - ", 1)[1].split(" ")[0] for line in done.stdout.splitlines() if line.startswith("not ok")})
        return done.returncode, failed, None
    env = dict(os.environ, CLAUDE_RUN_PREFIX="claude-evmcompact", CLAUDE_TASK_LABEL="CLAUDE-WUA-EVM-COMPACT-LAYOUT-001",
               CLAUDE_RUNNER_ROOT=str(dest), PYTHONIOENCODING="utf-8")
    env.pop("CLAUDE_EXTRA_PATH", None)
    done = subprocess.run([python, str(GATE), python, "mutant", *targets], cwd=dest, env=env, capture_output=True,
                          text=True, encoding="utf-8", errors="replace", timeout=900)
    summary = json.loads(done.stdout)
    failed = sorted({t[0].split(".")[-1].split(" ")[0] for t in summary.get("non_pass", []) if t[1] != "SKIP"})
    return summary["exit"], failed, summary.get("isolation_violations")


python, target = sys.argv[1], Path(sys.argv[2])
chosen = sys.argv[3:] or list(MUTANTS)
for name in chosen:  # every pattern must occur exactly once before anything runs
    file_name, edits, _ = MUTANTS[name]
    text = (REPO / file_name).read_bytes().decode("utf-8").replace("\r\n", "\n")
    for old, _new in edits:
        if text.count(old) != 1:
            sys.exit(f"{name}: pattern occurs {text.count(old)} times")
rows, controls = [], {}
for kind, targets in (PY, JS):
    dest = mirror([], None)
    try:
        code, failed, isolation = run(python, dest, kind, targets)
    finally:
        shutil.rmtree(dest, ignore_errors=True)
    controls[" ".join(targets)] = {"exit": code, "failing": failed, "isolation_violations": isolation,
                                   "verdict": "PASS" if code == 0 and not failed else "FAIL"}
    print(json.dumps({"control": targets, "verdict": controls[" ".join(targets)]["verdict"]}), flush=True)
for name in chosen:
    file_name, edits, (kind, targets) = MUTANTS[name]
    dest = mirror(edits, file_name)
    try:
        code, failed, isolation = run(python, dest, kind, targets)
    finally:
        shutil.rmtree(dest, ignore_errors=True)
    verdict = "KILLED" if code != 0 and failed else "SURVIVED"
    rows.append({"mutant": name, "file": file_name, "targets": targets, "exit": code, "failing_tests": failed,
                 "isolation_violations": isolation, "verdict": verdict})
    print(json.dumps({"mutant": name, "verdict": verdict, "failing": len(failed)}, ensure_ascii=False), flush=True)
record = {"task": "CLAUDE-WUA-EVM-COMPACT-LAYOUT-001", "controls": controls, "results": rows,
          "killed": sum(r["verdict"] == "KILLED" for r in rows), "mutants": len(rows)}
target.write_text(json.dumps(record, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
