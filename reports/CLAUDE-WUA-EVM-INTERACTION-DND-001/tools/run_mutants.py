"""TEST-QA for the EVM interaction (CLAUDE-WUA-EVM-INTERACTION-DND-001): each mutant weakens one new rule of
web_alarm/ui.py in a disposable TEMP mirror; the page tests must kill it. The unmodified mirror is the control and must
pass. Mirror = top-level *.py / *.js and web_alarm/*.py of the working tree (no Git metadata, no data). The tests run
with node --test inside the mirror (node:vm, no network). Only names, verdicts and counters are published.
Usage: run_mutants.py <out.json> [mutant-name ...]
"""
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
REPO = TOOLS.parents[2]
UI, TARGET = "web_alarm/ui.py", "test_web_alarm_evm_ui.js"

MUTANTS = {
    # click and drag
    "M01 a tremor below the threshold drags": [("    if(Math.hypot(ev.clientX-p.x,ev.clientY-p.y)<(p.type==='mouse'?DRAG_PX:DRAG_TOUCH_PX))return;\n", "")],
    "M02 the release after a drag opens the card": [("const d=evm.drag;endDrag();evm.suppressUntil=Date.now()+400;", "const d=evm.drag;endDrag();")],
    "M03 any button drags": [("  if(ev?.button!==0||!evm.cards?.view", "  if(!evm.cards?.view")],
    "M04 a cancelled press drags again": [("    if(p.cancelled)return;\n", "")],
    "M05 Escape does not cancel a drag": [("  if(evm.drag){cancelDrag();return}\n", "")],
    "M06 the place of the release is ignored": [("  if(evm.drag&&typeof ev?.clientX==='number')dragTo(ev.clientX,ev.clientY);", "")],
    "M07 a press on the star drags": [("    ev?.stopPropagation?.();evm.suppressUntil=Infinity};", "    evm.suppressUntil=Infinity};")],
    "M08 a press on the star ends as a click of the card": [("    ev?.stopPropagation?.();evm.suppressUntil=Infinity};", "    ev?.stopPropagation?.()};")],
    "M09 native drag-and-drop not blocked": [("  head.ondragstart=ev=>ev?.preventDefault?.();", "  head.ondragstart=()=>{};")],
    # where a card may go
    "M10 a card dropped into another source column": [("  for(const section of d.section==='favorites'?['favorites']:[d.section,'favorites']){",
                                                       "  for(const section of Object.keys(COLUMNS)){")],
    "M11 a favourite dropped again is duplicated": [("  const before=sectionIds(d.target),order=before.filter(i=>i!==d.id),adding=",
                                                     "  const before=sectionIds(d.target),order=[...before],adding=")],
    "M12 a refused drop stays on the page": [("    evm.viewSaving=false;evm.cards.view=before;\n    await loadEvm();\n", "    evm.viewSaving=false;\n")],
    "M13 the toast moves the board": [(".evm-toasts{position:fixed;", ".evm-toasts{position:static;")],
    "M14 autoscroll without a speed limit": [("if(own)sc.scrollTop+=Math.max(-24,Math.min(24,v));", "if(own)sc.scrollTop+=v;")],
    "M15 the drag label under the pointer": [("  let gx=x+14,gy=y+16;", "  let gx=x-20,gy=y-10;")],
    "M16 the drag label leaves the window": [("  if(vw&&gx+gw>vw-4)gx=Math.max(4,x-14-gw);\n  if(vh&&gy+gh>vh-4)gy=Math.max(4,y-16-gh);\n", "")],
    # the card in place
    "M17 a click floats the card (old behaviour)": [("  toggleExpanded(id,section)\n}", "  pinPeek(id,section,'open',false)\n}")],
    "M18 opening a card closes the others": [("  if(evm.expanded.has(key))evm.expanded.delete(key);else evm.expanded.add(key);",
                                              "  if(evm.expanded.has(key))evm.expanded.delete(key);else{evm.expanded.clear();evm.expanded.add(key)}")],
    "M19 open cards forgotten on a redraw": [("  for(const key of [...evm.expanded])if(!evm.ccards[key])evm.expanded.delete(key);", "  evm.expanded.clear();")],
    "M20 the keyboard lost after a redraw": [("  restoreFocus(focusKey)\n}", "}")],
    # the side panel
    "M21 a plain hover opens the panel": [("  if(typeof ev?.ctrlKey==='boolean')evm.ctrl=ev.ctrlKey;", "  evm.ctrl=true;")],
    "M22 releasing Ctrl keeps an unpinned panel": [("function evmKeyUp(e){if(e?.key==='Control'){evm.ctrl=false;if(evm.peek.id&&!evm.peek.pinned)closePeek()}}",
                                                    "function evmKeyUp(e){if(e?.key==='Control'){evm.ctrl=false}}")],
    "M23 Ctrl + hover replaces a pinned panel": [("evm.window||evm.peek.pinned||peekIs(h.id,h.section))return;", "evm.window||peekIs(h.id,h.section))return;")],
    "M24 a press inside does not pin the panel": [("$('evmPeek').onpointerdown=()=>pinCurrent();", "$('evmPeek').onpointerdown=()=>{};")],
    "M25 a drag keeps an unpinned panel": [("  if(evm.peek.id&&!evm.peek.pinned)closePeek();  // it stays closed", "  // it stays closed")],
    "M26 the panel comes back during a drag": [("evm.view!=='evm'||evm.press||evm.drag||evm.window", "evm.view!=='evm'||evm.window")],
    "M27 a pinned panel stays in the way of a drag": [("mark($('evmView'),'dragging',true);mark($('evmPeek'),'hold',true);", "mark($('evmView'),'dragging',true);")],
    "M28 a window closes the pinned panel": [("  if(evm.peek.id&&!evm.peek.pinned)closePeek();  // a pinned side panel stays under the window", "  closePeek();")],
    "M29 Ctrl + click opens the card in place": [("  if(ev?.ctrlKey){pinPeek(id,section,'open',false);return}", "")],
    "M30 Escape gives the keyboard to «open», not to «⧉»": [("(invoker==='quick'?evm.cquick[key]:evm.copen[key])?.focus()", "evm.copen[key]?.focus()")],
    # placement
    "M31 the panel over its own column": [("    left=side==='right'?col.right+G:col.left-G-width;", "    left=r.left;")],
    "M32 right columns prefer the right side": [("const sides=evm.peek.section==='favorites'||evm.peek.section==='api'?['right','left']:['left','right'];",
                                                 "const sides=['right','left'];")],
    "M33 no sheet on a narrow screen": [("  if(side){\n    left=side==='right'", "  if(side||true){side=side||'right';\n    left=side==='right'")],
    "M34 the sheet always below": [("side=below>=above?'below':'above';", "side='below';")],
    "M35 the panel under the sticky header": [("const minTop=Math.max(M,Math.round((head?head.bottom:0)+8));", "const minTop=M;")],
}


