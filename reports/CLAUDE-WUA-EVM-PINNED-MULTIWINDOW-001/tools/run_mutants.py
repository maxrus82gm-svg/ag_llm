"""TEST-QA for the pinned EVM windows (CLAUDE-WUA-EVM-PINNED-MULTIWINDOW-001): each mutant weakens one new rule in a
disposable TEMP mirror of the code; the tests must kill it. The unmodified mirror is the control and must pass.
Mirror = top-level *.py / *.js and web_alarm/*.py of the working tree (no Git metadata, no data). Python targets run
through run_gate.py with CLAUDE_RUNNER_ROOT pointing at the mirror (guarded runner, TEMP isolation); JS targets run with
node --test inside the mirror. Only names, verdicts and counters are published.
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
MC, SRV, UI = "web_alarm/model_cards.py", "web_alarm/server.py", "web_alarm/ui.py"
PY, JS = ("py", ("test_web_alarm_model_cards",)), ("js", ("test_web_alarm_evm_ui.js",))

MUTANTS = {
    # server: the layout part of the view file
    "L01 a window of an entry not shown is accepted": (MC, [("        if window is not None and connection_id not in {x for ids in present.values() for x in ids}:\n"
                                                             "            raise SettingsConflictError(\"the entry is not shown now; reload and repeat\")\n", "")], PY),
    "L02 an order save drops the windows": (MC, [("            if current[\"layout\"][\"state\"] == \"SAVED\":", "            if False:")], PY),
    "L03 a window moves the board revision": (MC, [("\"revision\": current[\"revision\"] or 0,\n", "\"revision\": (current[\"revision\"] or 0) + 1,\n")], PY),
    "L04 a second window of the same entry": (MC, [("            windows = [w for w in layout[\"windows\"] if w[\"connection_id\"] != connection_id]\n",
                                                     "            windows = list(layout[\"windows\"])\n")], PY),
    "L05 stored coordinates not checked": (MC, [("                and _CONNECTION_ID.fullmatch(window[\"connection_id\"]) and _coordinate(window[\"x\"]) and _coordinate(window[\"y\"])):",
                                                  "                and _CONNECTION_ID.fullmatch(window[\"connection_id\"])):")], PY),
    "L06 posted coordinates not checked": (MC, [("                                       and _coordinate(window[\"x\"]) and _coordinate(window[\"y\"])):",
                                                  "                                       ):")], PY),
    "L07 no limit of windows": (MC, [("            if len(windows) > MAX_WINDOWS:", "            if False:")], PY),
    "L08 a damaged layout overwritten, not kept": (MC, [("            if current[\"state\"] == \"CORRUPT\" or layout[\"state\"] == \"CORRUPT\":\n                self._set_aside(self.view_path)\n",
                                                          "            if False:\n                self._set_aside(self.view_path)\n")], PY),
    "L09 windows of absent entries shown": (MC, [("        windows = [dict(w) for w in layout[\"windows\"] if w[\"connection_id\"] in everywhere]",
                                                   "        windows = [dict(w) for w in layout[\"windows\"]]")], PY),
    "L10 windows of absent entries dropped on a save": (MC, [("            windows = [w for w in layout[\"windows\"] if w[\"connection_id\"] != connection_id]\n",
                                                               "            windows = [w for w in layout[\"windows\"] if w[\"connection_id\"] != connection_id and w[\"connection_id\"] in {x for ids in present.values() for x in ids}]\n")], PY),
    "L11 closing a closed window writes": (MC, [("            if window is None and len(windows) == len(layout[\"windows\"]) and layout[\"state\"] != \"CORRUPT\":\n"
                                                  "                return self.view(present)  # closing a window that is not open changes nothing\n", "")], PY),
    "L12 an order save over a damaged layout keeps nothing aside": (MC, [("            if current[\"state\"] == \"CORRUPT\" or current[\"layout\"][\"state\"] == \"CORRUPT\":",
                                                                           "            if current[\"state\"] == \"CORRUPT\":")], PY),
    "L13 the layout route answers GET": (SRV, [("                if method != \"POST\":\n                    raise ApiError(405, \"method_not_allowed\", \"the window layout is saved with POST\")\n", "")], PY),
    # page: windows, preview, layout
    "W01 a pinned model gets a preview copy": (UI, [("  if(pinned(h.id)){  // no second copy", "  if(false&&pinned(h.id)){  // no second copy")], JS),
    "W02 Ctrl release closes the windows": (UI, [("function evmKeyUp(e){if(e?.key==='Control'){evm.ctrl=false;if(evm.peek.id&&!evm.promote)closePeek()}}",
                                                   "function evmKeyUp(e){if(e?.key==='Control'){evm.ctrl=false;if(evm.peek.id&&!evm.promote)closePeek();for(const id of [...evm.pinOrder])closePin(id)}}")], JS),
    "W03 Escape closes the top window": (UI, [("  if(evm.peek.id)closePeek({focus:true})  // the preview only",
                                                "  if(evm.peek.id)closePeek({focus:true});else if(evm.pinOrder.length)closePin(evm.pinOrder[evm.pinOrder.length-1])  // the preview only")], JS),
    "W04 a second window of the same model (both guards gone)": (UI, [("  if(evm.pins[id]){activatePin(id,{flash:true,focus:opts.focus});return evm.pins[id]}\n", ""),
                                                                     ("  if(evm.pins[id]){activatePin(id,{flash:true,focus});return}\n", "")], JS),
    "W05 «⧉» again closes the window": (UI, [("  if(evm.pins[id]){activatePin(id,{flash:true,focus});return}", "  if(evm.pins[id]){closePin(id);return}")], JS),
    "W06 the preview under the windows": (UI, [(".evm-peek{position:fixed;z-index:18;", ".evm-peek{position:fixed;z-index:15;")], JS),
    "W07 a move saved on every pixel": (UI, [("  const at=placePin(p);p.x=Math.round(at.left);p.y=Math.round(at.top)  // it stays exactly where it is seen",
                                               "  const at=placePin(p);p.x=Math.round(at.left);p.y=Math.round(at.top);saveWindow(d.id)  // it stays exactly where it is seen")], JS),
    "W08 a tremor on the title moves the window": (UI, [("  if(!d.moved&&Math.hypot(ev.clientX-d.sx,ev.clientY-d.sy)<PIN_MOVE_PX)return;", "")], JS),
    "W09 a window may leave the screen": (UI, [("    left=Math.min(Math.max(p.x,0),Math.max(0,vw-w));top=Math.min(Math.max(p.y,minTop),Math.max(minTop,vh-48));", "    left=p.x;top=p.y;")], JS),
    "W10 showing a window inside overwrites its place": (UI, [("function placeAllPins(){for(const p of Object.values(evm.pins))placePin(p)}",
                                                               "function placeAllPins(){for(const p of Object.values(evm.pins)){const at=placePin(p);p.x=at.left;p.y=at.top}}")], JS),
    "W11 Escape does not cancel a window move": (UI, [("  if(evm.winDrag){pinCancel();return}\n", "")], JS),
    "W12 a redraw creates the windows again": (UI, [("  for(const id of evm.pinOrder)fillPin(id);  // the same windows",
                                                      "  for(const id of [...evm.pinOrder]){const q=evm.pins[id];closePin(id);openPin(id,{x:q.x,y:q.y})}  // the same windows")], JS),
    "W13 the saved windows restored on every read": (UI, [("  if(evm.layoutLoaded||!layout)return;", "  if(!layout)return;")], JS),
    "W14 a press inside the preview does not pin it": (UI, [("$('evmPeek').onpointerdown=ev=>previewPress(ev);", "$('evmPeek').onpointerdown=()=>{};")], JS),
    "W15 the preview pinned before the click of its button": (UI, [("  setTimeout(promotePreview,0)  // after the click", "  promotePreview()  // after the click")], JS),
    "W16 arrows save every step": (UI, [("  clearTimeout(p.saveTimer);p.saveTimer=setTimeout(()=>saveWindow(id),400)", "  saveWindow(id)")], JS),
    "W17 layout writes not queued": (UI, [("  evm.layoutQueue=evm.layoutQueue.then(async()=>{", "  evm.layoutQueue=Promise.resolve().then(async()=>{")], JS),
    "W18 a refused write is not told": (UI, [("    }catch(e){notice('evmError','Расположение окна не сохранено: '+e.message", "    }catch(e){void('Расположение окна не сохранено: '+e.message")], JS),
    "W19 «×» gives the keyboard to «open»": (UI, [("(evm.cquick[p.from]||evm.cquick[home]||evm.copen[home])?.focus()", "evm.copen[home]?.focus()")], JS),
    "W20 another view closes the windows": (UI, [("  if(name!=='evm'){closePeek();pinCancel()}", "  if(name!=='evm'){closePeek();pinCancel();for(const id of [...evm.pinOrder])closePin(id)}")], JS),
    "W21 a card drag closes the windows": (UI, [("  if(evm.peek.id)closePeek();  // it stays closed until the drop", "  if(evm.peek.id)closePeek();for(const id of [...evm.pinOrder])closePin(id);  // it stays closed until the drop")], JS),
    "W22 a press does not raise a window": (UI, [("  el.onpointerdown=()=>activatePin(id);", "  el.onpointerdown=()=>{};")], JS),
    "W23 an absent model leaves a broken window": (UI, [("  const e=entryOf(id);p.missing=!e;p.el.hidden=!e;", "  const e=entryOf(id);p.missing=!e;p.el.hidden=false;")], JS),
    "W24 Ctrl + hover on a pinned model does not show its window": (UI, [("    if(evm.hinted!==h.id){evm.hinted=h.id;activatePin(h.id,{flash:true})}\n", "")], JS),
    "W25 «×» does not save the closing": (UI, [("  saveWindow(id,true);syncQuick();", "  syncQuick();")], JS),
}


def mirror(edits, file_name) -> Path:
    dest = Path(tempfile.mkdtemp(prefix="claude-evmpins-mirror-"))
    for path in list(REPO.glob("*.py")) + list(REPO.glob("*.js")):
        shutil.copy2(path, dest / path.name)
    (dest / "web_alarm").mkdir()
    for path in (REPO / "web_alarm").glob("*.py"):
        shutil.copy2(path, dest / "web_alarm" / path.name)
    for path in (REPO / "web_alarm").glob("*.json"):
        shutil.copy2(path, dest / "web_alarm" / path.name)
    if file_name:
        target = dest / file_name
        raw = target.read_bytes()
        crlf = b"\r\n" in raw
        text = raw.decode("utf-8").replace("\r\n", "\n")
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
    env = dict(os.environ, CLAUDE_RUN_PREFIX="claude-evmpins", CLAUDE_TASK_LABEL="CLAUDE-WUA-EVM-PINNED-MULTIWINDOW-001",
               CLAUDE_RUNNER_ROOT=str(dest), PYTHONIOENCODING="utf-8")
    env.pop("CLAUDE_EXTRA_PATH", None)
    done = subprocess.run([python, str(GATE), python, "mutant", *targets], cwd=dest, env=env, capture_output=True,
                          text=True, encoding="utf-8", errors="replace", timeout=900)
    summary = json.loads(done.stdout)
    shutil.rmtree(summary["base"], ignore_errors=True)  # the runner's own TEMP attempt folder
    failed = sorted({t[0].split(".")[-1].split(" ")[0] for t in summary.get("non_pass", []) if t[1] != "SKIP"})
    return summary["exit"], failed, summary.get("isolation_violations")


def main():
    python, target = sys.argv[1], Path(sys.argv[2])
    chosen = sys.argv[3:] or list(MUTANTS)
    for name in chosen:  # every pattern must occur exactly once before anything runs
        file_name, edits, _ = MUTANTS[name]
        text = (REPO / file_name).read_bytes().decode("utf-8").replace("\r\n", "\n")
        for old, _new in edits:
            if text.count(old) != 1:
                sys.exit(f"{name}: pattern occurs {text.count(old)} times")
    controls = {}
    for kind, targets in (PY, JS):
        dest = mirror([], None)
        try:
            code, failed, isolation = run(python, dest, kind, targets)
        finally:
            shutil.rmtree(dest, ignore_errors=True)
        controls[" ".join(targets)] = {"exit": code, "failing": failed, "isolation_violations": isolation,
                                       "verdict": "PASS" if code == 0 and not failed else "FAIL"}
        print(json.dumps({"control": targets, "verdict": controls[" ".join(targets)]["verdict"]}), flush=True)
    rows = []
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
        print(json.dumps({"mutant": name, "verdict": verdict, "failing": failed}, ensure_ascii=False), flush=True)
    record = {"task": "CLAUDE-WUA-EVM-PINNED-MULTIWINDOW-001", "purpose": "mutation gate of the pinned windows and their layout (TEST-QA)",
              "controls": controls, "results": rows, "mutants": len(rows), "killed": sum(r["verdict"] == "KILLED" for r in rows)}
    target.write_text(json.dumps(record, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"mutants": record["mutants"], "killed": record["killed"],
                      "controls": {k: v["verdict"] for k, v in controls.items()}}))


if __name__ == "__main__":
    main()
