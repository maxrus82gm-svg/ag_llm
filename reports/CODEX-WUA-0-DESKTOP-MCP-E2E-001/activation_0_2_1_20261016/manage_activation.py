"""Scoped WUA installation, evidence, and guarded rollback. No GUI automation."""
from pathlib import Path
import argparse
import copy
import ctypes
from ctypes import wintypes
import datetime
import hashlib
import json
import os
import re
import shutil
import subprocess
import tomllib
import zipfile

HERE = Path(__file__).resolve().parent
TASK = HERE.parent
SOURCE = TASK / "plugin"
CONFIG = Path("C:/Users/REX/.codex/config.toml")
CACHE = Path("C:/Users/REX/.codex/plugins/cache/wua-desktop-e2e-local/wua-desktop-readonly")
CLI = Path("C:/Users/REX/AppData/Local/OpenAI/Codex/bin/9614f1d9b40d9c4f/codex.exe")
KEY = "wua-desktop-readonly@wua-desktop-e2e-local"
MARKETPLACE = "wua-desktop-e2e-local"
CATALOG = TASK / ".agents/plugins/marketplace.json"
PACKAGE = HERE / "package/plugin"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def save(name, value):
    (HERE / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read(name):
    return json.loads((HERE / name).read_text(encoding="utf-8"))


def tree(folder):
    return {p.relative_to(folder).as_posix(): digest(p.read_bytes())
            for p in sorted(folder.rglob("*")) if p.is_file()}


def config_summary(raw):
    value = tomllib.loads(raw.decode("utf-8-sig"))
    other = copy.deepcopy(value)
    setting = other.get("plugins", {}).pop(KEY, None)
    # The user's authorization also covers registering this one local source.
    other.get("marketplaces", {}).pop(MARKETPLACE, None)
    return {
        "file_sha256": digest(raw),
        "wua_plugin_setting": setting,
        "all_other_settings_sha256": digest(json.dumps(other, sort_keys=True, ensure_ascii=False).encode()),
        "all_mcp_settings_sha256": digest(json.dumps(value.get("mcp_servers", {}), sort_keys=True).encode()),
    }


def other_cache_metadata_digest():
    root = CACHE.parent.parent
    rows = []
    for parent, dirs, names in os.walk(root):
        directory = Path(parent)
        if directory == CACHE:
            dirs[:] = []
            continue
        for name in names:
            p = directory / name
            stat = p.stat()
            rows.append((p.relative_to(root).as_posix(), stat.st_size, stat.st_mtime_ns))
    return digest(json.dumps(sorted(rows), ensure_ascii=False).encode())


class Blob(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_ubyte))]


def dpapi(raw, protect):
    # No plaintext copy of other connections, secrets, or tokens is persisted.
    buffer = (ctypes.c_ubyte * len(raw)).from_buffer_copy(raw)
    source = Blob(len(raw), buffer)
    target = Blob()
    crypto = ctypes.WinDLL("crypt32", use_last_error=True)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    function = crypto.CryptProtectData if protect else crypto.CryptUnprotectData
    function.argtypes = [ctypes.POINTER(Blob), ctypes.c_void_p, ctypes.c_void_p,
                         ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(Blob)]
    function.restype = wintypes.BOOL
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    kernel.LocalFree.restype = ctypes.c_void_p
    if not function(ctypes.byref(source), None, None, None, None, 1, ctypes.byref(target)):
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        return ctypes.string_at(target.pbData, target.cbData)
    finally:
        kernel.LocalFree(target.pbData)


def cli_call(label, args):
    run = subprocess.run([str(CLI), *args], cwd=TASK, capture_output=True,
                         encoding="utf-8", timeout=60)
    if run.returncode:
        save(label + ".json", {"args": args, "exit_code": run.returncode,
                               "stderr": run.stderr, "stdout": run.stdout})
        raise RuntimeError(f"{label} failed; inspect task-local evidence")
    result = json.loads(run.stdout)
    # These commands are explicitly scoped to the one WUA marketplace/plugin.
    save(label + ".json", {"args": args, "exit_code": 0, "result": result, "stderr": run.stderr})
    return result


