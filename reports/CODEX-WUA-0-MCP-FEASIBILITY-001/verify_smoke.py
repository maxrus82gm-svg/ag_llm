"""Reproducible MCP wire smoke with exact checks and original-attempt evidence."""
from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import sys
import tempfile
import time

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
EXPECTED = {"ping", "list_capabilities", "read_synthetic_context"}


def sources() -> dict:
    paths = list((REPO / "web_alarm").glob("*.py")) + [REPO / "server.py", REPO / "ultra_ui.py", HERE / "adapter.py", Path(__file__)]
    return {p.relative_to(REPO).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}


async def run(output: Path) -> dict:
    record = {"task_id": "CODEX-WUA-0-MCP-FEASIBILITY-001", "started_utc": datetime.now(timezone.utc).isoformat(),
              "python": sys.version, "platform": platform.platform(),
              "packages": {k: importlib.metadata.version(k) for k in ("mcp", "httpx", "pydantic")},
              "transport": "stdio MCP -> own disposable loopback HTTP WebAlarmApi", "checks": [],
              "wire_results": [], "source_before": sources()}
    start = time.monotonic()

    def check(name, condition, observed=None):
        record["checks"].append({"id": name, "status": "PASS" if condition else "FAIL", "observed": observed})
        if not condition:
            raise AssertionError(name)

    async def call(session, name, arguments=None):
        result = await session.call_tool(name, arguments or {}, read_timeout_seconds=5)
        raw = result.model_dump(mode="json", exclude_none=True, by_alias=True)
        record["wire_results"].append({"name": name, "arguments": arguments or {}, "result": raw})
        return result

    def unpack(result):
        if result.is_error:
            raise AssertionError(result.model_dump_json())
        if result.structured_content:
            return result.structured_content
        return json.loads(next(item.text for item in result.content if item.type == "text"))

    nonce = None
    stderr_paths = []
    try:
        for attempt in range(2):
            with tempfile.NamedTemporaryFile(mode="w+", encoding="utf-8", delete=False, prefix="wua-mcp-stderr-") as error_file:
                stderr_paths.append(Path(error_file.name))
                params = StdioServerParameters(command=sys.executable, args=["-B", str(HERE / "adapter.py")], cwd=str(HERE))
                async with stdio_client(params, errlog=error_file) as (read, write):
                    async with ClientSession(read, write, read_timeout_seconds=8) as session:
                        init = await session.initialize()
                        check(f"{attempt}:initialize", init.server_info.name == "Web Alarm Synthetic Feasibility", init.model_dump(mode="json", exclude_none=True, by_alias=True))
                        listed = await session.list_tools()
                        check(f"{attempt}:exact_tool_allowlist", {t.name for t in listed.tools} == EXPECTED)
                        check(f"{attempt}:readonly_annotations", all(t.annotations.read_only_hint and not t.annotations.destructive_hint and not t.annotations.open_world_hint for t in listed.tools))
                        check(f"{attempt}:health", unpack(await call(session, "ping"))["service"] == "web_alarm_server")
                        initial = unpack(await call(session, "read_synthetic_context"))
                        check(f"{attempt}:synthetic_context_identity", initial["context"]["TASK"]["task_id"] == "synthetic_wua_0" and initial["synthetic"])
                        check(f"{attempt}:server_owned_projection", initial["context"]["AUTHORITY_SOURCE"] == "lifecycle"
                              and initial["context"]["TASK"]["status"] == "PLANNED"
                              and initial["context"]["CURRENT_STATUS"] == "NO_MICROTASK"
                              and initial["context"]["CHECKPOINT"]["status"] == "MISSING"
                              and not initial["context"]["CHECKPOINT"]["authoritative"], initial["context"])
                        digest = hashlib.sha256(json.dumps(initial["context"], sort_keys=True, ensure_ascii=False).encode()).hexdigest()
                        check(f"{attempt}:context_hash_oracle", digest == initial["content_sha256"])
                        repeated = unpack(await call(session, "read_synthetic_context"))
                        check(f"{attempt}:repeat_read_idempotent", initial == repeated)
                        for key, value in (("foreign_task", "real_production_task"), ("path_traversal", "../../.ultra"), ("absolute_path", "M:/GitHub/ag_llm/.ultra")):
                            rejected = await call(session, "read_synthetic_context", {"fixture_id": value})
                            check(f"{attempt}:reject_{key}", rejected.is_error and any("fixture_id_not_allowlisted" in getattr(x, "text", "") for x in rejected.content))
                        rejected = await call(session, "read_synthetic_context", {"fixture_id": {"bad": "type"}})
                        check(f"{attempt}:schema_reject_wrong_type", rejected.is_error)
                        rejected = await call(session, "execute_mutation")
                        check(f"{attempt}:unknown_mutation_tool_rejected", rejected.is_error)
                        caps = unpack(await call(session, "list_capabilities"))
                        check(f"{attempt}:raw_fixture_bytes_unchanged", caps["storage_unchanged"] and caps["baseline_sha256"] == caps["current_sha256"], caps)
                        check(f"{attempt}:only_allowlisted_gets", len(caps["requests"]) == 3 and all(r["method"] == "GET" for r in caps["requests"]), caps["requests"])
                        check(f"{attempt}:guard_violations_zero", all(v == 0 for v in caps["guard"].values()), caps["guard"])
                        current_nonce = initial["context"]["GOAL"]
                        if nonce is not None:
                            check("fresh_process_new_fixture", nonce != current_nonce)
                        nonce = current_nonce
                error_file.seek(0)
                stderr = error_file.read()
                record.setdefault("child_stderr", []).append(stderr)
        record["source_after"] = sources()
        check("runtime_and_poc_source_hashes_unchanged", record["source_before"] == record["source_after"])
        record["exit_code"] = 0
    except BaseException as exc:
        import traceback
        record["exit_code"] = 1
        record["error"] = {"type": type(exc).__name__, "text": str(exc), "traceback": traceback.format_exc()}
    finally:
        record["child_stderr"] = [p.read_text(encoding="utf-8") for p in stderr_paths]
        for p in stderr_paths:
            p.unlink()
        record["elapsed_seconds"] = round(time.monotonic() - start, 3)
        record["counts"] = {k: sum(c["status"] == k for c in record["checks"]) for k in ("PASS", "FAIL")}
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    return record


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    options = parser.parse_args()
    result = asyncio.run(run(options.output.resolve()))
    print(json.dumps({"counts": result["counts"], "exit_code": result["exit_code"], "elapsed_seconds": result["elapsed_seconds"], "evidence": str(options.output.resolve()), "error": result.get("error")}, ensure_ascii=False))
    raise SystemExit(result["exit_code"])
