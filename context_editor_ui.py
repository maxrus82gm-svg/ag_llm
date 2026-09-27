from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk

from context_registry import (
    delete_context_variant,
    get_context_record,
    get_user_contexts_path,
    list_context_groups,
    list_context_records,
    save_context_variant,
    set_active_variant,
)


_SCOPE_TEXT = {
    "NEXT_EVENT": "применяется к следующему server event",
    "NEXT_CALL": "применяется к следующему вызову модели",
    "NEXT_RUN": "применяется к следующему RUN",
}

_GROUP_UI_LABELS = {
    "planner": "Планировщик",
}


def open_context_editor(
    parent,
    *,
    agent_id: str = "ultra",
    app_title: str = "GigaChat Ultra Local Agent",
) -> None:
    try:
        groups = list_context_groups()
        storage_path = get_user_contexts_path(agent_id)
    except Exception as exc:
        messagebox.showerror(
            app_title,
            "Не удалось открыть Context Registry.\n\n"
            f"{type(exc).__name__}: {exc}",
            parent=parent,
        )
        return

    if not groups:
        messagebox.showerror(
            app_title,
            "Context Registry не содержит групп.",
            parent=parent,
        )
        return

    window = tk.Toplevel(parent)
    window.title("КОНТЕКСТЫ LLM")
    window.geometry("1240x820")
    window.minsize(920, 620)
    window.transient(parent)
    window.columnconfigure(0, weight=1)
    window.rowconfigure(1, weight=1)

    header = ttk.Frame(window, padding=(10, 10, 10, 0))
    header.grid(row=0, column=0, sticky="ew")
    header.columnconfigure(1, weight=1)

    ttk.Label(header, text="Группа:").grid(
        row=0, column=0, sticky="w", padx=(0, 6)
    )

    group_var = tk.StringVar()
    group_combo = ttk.Combobox(
        header,
        textvariable=group_var,
        state="readonly",
        width=34,
    )
    group_combo.grid(row=0, column=1, sticky="w")

    ttk.Label(
        header,
        text=f"Рабочее хранилище: {storage_path}",
    ).grid(
        row=1,
        column=0,
        columnspan=2,
        sticky="w",
        pady=(5, 0),
    )

    ttk.Label(
        header,
        text=(
            "Синий блок — служебное описание для человека. "
            "Зелёный блок — LLM-facing текст, который реально получает модель."
        ),
    ).grid(
        row=2,
        column=0,
        columnspan=2,
        sticky="w",
        pady=(3, 0),
    )

    body = ttk.PanedWindow(window, orient="horizontal")
    body.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)

    left = ttk.Frame(body, padding=(0, 0, 8, 0))
    right = ttk.PanedWindow(body, orient="vertical")

    body.add(left, weight=1)
    body.add(right, weight=4)

    ttk.Label(left, text="CONTEXT ID / ACTIVE").pack(
        anchor="w", pady=(0, 5)
    )

    context_list = tk.Listbox(
        left,
        exportselection=False,
        bg="#E5E6E8",
        fg="#252525",
        selectbackground="#B8C7D9",
        selectforeground="#111111",
        activestyle="none",
    )
    context_list.pack(fill="both", expand=True)

    working = ttk.Frame(right, padding=(8, 0, 0, 8))
    factory = ttk.Frame(right, padding=(8, 8, 0, 0))

    right.add(working, weight=4)
    right.add(factory, weight=2)

    working.columnconfigure(0, weight=1)
    working.rowconfigure(8, weight=1)

    context_id_var = tk.StringVar()
    source_var = tk.StringVar()
    owner_var = tk.StringVar()
    scope_var = tk.StringVar()
    variables_var = tk.StringVar()
    active_variant_var = tk.StringVar(value="default")
    edit_variant_var = tk.StringVar(value="default")
    variant_status_var = tk.StringVar()

    ttk.Label(working, textvariable=context_id_var).grid(
        row=0, column=0, sticky="w"
    )

    metadata = ttk.Frame(working)
    metadata.grid(row=1, column=0, sticky="ew", pady=(5, 5))

    ttk.Label(metadata, text="Источник:").pack(side="left")
    ttk.Label(metadata, textvariable=source_var).pack(
        side="left", padx=(4, 16)
    )

    ttk.Label(metadata, text="Owner:").pack(side="left")
    ttk.Label(metadata, textvariable=owner_var).pack(
        side="left", padx=(4, 16)
    )

    ttk.Label(metadata, text="Scope:").pack(side="left")
    ttk.Label(metadata, textvariable=scope_var).pack(
        side="left", padx=(4, 0)
    )

    ttk.Label(
        working,
        textvariable=variables_var,
    ).grid(row=2, column=0, sticky="w", pady=(0, 6))

    variant_bar = ttk.Frame(working)
    variant_bar.grid(row=3, column=0, sticky="ew", pady=(0, 7))

    ttk.Label(variant_bar, text="Редактировать:").pack(side="left")

    edit_variant_combo = ttk.Combobox(
        variant_bar,
        textvariable=edit_variant_var,
        values=("default", "custom"),
        state="readonly",
        width=12,
    )
    edit_variant_combo.pack(side="left", padx=(5, 18))

    ttk.Label(variant_bar, text="Активный:").pack(side="left")

    active_default_radio = ttk.Radiobutton(
        variant_bar,
        text="Default",
        variable=active_variant_var,
        value="default",
    )
    active_default_radio.pack(side="left", padx=(5, 5))

    active_custom_radio = ttk.Radiobutton(
        variant_bar,
        text="Custom",
        variable=active_variant_var,
        value="custom",
    )
    active_custom_radio.pack(side="left")

    ttk.Label(
        variant_bar,
        textvariable=variant_status_var,
    ).pack(side="left", padx=(18, 0))

    ttk.Label(
        working,
        text="Описание — человеку, НЕ отправляется LLM",
    ).grid(row=4, column=0, sticky="w")

    description_editor = scrolledtext.ScrolledText(
        working,
        wrap="word",
        height=4,
        undo=True,
        font=("Segoe UI", 10),
        bg="#EEF4FB",
        fg="#245C9C",
        insertbackground="#245C9C",
    )
    description_editor.grid(
        row=5,
        column=0,
        sticky="ew",
        pady=(3, 7),
    )

    ttk.Label(
        working,
        text="LLM-facing текст — напрямую влияет на поведение модели",
    ).grid(row=6, column=0, sticky="w")

    text_editor = scrolledtext.ScrolledText(
        working,
        wrap="word",
        undo=True,
        font=("Segoe UI", 10),
        bg="#EEF8F1",
        fg="#1F6B43",
        insertbackground="#1F6B43",
    )
    text_editor.grid(
        row=8,
        column=0,
        sticky="nsew",
        pady=(3, 0),
    )

    factory.columnconfigure(0, weight=1)
    factory.rowconfigure(3, weight=1)

    factory_description_var = tk.StringVar()

    ttk.Label(
        factory,
        text="FACTORY SEED — только чтение",
    ).grid(row=0, column=0, sticky="w")

    tk.Label(
        factory,
        textvariable=factory_description_var,
        bg="#E5E6E8",
        fg="#245C9C",
        anchor="w",
        justify="left",
        wraplength=850,
        padx=6,
        pady=4,
    ).grid(
        row=1,
        column=0,
        sticky="ew",
        pady=(3, 5),
    )

    factory_editor = scrolledtext.ScrolledText(
        factory,
        wrap="word",
        state="disabled",
        height=7,
        font=("Segoe UI", 9),
        bg="#E5E6E8",
        fg="#252525",
    )
    factory_editor.grid(
        row=3,
        column=0,
        sticky="nsew",
    )

    group_display_to_id: dict[str, str] = {}
    records: dict[str, dict] = {}
    context_ids_by_index: list[str] = []
    current_context_id: str | None = None

    def set_editor_text(widget, value: str) -> None:
        widget.delete("1.0", "end")
        if value:
            widget.insert("1.0", value)

    def set_readonly_text(widget, value: str) -> None:
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        if value:
            widget.insert("1.0", value)
        widget.configure(state="disabled")

    def current_group_id() -> str:
        display = group_var.get()
        return group_display_to_id[display]

    def load_variant_editor(record: dict) -> None:
        variant_id = edit_variant_var.get()
        if variant_id not in {"default", "custom"}:
            variant_id = "default"
            edit_variant_var.set(variant_id)

        if variant_id == "default":
            description = record["default_description"]
            text = record["default_text"]
            exists = record["has_default_override"]
            variant_status_var.set(
                "USER DEFAULT" if exists else "FACTORY DEFAULT"
            )
        else:
            custom = record["user_variants"].get("custom")
            if custom is None:
                description = record["default_description"]
                text = record["default_text"]
                exists = False
                variant_status_var.set("CUSTOM ещё не сохранён")
            else:
                description = custom["description"]
                text = custom["text"]
                exists = True
                variant_status_var.set("CUSTOM сохранён")

        set_editor_text(description_editor, description)
        set_editor_text(text_editor, text)

        reset_variant_button.configure(
            state="normal" if exists else "disabled"
        )

    def load_record(
        context_id: str,
        *,
        edit_variant: str | None = None,
    ) -> None:
        nonlocal current_context_id

        record = get_context_record(context_id, agent_id)
        records[context_id] = record
        current_context_id = context_id

        context_id_var.set(context_id)
        source_var.set(record["effective_source"])
        owner_var.set(record["runtime_owner"])

        scope = record["apply_scope"]
        scope_var.set(
            f"{scope} — {_SCOPE_TEXT.get(scope, scope)}"
        )

        allowed = record["allowed_variables"]
        variables_var.set(
            "Variables: "
            + (", ".join(allowed) if allowed else "нет")
        )

        active_variant_var.set(record["active_variant"])

        custom_exists = "custom" in record["user_variants"]
        active_custom_radio.configure(
            state="normal" if custom_exists else "disabled"
        )

        if edit_variant in {"default", "custom"}:
            edit_variant_var.set(edit_variant)
        elif edit_variant_var.get() not in {"default", "custom"}:
            edit_variant_var.set("default")

        factory_description_var.set(record["factory_description"])
        set_readonly_text(factory_editor, record["factory_text"])

        load_variant_editor(record)

    def load_selected(_event=None) -> None:
        selection = context_list.curselection()
        if not selection:
            return

        context_id = context_ids_by_index[selection[0]]
        load_record(context_id)

    def refresh_context_list(
        select_context_id: str | None = None,
        *,
        edit_variant: str | None = None,
    ) -> None:
        nonlocal records, context_ids_by_index

        group_id = current_group_id()
        items = list_context_records(agent_id, group_id=group_id)
        records = {
            item["context_id"]: item
            for item in items
        }

        context_list.delete(0, "end")
        context_ids_by_index = []

        selected_index = None

        for index, record in enumerate(items):
            context_id = record["context_id"]
            context_ids_by_index.append(context_id)

            active = record["active_variant"].upper()
            context_list.insert(
                "end",
                f"● {active:7}  {context_id}",
            )

            context_list.itemconfig(
                index,
                foreground=(
                    "#2D5F9A"
                    if record["active_variant"] != "default"
                    else "#2F7D4A"
                ),
            )

            if context_id == select_context_id:
                selected_index = index

        if not context_ids_by_index:
            return

        if selected_index is None:
            selected_index = 0

        context_list.selection_clear(0, "end")
        context_list.selection_set(selected_index)
        context_list.see(selected_index)

        load_record(
            context_ids_by_index[selected_index],
            edit_variant=edit_variant,
        )

    def on_group_changed(_event=None) -> None:
        edit_variant_var.set("default")
        refresh_context_list()

    def on_edit_variant_changed(_event=None) -> None:
        if current_context_id is None:
            return
        load_record(
            current_context_id,
            edit_variant=edit_variant_var.get(),
        )

    def save_variant() -> None:
        if current_context_id is None:
            return

        variant_id = edit_variant_var.get()

        try:
            save_context_variant(
                current_context_id,
                variant_id,
                text_editor.get("1.0", "end-1c"),
                description=description_editor.get(
                    "1.0", "end-1c"
                ),
                agent_id=agent_id,
            )

            refresh_context_list(
                current_context_id,
                edit_variant=variant_id,
            )

            messagebox.showinfo(
                app_title,
                (
                    f"{current_context_id} / {variant_id} сохранён.\n"
                    "Изменение будет использовано согласно apply_scope "
                    "без restart приложения."
                ),
                parent=window,
            )
        except Exception as exc:
            messagebox.showerror(
                app_title,
                "Не удалось сохранить контекст.\n\n"
                f"{type(exc).__name__}: {exc}",
                parent=window,
            )

    def reset_variant() -> None:
        if current_context_id is None:
            return

        variant_id = edit_variant_var.get()

        if not messagebox.askyesno(
            app_title,
            (
                f"Удалить пользовательский вариант "
                f"{current_context_id} / {variant_id}?\n\n"
                "Для default будет восстановлен Factory Seed. "
                "Для custom вариант будет удалён."
            ),
            parent=window,
        ):
            return

        try:
            delete_context_variant(
                current_context_id,
                variant_id,
                agent_id=agent_id,
            )

            refresh_context_list(
                current_context_id,
                edit_variant=variant_id,
            )
        except Exception as exc:
            messagebox.showerror(
                app_title,
                "Не удалось сбросить вариант.\n\n"
                f"{type(exc).__name__}: {exc}",
                parent=window,
            )

    def activate_variant() -> None:
        if current_context_id is None:
            return

        variant_id = active_variant_var.get()

        try:
            set_active_variant(
                current_context_id,
                variant_id,
                agent_id=agent_id,
            )

            refresh_context_list(
                current_context_id,
                edit_variant=edit_variant_var.get(),
            )
        except Exception as exc:
            try:
                record = get_context_record(
                    current_context_id,
                    agent_id,
                )
                active_variant_var.set(record["active_variant"])
            except Exception:
                pass

            messagebox.showerror(
                app_title,
                "Не удалось переключить активный вариант.\n\n"
                f"{type(exc).__name__}: {exc}",
                parent=window,
            )

    active_default_radio.configure(command=activate_variant)
    active_custom_radio.configure(command=activate_variant)

    edit_variant_combo.bind(
        "<<ComboboxSelected>>",
        on_edit_variant_changed,
    )
    context_list.bind(
        "<<ListboxSelect>>",
        load_selected,
    )
    group_combo.bind(
        "<<ComboboxSelected>>",
        on_group_changed,
    )

    buttons = ttk.Frame(window)
    buttons.grid(
        row=2,
        column=0,
        sticky="ew",
        padx=10,
        pady=(0, 10),
    )

    ttk.Button(
        buttons,
        text="Сохранить вариант",
        command=save_variant,
    ).pack(side="left")

    reset_variant_button = ttk.Button(
        buttons,
        text="Сбросить вариант",
        command=reset_variant,
    )
    reset_variant_button.pack(side="left", padx=(8, 0))

    ttk.Button(
        buttons,
        text="Закрыть",
        command=window.destroy,
    ).pack(side="right")

    group_values: list[str] = []

    for group in groups:
        group_label = _GROUP_UI_LABELS.get(
            group["group_id"], group["group_name"]
        )
        display = (
            f"{group_label}  [{group['group_id']}]"
        )
        group_values.append(display)
        group_display_to_id[display] = group["group_id"]

    group_combo.configure(values=group_values)
    group_var.set(group_values[0])

    window._context_editor_widgets = {
        "group_combo": group_combo,
        "context_list": context_list,
        "description_editor": description_editor,
        "text_editor": text_editor,
        "factory_editor": factory_editor,
        "edit_variant_combo": edit_variant_combo,
        "active_variant_var": active_variant_var,
        "reset_variant_button": reset_variant_button,
    }

    refresh_context_list()
