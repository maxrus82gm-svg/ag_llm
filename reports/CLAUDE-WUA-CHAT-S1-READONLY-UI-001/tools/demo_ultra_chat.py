"""Open the stage-1 Ultra Chat on synthetic data only: a new TEMP folder holds the Web Alarm storage and every
Workspace; the real Web Alarm storage, real Workspaces, the network and GigaChat are never used.

Usage (from the repository root, with the project venv):
    python reports/CLAUDE-WUA-CHAT-S1-READONLY-UI-001/tools/demo_ultra_chat.py [--port 8790] [--disable-ultra-chat] [--keep]
Then open the printed http://127.0.0.1:<port>/ address. Ctrl+C stops the server and removes the TEMP folder
(unless --keep). The fixtures cover the states the screen must show: a normal dialogue with older pages, an old
Tk failure, a question without an answer, an interrupted run, HTML-looking text, a damaged and a linked chat, a
chat of another Workspace, a damaged record, a folder without Ultra history and a history above the read limit.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

import context_storage as cs  # noqa: E402
import run_store  # noqa: E402
from web_alarm.server import WebAlarmApi, create_server  # noqa: E402


def build(base: Path) -> tuple[WebAlarmApi, list[Path]]:
    api = WebAlarmApi(base / "web_alarm_storage")
    links: list[Path] = []

    main = base / "demo_main"
    main.mkdir()
    ws = cs.ensure_workspace_storage(main)["workspace_id"]
    cs.create_chat(main, "Ранний диалог")
    chat = cs.create_chat(main, "Обсуждение проекта")["chat_id"]
    for n in range(1, 61):
        tb = cs.new_task_block_id()
        cs.append_raw_message(main, chat, "user", f"Вопрос {n}: как устроен модуль {n}?", task_block_id=tb)
        cs.append_raw_message(main, chat, "assistant", f"Ответ {n}: модуль {n} читает данные и ничего не пишет.",
                              task_block_id=tb)
    tb = cs.new_task_block_id()
    run_id = "demo_run_failed"
    cs.append_raw_message(main, chat, "user", "Запусти проверку", task_block_id=tb)
    run_store.create_run_summary(main, ws, chat, tb, run_id)
    run_store.update_run_summary_index(main, run_id, {"run_status": "FAILED"})
    cs.append_raw_message(main, chat, "assistant", "RUN STATUS: FAILED\nRuntimeError: демонстрационная ошибка",
                          task_block_id=tb)
    cs.append_raw_message(main, chat, "user", "Вопрос без сохранённого ответа", task_block_id=cs.new_task_block_id())
    tb = cs.new_task_block_id()
    cs.append_raw_message(main, chat, "user", "Запрос, прерванный перезапуском", task_block_id=tb)
    run_store.create_run_summary(main, ws, chat, tb, "demo_run_interrupted")
    cs.append_raw_message(main, chat, "user", "Текст с разметкой: <b>жирный</b> <script>alert('xss')</script>")
    api.registry.register("Демо — обычная история", main)

    damaged = base / "demo_damaged"
    damaged.mkdir()
    cs.ensure_workspace_storage(damaged)
    good = cs.create_chat(damaged, "Целый диалог")["chat_id"]
    cs.append_raw_message(damaged, good, "user", "Это сообщение читается")
    (damaged / ".ultra" / "chats" / good / "messages" / ("msg_" + "1" * 32 + ".json")).write_text("{", encoding="utf-8")
    broken = cs.create_chat(damaged, "Сломанный")["chat_id"]
    foreign = cs.create_chat(damaged, "Чужой")["chat_id"]
    meta = damaged / ".ultra" / "chats" / foreign / "metadata.json"
    meta.write_text(json.dumps({**json.loads(meta.read_text(encoding="utf-8")), "workspace_id": "ws_" + "f" * 32}),
                    encoding="utf-8")
    (damaged / ".ultra" / "chats" / broken / "metadata.json").write_text("{", encoding="utf-8")
    if os.name == "nt":
        import _winapi
        link = damaged / ".ultra" / "chats" / chat
        _winapi.CreateJunction(str(main / ".ultra" / "chats" / chat), str(link))
        links.append(link)
    api.registry.register("Демо — повреждения и ссылки", damaged)

    bare = base / "demo_bare"
    bare.mkdir()
    api.registry.register("Демо — папка без истории Ultra", bare)

    large = base / "demo_large"
    large.mkdir()
    cs.ensure_workspace_storage(large)
    big = cs.create_chat(large, "Слишком длинная история")["chat_id"]
    folder = large / ".ultra" / "chats" / big / "messages"
    for n in range(cs.DEFAULT_READ_LIMITS.max_message_files + 1):
        (folder / f"msg_{n:032x}.json").write_text("{}", encoding="utf-8")
    api.registry.register("Демо — история выше лимита", large)
    return api, links


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--disable-ultra-chat", action="store_true")
    parser.add_argument("--keep", action="store_true", help="keep the TEMP folder after stopping")
    args = parser.parse_args()
    base = Path(tempfile.mkdtemp(prefix="wa-ultra-chat-demo-")).resolve()
    api, links = build(base)
    server = create_server(api, port=args.port, enable_ultra_chat=not args.disable_ultra_chat)
    print(json.dumps({"url": f"http://127.0.0.1:{server.server_port}/", "ultra_chat": not args.disable_ultra_chat,
                      "storage": "TEMP (disposable)"}, ensure_ascii=False), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        if not args.keep:
            for link in links:
                os.rmdir(link)
            shutil.rmtree(base, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
