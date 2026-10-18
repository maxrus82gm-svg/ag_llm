"""Read-only input census for CLAUDE-WUA-0-EGRESS-ARCH-REVIEW-001.

Records bytes, SHA-256 and line endings of every source this review actually read (no other file is
opened). Writes inputs_read.json next to report.md. Usage: hash_inputs.py [--final]
(--final writes inputs_final.json to prove the inputs did not change during the review).
"""
import hashlib
import json
import sys
from pathlib import Path

REPO = Path(r"M:\GitHub\ag_llm")
HERE = Path(__file__).resolve().parent.parent
E2E = "reports/CODEX-WUA-0-DESKTOP-MCP-E2E-001/"
INPUTS = [
    "Документация/000_Задачи Claude.md",
    "Документация/000_Задачи для агента.md",
    "Документация/08_Старт.md",
    "Документация/18_Регламент сопровождения документации.md",
    "Документация/19_Архитектура внешних AI-интеграций - Codex CLI и ChatGPT MCP.md",
    "Документация/34_TACTICAL_CONTEXT.md",
    "Документация/01_Архитектура и текущее состояние.md",
    "Документация/36.1_Обязательный регламент тестирования для LLM.md",
    ".gitignore",
    E2E + "v2ray_proxy_constraints_20261016/report.md",
    E2E + "v2ray_preflight_20261017/report.md",
    E2E + "native_client_offline_20261017/report.md",
    E2E + "native_client_offline_20261017/proxy_path_audit.md",
    E2E + "http_socks_adapter_20261018/report.md",
    E2E + "http_socks_adapter_20261018/proxy_options.md",
    E2E + "http_socks_adapter_20261018/source_audit.md",
    E2E + "secure_tunnel_preparation/run_help.txt",
    E2E + "secure_tunnel_preparation/offline_profiles/wua-stdio-prepared.yaml",
    E2E + "secure_tunnel_preparation/start_tunnel.py",
    "reports/CODEX-WUA-0-NATIVE-EGRESS-GATE-001/report.md",
    "reports/CODEX-WUA-0-NATIVE-EGRESS-GATE-001/isolation_design.md",
    "reports/CODEX-WUA-0-NATIVE-EGRESS-GATE-001/native_egress_map.md",
    "reports/CODEX-WUA-0-OFFLINE-VM-PREFLIGHT-001/report.md",
    "reports/CODEX-WUA-0-OFFLINE-VM-PREFLIGHT-001/vm_platform_comparison.md",
    "reports/CODEX-WUA-0-OFFLINE-VM-PREFLIGHT-001/host_vm_inventory.md",
    "reports/CODEX-WUA-0-OFFLINE-VM-PREFLIGHT-001/isolation_preflight_contract.md",
]


def entry(path: Path) -> dict:
    data = path.read_bytes()
    eol = "NONE" if b"\n" not in data else ("LF" if b"\r" not in data else "CR_PRESENT")
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(), "eol": eol}


out = {"task": "CLAUDE-WUA-0-EGRESS-ARCH-REVIEW-001", "mode": "read-only census, no execution of any input",
       "inputs": {rel: entry(REPO / rel) for rel in INPUTS}}
name = "inputs_final.json" if "--final" in sys.argv else "inputs_read.json"
(HERE / name).write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
print(len(out["inputs"]), "inputs ->", name)
