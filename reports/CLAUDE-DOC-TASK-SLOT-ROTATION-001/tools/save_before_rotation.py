"""Before the first rotation, keep the exact previous BLOCK 1.1 text of the Claude card and the exact launch message
of the EVM task (no AMENDMENT in it) as evidence. Extraction is mechanical (markers / pasted block), not retyped.
Usage: save_before_rotation.py <session transcript .jsonl>
"""
import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[1]
REPO = PACKAGE.parents[1]
spec = importlib.util.spec_from_file_location("task_slot_rotate", REPO / "tools" / "task_slot_rotate.py")
tsr = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = tsr
sys.dont_write_bytecode = True
spec.loader.exec_module(tsr)

card = tsr.parse((REPO / "Документация" / "000_Задачи Claude.md").read_bytes())
assert not card.problems, card.problems
lines, texts, _ = card.body("b11b", "b11e")
previous = b"".join(lines)
slot = tsr.classify_block11(lines, texts, 0)
record = {"purpose": "exact content of BLOCK 1.1 of the Claude card before the first rotation (kept because the task "
                     "asks to secure the previous slot; it is the placeholder, no TASK in it)",
          "state": slot["state"], "text": previous.decode("utf-8"), "sha256_lf": tsr.sha_lf(previous),
          "card_sha256_at_extraction": hashlib.sha256(card.data).hexdigest()}
(PACKAGE / "evidence" / "previous_block11.json").write_text(json.dumps(record, ensure_ascii=False, indent=1) + "\n",
                                                            encoding="utf-8", newline="\n")
launch = None
for raw in Path(sys.argv[1]).read_text(encoding="utf-8").splitlines():
    try:
        row = json.loads(raw)
    except ValueError:
        continue
    content = row.get("message", {}).get("content") if row.get("type") == "user" else None
    for text in [content] if isinstance(content, str) else [c.get("text", "") for c in content or []
                                                              if isinstance(c, dict) and c.get("type") == "text"]:
        match = re.search(r"<pasted_content id=\"\w+\">\n(.*?)\n</pasted_content", text, re.S)
        if match and "тебе назначается отдельная задача `CLAUDE-WUA-EVM-COMPACT-LAYOUT-001`" in match.group(1):
            launch = match.group(1)
assert launch, "launch message not found"
record = {"purpose": "exact launch message of CLAUDE-WUA-EVM-COMPACT-LAYOUT-001 pasted by the user; it refers to the "
                     "full statement in BLOCK 1 and adds no requirement, so it is not a CHAT-ONLY AMENDMENT",
          "has_amendment": "AMENDMENT" in launch, "text": launch,
          "sha256": hashlib.sha256(launch.encode("utf-8")).hexdigest()}
(PACKAGE / "evidence" / "evm_launch_message.json").write_text(json.dumps(record, ensure_ascii=False, indent=1) + "\n",
                                                              encoding="utf-8", newline="\n")
print(json.dumps({"previous_state": slot["state"], "previous_sha256_lf": record and tsr.sha_lf(previous),
                  "launch_found": True, "launch_has_amendment": "AMENDMENT" in launch}))
