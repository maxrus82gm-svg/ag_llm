# OFFLINE tests — CODEX-WUA-EVM-CONTROLS-MULTIWINDOW-001

Дата 17.11.2026, локальный `.venv`, без реального OAuth/catalog/inference (0/0/0).

| Команда | Итог | Evidence |
|---|---:|---|
| `.venv/Scripts/python.exe -B -m unittest test_web_alarm_model_cards test_web_alarm_ordinary_application test_web_alarm_evm_unified` | PASS 53/53 | `evidence/python_final.txt` |
| `node test_web_alarm_evm_ui.js` | PASS 48/48 | `evidence/evm_js_final.txt` |
| `node test_web_alarm_ultra_chat_ui.js` | PASS 76/76 | `evidence/chat_js_final.txt` |
| `.venv/Scripts/python.exe -B test_rt002_s1_routes.py` | PASS 69/69 | `evidence/s1_final_source.txt` |
| `.venv/Scripts/python.exe -B -m unittest test_web_alarm_ultra_connections` | PASS 15/15 | `evidence/test_web_alarm_ultra_connections.txt` |
| `.venv/Scripts/python.exe -B -m unittest test_web_alarm_ultra_chat_turn_http` | PASS 8/8 | `evidence/test_web_alarm_ultra_chat_turn_http.txt` |
| `.venv/Scripts/python.exe -B -m unittest test_web_alarm_ordinary_test_activation` | PASS 3/3 | `evidence/test_web_alarm_ordinary_test_activation.txt` |
| `.venv/Scripts/python.exe -B -m unittest test_web_alarm_ultra_chat_s5` | PASS 12/13, SKIP 1 | `evidence/test_web_alarm_ultra_chat_s5.txt` |
| `.venv/Scripts/python.exe -B -m unittest test_web_alarm_ultra_chat_s5_recovery` | PASS 3/3 | `evidence/test_web_alarm_ultra_chat_s5_recovery.txt` |
| `.venv/Scripts/python.exe -B test_rt002_s2_budget_policy.py` | FAIL 72/73; один static isolation assertion | `evidence/s2.txt` |
| Общий запуск восьми Python-модулей одним процессом | ABORT Tcl/Tk cleanup, без финального unittest verdict | `evidence/python_full_final.txt` |
| AST parse пяти изменённых Python файлов | PASS | команда и результат в manual review |
| Windows multi-monitor move, physical topmost, F5 external/main | NOT RUN | `window-review.md` |

Негативные случаи: неверный тип `enabled`, stale revision, повреждённое хранилище и поле, ноль доступных моделей, запрет новых Turn при отключении, повтор уже принятого ключа без второй отправки, сохранение RAW/сообщений/модели чата, UNKNOWN и повторный Turn ID, чужое семейство в picker, popup blocked и отсутствие PiP API. JS тестирует вызовы браузерного API на mock, не физическое ОС поведение.

Первый системный `python` вне `.venv` не имел `httpx`; он не считается тестом продукта. После выбора проектного `.venv` адресный прогон прошёл. S1 reconciliation fingerprint обновлён на фактический SHA source после ревью `_settings`; тестовая защита осталась включённой. S2 FAIL сохранён без обхода.