def snapshot():
    if (HERE / "baseline.json").exists():
        raise RuntimeError("Baseline already exists; never overwrite it")
    expected = json.loads((TASK / "amendment_04/candidate_manifest.json").read_text(encoding="utf-8-sig"))["files"]
    actual = tree(SOURCE)
    extra = {p: h for p, h in actual.items() if p not in expected}
    unexpected = [p for p in extra if not re.fullmatch(
        r"CODEX-WUA-0-DESKTOP-MCP-E2E-001/evidence/[0-9a-f]{32}/session\.json", p)]
    if any(actual.get(p) != h for p, h in expected.items()) or unexpected:
        save("candidate_mismatch.json", {
            "missing": sorted(set(expected) - set(actual)),
            "extra": sorted(set(actual) - set(expected)),
            "changed": [p for p in actual.keys() & expected.keys() if actual[p] != expected[p]],
        })
        raise RuntimeError("Candidate does not match the sealed AMENDMENT 04 manifest")
    raw = CONFIG.read_bytes()
    encrypted = dpapi(raw, True)
    (HERE / "config.before.dpapi").write_bytes(encrypted)
    if dpapi(encrypted, False) != raw:
        raise RuntimeError("Encrypted backup round-trip failed")
    cached = tree(CACHE)
    catalog = CATALOG.read_bytes()
    (HERE / "marketplace.before.json").write_bytes(catalog)
    with zipfile.ZipFile(HERE / "wua-cache.before.zip", "w", zipfile.ZIP_DEFLATED) as archive:
        for relative in cached:
            archive.write(CACHE / relative, relative)
    baseline = {
        "task_id": TASK.name,
        "utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "authorization": "User explicitly authorized installation and activation of candidate 0.2.1; no GUI automation or other MCP changes.",
        "config": config_summary(raw),
        "config_dpapi_roundtrip": True,
        "cache_versions": sorted(p.name for p in CACHE.iterdir() if p.is_dir()),
        "cache_files": cached,
        "candidate_files": expected,
        "existing_source_receipts": extra,
        "catalog_sha256": digest(catalog),
        "other_plugin_cache_metadata_sha256": other_cache_metadata_digest(),
        "amendment_04_protected": {name: digest((TASK / "amendment_04" / name).read_bytes())
                                    for name in ("report.md", "candidate_manifest.json", "integrity.json")},
    }
    save("baseline.json", baseline)
    cli_call("plugin_list.before", ["plugin", "list", "--marketplace", MARKETPLACE, "--json"])
    print(json.dumps({"snapshot": "PASS", "candidate_files": len(expected),
                      "source_receipts_preserved_outside_install_payload": len(extra),
                      "cache_versions": baseline["cache_versions"], "encrypted_backup": True}))


def install():
    before = read("baseline.json")
    if config_summary(CONFIG.read_bytes()) != before["config"] or tree(CACHE) != before["cache_files"]:
        raise RuntimeError("Working state changed since snapshot; installation not attempted")
    if any(digest((SOURCE / p).read_bytes()) != h for p, h in before["candidate_files"].items()):
        raise RuntimeError("Candidate changed since snapshot")
    if CATALOG.read_bytes() != (HERE / "marketplace.before.json").read_bytes():
        raise RuntimeError("WUA marketplace changed since snapshot")
    if PACKAGE.exists():
        raise RuntimeError("Clean install package already exists; inspect evidence before retry")
    PACKAGE.mkdir(parents=True)
    for relative in before["candidate_files"]:
        source = SOURCE / relative
        if not source.resolve().is_relative_to(SOURCE.resolve()):
            raise RuntimeError("Source file escapes candidate root")
        target = PACKAGE / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    if tree(PACKAGE) != before["candidate_files"]:
        raise RuntimeError("Clean package copy mismatch")
    old_catalog = CATALOG.read_bytes()
    catalog = json.loads(old_catalog.decode("utf-8-sig"))
    if catalog["name"] != MARKETPLACE or len(catalog["plugins"]) != 1:
        raise RuntimeError("Marketplace is not the dedicated WUA-only catalog")
    entry = catalog["plugins"][0]
    if entry["name"] != "wua-desktop-readonly" or entry["source"] != {"source": "local", "path": "./plugin"}:
        raise RuntimeError("Unexpected WUA marketplace source")
    new_path = "./" + PACKAGE.relative_to(TASK).as_posix()
    old_token = json.dumps("./plugin").encode()
    if old_catalog.count(old_token) != 1:
        raise RuntimeError("Marketplace source token is not unique")
    updated = old_catalog.replace(old_token, json.dumps(new_path).encode(), 1)
    CATALOG.write_bytes(updated)
    save("marketplace.update.json", {"before_sha256": digest(old_catalog),
         "after_sha256": digest(updated), "source_before": "./plugin", "source_after": new_path,
         "purpose": "Install only sealed candidate files; keep mutable preexisting synthetic receipts out of new cache."})
    result = cli_call("plugin_install", ["plugin", "add", KEY, "--json"])
    print(json.dumps(result, ensure_ascii=False))


