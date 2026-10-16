"""Check that every RAM mutant in control-inputs.json is byte-for-byte the pre-repair method from the
'before' sources preserved inside evidence.zip (i.e. the controls revive the real old code, not a strawman)."""
import ast
import hashlib
import json
import textwrap
import zipfile
from pathlib import Path

PKG = Path(r"M:\GitHub\ag_llm\reports\CODEX-WA4-R-006-WINDOWS-F1F2F3-LOCAL-GATE")
inputs = json.loads((PKG / "control-inputs.json").read_text(encoding="utf-8"))
with zipfile.ZipFile(PKG / "evidence.zip") as zf:
    before = {n.split("sources/before/")[1]: zf.read(n).decode("utf-8") for n in zf.namelist()
              if n.startswith("sources/before/")}
    final = {n.split("sources/final/")[1]: zf.read(n).decode("utf-8") for n in zf.namelist()
             if n.startswith("sources/final/") and n.endswith(".py")}


def method_source(text, name):
    tree = ast.parse(text)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            lines = text.splitlines(keepends=True)
            start = (node.decorator_list[0].lineno if node.decorator_list else node.lineno) - 1
            return "".join(lines[start:node.end_lineno])
    return None


for name, entry in inputs.items():
    if not isinstance(entry, dict) or "code" not in entry:
        print("non-code entry", name, str(entry)[:200])
        continue
    rel = entry["file"]
    old = method_source(before.get(rel, ""), name)
    new = method_source(final.get(rel, ""), name)
    code = entry["code"]
    same_old = old is not None and textwrap.dedent(old) == textwrap.dedent(code)
    same_new = new is not None and textwrap.dedent(new) == textwrap.dedent(code)
    print(f"{name:<24} file={rel:<36} equals_BEFORE={same_old} equals_FINAL={same_new} "
          f"keys={sorted(entry)} code_sha={hashlib.sha256(code.encode()).hexdigest()[:12]}")
