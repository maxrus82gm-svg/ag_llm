# OFFLINE test evidence

Дата: 17.11.2026. Проектный `.venv` (Python 3.12); сетевые provider вызовы 0. Логи в `evidence/`, точные SHA в `manifest.json`.

| Selector / команда | Результат | Evidence |
|---|---|---|
| `.venv/Scripts/python.exe -X faulthandler -B -m unittest -v test_web_alarm_model_cards test_web_alarm_ultra_connections test_web_alarm_ordinary_application test_web_alarm_evm_unified test_web_alarm_ordinary_test_activation test_web_alarm_ultra_chat_s5 test_web_alarm_ultra_chat_s5_recovery test_web_alarm_ultra_chat_turn_http` | **97 run, 96 PASS, 1 SKIP**, exit 0, Tcl ошибок нет | `python_combined_final.txt` |
| `node test_web_alarm_evm_ui.js` | **50/50 PASS** | `evm_js_final.txt` |
| `node test_web_alarm_ultra_chat_ui.js` | **76/76 PASS** | `chat_js_final.txt` |
| `.venv/Scripts/python.exe -B test_rt002_s1_routes.py` | **69/69 PASS**, 0 guard/evidence problems | `s1_final.txt` |
| `.venv/Scripts/python.exe -B test_rt002_s2_budget_policy.py` | **73/73 PASS**, 0 isolation violations | `s2_final.txt` |
| `.venv/Scripts/python.exe -B -m unittest test_web_alarm_standard_live` | **13/13 PASS** | `standard_offline.txt` |
| `.venv/Scripts/python.exe -B -m unittest test_web_alarm_gigachat_live_control` | **4/4 PASS**, synthetic session | `live_control_offline.txt` |
| Python `compile(...)` семи изменённых модулей | **7/7 PASS** | `python_compile.txt` |
| S2 in-memory direct-import mutation | Baseline 0 issues; mutated 12 issues, rejected | `s2_negative_audit.txt` |

**Исходные красные:** S2 72/73 (`s2_before.txt`); F-02 отказ pre-send и ложный check UI (`f02_python_red.txt`, `f02_js_red.txt`); старый Turn ID не обновлял EVM при пропущенной вторичной записи (`f02_status_red.txt`); исходный общий прогон упал в Tcl/Tk с faulthandler stack (`python_combined_faulthandler.txt`). После минимального Tk test-cleanup промежуточный общий прогон: 96 run, 95 PASS, 1 SKIP (`python_combined_after.txt`); финальный: 97 run, 96 PASS, 1 SKIP после дополнительного теста статуса.

В первоначальном `f02_python_red.txt` один дополнительный FAIL был ошибочным ожиданием от отдельного default checker без Ordinary сессии; это ожидание удалено. Два остальных отказа воспроизводили проверяемые дефекты. Исправленный selector и полный итоговый набор прошли.

**Негативные границы:** нет сессии → 0 POST check; отключённая модель → запрет новой отправки при сохранении чата; отмена подтверждения → 0 POST; двойной клик во время проверки → 1 POST; `PreSendDenied` до Turn → 0 новых чатов; исключение неопределённого исхода → UNKNOWN/серый; старый Turn A после B не меняет evidence; popup block и отсутствие PiP API обрабатываются UI; попытка прямого импорта policy ломает S2 audit. F5 моделируется новым экземпляром/серверным readback, без присвоения зелёного от включения модели.

**NOT RUN:** реальные OAuth/catalog/inference, пользовательские Workspace, физический перенос обычного окна/PiP между мониторами, topmost над Blender, масштабирование экранов, фактический LIVE ответ GigaChat. Сводные OFFLINE PASS не заменяют физический и платный gates.