def verify():
    before = read("baseline.json")
    if (HERE / "installation_verification.json").exists() and not (HERE / "installation_verification.initial.json").exists():
        shutil.copy2(HERE / "installation_verification.json", HERE / "installation_verification.initial.json")
    # Reuse the successful readback; do not refresh unrelated catalog markers.
    if not (HERE / "plugin_list.after.json").exists():
        cli_call("plugin_list.after", ["plugin", "list", "--marketplace", MARKETPLACE, "--json"])
    now = config_summary(CONFIG.read_bytes())
    cached = tree(CACHE)
    versions = sorted(p.name for p in CACHE.iterdir() if p.is_dir())
    old_files_unchanged = all(cached.get(p) == value for p, value in before["cache_files"].items())
    new_roots = [CACHE / version for version in versions if version not in before["cache_versions"]]
    matching = [str(p) for p in new_roots if tree(p) == before["candidate_files"]]
    with zipfile.ZipFile(HERE / "wua-cache.before.zip") as archive:
        backup_files = {name: digest(archive.read(name)) for name in archive.namelist()}
    old_backup_exact = backup_files == before["cache_files"]
    removed_old_files = sorted(set(before["cache_files"]) - set(cached))
    modified_old_files = [p for p in before["cache_files"].keys() & cached.keys()
                          if before["cache_files"][p] != cached[p]]
    current_other_metadata_matches = other_cache_metadata_digest() == before["other_plugin_cache_metadata_sha256"]
    boundary_other_metadata_matches = (read("installation_verification.initial.json")["other_plugin_cache_metadata_unchanged"]
                                       if (HERE / "installation_verification.initial.json").exists()
                                       else current_other_metadata_matches)
    result = {
        "config": now,
        "cache_versions": versions,
        "new_cache_roots": [str(p) for p in new_roots],
        "exact_candidate_cache_roots": matching,
        "old_wua_cache_files_unchanged": old_files_unchanged,
        "old_wua_cache_backup_byte_exact": old_backup_exact,
        "old_wua_cache_files_pruned_by_native_installer": removed_old_files,
        "unexpected_modifications_to_retained_old_cache_files": modified_old_files,
        "other_config_settings_unchanged": now["all_other_settings_sha256"] == before["config"]["all_other_settings_sha256"],
        "all_direct_mcp_settings_unchanged": now["all_mcp_settings_sha256"] == before["config"]["all_mcp_settings_sha256"],
        "other_plugin_cache_metadata_unchanged": current_other_metadata_matches,
        "other_plugin_cache_metadata_unchanged_at_install_boundary": boundary_other_metadata_matches,
        "later_other_cache_metadata_note": "A later observation found rewritten .codex-remote-plugin-install.json markers. No unrelated config was changed. Attribution to a CLI read or background app refresh is unproven; markers were not restored or edited.",
        "amendment_04_evidence_unchanged": all(digest((TASK / "amendment_04" / p).read_bytes()) == h for p, h in before["amendment_04_protected"].items()),
        "sealed_candidate_source_unchanged": all(digest((SOURCE / p).read_bytes()) == h for p, h in before["candidate_files"].items()),
        "preexisting_source_receipts_preserved": all((SOURCE / p).exists() for p in before["existing_source_receipts"]),
        "catalog_after_sha256": digest(CATALOG.read_bytes()),
        "wua_enabled": bool((now["wua_plugin_setting"] or {}).get("enabled")),
        "cache_files": cached,
        "ordinary_chat_status": "DESKTOP E2E NOT VERIFIED",
        "running_desktop_reloaded": False,
    }
    result["installation_verified"] = bool(matching) and all(result[p] for p in [
        "old_wua_cache_backup_byte_exact", "other_config_settings_unchanged", "all_direct_mcp_settings_unchanged",
        "other_plugin_cache_metadata_unchanged_at_install_boundary", "amendment_04_evidence_unchanged", "wua_enabled",
        "sealed_candidate_source_unchanged", "preexisting_source_receipts_preserved"]) and not modified_old_files
    save("installation_verification.json", result)
    print(json.dumps({p: v for p, v in result.items() if p not in (
        "cache_files", "old_wua_cache_files_pruned_by_native_installer")}, ensure_ascii=False))
    if not result["installation_verified"]:
        raise RuntimeError("Installation verification incomplete; do not claim activation")


