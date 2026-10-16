"""TASK-scoped launcher for the official OpenAI tunnel client; no global setup."""
import argparse
import getpass
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

BASE = Path(__file__).resolve().parent
TASK = BASE.parent
PAYLOAD = TASK / "activation_0_2_1_20261016/package/plugin"
CLIENT = BASE / "tools/tunnel-client.exe"
PROFILE = BASE / "wua-stdio.template.yaml"


def check():
    manifest = json.loads((TASK / "amendment_04/candidate_manifest.json").read_text(encoding="utf-8"))
    for relative, expected in manifest["files"].items():
        target = (PAYLOAD / relative).resolve()
        if not target.is_relative_to(PAYLOAD.resolve()):
            raise RuntimeError("Unexpected payload manifest path")
        if hashlib.sha256(target.read_bytes()).hexdigest() != expected:
            raise RuntimeError("Sealed WUA payload changed: " + relative)
    integrity = json.loads((BASE / "portable_client_integrity.json").read_text(encoding="utf-8"))
    expected_client = next(row["sha256"] for row in integrity["extracted_files"] if row["path"] == "tunnel-client.exe")
    if hashlib.sha256(CLIENT.read_bytes()).hexdigest() != expected_client:
        raise RuntimeError("Official tunnel-client binary changed")
    return {"sealed_wua_files_verified": len(manifest["files"]), "tunnel_client_hash_verified": True,
            "profile": str(PROFILE), "live_tunnel_started": False,
            "hosted_tunnel_activation": "ON_HOLD_BY_USER",
            "mandatory_egress": "V2Ray only; direct internet prohibited",
            "v2ray_route_verified": False, "proxy_fail_closed_verified": False,
            "ordinary_chat_calls": 0, "desktop_e2e": "DESKTOP E2E NOT VERIFIED"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", action="store_true", help="Start a foreground tunnel after local credential entry")
    parser.add_argument("--tunnel-id", help="Existing real tunnel_id, associated with the target ChatGPT workspace")
    args = parser.parse_args()
    if args.start:
        raise RuntimeError(
            "HOSTED_TUNNEL_ON_HOLD_BY_USER: mandatory V2Ray routing and proxy fail-closed "
            "are not verified. Live startup requires a separately agreed next stage. "
            "No credentials read; no tunnel process started."
        )
    checked = check()
    if not args.start:
        print(json.dumps(checked, ensure_ascii=False, indent=2))
        return 0

    print("This starts the official outbound OpenAI tunnel for the sealed synthetic WUA server.")
    print("It does not register a ChatGPT plugin or change any existing MCP connection.")
    tunnel_id = args.tunnel_id or input("Existing tunnel_id: ").strip()
    if not re.fullmatch(r"tunnel_[A-Za-z0-9_-]{8,128}", tunnel_id):
        raise ValueError("Enter a real tunnel_id from Platform; no example ID is accepted here")
    if tunnel_id == "tunnel_0123456789abcdef0123456789abcdef":
        raise ValueError("The documentation example tunnel_id is not a real setup")
    runtime_key = getpass.getpass("Restricted runtime API key (hidden input; never paste into chat): ")
    if not runtime_key or any(c.isspace() for c in runtime_key):
        raise ValueError("A nonempty runtime API key is required")

    # Remove only this child's documented tunnel-client overrides. Preserve the
    # user's existing OS/network environment, including standard HTTPS proxy use.
    child_env = os.environ.copy()
    documented_names = set(re.findall(r"env\.([A-Z][A-Z0-9_]*)", (BASE / "run_help.txt").read_text(encoding="utf-8")))
    documented_names.update(re.findall(r"^  ([A-Z][A-Z0-9_]*)\t", (BASE / "run_help.txt").read_text(encoding="utf-8"), re.MULTILINE))
    documented_names.update({"OPENAI_API_KEY", "OPENAI_ADMIN_KEY", "CONTROL_PLANE_API_KEY", "WUA_TUNNEL_RUNTIME_KEY"})
    for name in documented_names:
        child_env.pop(name, None)
    child_env["WUA_TUNNEL_RUNTIME_KEY"] = runtime_key
    command = [str(CLIENT), "run", "--config", str(PROFILE),
               "--control-plane.tunnel-id", tunnel_id,
               "--control-plane.api-key", "env:WUA_TUNNEL_RUNTIME_KEY",
               "--mcp.stdio-send-initialized-notification",
               "--mcp.max-concurrent-requests", "1",
               "--health.listen-addr", "127.0.0.1:0",
               "--health.url-file", str(BASE / "runtime-health.url"),
               "--pid.file", str(BASE / "runtime.pid")]
    (BASE / "last_launch.json").write_text(json.dumps({
        "tunnel_id": tunnel_id, "payload": str(PAYLOAD),
        "command_without_secrets": command, "key_storage": "child environment only",
        "foreground": True, "desktop_e2e": "DESKTOP E2E NOT VERIFIED"
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Keep this window open for ChatGPT discovery and four real tool calls. Ctrl+C stops only this new tunnel.")
    child = None
    try:
        child = subprocess.Popen(command, cwd=BASE, env=child_env)
        return child.wait()
    except KeyboardInterrupt:
        if child is not None:
            try:
                child.wait(timeout=8)
            except subprocess.TimeoutExpired:
                child.terminate()
                child.wait(timeout=8)
        return 130
    finally:
        child_env.pop("WUA_TUNNEL_RUNTIME_KEY", None)
        runtime_key = None


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, RuntimeError, KeyError, StopIteration) as error:
        print("WUA tunnel preparation stopped: " + str(error), file=sys.stderr)
        sys.exit(1)
