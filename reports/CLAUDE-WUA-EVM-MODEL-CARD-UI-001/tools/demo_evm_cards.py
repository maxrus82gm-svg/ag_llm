"""Open the new EVM model cards on synthetic data only.

A new TEMP folder holds the Web Alarm storage and a synthetic Tk Ultra ``ui_state.json``; the real Web Alarm
storage, the real Tk settings, real keys and the network are never used. The process environment is not read
for keys: the demo gives the cards a fixed fake environment ("key present", PERS) so the settings window can
be seen. Three API states are seeded as synthetic evidence so all three colours can be seen; they are NOT API
checks. The page carries the red TEST frame and badge of the launcher.

Usage (from the repository root, with the project venv):
    python reports/CLAUDE-WUA-EVM-MODEL-CARD-UI-001/tools/demo_evm_cards.py [--port 8791] [--keep]
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
    "gigachat_2": "Демо-описание: быстрые ответы в диалоге, планирование коротких задач.\n"
                  "Текст задаёт пользователь в «Настройках», до 500 символов; длинный текст прокручивается внутри поля.",
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
    revision = 0
    for model_id, text in DESCRIPTIONS.items():
        api.dispatch("POST", f"/ultra/model-cards/{model_id}/settings", {"base_revision": revision, "description": text})
        revision += 1
    now = datetime.now(timezone.utc)
    seeds = (("gigachat_2", now - timedelta(days=2), True), ("gigachat_3_pro", now - timedelta(days=45), True),
             ("gigachat_2_max", now - timedelta(hours=3), False))
    for model_id, at, ok in seeds:  # synthetic evidence for the three colours, not an API check
        card = cards.card(model_id)
        cards.now = lambda at=at: at
        if ok:
            cards.record_success(card["connection_id"], card["settings_version"], source="diagnostic",
                                 reply="Демо: тестовое сообщение получено.", limit=1000)
        else:
            cards.record_failure(card["connection_id"], card["settings_version"], code="demo_http_401",
                                 message="Демо-отказ: ключ не принят", limit=1000)
    cards.now = lambda: datetime.now(timezone.utc)
    return api


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--keep", action="store_true")
    args = parser.parse_args()
    base = Path(tempfile.mkdtemp(prefix="wa-evm-cards-demo-"))
    try:
        server = create_server(build(base), port=args.port)
        server.RequestHandlerClass = _MarkedHandler
        server.web_alarm_launch = Launch(name="evm-cards-demo", title="EVM: карточки на синтетических данных", standard=False)
        print(f"EVM cards demo (synthetic data) on http://127.0.0.1:{server.server_port}/#evm", flush=True)
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
