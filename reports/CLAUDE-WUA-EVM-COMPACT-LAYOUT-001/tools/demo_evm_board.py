"""Open the compact EVM board on synthetic data only.

A new TEMP folder holds the Web Alarm storage and a synthetic Tk Ultra ``ui_state.json``; the real Web Alarm
storage, the real Tk settings, real keys and the network are never used. The cards get a fixed fake environment
("key present", PERS). Seeded: a chat-model preference, two descriptions, three API states (synthetic evidence,
NOT API checks), two favourites and a manual API order. MCP / local columns stay honestly empty: their sources
are not connected. The page carries the red TEST frame and badge of the launcher.

Usage (from the repository root, with the project venv):
    python reports/CLAUDE-WUA-EVM-COMPACT-LAYOUT-001/tools/demo_evm_board.py [--port 8795] [--keep]
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


def build(base: Path) -> WebAlarmApi:
    tk = base / "tk" / "ui_state.json"
    tk.parent.mkdir(parents=True)
    tk.write_text(json.dumps(TK), encoding="utf-8")
    api = WebAlarmApi(base / "web_alarm_storage", tk_state_path=tk)
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
    args = parser.parse_args()
    base = Path(tempfile.mkdtemp(prefix="wa-evm-board-demo-"))
    try:
        server = create_server(build(base), port=args.port)
        server.RequestHandlerClass = _MarkedHandler
        server.web_alarm_launch = Launch(name="evm-board-demo", title="EVM: компактная доска на синтетических данных", standard=False)
        print(f"EVM board demo (synthetic data) on http://127.0.0.1:{server.server_port}/#evm", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()
    finally:
        if not args.keep:
            shutil.rmtree(base, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
