import asyncio
from pathlib import Path

from server import run_agent_task


def read_multiline_task() -> str:
    print()
    print("Вставь задачу для GigaChat Ultra.")
    print("Когда закончишь, введи отдельной строкой: END")
    print()

    lines = []
    while True:
        line = input()
        if line.strip() == "END":
            break
        lines.append(line)

    task = "\n".join(lines).strip()
    if not task:
        raise ValueError("Задача пустая.")
    return task


def main() -> None:
    default_workspace = Path.cwd()

    print("=== GigaChat Ultra Local Agent ===")
    print(f"Папка по умолчанию: {default_workspace}")
    workspace = input("Workspace (Enter = текущая папка): ").strip().strip('"')

    if not workspace:
        workspace = str(default_workspace)

    task = read_multiline_task()

    print()
    print("Ultra работает...")
    print()

    result = asyncio.run(run_agent_task(task, workspace))

    print("=== ОТВЕТ ULTRA ===")
    print(result)


if __name__ == "__main__":
    main()