def register_install():
    before = read("baseline.json")
    if CONFIG.read_bytes() != dpapi((HERE / "config.before.dpapi").read_bytes(), False):
        raise RuntimeError("Configuration changed since snapshot; registration not attempted")
    if tree(CACHE) != before["cache_files"] or tree(PACKAGE) != before["candidate_files"]:
        raise RuntimeError("WUA cache or prepared package changed")
    cli_call("marketplace_add", ["plugin", "marketplace", "add", str(TASK), "--json"])
    now = config_summary(CONFIG.read_bytes())
    if now["all_other_settings_sha256"] != before["config"]["all_other_settings_sha256"]:
        raise RuntimeError("Registration changed settings outside the one WUA source")
    result = cli_call("plugin_install.after_registration", ["plugin", "add", KEY, "--json"])
    print(json.dumps(result, ensure_ascii=False))


def rollback(apply):
    before, after = read("baseline.json"), read("installation_verification.json")
    if config_summary(CONFIG.read_bytes()) != after["config"]:
        raise RuntimeError("Config changed after installation; refuse to overwrite later edits")
    current = tree(CACHE)
    if current != after["cache_files"]:
        raise RuntimeError("WUA cache changed after installation; preserve new receipts before planning rollback")
    if digest(CATALOG.read_bytes()) != after["catalog_after_sha256"]:
        raise RuntimeError("WUA marketplace changed after installation; refuse to overwrite later edits")
    new_roots = [Path(p).resolve() for p in after["new_cache_roots"]]
    for p in new_roots:
        if p.parent != CACHE.resolve() or p.name in before["cache_versions"] or p.is_symlink():
            raise RuntimeError("Rollback path escapes the new WUA version scope")
    original = dpapi((HERE / "config.before.dpapi").read_bytes(), False)
    if digest(original) != before["config"]["file_sha256"]:
        raise RuntimeError("Backup integrity mismatch")
    result = {"dry_run": not apply, "guard_checks": "PASS",
              "new_wua_cache_roots_only": [str(p) for p in new_roots],
              "config_restore_needed": CONFIG.read_bytes() != original,
              "restore_old_cache_files": len(before["cache_files"])}
    with zipfile.ZipFile(HERE / "wua-cache.before.zip") as archive:
        if {name: digest(archive.read(name)) for name in archive.namelist()} != before["cache_files"]:
            raise RuntimeError("Original WUA cache backup integrity mismatch")
        for name in archive.namelist():
            target = (CACHE / name).resolve()
            if not target.is_relative_to(CACHE.resolve()) or target == CACHE.resolve():
                raise RuntimeError("Original cache backup path escapes WUA scope")
    if apply:
        # Only user-requested rollback: no uninstall command that removes old cache.
        for p in new_roots:
            shutil.rmtree(p)
        with zipfile.ZipFile(HERE / "wua-cache.before.zip") as archive:
            for name in archive.namelist():
                target = CACHE / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(archive.read(name))
        if CONFIG.read_bytes() != original:
            CONFIG.write_bytes(original)
        CATALOG.write_bytes((HERE / "marketplace.before.json").read_bytes())
        if tree(CACHE) != before["cache_files"] or CONFIG.read_bytes() != original:
            raise RuntimeError("Rollback readback mismatch")
        result["restored_byte_exact"] = True
    save("rollback.applied.json" if apply else "rollback.dry_run.json", result)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["snapshot", "install", "register-install", "verify", "rollback"])
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    if args.apply and args.action != "rollback":
        parser.error("--apply is only for an explicitly requested rollback")
    if args.action == "rollback":
        rollback(args.apply)
    else:
        {"snapshot": snapshot, "install": install, "register-install": register_install, "verify": verify}[args.action]()
