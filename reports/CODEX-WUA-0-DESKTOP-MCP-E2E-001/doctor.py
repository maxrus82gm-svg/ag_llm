"""Read-only local manifest/runtime readiness; does not install/register anything."""
from __future__ import annotations

import hashlib
import importlib.metadata
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
PLUGIN = HERE / "plugin"
portable = json.loads((PLUGIN / "plugin.json").read_bytes())
mcps = json.loads((PLUGIN / "mcp.json").read_bytes())["mcpServers"]
market = json.loads((HERE / ".agents/plugins/marketplace.json").read_bytes())
entry = market["plugins"][0]
server = mcps["wua_desktop_readonly"]
vendor = json.loads((PLUGIN / "vendor_manifest.json").read_bytes())
actual = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (PLUGIN / "vendor/web_alarm").glob("*.py")}
config = json.loads((PLUGIN / "local_config.json").read_bytes())
checks = {
    "plugin_and_marketplace_names": portable["name"] == entry["name"] == "wua-desktop-readonly",
    "marketplace_source_resolves_to_plugin": (HERE / entry["source"]["path"]).resolve() == PLUGIN.resolve(),
    "local_stdio": server["type"] == "stdio" and "url" not in server,
    "python_exists": Path(server["command"]).is_file(),
    "cache_relative_entrypoint": "${PLUGIN_ROOT}/server.py" in server["args"] and server["cwd"] == "${PLUGIN_ROOT}",
    "mcp_version": importlib.metadata.version("mcp") == "2.2.0",
    "frozen_vendor_hashes": actual == vendor,
    "evidence_root_within_task": Path(config["evidence_root"]).resolve() == HERE / "evidence",
    "read_only_display_metadata": portable["extensions"]["com.openai"]["interface"]["capabilities"] == ["Read"],
}
result = {"kind": "LOCAL_READINESS_NOT_DESKTOP_E2E", "checks": checks,
          "PASS": all(checks.values()), "python": sys.version,
          "packages": {n: importlib.metadata.version(n) for n in ("mcp", "httpx", "pydantic")},
          "config_or_permission_changes": False}
print(json.dumps(result, ensure_ascii=False, indent=2))
raise SystemExit(0 if result["PASS"] else 1)
