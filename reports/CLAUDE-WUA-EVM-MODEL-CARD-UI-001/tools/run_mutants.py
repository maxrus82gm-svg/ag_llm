"""TEST-QA for the EVM model cards: each mutant weakens one rule in a disposable TEMP mirror of the code; the new
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
MC, SV, UI = "web_alarm/model_cards.py", "web_alarm/server.py", "web_alarm/ui.py"
PY, JS = ("py", ("test_web_alarm_model_cards",)), ("js", ("test_web_alarm_evm_ui.js",))

MUTANTS = {
    # server status, settings and secrets
    "M01 30-day boundary exclusive": (MC, [("if age <= timedelta(days=freshness_days)", "if age < timedelta(days=freshness_days)")], PY),
    "M02 key presence outside the settings version": (MC, [('"credential_present": facts["credential"]["present"], ', "")], PY),
    "M03 called model outside the settings version": (MC, [('"provider_model_id": spec.provider_model_id,\n        }',
                                                           '\n        }')], PY),
    "M04 simulated answer confirms the model": (MC, [("        if not result.live:\n", "        if False:\n")], PY),
    "M05 failure after success ignored": (MC, [("        if failure_at is not None and failure_at > success_at:", "        if False:")], PY),
    "M06 future timestamp accepted": (MC, [("        if success_at > now + FUTURE_TOLERANCE:", "        if False:")], PY),
    "M07 description limit not enforced": (MC, [("    if len(text) > MAX_DESCRIPTION:", "    if False:")], PY),
    "M08 base revision not compared": (MC, [('            if body.get("base_revision") != current["revision"]:', "            if False:")], PY),
    "M09 damaged checks overwritten, not kept": (MC, [("                self._set_aside(self.checks_path)\n", "                pass\n")], PY),
    "M10 key value read": (MC, [("provider.credential_env in self.environ  # presence only",
                                 "bool(self.environ.get(provider.credential_env))")], PY),
    "M11 Tk fallback to defaults skipped": (MC, [("        if spec is None or not spec.enabled:  # Tk itself falls back to its default here",
                                                  "        if False:")], PY),
    "M12 role switch ignored": (MC, [('        elif role.enabled_field and not tk["values"][role.enabled_field]:', "        elif False:")], PY),
    "M13 Dredd given the Planner model": (MC, [('"Верификатора, пока включён Планировщик.", field="verifier_model_id"',
                                               '"Верификатора, пока включён Планировщик.", field="planner_model_id"')], PY),
    "M14 reading the cards writes a store": (MC, [('        ctx = self._context()\n        settings, tk = ctx["settings"], ctx["tk"]\n',
                                                   '        ctx = self._context()\n        settings, tk = ctx["settings"], ctx["tk"]\n'
                                                   '        self._write(self.checks_path, {"schema": CHECKS_SCHEMA, "version": SCHEMA_VERSION, "checks": {}})\n')], PY),
    "M15 manual provider names an adapter": (MC, [('_clean_title(entry.get("country", "—")), None,',
                                                   '_clean_title(entry.get("country", "—")), entry.get("adapter"),')], PY),
    "M17 chat role shown as running": (MC, [('        if state == "assigned" and not role.runs:', "        if False:")], PY),
    "M16 Authorization values not hidden": (MC, [('    text = _SECRETISH.sub(lambda m: m.group(1) + " [скрыто]", text)\n', "")], PY),
    # HTTP boundary
    "S01 model cards without the local origin": (SV, [("                self._require_local_ui_origin('model_cards_forbidden', 'EVM model cards')\n", "")], PY),
    "S02 writes without Origin": (SV, [("                if self.command != 'GET' and len(self.headers.get_all('Origin', [])) != 1:",
                                        "                if False:")], PY),
    "S03 real Tk settings for any storage": (SV, [("            tk_state_path = default_tk_state_path() if storage_root is None else None",
                                                   "            tk_state_path = default_tk_state_path()")], PY),
    "S04 check accepts a message": (SV, [("                if data:\n                    raise ApiError(400, \"invalid_model_card_request\"",
                                          "                if False:\n                    raise ApiError(400, \"invalid_model_card_request\"")], PY),
    # page
    "U01 unknown role shown as assigned": (UI, [("const [mark,cls,label]=ROLE_MARK[state]||ROLE_MARK.unknown;",
                                                 "const [mark,cls,label]=ROLE_MARK[state]||ROLE_MARK.assigned;")], JS),
    "U02 check answer paints the indicator": (UI, [("  await loadEvm()  // the indicator always comes from the server, never from this answer",
                                                    "  if(evm.outputs[id].kind!=='error')c.api={...c.api,color:'green',reason:'CONFIRMED'};renderEvm();fillCheck()")], JS),
    "U03 drafts dropped on close": (UI, [("  evm.window=null;$('evmSettingsWindow').hidden=true;", "  evm.window=null;evm.drafts={};$('evmSettingsWindow').hidden=true;")], JS),
    "U04 description rendered as markup": (UI, [("  const strengths=element('div',c.description||",
                                                 "  const strengths=(d=>(d.innerHTML=c.description,d))(element('div',null,'strengths'))||element('div',c.description||")], JS),
    "U05 settings saved without the read revision": (UI, [("  return {base_revision:d.base_revision,", "  return {base_revision:null,")], JS),
    "U06 choice button back in the card": (UI, [("actions.append(settings,check);", "actions.append(settings,check,element('button','Выбрать'));")], JS),
    "U07 cards invented without card data": (UI, [("full.has(c.connection_id)?modelCard(full.get(c.connection_id),cards):plainCard(c,evm.cardsError||'нет данных сервера')",
                                                   "modelCard(full.get(c.connection_id)||{...c,provider_id:'',description:'',roles:[],api:{color:'green',reason:'CONFIRMED'}},"
                                                   "cards||{providers:[],role_definitions:[]})")], JS),
    "U08 window status differs from the card": (UI, [("$('evmCheckDot').replaceChildren(apiDot(c.api));", "$('evmCheckDot').replaceChildren(apiDot({...c.api,color:'green'}));")], JS),
    "U09 voice place enabled": (UI, [('<button type="button" id="chatMic" disabled ', '<button type="button" id="chatMic" ')], JS),
}


def mirror(edits, file_name) -> Path:
    dest = Path(tempfile.mkdtemp(prefix="claude-evmcard-mirror-"))
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
    env = dict(os.environ, CLAUDE_RUN_PREFIX="claude-evmcard", CLAUDE_TASK_LABEL="CLAUDE-WUA-EVM-MODEL-CARD-UI-001",
               CLAUDE_RUNNER_ROOT=str(dest), PYTHONIOENCODING="utf-8")
    env.pop("CLAUDE_EXTRA_PATH", None)
    done = subprocess.run([python, str(GATE), python, "mutant", *targets], cwd=dest, env=env, capture_output=True,
                          text=True, encoding="utf-8", errors="replace", timeout=900)
    summary = json.loads(done.stdout)
    failed = sorted({t[0].split(".")[-1].split(" ")[0] for t in summary.get("non_pass", []) if t[1] != "SKIP"})
    return summary["exit"], failed, summary.get("isolation_violations")


python, target = sys.argv[1], Path(sys.argv[2])
chosen = sys.argv[3:] or list(MUTANTS)
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
record = {"task": "CLAUDE-WUA-EVM-MODEL-CARD-UI-001", "controls": controls, "results": rows,
          "killed": sum(r["verdict"] == "KILLED" for r in rows), "mutants": len(rows)}
target.write_text(json.dumps(record, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
