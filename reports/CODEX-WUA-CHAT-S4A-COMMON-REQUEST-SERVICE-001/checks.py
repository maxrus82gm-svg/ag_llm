"""In-memory compile and hash conservation, never opens Git or writes live data."""
import ast
import hashlib
import json
import os
from pathlib import Path
import sys

package = Path(__file__).resolve().parent
root = package.parent.parent


def stamp(path):
    data = path.read_bytes()
    return {"path": path.relative_to(root).as_posix(), "size": len(data),
            "sha256": hashlib.sha256(data).hexdigest()}


def compile_check():
    paths = [root / name for name in ("ordinary_chat_service.py", "test_ordinary_chat_service.py")]
    for path in paths:
        compile(path.read_bytes(), str(path), "exec")
    tree = ast.parse(paths[0].read_text(encoding="utf-8"))
    imports = sorted({node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)} |
                     {alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names})
    assert set(imports) == {"__future__", "asyncio", "dataclasses", "enum", "hashlib", "json", "math", "time", "typing",
                            "gigachat_transport", "model_registry", "provider_accounting"}, imports
    return {"compiled": [stamp(path) for path in paths], "service_imports": imports,
            "pyc_written": False, "ui_smoke": "NOT RUN: no existing UI/runtime module changed"}


def conservation(after_finish):
    baseline = json.loads((package / "evidence/baseline.json").read_text(encoding="utf-8"))
    source_changes = []
    for old in baseline["source"]:
        if stamp(root / old["path"]) != old:
            source_changes.append(old["path"])
    current = []
    for folder in (".ultra", "Чат_pro", "Чат_Pro_01", ".obsidian"):
        target = root / folder
        if not target.exists():
            continue
        for directory, subdirs, files in os.walk(target, followlinks=False):
            subdirs[:] = [name for name in subdirs if not (Path(directory) / name).is_junction()
                          and not (Path(directory) / name).is_symlink()]
            current.extend(stamp(Path(directory) / name) for name in files
                           if not (Path(directory) / name).is_symlink())
    before = {v["path"]: v for v in baseline["protected"]}
    after = {v["path"]: v for v in current}
    differences = [path for path in sorted(before.keys() | after.keys()) if before.get(path) != after.get(path)]
    editor_changes = [path for path in differences if path.startswith(".obsidian/")]
    data_changes = [path for path in differences if path not in editor_changes]
    launcher = json.loads((root / "web_alarm/launch_config.json").read_text(encoding="utf-8"))
    allowed_source_changes = ["Документация/000_Задачи Codex.md"] if after_finish else []
    assert source_changes == allowed_source_changes, source_changes
    assert not data_changes, data_changes
    assert launcher["active"] == "standard"
    return {"baseline_utc": baseline["utc"], "protected_before": len(before), "protected_after": len(after),
            "user_data_before": sum(not p.startswith(".obsidian/") for p in before),
            "user_data_after": sum(not p.startswith(".obsidian/") for p in after),
            "user_data_changes": data_changes, "editor_changes_preserved": editor_changes,
            "source_changes": source_changes, "launcher": launcher["active"]}


mode = sys.argv[1]
value = compile_check() if mode == "compile" else conservation(mode == "after-finish")
output = package / "evidence" / (mode + ".json")
assert not output.exists(), "Preserve previous evidence"
output.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(value, ensure_ascii=False, indent=2))
