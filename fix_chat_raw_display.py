from __future__ import annotations

import os
import sys
from pathlib import Path


OLD = """            if role in {"user", "assistant"}:
                resolved = get_message_working_representation(
                    workspace,
                    self.current_chat_id,
                    message_id,
                )
                text = resolved["text"]
"""

NEW = """            if role in {"user", "assistant"}:
                # CHAT показывает неизменяемую RAW HISTORY пользователю.
                # resolved используется только для FULL/COMPRESSED state
                # и message actions; MAIN CHAT получает working representation
                # отдельно через server.py / load_chat_working_messages().
                resolved = get_message_working_representation(
                    workspace,
                    self.current_chat_id,
                    message_id,
                )
"""


def main() -> None:
    target = Path(sys.argv[1] if len(sys.argv) > 1 else "ultra_ui.py").resolve()
    if not target.is_file():
        raise FileNotFoundError(f"Не найден файл: {target}")

    original = target.read_text(encoding="utf-8")
    count = original.count(OLD)
    if count != 1:
        raise RuntimeError(
            f"Ожидалось ровно одно совпадение нужного блока, найдено: {count}. "
            "Файл не изменён."
        )

    updated = original.replace(OLD, NEW, 1)

    compile(updated, str(target), "exec")

    temp = target.with_name(f".{target.name}.raw_display_patch.tmp")
    try:
        temp.write_text(updated, encoding="utf-8", newline="\n")
        os.replace(temp, target)
    finally:
        try:
            temp.unlink()
        except FileNotFoundError:
            pass

    print(f"OK: RAW display restored in chat UI: {target}")
    print("MAIN CHAT working-context logic is untouched.")
    print("No Git commands were run.")


if __name__ == "__main__":
    main()
