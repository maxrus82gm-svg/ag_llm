from pathlib import Path

import ui_state


def test_pytest_ui_state_is_redirected_to_temp_path(tmp_path: Path):
    real_default_path = (
        Path(ui_state.STATE_DIR)
        / "ui_state.json"
    )

    assert ui_state.STATE_PATH != real_default_path

    state = ui_state.default_ui_state()
    state["active_workspace_id"] = "test_workspace"
    state["workspaces"] = [
        {
            "workspace_id": "test_workspace",
            "path": "M:/TEST_ONLY",
            "last_chat_id": None,
        }
    ]

    ui_state.save_ui_state(state)

    assert ui_state.STATE_PATH.is_file()
    assert ui_state.STATE_PATH.parent == tmp_path

    loaded = ui_state.load_ui_state()

    assert loaded["active_workspace_id"] == "test_workspace"
    assert loaded["workspaces"][0]["workspace_id"] == "test_workspace"
