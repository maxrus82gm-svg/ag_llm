"""Read-only, deidentified GUI policy; never claim it is the effective loaded core."""
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
from urllib.parse import urlsplit

HERE = Path(__file__).resolve().parent


def main():
    p = subprocess.run(["powershell.exe", "-NoProfile", "-Command",
        '[Console]::OutputEncoding=[Text.UTF8Encoding]::new(); (Get-CimInstance Win32_Process | Where-Object Name -eq "v2rayN.exe").ExecutablePath | ConvertTo-Json'],
        capture_output=True, encoding="utf-8-sig", errors="replace", timeout=15)
    root = Path(json.loads(p.stdout)).parent
    path = root / "guiConfigs/guiNConfig.json"
    raw = path.read_bytes()
    cfg = json.loads(raw.decode("utf-8-sig"))
    get = lambda name: cfg.get(name) or {}
    mode = get("ClashUIItem").get("RuleMode")
    result = {
        "authority": "stored GUI policy only; loaded sing-box config and runtime selection NOT VERIFIED",
        "gui_sha256": hashlib.sha256(raw).hexdigest(),
        "tun_enabled": get("TunModeItem").get("EnableTun"),
        "gui_clash_mode": mode if str(mode).lower() in {"rule", "global", "direct"} else "unrecognized-redacted",
        "gui_clash_mode_present": bool(mode),
        "gui_clash_mode_numeric": mode if isinstance(mode, (int, float)) else int(mode) if isinstance(mode, str) and mode.isdecimal() else None,
        "routing_selection_id_present": bool(get("RoutingBasicItem").get("RoutingIndexId")),
        "domain_strategy": get("RoutingBasicItem").get("DomainStrategy"),
        "singbox_domain_strategy": get("RoutingBasicItem").get("DomainStrategy4Singbox"),
        "system_proxy_mode_numeric": get("SystemProxyItem").get("SysProxyType"),
        "system_proxy_exceptions_present": bool(get("SystemProxyItem").get("SystemProxyExceptions")),
        "system_proxy_bypass_local": get("SystemProxyItem").get("NotProxyLocalAddress"),
        "inbounds": [], "dns": {}, "stored_routing_profiles": []}
    for row in cfg.get("Inbound", []):
        result["inbounds"].append({k: row.get(k) for k in ["LocalPort", "Protocol", "UdpEnabled", "SniffingEnabled", "RouteOnly", "AllowLANConn", "SecondLocalPortEnabled"]})
    dns = get("SimpleDNSItem")
    for key in ["UseSystemHosts", "AddCommonHosts", "FakeIP", "GlobalFakeIp", "ServeStale", "ParallelQuery"]:
        result["dns"][key] = dns.get(key)
    for key in ["DirectDNS", "RemoteDNS", "BootstrapDNS"]:
        value = dns.get(key)
        result["dns"][key] = {"configured": bool(value), "scheme": urlsplit(value).scheme if isinstance(value, str) and "://" in value else "unspecified; address redacted"}
    db = root / "guiConfigs/guiNDB.db"
    before_db = hashlib.sha256(db.read_bytes()).hexdigest()
    result["database_sha256"] = before_db
    con = sqlite3.connect(db.as_uri() + "?mode=ro&immutable=1", uri=True)
    con.execute("PRAGMA query_only=ON")
    for enabled, active, ruleset in con.execute("SELECT Enabled, IsActive, RuleSet FROM RoutingItem"):
        try:
            rules = json.loads(ruleset) if ruleset else []
        except ValueError:
            result["stored_routing_profiles"].append({"parse_status": "NOT_STANDARD_JSON"})
            continue
        summaries = []
        for rule in rules:
            lower = {k.lower(): v for k, v in rule.items()}
            tag = lower.get("outboundtag", lower.get("outbound"))
            domains = lower.get("domain", []) or []
            domains = domains if isinstance(domains, list) else [domains]
            summaries.append({"enabled": lower.get("enabled"),
                "outbound_semantic": tag if str(tag).lower() in {"proxy", "direct", "block", "dns"} else "custom-redacted",
                "condition_keys": sorted(k for k in lower if k not in {"id", "remarks", "enabled", "outboundtag"}),
                "domain_condition_count": len(domains),
                "openai_literal_condition": any(d in {"openai.com", "api.openai.com", "domain:openai.com", "domain:api.openai.com", "full:api.openai.com", "geosite:openai"} for d in domains),
                "external_ruleset_condition": any(str(d).startswith(("geosite:", "ext:")) for d in domains),
                "process_condition_present": bool(lower.get("process") or lower.get("processname") or lower.get("process_name"))})
        result["stored_routing_profiles"].append({"enabled": bool(enabled), "is_active": bool(active), "rules": summaries})
    selected = con.execute("SELECT ConfigType, CoreType FROM ProfileItem WHERE IndexId=?", (cfg.get("IndexId"),)).fetchone()
    result["selected_profile_type_numeric"] = list(selected) if selected else None
    con.close()
    result["database_read_mode"] = "ro+immutable; no WAL/SHM creation; on-disk snapshot only"
    result["database_wal_present"] = Path(str(db) + "-wal").exists()
    result["database_shm_present"] = Path(str(db) + "-shm").exists()
    result["database_unchanged_during_read"] = hashlib.sha256(db.read_bytes()).hexdigest() == before_db
    result["gui_unchanged_during_read"] = path.read_bytes() == raw
    result["remote_route_verified"] = False
    (HERE / "gui_policy.sanitized.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