def mirror(edits) -> Path:
    dest = Path(tempfile.mkdtemp(prefix="claude-evmdnd-mirror-"))
    for path in list(REPO.glob("*.py")) + list(REPO.glob("*.js")):
        shutil.copy2(path, dest / path.name)
    (dest / "web_alarm").mkdir()
    for path in (REPO / "web_alarm").glob("*.py"):
        shutil.copy2(path, dest / "web_alarm" / path.name)
    if edits:
        target = dest / UI
        raw = target.read_bytes()
        crlf = b"\r\n" in raw
        text = raw.decode("utf-8").replace("\r\n", "\n")
        for old, new in edits:
            if text.count(old) != 1:
                shutil.rmtree(dest)
                sys.exit(f"pattern occurs {text.count(old)} times: {old[:60]!r}")
            text = text.replace(old, new)
        target.write_bytes((text.replace("\n", "\r\n") if crlf else text).encode("utf-8"))
    return dest


def run(dest):
    done = subprocess.run(["node", "--test", TARGET], cwd=dest, capture_output=True, text=True, encoding="utf-8")
    failed = sorted({line.split(" - ", 1)[1].split(" ")[0] for line in done.stdout.splitlines() if line.startswith("not ok")})
    return done.returncode, failed


def main():
    target = Path(sys.argv[1])
    chosen = sys.argv[2:] or list(MUTANTS)
    text = (REPO / UI).read_bytes().decode("utf-8").replace("\r\n", "\n")
    for name in chosen:  # every pattern must occur exactly once before anything runs
        for old, _new in MUTANTS[name]:
            if text.count(old) != 1:
                sys.exit(f"{name}: pattern occurs {text.count(old)} times")
    dest = mirror([])
    try:
        code, failed = run(dest)
    finally:
        shutil.rmtree(dest, ignore_errors=True)
    control = {"exit": code, "failing": failed, "verdict": "PASS" if code == 0 and not failed else "FAIL"}
    print(json.dumps({"control": control["verdict"]}), flush=True)
    rows = []
    for name in chosen:
        dest = mirror(MUTANTS[name])
        try:
            code, failed = run(dest)
        finally:
            shutil.rmtree(dest, ignore_errors=True)
        verdict = "KILLED" if code != 0 and failed else "SURVIVED"
        rows.append({"mutant": name, "file": UI, "target": TARGET, "exit": code, "failing_tests": failed, "verdict": verdict})
        print(json.dumps({"mutant": name, "verdict": verdict, "failing": failed}, ensure_ascii=False), flush=True)
    record = {"task": "CLAUDE-WUA-EVM-INTERACTION-DND-001", "purpose": "mutation gate of the new interaction rules (TEST-QA)",
              "control": control, "results": rows, "mutants": len(rows), "killed": sum(r["verdict"] == "KILLED" for r in rows)}
    target.write_text(json.dumps(record, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"mutants": record["mutants"], "killed": record["killed"], "control": control["verdict"]}))


if __name__ == "__main__":
    main()
