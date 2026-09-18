from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SERVER = ROOT / "server.py"
UI = ROOT / "ultra_ui.py"

SERVER_REPLACEMENTS = [('MAX_AGENT_TOOL_ITERATIONS = 20\n',
  'MAX_AGENT_TOOL_ITERATIONS = 20\nMAX_CONFIGURABLE_TOOL_ITERATIONS = 200\n',
  'server: configurable tool limit constant'),
 ('    },\n]\n\n_access_token: str | None = None',
  '    },\n'
  '    {\n'
  '        "name": "delete_file",\n'
  '        "description": (\n'
  '            "Удалить существующий текстовый файл внутри рабочей папки. "\n'
  '            "Инструмент доступен только когда сервер явно разрешил удаление."\n'
  '        ),\n'
  '        "parameters": {\n'
  '            "type": "object",\n'
  '            "properties": {\n'
  '                "path": {\n'
  '                    "type": "string",\n'
  '                    "description": "Относительный путь к удаляемому текстовому файлу.",\n'
  '                }\n'
  '            },\n'
  '            "required": ["path"],\n'
  '        },\n'
  '    },\n'
  ']\n'
  '\n'
  '_access_token: str | None = None',
  'server: delete tool schema'),
 ('        permissions = {\n'
  '            "allow_read": True,\n'
  '            "allow_write": False,\n'
  '            "read_scope": ".",\n'
  '            "write_scope": ".",\n'
  '            "auto_backup": True,\n'
  '        }',
  '        permissions = {\n'
  '            "allow_read": True,\n'
  '            "allow_write": False,\n'
  '            "allow_delete": False,\n'
  '            "read_scope": ".",\n'
  '            "write_scope": ".",\n'
  '            "delete_scope": ".",\n'
  '            "tool_limit": MAX_AGENT_TOOL_ITERATIONS,\n'
  '            "auto_backup": True,\n'
  '        }',
  'server: safe defaults'),
 ('    allow_read = bool(permissions.get("allow_read", True))\n'
  '    allow_write = bool(permissions.get("allow_write", False))\n'
  '    auto_backup = bool(permissions.get("auto_backup", True))\n'
  '    read_scope = clean_scope(permissions.get("read_scope", "."), "read_scope")\n'
  '    write_scope = clean_scope(permissions.get("write_scope", "."), "write_scope")\n'
  '\n'
  '    return {\n'
  '        "allow_read": allow_read,\n'
  '        "allow_write": allow_write,\n'
  '        "read_scope": read_scope,\n'
  '        "write_scope": write_scope,\n'
  '        "auto_backup": auto_backup,\n'
  '    }',
  '    allow_read = bool(permissions.get("allow_read", True))\n'
  '    allow_write = bool(permissions.get("allow_write", False))\n'
  '    allow_delete = bool(permissions.get("allow_delete", False))\n'
  '    auto_backup = bool(permissions.get("auto_backup", True))\n'
  '    read_scope = clean_scope(permissions.get("read_scope", "."), "read_scope")\n'
  '    write_scope = clean_scope(permissions.get("write_scope", "."), "write_scope")\n'
  '    delete_scope = clean_scope(permissions.get("delete_scope", "."), "delete_scope")\n'
  '\n'
  '    try:\n'
  '        tool_limit = int(\n'
  '            permissions.get("tool_limit", MAX_AGENT_TOOL_ITERATIONS)\n'
  '        )\n'
  '    except (TypeError, ValueError) as exc:\n'
  '        raise ValueError("tool_limit должен быть целым числом.") from exc\n'
  '    if not 1 <= tool_limit <= MAX_CONFIGURABLE_TOOL_ITERATIONS:\n'
  '        raise ValueError(\n'
  '            "tool_limit должен быть в диапазоне "\n'
  '            f"1..{MAX_CONFIGURABLE_TOOL_ITERATIONS}."\n'
  '        )\n'
  '\n'
  '    return {\n'
  '        "allow_read": allow_read,\n'
  '        "allow_write": allow_write,\n'
  '        "allow_delete": allow_delete,\n'
  '        "read_scope": read_scope,\n'
  '        "write_scope": write_scope,\n'
  '        "delete_scope": delete_scope,\n'
  '        "tool_limit": tool_limit,\n'
  '        "auto_backup": auto_backup,\n'
  '    }',
  'server: normalize delete + tool limit'),
 ('    read_root = _resolve_workspace_path(root, result["read_scope"])\n'
  '    write_root = _resolve_workspace_path(root, result["write_scope"])\n'
  '\n'
  '    if result["allow_read"] and not read_root.is_dir():\n'
  '        raise NotADirectoryError(\n'
  '            f"Разрешённая область чтения не найдена: {result[\'read_scope\']}"\n'
  '        )\n'
  '    if result["allow_write"] and not write_root.is_dir():\n'
  '        raise NotADirectoryError(\n'
  '            f"Разрешённая область записи не найдена: {result[\'write_scope\']}"\n'
  '        )\n'
  '\n'
  '    result["_read_root"] = read_root\n'
  '    result["_write_root"] = write_root\n'
  '    return result',
  '    read_root = _resolve_workspace_path(root, result["read_scope"])\n'
  '    write_root = _resolve_workspace_path(root, result["write_scope"])\n'
  '    delete_root = _resolve_workspace_path(root, result["delete_scope"])\n'
  '\n'
  '    if result["allow_read"] and not read_root.is_dir():\n'
  '        raise NotADirectoryError(\n'
  '            f"Разрешённая область чтения не найдена: {result[\'read_scope\']}"\n'
  '        )\n'
  '    if result["allow_write"] and not write_root.is_dir():\n'
  '        raise NotADirectoryError(\n'
  '            f"Разрешённая область записи не найдена: {result[\'write_scope\']}"\n'
  '        )\n'
  '    if result["allow_delete"] and not delete_root.is_dir():\n'
  '        raise NotADirectoryError(\n'
  '            f"Разрешённая область удаления не найдена: {result[\'delete_scope\']}"\n'
  '        )\n'
  '\n'
  '    result["_read_root"] = read_root\n'
  '    result["_write_root"] = write_root\n'
  '    result["_delete_root"] = delete_root\n'
  '    return result',
  'server: prepare delete scope'),
 ('    elif operation == "write":\n'
  '        if not policy["allow_write"]:\n'
  '            raise PermissionError("Запись отключена для этого запуска.")\n'
  '        scope_root = policy["_write_root"]\n'
  '        scope_name = policy["write_scope"]\n'
  '    else:\n'
  '        raise ValueError(f"Неизвестная операция доступа: {operation}")',
  '    elif operation == "write":\n'
  '        if not policy["allow_write"]:\n'
  '            raise PermissionError("Запись отключена для этого запуска.")\n'
  '        scope_root = policy["_write_root"]\n'
  '        scope_name = policy["write_scope"]\n'
  '    elif operation == "delete":\n'
  '        if not policy["allow_delete"]:\n'
  '            raise PermissionError("Удаление отключено для этого запуска.")\n'
  '        scope_root = policy["_delete_root"]\n'
  '        scope_name = policy["delete_scope"]\n'
  '    else:\n'
  '        raise ValueError(f"Неизвестная операция доступа: {operation}")',
  'server: delete permission gate'),
 ('    if policy["allow_write"]:\n'
  '        allowed_names.add("write_file")\n'
  '    return [item for item in AGENT_FUNCTIONS if item["name"] in allowed_names]',
  '    if policy["allow_write"]:\n'
  '        allowed_names.add("write_file")\n'
  '    if policy["allow_delete"]:\n'
  '        allowed_names.add("delete_file")\n'
  '    return [item for item in AGENT_FUNCTIONS if item["name"] in allowed_names]',
  'server: expose delete only when enabled'),
 ('        "allow_read": policy["allow_read"],\n'
  '        "allow_write": policy["allow_write"],\n'
  '        "read_scope": policy["read_scope"],\n'
  '        "write_scope": policy["write_scope"],\n'
  '        "auto_backup": policy["auto_backup"],',
  '        "allow_read": policy["allow_read"],\n'
  '        "allow_write": policy["allow_write"],\n'
  '        "allow_delete": policy["allow_delete"],\n'
  '        "read_scope": policy["read_scope"],\n'
  '        "write_scope": policy["write_scope"],\n'
  '        "delete_scope": policy["delete_scope"],\n'
  '        "tool_limit": policy["tool_limit"],\n'
  '        "auto_backup": policy["auto_backup"],',
  'server: policy summary'),
 ('        "core_files": copied_core,\n'
  '        "changed_files": [],\n'
  '        "new_files": [],\n'
  '    }\n'
  '    session = {\n'
  '        "backup_dir": backup_dir,\n'
  '        "backed_up_paths": set(),\n'
  '        "manifest": manifest,\n'
  '    }',
  '        "core_files": copied_core,\n'
  '        "changed_files": [],\n'
  '        "new_files": [],\n'
  '        "deleted_files": [],\n'
  '    }\n'
  '    session = {\n'
  '        "backup_dir": backup_dir,\n'
  '        "backed_up_paths": set(),\n'
  '        "delete_backed_up_paths": set(),\n'
  '        "manifest": manifest,\n'
  '    }',
  'server: deletion backup manifest'),
 ('def _require_text_suffix(path: Path) -> None:\n',
  'def _backup_before_delete(root: Path, path: Path, session: dict | None) -> None:\n'
  '    """Сохранить файл непосредственно перед delete_file."""\n'
  '    if session is None:\n'
  '        return\n'
  '\n'
  '    relative = path.relative_to(root).as_posix()\n'
  '    if relative in session["delete_backed_up_paths"]:\n'
  '        return\n'
  '    if not path.is_file():\n'
  '        raise ValueError(f"Нельзя резервировать перед удалением не-файл: {relative}")\n'
  '\n'
  '    destination = session["backup_dir"] / "deleted" / Path(relative)\n'
  '    destination.parent.mkdir(parents=True, exist_ok=True)\n'
  '    shutil.copy2(path, destination)\n'
  '\n'
  '    session["delete_backed_up_paths"].add(relative)\n'
  '    if relative not in session["manifest"]["deleted_files"]:\n'
  '        session["manifest"]["deleted_files"].append(relative)\n'
  '    _write_backup_manifest(session)\n'
  '\n'
  '\n'
  'def _require_text_suffix(path: Path) -> None:\n',
  'server: backup before delete helper'),
 ('def _parse_agent_arguments(function_name: str, raw_arguments: object) -> dict:\n',
  'def _agent_delete_file(\n'
  '    root: Path,\n'
  '    path_text: str,\n'
  '    policy: dict,\n'
  '    backup_session: dict | None,\n'
  ') -> dict:\n'
  '    path = _require_operation_permission(root, path_text, "delete", policy)\n'
  '    _require_text_suffix(path)\n'
  '\n'
  '    if path == root:\n'
  '        raise ValueError("Нельзя удалить workspace_root.")\n'
  '    if path.is_symlink():\n'
  '        raise ValueError("Удаление symlink запрещено.")\n'
  '    if not path.exists():\n'
  '        raise FileNotFoundError(f"Файл не найден: {path_text}")\n'
  '    if not path.is_file():\n'
  '        raise ValueError("delete_file удаляет только файлы, не папки.")\n'
  '\n'
  '    size = path.stat().st_size\n'
  '    _backup_before_delete(root, path, backup_session)\n'
  '    path.unlink()\n'
  '\n'
  '    return {\n'
  '        "path": path.relative_to(root).as_posix(),\n'
  '        "deleted": True,\n'
  '        "bytes": size,\n'
  '    }\n'
  '\n'
  '\n'
  'def _parse_agent_arguments(function_name: str, raw_arguments: object) -> dict:\n',
  'server: delete implementation'),
 ('    name = function_call.get("name")\n'
  '    if name not in {"list_dir", "read_file", "write_file"}:\n'
  '        raise ValueError(f"GigaChat запросил неизвестную функцию: {name!r}.")\n'
  '\n'
  '    arguments = _parse_agent_arguments(name, function_call.get("arguments"))\n'
  '    expected_keys = {\n'
  '        "list_dir": {"path"},\n'
  '        "read_file": {"path"},\n'
  '        "write_file": {"path", "content"},\n'
  '    }[name]',
  '    name = function_call.get("name")\n'
  '    if name not in {"list_dir", "read_file", "write_file", "delete_file"}:\n'
  '        raise ValueError(f"GigaChat запросил неизвестную функцию: {name!r}.")\n'
  '\n'
  '    arguments = _parse_agent_arguments(name, function_call.get("arguments"))\n'
  '    expected_keys = {\n'
  '        "list_dir": {"path"},\n'
  '        "read_file": {"path"},\n'
  '        "write_file": {"path", "content"},\n'
  '        "delete_file": {"path"},\n'
  '    }[name]',
  'server: dispatcher names'),
 ('    if name == "list_dir":\n'
  '        return _agent_list_dir(root, arguments["path"], policy)\n'
  '    if name == "read_file":\n'
  '        return _agent_read_file(root, arguments["path"], policy)\n'
  '    return _agent_write_file(\n'
  '        root,\n'
  '        arguments["path"],\n'
  '        arguments["content"],\n'
  '        policy,\n'
  '        backup_session,\n'
  '    )',
  '    if name == "list_dir":\n'
  '        return _agent_list_dir(root, arguments["path"], policy)\n'
  '    if name == "read_file":\n'
  '        return _agent_read_file(root, arguments["path"], policy)\n'
  '    if name == "delete_file":\n'
  '        return _agent_delete_file(\n'
  '            root,\n'
  '            arguments["path"],\n'
  '            policy,\n'
  '            backup_session,\n'
  '        )\n'
  '    return _agent_write_file(\n'
  '        root,\n'
  '        arguments["path"],\n'
  '        arguments["content"],\n'
  '        policy,\n'
  '        backup_session,\n'
  '    )',
  'server: dispatcher delete branch'),
 ('        f"Запись: {\'РАЗРЕШЕНА\' if policy[\'allow_write\'] else \'ЗАПРЕЩЕНА\'}\\n"\n'
  '        f"Область записи: {policy[\'write_scope\']}\\n"\n'
  '        f"Автобэкап: {\'ВКЛЮЧЁН\' if policy[\'auto_backup\'] else \'ВЫКЛЮЧЕН\'}\\n"',
  '        f"Запись: {\'РАЗРЕШЕНА\' if policy[\'allow_write\'] else \'ЗАПРЕЩЕНА\'}\\n"\n'
  '        f"Область записи: {policy[\'write_scope\']}\\n"\n'
  '        f"Удаление: {\'РАЗРЕШЕНО\' if policy[\'allow_delete\'] else \'ЗАПРЕЩЕНО\'}\\n"\n'
  '        f"Область удаления: {policy[\'delete_scope\']}\\n"\n'
  '        f"Лимит вызовов инструментов: {policy[\'tool_limit\']}\\n"\n'
  '        "Планируй действия так, чтобы уложиться в этот лимит. "\n'
  '        "Не трать вызовы на повторное чтение без необходимости.\\n"\n'
  '        f"Автобэкап: {\'ВКЛЮЧЁН\' if policy[\'auto_backup\'] else \'ВЫКЛЮЧЕН\'}\\n"',
  'server: tell model permissions and tool budget'),
 ('                "Никогда не передавай абсолютные Windows-пути в list_dir, "\n                "read_file или write_file."',
  '                "Никогда не передавай абсолютные Windows-пути в list_dir, "\n                "read_file, write_file или delete_file."',
  'server: system tool names'),
 ('                if tool_iterations >= MAX_AGENT_TOOL_ITERATIONS:',
  '                if tool_iterations >= policy["tool_limit"]:',
  'server: enforce per-run tool limit'),
 ('                        f"Tool calls: {tool_call_count}\\n"\n                        f"Last function: {last_tool_name}\\n"',
  '                        f"Tool calls: {tool_call_count}\\n"\n'
  '                        f"Tool limit: {policy[\'tool_limit\']}\\n"\n'
  '                        f"Last function: {last_tool_name}\\n"',
  'server: tool limit error detail'),
 ('                messages.append(\n'
  '                    {\n'
  '                        "role": "function",\n'
  '                        "name": function_name,\n'
  '                        "content": json.dumps(result, ensure_ascii=False),\n'
  '                    }\n'
  '                )\n'
  '                tool_iterations += 1',
  '                tool_iterations += 1\n'
  '                result_for_model = dict(result)\n'
  '                remaining_tools = max(policy["tool_limit"] - tool_iterations, 0)\n'
  '                result_for_model["_tool_budget"] = {\n'
  '                    "limit": policy["tool_limit"],\n'
  '                    "used": tool_iterations,\n'
  '                    "remaining": remaining_tools,\n'
  '                    "instruction": (\n'
  '                        "Если оставшихся вызовов мало, прекрати лишнее исследование "\n'
  '                        "и заверши задачу или сообщи, что требуется новый запуск."\n'
  '                    ),\n'
  '                }\n'
  '                messages.append(\n'
  '                    {\n'
  '                        "role": "function",\n'
  '                        "name": function_name,\n'
  '                        "content": json.dumps(result_for_model, ensure_ascii=False),\n'
  '                    }\n'
  '                )',
  'server: report remaining tool budget to model')]
