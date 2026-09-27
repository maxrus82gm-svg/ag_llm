from pathlib import Path

import pytest

import ui_state


@pytest.fixture(autouse=True)
def isolate_ui_state_file(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(
        ui_state,
        "STATE_PATH",
        tmp_path / "ui_state.json",
    )
