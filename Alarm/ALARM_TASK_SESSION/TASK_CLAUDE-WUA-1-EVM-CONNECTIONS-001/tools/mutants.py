"""TEST-QA: each mutant is one exact replacement in a disposable TEMP copy of the code; the new tests must fail.

P* mutants break web_alarm/ultra_connections.py or web_alarm/server.py and run test_web_alarm_ultra_connections
through the guarded runner (tools/run_gate.py, CLAUDE_RUNNER_ROOT = the copy). U* mutants break the shipped page
(web_alarm/ui.py) and run test_web_alarm_evm_ui.js with node in the copy. "final" is the unmodified control of
each kind. The repository is only read. Writes <TEMP>/claude-wua1-<batch>.mutants.json.
Usage: mutants.py <python> <node> <batch>
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
TOOLS = Path(__file__).resolve().parent
TEMP = Path(tempfile.gettempdir()).resolve()
UC, SRV, UI = "web_alarm/ultra_connections.py", "web_alarm/server.py", "web_alarm/ui.py"
SIX = '("gigachat_2", "gigachat_2_max", "gigachat_2_pro", "gigachat_3_lightning", "gigachat_3_pro", "gigachat_ultra")'
MUTANTS = {
    "P0-final": None,
    "P1-catalog-copied": (UC, "specs = _registry().list_model_specs()",
                          f"specs = tuple(_registry().MODEL_REGISTRY[k] for k in {SIX})"),
    "P2-wrong-provider-id": (UC, "display_name=spec.display_name,\n                      provider_model_id=spec.provider_model_id)",
                             "display_name=spec.display_name,\n                      provider_model_id=spec.model_id)"),
    "P3-corrupt-as-empty": (UC, 'return {"state": "CORRUPT", "roles": {}, "reason": f"saved choice is unreadable: {type(exc).__name__}"}',
                            'return {"state": "NOT_SELECTED", "roles": {}}'),
    "P4-disabled-accepted": (UC, "            return registry.get_model_spec(model_id)  # the registry's own rules (e.g. disabled)",
                             "            return spec"),
    "P5-not-persisted": (UC, "    def _write(self, data: dict[str, Any]) -> None:\n",
                         "    def _write(self, data: dict[str, Any]) -> None:\n        return\n"),
    "P6-read-creates-storage": (UC, '        selection = self.selection("chat")\n        selected_id',
                                '        self.path.parent.mkdir(parents=True, exist_ok=True)\n        selection = self.selection("chat")\n        selected_id'),
    "P7-damage-not-kept": (UC, "                self._set_aside()", "                pass"),
    "P8-claims-verified": (UC, '            "verification": UNVERIFIED,', '            "verification": "VERIFIED",'),
    "P9-role-ignored": (SRV, 'data.get("role", "chat"), data.get("connection_id")', '"chat", data.get("connection_id")'),
    "U0-final": None,
    "U1-fetch-at-load": (UI, "\nrefresh();\n</script>", "\nloadEvm();refresh();\n</script>"),
    "U2-no-busy-guard": (UI, "  if(evm.busy)return;evm.busy=true;", "  evm.busy=true;"),
    "U3-no-reload-after-refusal": (UI, "  evm.busy=false;\n  await loadEvm();", "  evm.busy=false;\n  if(!error)await loadEvm();"),
    "U4-markup-rendering": (UI, "card.append(element('strong',c.display_name),", "const n=element('strong');n.innerHTML=c.display_name;card.append(n,"),
    "U5-no-shape-check": (UI, "    if(!validEvm(data))throw new Error", "    if(false)throw new Error"),
    "U6-no-way-back": (UI, "$('viewOperator').onclick=()=>showView('operator');", "$('viewOperator').onclick=()=>showView('evm');"),
    "U7-disabled-selectable": (UI, "button.disabled=evm.busy||c.selected||!c.selectable;", "button.disabled=evm.busy||c.selected;"),
}


def mirror(name: str) -> Path:
    dest = Path(tempfile.mkdtemp(prefix=f"claude-wua1-mirror-{name}-", dir=TEMP)) / "code"
    (dest / "web_alarm").mkdir(parents=True)
    for pattern in ("*.py", "*.js"):
        for path in REPO.glob(pattern):
            shutil.copy2(path, dest / path.name)
    for path in (REPO / "web_alarm").glob("*.py"):
        shutil.copy2(path, dest / "web_alarm" / path.name)
    return dest


python, node, batch = sys.argv[1], sys.argv[2], sys.argv[3]
rows = []
for name, change in MUTANTS.items():
    code = mirror(name)
    if change is not None:
        rel, old, new = change
        target = code / rel
        text = target.read_bytes().decode("utf-8")
        eol = "\r\n" if "\r\n" in text else "\n"
        text = text.replace("\r\n", "\n")
        if text.count(old) != 1:
            rows.append({"mutant": name, "build_error": f"pattern found {text.count(old)} times"})
            print(json.dumps(rows[-1]), flush=True)
            continue
        target.write_bytes(text.replace(old, new).replace("\n", eol).encode("utf-8"))
    if name.startswith("P"):
        env = dict(os.environ, CLAUDE_RUNNER_ROOT=str(code), CLAUDE_RUN_PREFIX=f"claude-wua1-{batch}")
        proc = subprocess.run([python, "-I", "-B", str(TOOLS / "run_gate.py"), python, name, "test_web_alarm_ultra_connections"],
                              env=env, capture_output=True, cwd=str(TEMP))
        summary = json.loads(proc.stdout.decode("ascii", errors="replace").strip().splitlines()[-1])
        row = {"mutant": name, "kind": "python", "exit": summary["exit"], "tests_run": summary.get("tests_run"),
               "failures": summary.get("failures"), "errors": summary.get("errors"),
               "isolation_violations": summary.get("isolation_violations"), "attempt": Path(summary["base"]).name}
    else:
        proc = subprocess.run([node, "--test", "test_web_alarm_evm_ui.js"], cwd=str(code), capture_output=True, timeout=300)
        out = proc.stdout.decode("utf-8", errors="replace")
        counts = {k: int(v) for k, v in (line[2:].split(" ", 1) for line in out.splitlines()
                                         if line.startswith(("# tests ", "# pass ", "# fail ")))}
        failed = [line.split(" - ", 1)[1] for line in out.splitlines() if line.startswith("not ok ")]
        row = {"mutant": name, "kind": "node", "exit": proc.returncode, **counts, "failed_tests": failed}
    row["killed"] = row["exit"] != 0 if change is not None else None
    row["control_pass"] = row["exit"] == 0 if change is None else None
    rows.append(row)
    print(json.dumps({k: row[k] for k in ("mutant", "exit", "killed", "control_pass")}), flush=True)
(TEMP / f"claude-wua1-{batch}.mutants.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
