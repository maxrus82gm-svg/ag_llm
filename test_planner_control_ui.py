from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import ui_state
import ultra_ui
from audit_storage import AuditThreadRecorder, load_audit_thread


def test_left_vertical_ratios_round_trip(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(ui_state, "STATE_PATH", tmp_path / "ui_state.json")
    state = ui_state.default_ui_state()
    assert state["left_vertical_ratios"] == {"normal": 0.55, "zoomed": 0.55}
    state["left_vertical_ratios"]["normal"] = 0.61
    ui_state.save_ui_state(state)
    assert ui_state.load_ui_state()["left_vertical_ratios"]["normal"] == 0.61


def test_left_vertical_paned_is_captured_by_layout_persistence():
    class Paned:
        def winfo_height(self):
            return 400

        def sash_coord(self, _index):
            return 0, 240

    fake = SimpleNamespace(
        _ui_state=ui_state.default_ui_state(),
        _capture_panel_ratios=lambda: [],
        _window_mode=lambda: "normal",
        audit_visible_var=SimpleNamespace(get=lambda: True),
        left_vertical_paned=Paned(),
    )
    ultra_ui.UltraApp._store_current_panel_ratios(fake)
    assert fake._ui_state["left_vertical_ratios"]["normal"] == 0.6


def test_planner_conversation_renders_human_speaker_order():
    thread = {
        "task_block_id": "tb_1234567890abcdef",
        "planner_session": {
            "session_id": "ps_test", "status": "VALID",
            "dredd_review": {"model_display_name": "GigaChat 3 Pro"},
            "messages": [
                {"speaker": "TASK", "text": "do it"},
                {"speaker": "PLANNER", "model_display_name": "GigaChat Ultra", "text": "{}"},
                {"speaker": "SERVER", "text": "SERVER VALIDATION"},
                {"speaker": "DREDD", "text": "DREDD REVIEW"},
                {"speaker": "PLANNER", "model_display_name": "GigaChat Ultra", "text": "{}"},
            ],
        },
    }
    rendered = "".join(text for _tag, text in ultra_ui.UltraApp._planner_session_segments(thread))
    positions = [rendered.index(value) for value in (
        "TASK\ndo it", "PLANNER · GigaChat Ultra", "SERVER\nSERVER VALIDATION",
        "DREDD · GigaChat 3 Pro", "PLANNER · GigaChat Ultra", 
    )]
    assert positions[:4] == sorted(positions[:4])
    assert rendered.count("PLANNER · GigaChat Ultra") == 2
    assert "PLANNER / REQUEST" not in rendered
    assert "PLANNER / CONTEXT" not in rendered


def test_planner_session_events_survive_audit_reload(tmp_path: Path):
    task_id = "tb_1234567890abcdef1234567890abcdef"
    recorder = AuditThreadRecorder(
        tmp_path, "ws_test", "chat_test", "run_test", task_id,
    )
    base = {"run_id": "run_test", "task_block_id": task_id}
    recorder.observe({"event": "planner_session_started", **base,
                      "session_id": "ps_test", "status": "ACTIVE"})
    recorder.observe({"event": "planner_session_message", **base,
                      "session_id": "ps_test", "mode": "INITIAL", "speaker": "TASK",
                      "attempt": 1, "text": "do it"})
    recorder.observe({"event": "planner_session_completed", **base,
                      "session_id": "ps_test", "status": "VALID"})
    thread = load_audit_thread(tmp_path, "ws_test", "chat_test", "run_test")
    assert thread["planner_session"]["session_id"] == "ps_test"
    assert thread["planner_session"]["status"] == "VALID"
    assert thread["planner_session"]["messages"][0]["speaker"] == "TASK"


def test_user_and_assistant_share_task_block_and_run():
    task_id = "tb_1234567890abcdef"
    messages = [
        {"message_id": "user_1", "role": "user", "task_block_id": task_id},
        {"message_id": "assistant_1", "role": "assistant", "task_block_id": task_id,
         "audit_run_id": "run_1"},
    ]
    threads = [{"task_block_id": task_id, "run_id": "run_1"}]
    index, order, message_ids = ultra_ui.UltraApp._build_task_block_index(
        messages, threads, "chat_1",
    )
    assert order == [task_id]
    assert message_ids["user_1"] == message_ids["assistant_1"] == task_id
    assert index[task_id]["run_id"] == "run_1"


def test_viewport_center_selects_new_task_when_top_is_previous_task():
    order = ["A", "B"]
    index = {
        "A": {"ui_start_mark": "A", "run_id": "run_A"},
        "B": {"ui_start_mark": "B", "run_id": "run_B"},
    }
    positions = {"A": 0, "B": 100}
    selected = []
    chat = SimpleNamespace(
        winfo_height=lambda: 200,
        index=lambda coordinate: 150 if coordinate == "@0,100" else 0,
        compare=lambda mark, _operator, reference: positions[mark] <= reference,
    )
    fake = SimpleNamespace(
        _task_block_order=order, _task_block_index=index,
        _chat_audit_sync_after=None, chat=chat,
        _task_block_for_viewport=ultra_ui.UltraApp._task_block_for_viewport,
        _select_task_block=lambda task_id: selected.append(task_id),
    )
    ultra_ui.UltraApp._sync_audit_to_viewport(fake)
    assert selected == ["B"]


def test_short_task_id_is_shared_by_user_and_assistant_labels():
    task_id = "tb_c99a94b812345678"
    assert ultra_ui.UltraApp._short_task_id(task_id) == "c99a94b8"
    fake = SimpleNamespace(_short_task_id=ultra_ui.UltraApp._short_task_id)
    label = ultra_ui.UltraApp._assistant_label(
        fake, {"model_display_name": "GigaChat 3 Ultra"}, task_id,
    )
    assert label == "АССИСТЕНТ · GigaChat 3 Ultra"

