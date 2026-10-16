"""Read-only installation/discovery inspection plus cached-server metadata handshake.

No installation, activation, permission/config change, Git or model calls.
The explicit SDK handshake is NOT a Desktop E2E invocation.
"""
from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import tomllib

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import Implementation

HERE = Path(__file__).resolve().parent
CODEX_HOME_PATH = Path("C:/Users/REX/.codex")
CACHE = CODEX_HOME_PATH / "plugins/cache/wua-desktop-e2e-local/wua-desktop-readonly/0.2.0"
CLI = Path("C:/Users/REX/AppData/Local/OpenAI/Codex/bin/9614f1d9b40d9c4f/codex.exe")
PLUGIN_KEY = "wua-desktop-readonly@wua-desktop-e2e-local"


def hashes(root):
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob("*")) if p.is_file()}


def cli_read(arguments):
    result = subprocess.run([str(CLI), *arguments], capture_output=True,
                            text=True, encoding="utf-8", timeout=20)
    try:
        value = json.loads(result.stdout)
    except ValueError:
        value = result.stdout[:1000]
    return {"arguments": arguments, "exit_code": result.returncode,
            "result": value, "stderr": result.stderr[:1500]}


async def inspect_cached_server(record):
    configuration = json.loads((CACHE / "mcp.json").read_bytes())["mcpServers"]["wua_desktop_readonly"]
    evidence = Path(json.loads((CACHE / "local_config.json").read_bytes())["evidence_root"]).resolve()
    if evidence != HERE / "evidence":
        raise RuntimeError("Refusing an unexpected evidence root")
    before = {p.name for p in evidence.iterdir()} if evidence.exists() else set()
    params = StdioServerParameters(command=configuration["command"],
        args=[a.replace("${PLUGIN_ROOT}", str(CACHE)) for a in configuration["args"]],
        cwd=configuration["cwd"].replace("${PLUGIN_ROOT}", str(CACHE)))
    with tempfile.TemporaryFile(mode="w+", encoding="utf-8") as stderr:
        try:
            async with stdio_client(params, errlog=stderr) as (read, write):
                async with ClientSession(read, write, read_timeout_seconds=8,
                    client_info=Implementation(name="WUA Local SDK Regression - Cache Startup Diagnostic", version="0.2.0")) as session:
                    init = await session.initialize()
                    listing = await session.list_tools()
                    record["cache_startup_diagnostic"] = {
                        "kind": "SDK METADATA HANDSHAKE ONLY; NOT DESKTOP E2E",
                        "server": init.server_info.model_dump(mode="json"),
                        "protocol": init.protocol_version,
                        "tools": [t.name for t in listing.tools], "tool_calls": 0,
                        "mcp_requests": ["initialize", "tools/list"],
                    }
        finally:
            stderr.seek(0)
            record["cache_startup_stderr"] = stderr.read()[:4000]
    after = {p.name for p in evidence.iterdir()} if evidence.exists() else set()
    new_sessions = []
    for session_id in sorted(after - before):
        path = evidence / session_id / "session.json"
        proof = json.loads(path.read_bytes())
        new_sessions.append({"path": str(path), "session_id": session_id,
                             "origin": "EXPLICIT SDK CACHE DIAGNOSTIC, NOT HUMAN DESKTOP CHAT",
                             "state": proof["state"], "event_total": proof["event_total"],
                             "storage_unchanged": proof["storage_unchanged"],
                             "guard_denials": proof["guard_denials"],
                             "proof_sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    record["sdk_diagnostic_sessions"] = new_sessions


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(HERE) or output.exists():
        raise SystemExit("Use a NEW output path inside this TASK")
    config_file = CODEX_HOME_PATH / "config.toml"
    raw_config = config_file.read_bytes()
    config = tomllib.loads(raw_config.decode("utf-8-sig"))
    source_before, cache_before = hashes(HERE / "plugin"), hashes(CACHE)
    evidence = HERE / "evidence"
    existing_proofs = list(evidence.glob("*/session.json")) if evidence.exists() else []
    record = {"task_id": "CODEX-WUA-0-DESKTOP-MCP-E2E-001",
              "started_utc": datetime.now(timezone.utc).isoformat(),
              "plugin_config": config.get("plugins", {}).get(PLUGIN_KEY),
              "cache_path": str(CACHE), "source_hashes": source_before,
              "cache_hashes": cache_before, "source_cache_exact_match": source_before == cache_before,
              "host_proofs_before_diagnostic": [str(p) for p in existing_proofs],
              "config_before_sha256": hashlib.sha256(raw_config).hexdigest(),
              "publication": "ON HOLD: latest user instruction forbids GitHub changes without agreement",
              "ordinary_chat_tool_calls": 0, "desktop_e2e": "NOT VERIFIED / MCP TOOLS UNAVAILABLE"}
    try:
        record["marketplace_registry"] = cli_read(["plugin", "marketplace", "list", "--json"])
        record["scoped_plugin_listing"] = cli_read(["plugin", "list", "--marketplace", "wua-desktop-e2e-local", "--json"])
        if source_before != cache_before:
            raise RuntimeError("Installed cache differs; do not launch unverified bytes")
        asyncio.run(inspect_cached_server(record))
    except BaseException as exc:
        import traceback
        record["error"] = {"type": type(exc).__name__, "text": str(exc), "traceback": traceback.format_exc()}
    record["config_unchanged"] = config_file.read_bytes() == raw_config
    record["source_unchanged"] = hashes(HERE / "plugin") == source_before
    record["cache_unchanged"] = hashes(CACHE) == cache_before
    names = [x.get("name") for x in record.get("marketplace_registry", {}).get("result", {}).get("marketplaces", [])]
    record["wua_marketplace_registered"] = "wua-desktop-e2e-local" in names
    record["diagnostic_complete"] = "error" not in record and all(record[k] for k in ("config_unchanged", "source_unchanged", "cache_unchanged"))
    output.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"diagnostic_complete": record["diagnostic_complete"],
                      "wua_marketplace_registered": record["wua_marketplace_registered"],
                      "cache_startup": record.get("cache_startup_diagnostic"),
                      "sdk_sessions": record.get("sdk_diagnostic_sessions"),
                      "config_unchanged": record["config_unchanged"], "cache_unchanged": record["cache_unchanged"],
                      "desktop_e2e": record["desktop_e2e"], "error": record.get("error")}, ensure_ascii=False))
    raise SystemExit(0 if record["diagnostic_complete"] else 1)
