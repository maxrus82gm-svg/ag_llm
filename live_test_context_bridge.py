from __future__ import annotations

from context_registry import (
    delete_context_variant,
    get_context_record,
    save_context_variant,
    set_active_variant,
)
from server_context_messages import (
    load_server_context_messages,
    resolve_server_context_message,
)

EVENT_ID = "task.stage"
TEST_VARIANT = "bridge_test"
MARKER = "CONTEXT REGISTRY BRIDGE TEST OK"


def main() -> None:
    legacy = load_server_context_messages("ultra")
    legacy_record = legacy["messages"].get(EVENT_ID)
    if legacy_record is not None:
        raise SystemExit(
            "STOP: для task.stage уже существует legacy override в "
            "server_context_messages.json. Он имеет более высокий приоритет и "
            "замаскирует новый Registry. Ничего не изменено."
        )

    before = get_context_record(EVENT_ID, "ultra")
    original_active = before["active_variant"]

    if TEST_VARIANT in before["user_variants"]:
        raise SystemExit(
            f"STOP: вариант {TEST_VARIANT!r} уже существует. Ничего не изменено."
        )

    print("До теста:")
    print(f"  active_variant = {original_active}")
    print(f"  effective_source = {before['effective_source']}")

    try:
        save_context_variant(
            EVENT_ID,
            TEST_VARIANT,
            MARKER,
            description="Временный вариант для проверки bridge.",
            agent_id="ultra",
        )
        set_active_variant(
            EVENT_ID,
            TEST_VARIANT,
            agent_id="ultra",
        )

        resolved = resolve_server_context_message(EVENT_ID, {}, "ultra")
        print()
        print("Результат через настоящий resolve_server_context_message():")
        print(f"  {resolved}")

        if resolved != MARKER:
            raise RuntimeError(
                "Bridge не сработал: runtime вернул не тестовый текст."
            )

        print()
        print(
            "PASS: server_context_messages.py реально получил текст "
            "из нового Context Registry."
        )
    finally:
        try:
            set_active_variant(
                EVENT_ID,
                original_active,
                agent_id="ultra",
            )
        finally:
            delete_context_variant(
                EVENT_ID,
                TEST_VARIANT,
                agent_id="ultra",
            )

    after = get_context_record(EVENT_ID, "ultra")
    print()
    print("После теста:")
    print(f"  active_variant = {after['active_variant']}")
    print(f"  effective_source = {after['effective_source']}")
    print("Очистка временного варианта выполнена.")


if __name__ == "__main__":
    main()
