"""TEST-QA of stage 2 (CLAUDE-WUA-CHAT-S2-SHARED-STORAGE-001): each mutant weakens one rule of the shared writer, the
web write path, the page or the Tk writer in a disposable TEMP mirror of the code; the tests must kill it. The
unmodified mirror is the control for every target set and must pass.
Mirror = top-level *.py / *.js / *.json and web_alarm/*.py / *.json of the working tree (no Git metadata, no data).
Python targets run through run_gate.py with CLAUDE_RUNNER_ROOT pointing at the mirror (guarded runner, TEMP
isolation); JS targets run with node --test inside the mirror; the Tk target runs tools/tk_contour_check.py against
the mirror (S2_MIRROR). Only names, verdicts and counters are published.
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
CS, UC, SRV, UI, TK = "context_storage.py", "web_alarm/ultra_chat.py", "web_alarm/server.py", "web_alarm/ui.py", "ultra_ui.py"
CORE = ("py", ("test_ultra_chat_storage",))
HTTP = ("py", ("test_web_alarm_ultra_chat_storage",))
JS = ("js", ("test_web_alarm_ultra_chat_ui.js",))
TKC = ("tk", ("tk_contour_check",))

MUTANTS = {
    # the shared writer (context_storage.py)
    # C01 removes the OS lock cleanly (no lock, no unlock), so only the concurrency and busy tests can see it
    "C01 no inter-process lock": (CS, [("            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)\n", "            pass\n"),
                                       ("            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)\n", "            pass\n")], CORE),
    "C02 identity not read again under the lock": (CS, [(
        "        metadata = _read_workspace_metadata_for_write(anchor)  # it may have changed while this writer waited\n"
        "        _check_expected_workspace(metadata, expected_workspace_id)\n",
        "        metadata = _read_workspace_metadata_for_write(anchor)  # it may have changed while this writer waited\n")], CORE),
    "C03 RAW published by replace (may overwrite)": (CS, [("                    os.rename(temp, target)\n", "                    os.replace(temp, target)\n")], CORE),
    "C04 RAW conflict not detected": (CS, [("        if _raw_canonical(existing) != _raw_canonical(candidate):\n", "        if False:\n")], CORE),
    "C05 created_at compared (a repeat becomes a conflict)": (CS, [(
        "    return {key: record[key] for key in _RAW_COMPARED_FIELDS if key in record}\n", "    return dict(record)\n")], CORE),
    "C06 chat ownership not checked by writers": (CS, [(
        "    problem = _chat_metadata_problem(data, chat_id, writer.workspace_id)\n",
        "    problem = _chat_metadata_problem(data, chat_id, data.get(\"workspace_id\") if isinstance(data, dict) else None)\n")], CORE),
    "C07 newer chat card version accepted": (CS, [(
        "    version = data.get(\"schema_version\", SCHEMA_VERSION)\n    if version != SCHEMA_VERSION:\n",
        "    version = data.get(\"schema_version\", SCHEMA_VERSION)\n    if False:\n")], CORE),
    "C08 newer workspace version accepted by writers": (CS, [(
        "    version = data.get(\"schema_version\")\n    if version != SCHEMA_VERSION:\n        newer =",
        "    version = data.get(\"schema_version\")\n    if False:\n        newer =")], CORE),
    "C09 temporary file location not checked": (CS, [(
        "            if os.path.normcase(_final_path_of_fd(fd)) != anchor.expected(parts[:-1] + (temp.name,)):\n", "            if False:\n")], CORE),
    "C10 new identity minted next to an orphaned history": (CS, [("                if _has_chat_history(anchor):\n", "                if False:\n")], CORE),
    "C11 storage initialised without lock, identity by replace (old code)": (CS, [
        ("        with _workspace_writer_lock(anchor):\n            for name in _STORAGE_SUBDIRECTORIES:\n",
         "        with contextlib.nullcontext():\n            for name in _STORAGE_SUBDIRECTORIES:\n"),
        ("                    _publish_new_file(anchor, (ULTRA_DIRNAME, WORKSPACE_METADATA_NAME), _json_bytes(new_metadata))\n",
         "                    _atomic_write_json(workspace_path, new_metadata)\n")], CORE),
    "C12 no replace retry": (CS, [("    for delay in (*_REPLACE_RETRY_DELAYS, None):\n        try:\n            os.replace(source, destination)\n",
                                   "    for delay in (None,):\n        try:\n            os.replace(source, destination)\n")], CORE),
    "C13 rename ignores the seen title": (CS, [("        if expected_title is not None and metadata.get(\"title\") != expected_title:\n", "        if False:\n")], CORE),
    "C14 no chat limit": (CS, [("        if len(listing[\"chats\"]) >= MAX_CHATS_PER_WORKSPACE:\n", "        if False:\n")], CORE),
    "C15 a repeated create with another title passes": (CS, [(
        "            if requested_title is not None and existing.get(\"title\") != requested_title:\n", "            if False:\n")], CORE),
    "C16 lock not reentrant in its thread": (CS, [("    if key in held:  # the same thread", "    if False:  # the same thread")], CORE),
    "C17 control characters in titles": (CS, [("    if _TITLE_FORBIDDEN_RE.search(clean):\n", "    if False:\n")], CORE),
    "C18 locked byte 0 (blocks readers and copies)": (CS, [("_WRITER_LOCK_OFFSET = 1 << 30\n", "_WRITER_LOCK_OFFSET = 0\n")], CORE),
    "C19 published bytes not read back": (CS, [(
        "                time.sleep(delay)\n    finally:\n        try:\n            os.unlink(temp)\n        except FileNotFoundError:\n            pass\n"
        "    _verify_published(anchor, parts, payload)\n",
        "                time.sleep(delay)\n    finally:\n        try:\n            os.unlink(temp)\n        except FileNotFoundError:\n            pass\n")], CORE),
    "C20 no retry for a chat folder that cannot move yet": (CS, [(
        "    for delay in (*_REPLACE_RETRY_DELAYS, None):\n        try:\n            os.rename(staging_dir, chat_dir)\n",
        "    for delay in (None,):\n        try:\n            os.rename(staging_dir, chat_dir)\n")], CORE),
    # the web write path (ultra_chat.py / server.py)
    "H01 the read capability authorises writes": (SRV, [("            self.server.web_alarm_ultra_chat_write_access.require(self.headers)\n",
                                                         "            self.server.web_alarm_ultra_chat_access.require(self.headers)\n")], HTTP),
    "H02 no Origin required for writes": (SRV, [("        if len(self.headers.get_all('Origin', [])) != 1:\n            raise ApiError(403, 'ultra_chat_forbidden', 'A same-origin request is required')\n", "")], HTTP),
    "H03 writes on although reading is off": (SRV, [("        enabled=enable_ultra_chat and enable_ultra_chat_write, loopback=host in LOOPBACK_HOSTS)\n",
                                                     "        enabled=enable_ultra_chat_write, loopback=host in LOOPBACK_HOSTS)\n")], HTTP),
    "H04 any chat_id from the page": (UC, [("_NEW_CHAT_ID_RE = re.compile(r\"^chat_[0-9a-f]{32}$\")\n", "_NEW_CHAT_ID_RE = _CHAT_ID_RE\n")], HTTP),
    "H05 no history check before the core": (UC, [("        if identity[\"status\"] != \"ok\":\n            raise UltraChatError(409, \"workspace_unavailable\"",
                                                   "        if False:\n            raise UltraChatError(409, \"workspace_unavailable\"")], HTTP),
    "H06 the core message reaches the page": (UC, [(
        "        return UltraChatError(status, exc.code if exc.code in _WRITE_REFUSALS else \"storage_write_failed\", message)\n",
        "        return UltraChatError(status, exc.code if exc.code in _WRITE_REFUSALS else \"storage_write_failed\", str(exc))\n")], HTTP),
    "H07 no body size refusal": (SRV, [("            if body_problem == 'too_large':\n", "            if False:\n")], HTTP),
    "H08 the adapter drops the seen title": (UC, [("            chat = core.rename_chat(root, chat_id, body[\"title\"], expected_title=body[\"expected_title\"],\n",
                                                   "            chat = core.rename_chat(root, chat_id, body[\"title\"], expected_title=None,\n")], HTTP),
    # the page (ui.py)
    "J01 both tokens on a write": (UI, [("  try{return await api(path,{method:'POST',headers:{[CHAT_WRITE_HEADER]:chatEdit.token},body})}\n",
                                         "  try{return await api(path,{method:'POST',headers:{[CHAT_WRITE_HEADER]:chatEdit.token,[CHAT_TOKEN_HEADER]:chat.token},body})}\n")], JS),
    "J02 a new chat_id on every Save": (UI, [("title?{chat_id:chatEdit.pendingId,title}:{chat_id:chatEdit.pendingId}", "title?{chat_id:newChatId(),title}:{chat_id:newChatId()}")], JS),
    "J03 the refreshed title not taken after a refusal": (UI, [("      if(fresh)chatEdit.expected=fresh.title\n", "      if(fresh)void 0\n")], JS),
    "J04 no guard while saving": (UI, [("  if(chatEdit.busy||!chatEdit.mode)return;\n", "  if(!chatEdit.mode)return;\n")], JS),
    "J05 the write capability asked at load": (UI, [("function startChat(){if(chat.started)return;chat.started=true;loadChatModel();return loadChatWorkspaces()}",
                                                     "function startChat(){if(chat.started)return;chat.started=true;loadChatModel();loadChatWriteAccess().catch(()=>{});return loadChatWorkspaces()}")], JS),
    "J06 the list not re-read after a change": (UI, [("clearChatHistory('Загружаем историю…');\n  return loadChatList()\n}", "clearChatHistory('Загружаем историю…');\n  return null\n}")], JS),
    "J07 create offered without history": (UI, [("  $('chatNew').disabled=chatEdit.busy||!w||w.history!=='ok';", "  $('chatNew').disabled=chatEdit.busy||!w;")], JS),
    "J08 a Workspace switch keeps the form": (UI, [("function selectChatWorkspace(id){\n  closeChatName();\n", "function selectChatWorkspace(id){\n")], JS),
    "J09 a refused save stays open after a Workspace switch": (UI, [(
        "  if(ws!==chat.workspace){closeChatName();return}// the user moved to another Workspace meanwhile: nothing of the old one stays\n", "")], JS),
    "J10 a taken chat_id does not re-read the list": (UI, [("['title_changed','chat_not_found','chat_id_conflict']", "['title_changed','chat_not_found']")], JS),
    # the Tk writer (ultra_ui.py)
    "T01 Tk rename without the seen title": (TK, [("                expected_title=current[\"title\"],\n", "                expected_title=None,\n")], TKC),
}


def mirror(edits, file_name) -> Path:
    dest = Path(tempfile.mkdtemp(prefix="claude-s2-mirror-"))
    for pattern in ("*.py", "*.js", "*.json"):
        for path in REPO.glob(pattern):
            shutil.copy2(path, dest / path.name)
    (dest / "web_alarm").mkdir()
    for pattern in ("*.py", "*.json"):
        for path in (REPO / "web_alarm").glob(pattern):
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
        compile_target = text if file_name.endswith(".py") and file_name != UI else None
        if compile_target is not None:
            compile(compile_target, file_name, "exec")  # a mutant must stay valid Python (no false kill)
        target.write_bytes((text.replace("\n", "\r\n") if crlf else text).encode("utf-8"))
    return dest


def run(python, dest, kind, targets):
    if kind == "js":
        done = subprocess.run(["node", "--test", *targets], cwd=dest, capture_output=True, text=True, encoding="utf-8")
        failed = sorted({line.split(" - ", 1)[1].split(" ")[0] for line in done.stdout.splitlines() if line.startswith("not ok")})
        return done.returncode, failed, None
    if kind == "tk":
        out = Path(tempfile.mkdtemp(prefix="claude-s2-tk-")) / "tk.json"
        env = dict(os.environ, S2_MIRROR=str(dest))
        done = subprocess.run([python, "-B", str(TOOLS / "tk_contour_check.py"), str(out)], env=env, capture_output=True,
                              text=True, encoding="utf-8", errors="replace", timeout=900)
        record = json.loads(out.read_text(encoding="utf-8")) if out.exists() else {"passed": False, "tk_contour": {"checks": {}}}
        shutil.rmtree(out.parent, ignore_errors=True)
        failed = sorted(k for k, v in record["tk_contour"]["checks"].items() if v is False)
        return (0 if record["passed"] else 1), failed or ([] if record["passed"] else ["tk_contour"]), None
    env = dict(os.environ, CLAUDE_RUN_PREFIX="claude-s2", CLAUDE_TASK_LABEL="CLAUDE-WUA-CHAT-S2-SHARED-STORAGE-001",
               CLAUDE_RUNNER_ROOT=str(dest), PYTHONIOENCODING="utf-8")
    env.pop("CLAUDE_EXTRA_PATH", None)
    done = subprocess.run([python, str(GATE), python, "mutant", *targets], cwd=dest, env=env, capture_output=True,
                          text=True, encoding="utf-8", errors="replace", timeout=1800)
    summary = json.loads(done.stdout)
    shutil.rmtree(summary["base"], ignore_errors=True)  # the runner's own TEMP attempt folder
    failed = sorted({t[0].split(".")[-1].split(" ")[0] for t in summary.get("non_pass", []) if t[1] != "SKIP"})
    return summary["exit"], failed, summary.get("isolation_violations")


def leftovers() -> list[str]:
    """Synthetic folders the tests of this task leave in TEMP (full names, so a new one is never hidden by a mask)."""
    temp = Path(tempfile.gettempdir())
    return sorted(p.name for pattern in ("wa_s2_*", "claude-s2-*", "s2-tk-*") for p in temp.glob(pattern))


def main():
    python, target = sys.argv[1], Path(sys.argv[2])
    chosen = sys.argv[3:] or list(MUTANTS)
    for name in chosen:  # every pattern must occur exactly once before anything runs
        file_name, edits, _ = MUTANTS[name]
        text = (REPO / file_name).read_bytes().decode("utf-8").replace("\r\n", "\n")
        for old, _new in edits:
            if text.count(old) != 1:
                sys.exit(f"{name}: pattern occurs {text.count(old)} times")
    before = set(leftovers())
    controls = {}
    for kind, targets in sorted({MUTANTS[name][2] for name in chosen}):
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
        rows.append({"mutant": name, "file": file_name, "targets": list(targets), "exit": code, "failing_tests": failed,
                     "isolation_violations": isolation, "verdict": verdict})
        print(json.dumps({"mutant": name, "verdict": verdict, "failing": failed}, ensure_ascii=False), flush=True)
    record = {"task": "CLAUDE-WUA-CHAT-S2-SHARED-STORAGE-001", "purpose": "mutation gate of the shared writer, the web write path, the page and the Tk writer (TEST-QA)",
              "controls": controls, "results": rows, "mutants": len(rows), "killed": sum(r["verdict"] == "KILLED" for r in rows),
              "temp_leftovers_new": sorted(set(leftovers()) - before)}
    target.write_text(json.dumps(record, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"mutants": record["mutants"], "killed": record["killed"],
                      "controls": {k: v["verdict"] for k, v in controls.items()}}))


if __name__ == "__main__":
    main()
