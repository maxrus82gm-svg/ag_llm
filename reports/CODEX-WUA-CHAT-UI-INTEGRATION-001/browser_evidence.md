# Browser smoke — Codex author observation

Fixture: `workspace_probe.py --browser`, actual shipped page and server, loopback and disposable TEMP only. An existing Workspace and RAW were seeded via shared Python core; this browser run pre-registered the Workspace. The separate HTTP probe verified the existing registration endpoint.

1. In-app browser opened the served Ultra Chat. Accessibility tree displayed Synthetic browser Workspace, Старый синтетический диалог, literal `<b>Синтетическая история</b>`, and disabled Отправить.
2. Clicked Подключить папку Workspace: existing operator form was visible. Returned to Ultra Chat without submitting the form.
3. Created Браузерный тест using the browser form, then renamed it to Переименовано в браузере. The heading showed the new name; sendEnabled=false.
4. Reloaded the page. The renamed heading reappeared. Selected the old dialogue: history contained the literal RAW and the history subtree contained zero b elements.
5. Closed the browser tab and stopped the fixture; common-core list returned both titles, including the browser rename.

Browser reload is distinct from server restart. Restart was covered by the separate real HTTP fixture using the same disposable registry and storage across server instances. Native Windows folder picker, Tkinter GUI, viewport resizing, and real user data: NOT RUN.
