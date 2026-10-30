"""Open the EVM board on synthetic data only, to try the interaction of CLAUDE-WUA-EVM-INTERACTION-DND-001 by mouse.

A new TEMP folder holds the Web Alarm storage and a synthetic Tk Ultra ``ui_state.json``; the real Web Alarm storage,
the real Tk settings, real keys and the network are never used. The cards get a fixed fake environment ("key
present", PERS). Seeded: a chat-model preference, two descriptions, three API states (synthetic evidence, NOT API
checks), two favourites and a manual API order. The MCP / local columns get two invented entries each, only inside
this demo process (the catalog of the running demo is wrapped; no project file changes): so the right-hand columns
and «drag into Избранное» from them can be tried. The page carries the red TEST frame and badge of the launcher.

Usage (from the repository root, with the project venv):
    python reports/CLAUDE-WUA-EVM-INTERACTION-DND-001/tools/demo_evm_dnd.py [--port 8796] [--keep]
Then open http://127.0.0.1:<port>/#evm . Ctrl+C stops the server and removes the TEMP folder (unless --keep).
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from web_alarm.launcher import Launch, _MarkedHandler  # noqa: E402
from web_alarm.server import WebAlarmApi, create_server  # noqa: E402

TK = {"main_chat_model_id": "gigachat_2", "planner_model_id": "gigachat_2", "verifier_model_id": "gigachat_3_pro",
      "compressor_model_id": "gigachat_3_pro", "planner_enabled": True, "final_audit_enabled": True}
FAKE_ENV = {"GIGACHAT_CREDENTIALS": "demo-placeholder-not-a-key", "GIGACHAT_SCOPE": "GIGACHAT_API_PERS"}
DESCRIPTIONS = {
    "gigachat_2": "Демо-описание: быстрые ответы в диалоге, планирование коротких задач.",
    "gigachat_3_pro": "Демо-описание: проверка результатов и сжатие длинной истории.",
}
EXTRA = {  # invented entries of the demo only: their sources are not connected in the product
    "mcp_agents": [{"connection_id": "mcp:demo:planner-agent", "kind": "mcp", "provider": "demo", "display_name": "Демо-агент: планировщик"},
                   {"connection_id": "mcp:demo:files-tool", "kind": "mcp", "provider": "demo", "display_name": "Демо-инструмент: файлы"}],
    "local_llm": [{"connection_id": "local:demo:llama-8b", "kind": "local", "provider": "demo", "display_name": "Демо: локальная 8B"},
                  {"connection_id": "local:demo:qwen-14b", "kind": "local", "provider": "demo", "display_name": "Демо: локальная 14B"}],
}


def build(base: Path) -> WebAlarmApi:
    tk = base / "tk" / "ui_state.json"
    tk.parent.mkdir(parents=True)
    tk.write_text(json.dumps(TK), encoding="utf-8")
    api = WebAlarmApi(base / "web_alarm_storage", tk_state_path=tk)
    real_catalog = api.ultra_connections.catalog

    def catalog():  # the same object serves /ultra/connections and the board of /ultra/model-cards
        data = real_catalog()
        for column, entries in EXTRA.items():
            data["columns"][column] = {"state": "AVAILABLE", "connections": [dict(e) for e in entries]}
        return data

    api.ultra_connections.catalog = catalog
    cards = api.model_cards
    cards.environ = dict(FAKE_ENV)
    api.dispatch("POST", "/ultra/connections/selection", {"role": "chat", "connection_id": "api:gigachat:gigachat_2"})
    for revision, (model_id, text) in enumerate(DESCRIPTIONS.items()):
        api.dispatch("POST", f"/ultra/model-cards/{model_id}/settings", {"base_revision": revision, "description": text})
    now = datetime.now(timezone.utc)
    for model_id, at, ok in (("gigachat_2", now - timedelta(days=2), True), ("gigachat_3_pro", now - timedelta(days=45), True),
                             ("gigachat_2_max", now - timedelta(hours=3), False)):  # synthetic evidence, not an API check
        card = cards.card(model_id)
        cards.now = lambda at=at: at
        if ok:
            cards.record_success(card["connection_id"], card["settings_version"], source="diagnostic",
                                 reply="Демо: тестовое сообщение получено.", limit=1000)
        else:
            cards.record_failure(card["connection_id"], card["settings_version"], code="demo_http_401",
                                 message="Демо-отказ: ключ не принят", limit=1000)
    cards.now = lambda: datetime.now(timezone.utc)
    view = api.dispatch("GET", "/ultra/model-cards")[1]["view"]
    order = ["api:gigachat:gigachat_ultra"] + [x for x in view["sections"]["api"] if x != "api:gigachat:gigachat_ultra"]
    api.dispatch("POST", "/ultra/model-cards/view", {"base_revision": 0, "section": "api", "order": order})
    api.dispatch("POST", "/ultra/model-cards/view", {"base_revision": 1, "section": "favorites",
                                                     "order": ["api:gigachat:gigachat_2", "api:gigachat:gigachat_3_pro"]})
    return api


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--keep", action="store_true")
    parser.add_argument("--base", help="use this empty folder instead of a new TEMP one (for a restart test)")
    args = parser.parse_args()
    base = Path(args.base) if args.base else Path(tempfile.mkdtemp(prefix="wa-evm-dnd-demo-"))
    fresh = not (base / "web_alarm_storage").exists()
    try:
        api = build(base) if fresh else WebAlarmApi(base / "web_alarm_storage", tk_state_path=base / "tk" / "ui_state.json")
        if not fresh:  # a restart over the same storage: only the demo catalog and environment again, nothing seeded
            real_catalog = api.ultra_connections.catalog
            api.ultra_connections.catalog = lambda: {**real_catalog(), "columns": {**real_catalog()["columns"], **{
                column: {"state": "AVAILABLE", "connections": [dict(e) for e in entries]} for column, entries in EXTRA.items()}}}
            api.model_cards.environ = dict(FAKE_ENV)
        server = create_server(api, port=args.port)
        server.RequestHandlerClass = _MarkedHandler
        server.web_alarm_launch = Launch(name="evm-dnd-demo", title="EVM: раскрытие и перетаскивание на синтетических данных", standard=False)
        print(f"EVM DnD demo (synthetic data, {'new' if fresh else 'restarted'} storage) on http://127.0.0.1:{server.server_port}/#evm", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()
    finally:
        if not args.keep and not args.base:
            shutil.rmtree(base, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