UI_REPLACEMENTS = [('        self.allow_read_var = tk.BooleanVar(value=True)\n'
  '        self.allow_write_var = tk.BooleanVar(value=False)\n'
  '        self.auto_backup_var = tk.BooleanVar(value=True)\n'
  '        self.read_scope_var = tk.StringVar(value=".")\n'
  '        default_write_scope = "Документация" if (Path.cwd() / "Документация").is_dir() else "."\n'
  '        self.write_scope_var = tk.StringVar(value=default_write_scope)\n'
  '        self.backup_path_var = tk.StringVar(value=str(get_backup_base_path()))',
  '        self.allow_read_var = tk.BooleanVar(value=True)\n'
  '        self.allow_write_var = tk.BooleanVar(value=False)\n'
  '        self.allow_delete_var = tk.BooleanVar(value=False)\n'
  '        self.auto_backup_var = tk.BooleanVar(value=True)\n'
  '        self.dark_theme_var = tk.BooleanVar(value=True)\n'
  '        self.tool_limit_var = tk.StringVar(value="20")\n'
  '        self.read_scope_var = tk.StringVar(value=".")\n'
  '        default_write_scope = "Документация" if (Path.cwd() / "Документация").is_dir() else "."\n'
  '        self.write_scope_var = tk.StringVar(value=default_write_scope)\n'
  '        self.delete_scope_var = tk.StringVar(value=".")\n'
  '        self.backup_path_var = tk.StringVar(value=str(get_backup_base_path()))',
  'ui: variables'),
 ('        self._build_ui()\n        self.after(100, self._poll_events)',
  '        self._build_ui()\n        self._apply_theme()\n        self.after(100, self._poll_events)',
  'ui: apply initial theme'),
 ('    def _record_initial_mtimes(self) -> None:\n',
  '    def _apply_theme(self) -> None:\n'
  '        dark = self.dark_theme_var.get()\n'
  '        style = ttk.Style(self)\n'
  '        try:\n'
  '            style.theme_use("clam")\n'
  '        except tk.TclError:\n'
  '            pass\n'
  '\n'
  '        if dark:\n'
  '            bg = "#1e1f22"\n'
  '            panel = "#2b2d30"\n'
  '            field = "#202124"\n'
  '            fg = "#e8e8e8"\n'
  '            muted = "#b8b8b8"\n'
  '            select_bg = "#3f638f"\n'
  '            button_bg = "#35383d"\n'
  '        else:\n'
  '            bg = "#f3f3f3"\n'
  '            panel = "#f3f3f3"\n'
  '            field = "#ffffff"\n'
  '            fg = "#111111"\n'
  '            muted = "#444444"\n'
  '            select_bg = "#99c2ff"\n'
  '            button_bg = "#e7e7e7"\n'
  '\n'
  '        self.configure(bg=bg)\n'
  '        style.configure(".", background=panel, foreground=fg)\n'
  '        style.configure("TFrame", background=panel)\n'
  '        style.configure("TLabel", background=panel, foreground=fg)\n'
  '        style.configure("TLabelframe", background=panel, foreground=fg)\n'
  '        style.configure("TLabelframe.Label", background=panel, foreground=fg)\n'
  '        style.configure("TCheckbutton", background=panel, foreground=fg)\n'
  '        style.configure("TButton", background=button_bg, foreground=fg)\n'
  '        style.configure("TEntry", fieldbackground=field, foreground=fg)\n'
  '        style.configure("TSpinbox", fieldbackground=field, foreground=fg)\n'
  '        style.map(\n'
  '            "TButton",\n'
  '            background=[("active", button_bg)],\n'
  '            foreground=[("disabled", muted), ("!disabled", fg)],\n'
  '        )\n'
  '        style.map(\n'
  '            "TCheckbutton",\n'
  '            background=[("active", panel)],\n'
  '            foreground=[("disabled", muted), ("!disabled", fg)],\n'
  '        )\n'
  '\n'
  '        for name in ("trace_log", "chat", "input_box"):\n'
  '            widget = getattr(self, name, None)\n'
  '            if widget is not None:\n'
  '                widget.configure(\n'
  '                    bg=field,\n'
  '                    fg=fg,\n'
  '                    insertbackground=fg,\n'
  '                    selectbackground=select_bg,\n'
  '                    selectforeground=fg,\n'
  '                )\n'
  '\n'
  '    def _record_initial_mtimes(self) -> None:\n',
  'ui: theme method'),
 ('        # Автобэкап — отдельный общий переключатель запуска.\n'
  '        backup_check = ttk.Checkbutton(\n'
  '            security,\n'
  '            text="Автобэкап ДО запуска",\n'
  '            variable=self.auto_backup_var,\n'
  '        )\n'
  '        backup_check.grid(\n'
  '            row=0, column=0, columnspan=4, sticky="w", pady=(0, 4)\n'
  '        )',
  '        # Верхняя строка: backup, лимит инструментов и тема.\n'
  '        backup_check = ttk.Checkbutton(\n'
  '            security,\n'
  '            text="Автобэкап ДО запуска",\n'
  '            variable=self.auto_backup_var,\n'
  '        )\n'
  '        backup_check.grid(\n'
  '            row=0, column=0, columnspan=2, sticky="w", pady=(0, 4)\n'
  '        )\n'
  '\n'
  '        ttk.Label(security, text="Лимит tools:").grid(\n'
  '            row=0, column=2, sticky="e", padx=(12, 4), pady=(0, 4)\n'
  '        )\n'
  '        tool_limit_spin = ttk.Spinbox(\n'
  '            security,\n'
  '            from_=1,\n'
  '            to=200,\n'
  '            width=6,\n'
  '            textvariable=self.tool_limit_var,\n'
  '        )\n'
  '        tool_limit_spin.grid(\n'
  '            row=0, column=3, sticky="w", pady=(0, 4)\n'
  '        )\n'
  '\n'
  '        theme_check = ttk.Checkbutton(\n'
  '            security,\n'
  '            text="Тёмная тема",\n'
  '            variable=self.dark_theme_var,\n'
  '            command=self._apply_theme,\n'
  '        )\n'
  '        theme_check.grid(\n'
  '            row=0, column=4, sticky="w", padx=(14, 0), pady=(0, 4)\n'
  '        )',
  'ui: top controls'),
 ('        write_scope_button.grid(row=2, column=3, sticky="w", pady=(6, 0))\n'
  '\n'
  '        ttk.Label(security, text="Защищённые бэкапы:").grid(\n'
  '            row=3, column=1, sticky="w", padx=(2, 0), pady=(6, 0)\n'
  '        )',
  '        write_scope_button.grid(row=2, column=3, sticky="w", pady=(6, 0))\n'
  '\n'
  '        # Удаление — отдельное разрешение, независимо от записи.\n'
  '        delete_check = ttk.Checkbutton(\n'
  '            security,\n'
  '            text="",\n'
  '            variable=self.allow_delete_var,\n'
  '        )\n'
  '        delete_check.grid(row=3, column=0, sticky="w", pady=(6, 0))\n'
  '\n'
  '        ttk.Label(security, text="Удаление только в:").grid(\n'
  '            row=3, column=1, sticky="w", padx=(2, 0), pady=(6, 0)\n'
  '        )\n'
  '        delete_scope_entry = ttk.Entry(\n'
  '            security,\n'
  '            textvariable=self.delete_scope_var,\n'
  '            width=62,\n'
  '        )\n'
  '        delete_scope_entry.grid(\n'
  '            row=3, column=2, sticky="w", padx=(8, 8), pady=(6, 0)\n'
  '        )\n'
  '        bind_edit_shortcuts(delete_scope_entry)\n'
  '        delete_scope_button = ttk.Button(\n'
  '            security,\n'
  '            text="Выбрать",\n'
  '            command=lambda: self._choose_scope(self.delete_scope_var),\n'
  '        )\n'
  '        delete_scope_button.grid(row=3, column=3, sticky="w", pady=(6, 0))\n'
  '\n'
  '        ttk.Label(security, text="Защищённые бэкапы:").grid(\n'
  '            row=4, column=1, sticky="w", padx=(2, 0), pady=(6, 0)\n'
  '        )',
  'ui: delete row'),
 ('        backup_label.grid(\n            row=3, column=2, columnspan=2, sticky="w", padx=(8, 0), pady=(6, 0)\n        )',
  '        backup_label.grid(\n            row=4, column=2, columnspan=3, sticky="w", padx=(8, 0), pady=(6, 0)\n        )',
  'ui: backup row shift'),
 ('        hint.grid(row=4, column=1, columnspan=3, sticky="w", pady=(8, 0))',
  '        hint.grid(row=5, column=1, columnspan=4, sticky="w", pady=(8, 0))',
  'ui: hint row shift'),
 ('                read_check,\n'
  '                write_check,\n'
  '                backup_check,\n'
  '                read_scope_entry,\n'
  '                read_scope_button,\n'
  '                write_scope_entry,\n'
  '                write_scope_button,\n'
  '            ]',
  '                read_check,\n'
  '                write_check,\n'
  '                delete_check,\n'
  '                backup_check,\n'
  '                tool_limit_spin,\n'
  '                read_scope_entry,\n'
  '                read_scope_button,\n'
  '                write_scope_entry,\n'
  '                write_scope_button,\n'
  '                delete_scope_entry,\n'
  '                delete_scope_button,\n'
  '            ]',
  'ui: security widgets'),
 ('                f"R={perms.get(\'allow_read\')}:{perms.get(\'read_scope\')} | "\n'
  '                f"W={perms.get(\'allow_write\')}:{perms.get(\'write_scope\')} | "\n'
  '                f"BACKUP={perms.get(\'auto_backup\')} | {task_preview[:40]}"',
  '                f"R={perms.get(\'allow_read\')}:{perms.get(\'read_scope\')} | "\n'
  '                f"W={perms.get(\'allow_write\')}:{perms.get(\'write_scope\')} | "\n'
  '                f"D={perms.get(\'allow_delete\')}:{perms.get(\'delete_scope\')} | "\n'
  '                f"LIMIT={perms.get(\'tool_limit\')} | "\n'
  '                f"BACKUP={perms.get(\'auto_backup\')} | {task_preview[:40]}"',
  'ui: trace permissions'),
 ('            write_scope = self._normalize_scope_for_ui(\n'
  '                workspace,\n'
  '                self.write_scope_var.get(),\n'
  '                "Область записи",\n'
  '                self.allow_write_var.get(),\n'
  '            )\n'
  '        except ValueError as exc:',
  '            write_scope = self._normalize_scope_for_ui(\n'
  '                workspace,\n'
  '                self.write_scope_var.get(),\n'
  '                "Область записи",\n'
  '                self.allow_write_var.get(),\n'
  '            )\n'
  '            delete_scope = self._normalize_scope_for_ui(\n'
  '                workspace,\n'
  '                self.delete_scope_var.get(),\n'
  '                "Область удаления",\n'
  '                self.allow_delete_var.get(),\n'
  '            )\n'
  '            try:\n'
  '                tool_limit = int(self.tool_limit_var.get().strip())\n'
  '            except ValueError as exc:\n'
  '                raise ValueError("Лимит tools должен быть целым числом.") from exc\n'
  '            if not 1 <= tool_limit <= 200:\n'
  '                raise ValueError("Лимит tools должен быть от 1 до 200.")\n'
  '        except ValueError as exc:',
  'ui: validate delete scope and tool limit'),
 ('        permissions = {\n'
  '            "allow_read": self.allow_read_var.get(),\n'
  '            "allow_write": self.allow_write_var.get(),\n'
  '            "read_scope": read_scope,\n'
  '            "write_scope": write_scope,\n'
  '            "auto_backup": self.auto_backup_var.get(),\n'
  '        }',
  '        permissions = {\n'
  '            "allow_read": self.allow_read_var.get(),\n'
  '            "allow_write": self.allow_write_var.get(),\n'
  '            "allow_delete": self.allow_delete_var.get(),\n'
  '            "read_scope": read_scope,\n'
  '            "write_scope": write_scope,\n'
  '            "delete_scope": delete_scope,\n'
  '            "tool_limit": tool_limit,\n'
  '            "auto_backup": self.auto_backup_var.get(),\n'
  '        }',
  'ui: permissions payload'),
 ('                f"WRITE={\'ON\' if permissions[\'allow_write\'] else \'OFF\'} "\n'
  '                f"[{write_scope}], "\n'
  '                f"BACKUP={\'ON\' if permissions[\'auto_backup\'] else \'OFF\'}."',
  '                f"WRITE={\'ON\' if permissions[\'allow_write\'] else \'OFF\'} "\n'
  '                f"[{write_scope}], "\n'
  '                f"DELETE={\'ON\' if permissions[\'allow_delete\'] else \'OFF\'} "\n'
  '                f"[{delete_scope}], "\n'
  '                f"TOOLS={tool_limit}, "\n'
  '                f"BACKUP={\'ON\' if permissions[\'auto_backup\'] else \'OFF\'}."',
  'ui: chat permissions summary'),
 ('                "Интерфейс готов. По умолчанию чтение разрешено, запись "\n'
  '                "ЗАПРЕЩЕНА, автобэкап включён. Серверные галочки — это "\n'
  '                "реальные ограничения, а не только текст в промпте."',
  '                "Интерфейс готов. По умолчанию чтение разрешено, запись "\n'
  '                "и удаление ЗАПРЕЩЕНЫ, автобэкап включён. Лимит tools = 20. "\n'
  '                "Серверные галочки — это реальные ограничения, а не только "\n'
  '                "текст в промпте."',
  'ui: startup message')]

