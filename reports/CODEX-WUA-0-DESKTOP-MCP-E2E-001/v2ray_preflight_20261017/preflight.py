"""Read-only local proxy inventory; serialize allowlisted, deidentified fields only."""
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import urllib.parse

HERE = Path(__file__).resolve().parent
PUBLIC_TARGETS = {"api.openai.com", "mtls.api.openai.com", "openai.com", "chatgpt.com"}


def ps(script):
    p = subprocess.run(["powershell.exe", "-NoProfile", "-Command", script],
                       capture_output=True, encoding="utf-8-sig", errors="replace", timeout=20)
    if p.returncode:
        raise RuntimeError("Read-only PowerShell inventory failed; raw output withheld")
    return json.loads(p.stdout or "null")


def host_class(value):
    if not isinstance(value, str):
        return "not-recorded"
    if value in PUBLIC_TARGETS:
        return "allowlisted-openai-domain"
    if value in {"localhost", "local", "system"}:
        return "local-or-system"
    try:
        address = ipaddress.ip_address(value)
        return "loopback" if address.is_loopback else "nonloopback-address-redacted"
    except ValueError:
        return "hostname-redacted"


def main():
    processes = ps("[Console]::OutputEncoding=[Text.UTF8Encoding]::new(); @(" 
                   "Get-CimInstance Win32_Process | Where-Object { $_.Name -match "
                   r"'^(v2rayN|v2ray|xray|sing-box)\.exe$' } | "
                   "Select-Object Name,ProcessId,ParentProcessId,ExecutablePath,CommandLine) | ConvertTo-Json -Depth 3")
    processes = processes or []
    if isinstance(processes, dict):
        processes = [processes]
    ports = ps("[Console]::OutputEncoding=[Text.UTF8Encoding]::new(); @(" 
               "Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue | "
               "Select-Object LocalAddress,LocalPort,OwningProcess) | ConvertTo-Json -Depth 3") or []
    if isinstance(ports, dict):
        ports = [ports]
    result = {"processes": [], "configs": [], "environment": {},
              "external_requests": 0, "live_config_writes": 0,
              "subscriptions_or_raw_credentials_exported": False}
    for name in ["HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY"]:
        value = os.environ.get(name)
        row = {"present": bool(value)}
        if value and name != "NO_PROXY":
            u = urllib.parse.urlsplit(value)
            row.update(scheme=u.scheme, host_class=host_class(u.hostname), credentials_present=bool(u.username or u.password))
        result["environment"][name] = row
    for proc in processes:
        pid = proc["ProcessId"]
        listeners = [{"address": r["LocalAddress"] if host_class(r["LocalAddress"]) == "loopback" else "nonloopback-redacted",
                      "port": r["LocalPort"]} for r in ports if r["OwningProcess"] == pid]
        result["processes"].append({"name": proc["Name"], "pid": pid, "parent_pid": proc.get("ParentProcessId"), "listeners": listeners,
            "executable_sha256": hashlib.sha256(Path(proc["ExecutablePath"]).read_bytes()).hexdigest() if proc.get("ExecutablePath") else None})
        if proc["Name"].lower() not in {"sing-box.exe", "v2ray.exe", "xray.exe"}:
            continue
        tokens = shlex.split(proc.get("CommandLine") or "", posix=False)
        candidates = []
        for i, token in enumerate(tokens[:-1]):
            if token in {"-c", "--config"}:
                candidates.append(tokens[i + 1].strip('"'))
        for candidate in candidates:
            path = Path(candidate)
            resolution = "absolute-process-argument"
            if not path.is_absolute():
                manager = next((p for p in processes if p["ProcessId"] == proc.get("ParentProcessId")), None)
                bases = [Path(proc["ExecutablePath"]).parent]
                if manager and manager.get("ExecutablePath"):
                    parent = Path(manager["ExecutablePath"]).parent
                    bases.extend([parent, parent / "binConfigs"])
                found = list(dict.fromkeys((base / path).resolve() for base in bases if (base / path).is_file()))
                if len(found) == 1:
                    path = found[0]
                    resolution = "unique-manager-relative-candidate; actual-process-cwd-not-read"
            if not path.is_absolute() or not path.is_file():
                result["configs"].append({"process_pid": pid, "status": "ACTIVE_CONFIG_PATH_NOT_RESOLVED"})
                continue
            raw = path.read_bytes()
            try:
                config = json.loads(raw.decode("utf-8-sig"))
            except (ValueError, UnicodeError):
                result["configs"].append({"process_pid": pid, "status": "CONFIG_NOT_STANDARD_JSON", "sha256": hashlib.sha256(raw).hexdigest()})
                continue
            outbounds = config.get("outbounds", [])
            tags = {o.get("tag"): "outbound_" + str(i + 1) for i, o in enumerate(outbounds)}
            inbound_tags = {o.get("tag"): "inbound_" + str(i + 1) for i, o in enumerate(config.get("inbounds", []))}
            rule_sets = config.get("route", {}).get("rule_set", [])
            sets = {o.get("tag"): "ruleset_" + str(i + 1) for i, o in enumerate(rule_sets)}
            dns_tags = {o.get("tag"): "dns_" + str(i + 1) for i, o in enumerate(config.get("dns", {}).get("servers", []))}

            def alias(value):
                if isinstance(value, list):
                    return [alias(v) for v in value]
                return tags.get(value, inbound_tags.get(value, sets.get(value, dns_tags.get(value, "unresolved-redacted"))))

            def rule(row):
                clean = {"keys": sorted(row)}
                for key, value in row.items():
                    if key in {"type", "action", "invert", "ip_is_private", "port", "port_range", "network", "protocol"}:
                        clean[key] = value
                    elif key in {"outbound", "inbound", "rule_set", "server"}:
                        clean[key] = alias(value)
                    elif key == "rules":
                        clean[key] = [rule(v) for v in value]
                    elif key in {"domain", "domain_suffix", "domain_keyword"}:
                        values = value if isinstance(value, list) else [value]
                        safe = [v for v in values if v in PUBLIC_TARGETS]
                        clean[key] = {"allowlisted_values": safe, "other_value_count": len(values) - len(safe)}
                        matches = {}
                        for target in sorted(PUBLIC_TARGETS):
                            if key == "domain":
                                hits = [target == v for v in values]
                            elif key == "domain_suffix":
                                hits = [target == v.lstrip(".") or target.endswith("." + v.lstrip(".")) for v in values]
                            else:
                                hits = [v in target for v in values]
                            matches[target] = any(hits)
                        clean[key + "_openai_matches_in_memory"] = matches
                    elif key in {"process_name", "process_path", "process_path_regex"}:
                        values = value if isinstance(value, list) else [value]
                        clean[key] = {"value_count": len(values), "tunnel_client_literal_present": any("tunnel-client" in str(v).lower() for v in values)}
                    else:
                        clean[key] = {"value_type": type(value).__name__, "value_count": len(value) if isinstance(value, (list, dict)) else 1}
                return clean

            clean = {"status": "READ_ONLY_CONFIG_CORRELATED_WITH_PROCESS", "path_resolution": resolution, "process_pid": pid,
                     "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw),
                     "inbounds": [], "outbounds": [], "route": {}, "dns": {}, "experimental": {}}
            for i, inbound in enumerate(config.get("inbounds", [])):
                listen = inbound.get("listen", "")
                clean["inbounds"].append({"alias": "inbound_" + str(i + 1), "type": inbound.get("type"),
                    "listen": listen if host_class(listen) == "loopback" else "nonloopback-redacted",
                    "listen_port": inbound.get("listen_port"), "sniff": inbound.get("sniff"),
                    "sniff_override_destination": inbound.get("sniff_override_destination"),
                    "set_system_proxy": inbound.get("set_system_proxy"), "users_present": bool(inbound.get("users")),
                    "live_listener_matches": any(r["LocalPort"] == inbound.get("listen_port") and r["OwningProcess"] == pid for r in ports)})
            for i, outbound in enumerate(outbounds):
                clean["outbounds"].append({"alias": "outbound_" + str(i + 1), "type": outbound.get("type"),
                    "members": alias(outbound["outbounds"]) if "outbounds" in outbound else None,
                    "default": alias(outbound["default"]) if "default" in outbound else None,
                    "detour": alias(outbound["detour"]) if "detour" in outbound else None,
                    "server_class": host_class(outbound.get("server")),
                    "url_test_target_configured": bool(outbound.get("url")),
                    "current_runtime_selection": "NOT QUERIED" if outbound.get("type") in {"selector", "urltest"} else "N/A"})
            route = config.get("route", {})
            clean["route"] = {"keys": sorted(route), "final": alias(route.get("final")),
                "auto_detect_interface": route.get("auto_detect_interface"),
                "rules": [rule(r) for r in route.get("rules", [])],
                "rule_sets": [{"alias": "ruleset_" + str(i + 1), "type": r.get("type"),
                    "format": r.get("format"), "download_detour": alias(r.get("download_detour")),
                    "payload_not_exported": True} for i, r in enumerate(rule_sets)]}
            dns = config.get("dns", {})
            clean["dns"] = {"keys": sorted(dns), "strategy": dns.get("strategy"), "final": alias(dns.get("final")),
                "rules": [rule(r) for r in dns.get("rules", [])], "servers": []}
            for i, server in enumerate(dns.get("servers", [])):
                address = server.get("address", server.get("server", ""))
                parsed = urllib.parse.urlsplit(address) if isinstance(address, str) and "://" in address else None
                clean["dns"]["servers"].append({"alias": "dns_" + str(i + 1), "type": server.get("type"),
                    "address_scheme": parsed.scheme if parsed else None,
                    "address_class": host_class(parsed.hostname if parsed else address),
                    "detour": alias(server.get("detour")), "address_resolver": alias(server.get("address_resolver"))})
            for key, value in config.get("experimental", {}).items():
                clean["experimental"][key] = {"keys": sorted(value) if isinstance(value, dict) else [],
                    "secret_present": bool(value.get("secret")) if isinstance(value, dict) else False}
            result["configs"].append(clean)
    (HERE / "preflight.sanitized.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
