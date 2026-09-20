from __future__ import annotations

import os
import sys
from pathlib import Path


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(
            f"{label}: ожидалось ровно 1 совпадение, найдено {count}. "
            "Файл не изменён."
        )
    return text.replace(old, new, 1)


def main() -> None:
    target = Path(sys.argv[1] if len(sys.argv) > 1 else "ultra_ui.py").resolve()
    if not target.is_file():
        raise FileNotFoundError(f"Не найден файл: {target}")

    original = target.read_text(encoding="utf-8")
    updated = original

    old = '''        self.compressor_status_var = tk.StringVar(
            value="сообщение не выбрано"
        )
'''
    new = '''        self.compressor_message_id_var = tk.StringVar(value="—")
        self.compressor_status_var = tk.StringVar(value="не выбрано")
'''
    updated = replace_once(
        updated,
        old,
        new,
        "Compressor status vars",
    )

    old = '''        ttk.Label(model_frame, text="Модель:").pack(side="left")
        ttk.Label(
            model_frame,
            textvariable=self.main_chat_model_display_var,
        ).pack(side="left", padx=(6, 12))
        model_registry_button = ttk.Button(
            model_frame,
            text="Модели...",
            command=lambda: self._open_model_registry("main_chat"),
        )
        model_registry_button.pack(side="left")
        main_context_button = ttk.Button(
            model_frame,
            text="Контекст MAIN CHAT...",
            command=self._open_global_ultra_context_editor,
        )
        main_context_button.pack(side="left", padx=(8, 0))
'''
    new = '''        model_registry_button = ttk.Button(
            model_frame,
            text="Модель",
            command=lambda: self._open_model_registry("main_chat"),
        )
        model_registry_button.pack(side="left")
        ttk.Label(
            model_frame,
            textvariable=self.main_chat_model_display_var,
        ).pack(side="left", padx=(8, 16))
        main_context_button = ttk.Button(
            model_frame,
            text="Контекст MAIN CHAT...",
            command=self._open_global_ultra_context_editor,
        )
        main_context_button.pack(side="left")
'''
    updated = replace_once(
        updated,
        old,
        new,
        "MAIN CHAT model row",
    )

    old = '''        compressor_frame = ttk.LabelFrame(
            right_frame,
            text="КОНТЕКСТ СООБЩЕНИЙ / COMPRESSOR",
            padding=(8, 5),
        )
        compressor_frame.pack(fill="x", pady=(0, 8))

        ttk.Label(compressor_frame, text="Модель:").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(
            compressor_frame,
            textvariable=self.compressor_model_display_var,
        ).grid(row=0, column=1, sticky="w", padx=(6, 12))
        compressor_models_button = ttk.Button(
            compressor_frame,
            text="Модели...",
            command=lambda: self._open_model_registry("compressor"),
        )
        compressor_models_button.grid(row=0, column=2, sticky="w")

        compressor_role_button = ttk.Button(
            compressor_frame,
            text="Контекст роли...",
            command=self._open_compressor_role_context_editor,
        )
        compressor_role_button.grid(
            row=1, column=0, sticky="w", pady=(6, 0)
        )
        compressor_template_button = ttk.Button(
            compressor_frame,
            text="Шаблон задачи...",
            command=self._open_compressor_template_editor,
        )
        compressor_template_button.grid(
            row=1, column=1, sticky="w", padx=(6, 0), pady=(6, 0)
        )
        compressor_final_template_button = ttk.Button(
            compressor_frame,
            text="Финальная проверка...",
            command=self._open_compressor_final_check_template_editor,
        )
        compressor_final_template_button.grid(
            row=1, column=2, sticky="w", padx=(12, 0), pady=(6, 0)
        )

        ttk.Label(
            compressor_frame,
            text="Сократить примерно на:",
        ).grid(row=2, column=0, sticky="w", pady=(6, 0))
        compressor_reduction_spin = ttk.Spinbox(
            compressor_frame,
            from_=1,
            to=95,
            width=5,
            textvariable=self.compressor_reduction_percent_var,
            command=lambda: self._save_ui_state(silent=True),
        )
        compressor_reduction_spin.grid(
            row=2, column=1, sticky="w", padx=(6, 0), pady=(6, 0)
        )
        ttk.Label(compressor_frame, text="%").grid(
            row=2, column=1, sticky="w", padx=(58, 0), pady=(6, 0)
        )
        compressor_reduction_spin.bind(
            "<FocusOut>",
            lambda _event: self._save_ui_state(silent=True),
        )
        compressor_final_check = ttk.Checkbutton(
            compressor_frame,
            text="Финальная проверка цели",
            variable=self.compressor_final_check_enabled_var,
            command=lambda: self._save_ui_state(silent=True),
        )
        compressor_final_check.grid(
            row=2, column=2, sticky="w", padx=(12, 0), pady=(6, 0)
        )

        ttk.Label(compressor_frame, text="Состояние:").grid(
            row=3, column=0, sticky="w", pady=(6, 0)
        )
        ttk.Label(
            compressor_frame,
            textvariable=self.compressor_status_var,
        ).grid(
            row=3,
            column=1,
            columnspan=2,
            sticky="w",
            padx=(6, 0),
            pady=(6, 0),
        )

        self._compressor_widgets.extend(
            [
                compressor_models_button,
                compressor_role_button,
                compressor_template_button,
                compressor_final_template_button,
                compressor_reduction_spin,
                compressor_final_check,
            ]
        )
'''
    new = '''        compressor_frame = ttk.LabelFrame(
            right_frame,
            text="КОНТЕКСТ СООБЩЕНИЙ / COMPRESSOR",
            padding=(8, 5),
        )
        compressor_frame.pack(fill="x", pady=(0, 8))
        compressor_frame.columnconfigure(1, minsize=180)
        compressor_frame.columnconfigure(3, weight=1)

        compressor_models_button = ttk.Button(
            compressor_frame,
            text="Модель",
            command=lambda: self._open_model_registry("compressor"),
        )
        compressor_models_button.grid(row=0, column=0, sticky="w")
        ttk.Label(
            compressor_frame,
            textvariable=self.compressor_model_display_var,
        ).grid(row=0, column=1, sticky="w", padx=(8, 18))
        compressor_role_button = ttk.Button(
            compressor_frame,
            text="Контекст роли...",
            command=self._open_compressor_role_context_editor,
        )
        compressor_role_button.grid(row=0, column=2, sticky="w")

        ttk.Label(
            compressor_frame,
            text="Порог сокращения:",
        ).grid(row=1, column=0, sticky="w", pady=(6, 0))
        reduction_value_frame = ttk.Frame(compressor_frame)
        reduction_value_frame.grid(
            row=1,
            column=1,
            sticky="w",
            padx=(8, 18),
            pady=(6, 0),
        )
        compressor_reduction_spin = ttk.Spinbox(
            reduction_value_frame,
            from_=1,
            to=95,
            width=5,
            textvariable=self.compressor_reduction_percent_var,
            command=lambda: self._save_ui_state(silent=True),
        )
        compressor_reduction_spin.pack(side="left")
        ttk.Label(reduction_value_frame, text="%").pack(
            side="left",
            padx=(4, 0),
        )
        compressor_reduction_spin.bind(
            "<FocusOut>",
            lambda _event: self._save_ui_state(silent=True),
        )
        compressor_template_button = ttk.Button(
            compressor_frame,
            text="Контекст сжатия...",
            command=self._open_compressor_template_editor,
        )
        compressor_template_button.grid(
            row=1,
            column=2,
            sticky="w",
            pady=(6, 0),
        )

        compressor_final_check = ttk.Checkbutton(
            compressor_frame,
            text="Дополнительная проверка",
            variable=self.compressor_final_check_enabled_var,
            command=lambda: self._save_ui_state(silent=True),
        )
        compressor_final_check.grid(
            row=2,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(6, 0),
        )
        compressor_final_template_button = ttk.Button(
            compressor_frame,
            text="Контекст дополнительной проверки...",
            command=self._open_compressor_final_check_template_editor,
        )
        compressor_final_template_button.grid(
            row=2,
            column=2,
            sticky="w",
            pady=(6, 0),
        )

        ttk.Label(compressor_frame, text="Сообщение:").grid(
            row=3,
            column=0,
            sticky="w",
            pady=(6, 0),
        )
        ttk.Label(
            compressor_frame,
            textvariable=self.compressor_message_id_var,
        ).grid(
            row=3,
            column=1,
            sticky="w",
            padx=(8, 18),
            pady=(6, 0),
        )
        ttk.Label(compressor_frame, text="Состояние:").grid(
            row=3,
            column=2,
            sticky="w",
            pady=(6, 0),
        )
        ttk.Label(
            compressor_frame,
            textvariable=self.compressor_status_var,
        ).grid(
            row=3,
            column=3,
            sticky="w",
            padx=(8, 0),
            pady=(6, 0),
        )

        self._compressor_widgets.extend(
            [
                compressor_models_button,
                compressor_role_button,
                compressor_template_button,
                compressor_final_template_button,
                compressor_reduction_spin,
                compressor_final_check,
            ]
        )
'''
    updated = replace_once(
        updated,
        old,
        new,
        "COMPRESSOR visual block",
    )

    old = '''    def _open_compressor_template_editor(self) -> None:
        self._open_compressor_text_template_editor(
            window_title="MESSAGE COMPRESSION TEMPLATE",
            description=(
                "Шаблон инструкции для конкретного SOURCE MESSAGE. "
                "Поддерживаются только {{REDUCTION_PERCENT}} и "
                "{{REMAINING_PERCENT}}."
            ),
            load_template=load_message_compression_template,
            get_template_path=get_message_compression_template_path,
            save_template=save_message_compression_template,
        )

    def _open_compressor_final_check_template_editor(self) -> None:
        self._open_compressor_text_template_editor(
            window_title="FINAL CHECK TEMPLATE",
            description=(
                "Дополнительная финальная инструкция COMPRESSOR. "
                "Checkbox определяет, включать ли этот блок в prompt. "
                "Поддерживаются {{REDUCTION_PERCENT}} и "
                "{{REMAINING_PERCENT}}."
            ),
            load_template=load_final_check_template,
            get_template_path=get_final_check_template_path,
            save_template=save_final_check_template,
        )
'''
    new = '''    def _open_compressor_template_editor(self) -> None:
        self._open_compressor_text_template_editor(
            window_title="КОНТЕКСТ СЖАТИЯ",
            description=(
                "Редактируемый контекст сжатия для конкретного SOURCE MESSAGE. "
                "Поддерживаются только {{REDUCTION_PERCENT}} и "
                "{{REMAINING_PERCENT}}."
            ),
            load_template=load_message_compression_template,
            get_template_path=get_message_compression_template_path,
            save_template=save_message_compression_template,
        )

    def _open_compressor_final_check_template_editor(self) -> None:
        self._open_compressor_text_template_editor(
            window_title="КОНТЕКСТ ДОПОЛНИТЕЛЬНОЙ ПРОВЕРКИ",
            description=(
                "Редактируемый контекст дополнительной проверки COMPRESSOR. "
                "Галочка в основном окне определяет, включать ли этот блок "
                "в prompt. Поддерживаются {{REDUCTION_PERCENT}} и "
                "{{REMAINING_PERCENT}}."
            ),
            load_template=load_final_check_template,
            get_template_path=get_final_check_template_path,
            save_template=save_final_check_template,
        )
'''
    updated = replace_once(
        updated,
        old,
        new,
        "COMPRESSOR editor titles",
    )

    compile(updated, str(target), "exec")

    temp = target.with_name(f".{target.name}.visual_patch.tmp")
    try:
        temp.write_text(updated, encoding="utf-8", newline="\n")
        os.replace(temp, target)
    finally:
        try:
            temp.unlink()
        except FileNotFoundError:
            pass

    print(f"OK: UI visual patch applied to {target}")
    print("Changed only ultra_ui.py; no Git commands were run.")


if __name__ == "__main__":
    main()
