"""Research-only stdio MCP -> disposable Web Alarm HTTP. Never opens live storage."""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
from pathlib import Path
import secrets
import sys
import tempfile
import threading
import urllib.request

sys.dont_write_bytecode = True
REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations
from web_alarm.server import WebAlarmApi, create_server

FIXTURE_ID = "synthetic_wua_0"
TOOL_NAMES = ["ping", "list_capabilities", "read_synthetic_context"]
MAX_RESPONSE_BYTES = 65536


def tree_hash(root: Path) -> str:
    entries = {
        p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(root.rglob("*")) if p.is_file()
    }
    return hashlib.sha256(json.dumps(entries, sort_keys=True).encode()).hexdigest()


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("redirect_denied")


def main() -> None:
    # Windows creates an internal socketpair when constructing the event loop.
    # Construct it before restricting all later connections to the fixture port.
    runner = asyncio.Runner()
    runner.get_loop()
    with tempfile.TemporaryDirectory(prefix="wua-mcp-") as raw_root:
        root = Path(raw_root).resolve()
        guard = {"denied_network": 0, "denied_file_writes": 0, "denied_subprocess": 0}
        allowed_port = [None]

        def audit(event, args):
            if event == "socket.connect":
                address = args[1]
                if address != ("127.0.0.1", allowed_port[0]):
                    guard["denied_network"] += 1
                    raise PermissionError("only_own_fixture_loopback_allowed")
            elif event == "socket.bind":
                if args[1] != ("127.0.0.1", 0):
                    guard["denied_network"] += 1
                    raise PermissionError("only_ephemeral_loopback_bind_allowed")
            elif event in {"subprocess.Popen", "os.system", "os.posix_spawn"}:
                guard["denied_subprocess"] += 1
                raise PermissionError("child_process_denied")
            elif event == "open" and not isinstance(args[0], int):
                flags = args[2]
                if isinstance(flags, int) and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND):
                    if not Path(args[0]).resolve().is_relative_to(root):
                        guard["denied_file_writes"] += 1
                        raise PermissionError("write_outside_disposable_fixture_denied")

        sys.addaudithook(audit)
        project = root / "project"
        project.mkdir()
        nonce = secrets.token_hex(12)
        api = WebAlarmApi(root / "state")
        status, _ = api.dispatch("POST", "/workspaces", {
            "workspace_id": "synthetic_ws", "display_name": "Synthetic WUA fixture",
            "workspace_root": str(project),
        })
        if status != 201:
            raise RuntimeError("fixture_workspace_setup_failed")
        status, _ = api.dispatch("POST", "/tasks", {
            "workspace_id": "synthetic_ws", "task_id": FIXTURE_ID,
            "title": "Synthetic MCP research", "raw_task": "Synthetic read-only test; no real TASK.",
            "goal": "Synthetic nonce: " + nonce,
        })
        if status != 201:
            raise RuntimeError("fixture_task_setup_failed")
        server = create_server(api, host="127.0.0.1", port=0)
        allowed_port[0] = server.server_address[1]
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
        request_log: list[dict] = []
        baseline = tree_hash(root)

        def get(path: str) -> dict:
            if path not in {"/status", f"/tasks/{FIXTURE_ID}/context"}:
                raise ValueError("route_not_allowlisted")
            request_log.append({"method": "GET", "path": path})
            with opener.open(f"http://127.0.0.1:{allowed_port[0]}{path}", timeout=3) as response:
                data = response.read(MAX_RESPONSE_BYTES + 1)
            if len(data) > MAX_RESPONSE_BYTES:
                raise ValueError("response_too_large")
            return json.loads(data)

        mcp = MCPServer(
            "Web Alarm Synthetic Feasibility", version="0.1.0",
            instructions="Research-only. All data is synthetic. Only three read tools; no model, Git or mutation tools.",
        )
        hints = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False)

        @mcp.tool(annotations=hints)
        def ping() -> dict:
            """Check the disposable Web Alarm HTTP fixture. Never contacts the real server."""
            value = get("/status")
            return {"status": value["status"], "service": value["service"],
                    "api_version": value["api_version"], "synthetic": True}

        @mcp.tool(annotations=hints)
        def list_capabilities() -> dict:
            """List the explicit read-only allowlist and fixture isolation diagnostics."""
            current = tree_hash(root)
            return {"schema_version": 1, "tools": TOOL_NAMES, "synthetic": True,
                    "mutations": False, "model_api": False, "guard": dict(guard),
                    "storage_unchanged": current == baseline, "baseline_sha256": baseline,
                    "current_sha256": current, "requests": list(request_log),
                    "fixture_id": FIXTURE_ID}

        @mcp.tool(annotations=hints)
        def read_synthetic_context(fixture_id: str = FIXTURE_ID) -> dict:
            """Read the single synthetic TASK through Web Alarm's server-owned context endpoint."""
            if fixture_id != FIXTURE_ID:
                raise ToolError("fixture_id_not_allowlisted")
            pack = get(f"/tasks/{FIXTURE_ID}/context")
            value = {k: pack[k] for k in (
                "PACK_VERSION", "TASK", "GOAL", "CURRENT_STATUS", "NEXT_SAFE_ACTION",
                "AUTHORITY_SOURCE", "CHECKPOINT", "PROJECTION", "PROTOCOL_RULES",
            )}
            data = json.dumps(value, sort_keys=True, ensure_ascii=False).encode("utf-8")
            return {"synthetic": True, "fixture_id": FIXTURE_ID, "context": value,
                    "content_sha256": hashlib.sha256(data).hexdigest(),
                    "provenance": "disposable WebAlarmApi GET /tasks/synthetic_wua_0/context"}

        try:
            runner.run(mcp.run_stdio_async())
        finally:
            server.shutdown()
            server.server_close()
            worker.join(timeout=5)
            runner.close()


if __name__ == "__main__":
    main()
