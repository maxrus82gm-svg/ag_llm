"""Syntax verification without importing runtime or creating bytecode."""
from pathlib import Path

files = ["web_alarm/ordinary_chat_bridge.py", "web_alarm/ultra_chat.py",
         "web_alarm/turn_service.py", "web_alarm/server.py", "test_web_alarm_ordinary_core_bridge.py"]
for name in files:
    compile(Path(name).read_bytes(), name, "exec")
print(f"{len(files)} Python syntax checks PASS")