def apply_replacements(text: str, replacements, filename: str) -> str:
    for old, new, label in replacements:
        count = text.count(old)
        if count != 1:
            raise RuntimeError(
                f"{filename} / {label}: ожидалось 1 совпадение, найдено {count}. "
                "Рабочие файлы не изменены."
            )
        text = text.replace(old, new, 1)
    return text

def main() -> None:
    if not SERVER.is_file() or not UI.is_file():
        raise RuntimeError(
            "Положи apply_safe_v2_fix.py в корень ag_llm рядом с server.py и ultra_ui.py."
        )

    server_original = SERVER.read_text(encoding="utf-8")
    ui_original = UI.read_text(encoding="utf-8")

    server_new = apply_replacements(
        server_original, SERVER_REPLACEMENTS, "server.py"
    )
    ui_new = apply_replacements(
        ui_original, UI_REPLACEMENTS, "ultra_ui.py"
    )

    # До записи проверяем синтаксис обоих новых файлов.
    compile(server_new, "server.py", "exec")
    compile(ui_new, "ultra_ui.py", "exec")

    server_backup = ROOT / "server.py.before_safe_v2"
    ui_backup = ROOT / "ultra_ui.py.before_safe_v2"
    shutil.copy2(SERVER, server_backup)
    shutil.copy2(UI, ui_backup)

    SERVER.write_text(server_new, encoding="utf-8")
    UI.write_text(ui_new, encoding="utf-8")

    print("OK — SAFE v2 применён.")
    print("Добавлено:")
    print("  - DELETE как отдельный физический permission + delete_file")
    print("  - backup удаляемого файла ДО удаления")
    print("  - ручной лимит tool calls 1..200 (default 20)")
    print("  - Ultra видит общий лимит и остаток после каждого tool call")
    print("  - переключатель тёмная/светлая тема (default dark)")
    print()
    print("Созданы локальные откатные копии:")
    print("  server.py.before_safe_v2")
    print("  ultra_ui.py.before_safe_v2")
    print()
    print("Теперь ПОЛНОСТЬЮ перезапусти Ultra UI.")

if __name__ == "__main__":
    main()
