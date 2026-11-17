# Независимая инженерная сверка H42 — EVM OWNER SMOKE REPAIR

**Дата:** 17.11.2026. **TASK ID:** `CODEX-WUA-EVM-OWNER-SMOKE-REPAIR-001`. **HISTORY ID:** `H-CODEX-000042`. **Original source:** `main@a216c45f19d855f7049c30aee5df93b045e0a0ac` (№642). **Published combined history:** `main@238f69ab5456259e4b802fa9f82909327cc4da15` (user merge GPT + H42). **Author outcome:** `PARTIAL / SUBMITTED / REVIEW PENDING`.

**Independent verdict:** `PARTIAL / INDEPENDENT SOURCE REVIEW ONLY`. Я прочитал отчёт, исходный commit diff, отдельные участки исходников, author test evidence и `root-cause.md`. Я **не запускал** независимый GitHub-hosted Windows CI, локальный Tk/Chrome, настоящий OAuth/catalog/inference, paid check или физический multi-monitor; поэтому `FULL TECHNICAL PASS / REAL APPLICATION PASS / USER UX PASS / RELEASE PASS` **НЕ ЗАЯВЛЯЮ**. Сам факт кода, совместимый с отчётом, является подтверждённым source evidence, а результаты тестов остаются авторскими до независимого прогона.

## Фактический исход по дефектам

| Пункт | Проверка исходников | Итог |
| --- | --- | --- |
| **F-01** | В `web_alarm/ui.py` добавлены подсказки переноса browser popup за системный заголовок и `Win+Shift+←/→`. Механизмы DOM-pin/popup/PiP не объединены. | **PARTIAL.** Перенос popup на второй монитор, topmost над Blender, несколько PiP, resize/focus/F5 физически NOT RUN. Пользовательский образец единой карточки остаётся отдельным UX-решением. |
| **F-02** | `ui.py` предлагает подключение GigaChat внутри EVM и отдельно спрашивает согласие на возможно тарифицируемый test Turn; `ordinary_provider.py` устраняет текст про Ultra Chat и переводит pre-send `PreSendDenied` в отказ до создания проверочного Turn. `ModelCards.run_check` различает UNKNOWN и FAILED, повтор Turn ID дедуплицирован. | **SOURCE IMPLEMENTED, AUTHOR OFFLINE TESTED.** Реального ответа GigaChat и подтверждения зелёного статуса не было. В обычном STANDARD chat Send причина предыдущей блокировки и исправление не доказаны. |
| **F-03** | В карточке раздельно формируются `Модель`, `Провайдер`, `Работоспособность` на серверных состояниях. | **SOURCE IMPLEMENTED**, реальный F5 owner GUI NOT RUN. |
| **F-04** | `rt002_multimodel_reconciliation.json` меняет только fingerprint `web_alarm.ordinary_provider` для ранее рассмотренного fixture gate. S2 negative audit не удалён. | **AUTHOR S2 73/73 PASS**, negative mutation 12 violations по author evidence; независимый Windows CI NOT RUN. Исторический H41 S2 72/73 FAIL сохраняется. |
| **F-05** | `test_web_alarm_ultra_chat_s5.py`: cleanup `app.destroy` затем `gc.collect` на test/main thread (LIFO); product Tk runtime не менялся. | **AUTHOR combined Python 97 run: 96 PASS, 1 SKIP**, Tcl crash не повторился у автора; independent rerun NOT RUN. Исторический Tcl abort сохраняется. |

**Остальные авторские результаты:** EVM JS 50/50, Ultra Chat JS 76/76, S1 69/69, STANDARD offline 13/13. Реальные обращения: OAuth 0, catalog 0, inference 0. Точное evidence `reports/CODEX-WUA-EVM-OWNER-SMOKE-REPAIR-001/tests.md`, `evidence/s2_final.txt`, `evidence/python_combined_final.txt`. GitHub Actions на опубликованном H42 SHA — ноль зарегистрированных runs/checks на момент source review; независимые проверки не выполнены.

## Отдельная гипотеза риска, не утверждать DEFECT без теста

В H42 добавлен `ModelCards.record_unknown(connection_id, settings_version, ...)`, который без `turn_id` записывает UNKNOWN напрямую без явной сверки перед записью `settings_version == current_card.settings_version`; в `record_chat_*` такая сверка есть. Тестировать сценарий: долгий diagnostic A → смена настроек профиля B → подтверждённый новый ответ B → поздний UNKNOWN A. Принцип: неизменяемость доказательств версии и недопустимость ложного зелёного/серого. Это гипотеза, а не подтверждённая гонка. FOLLOWUP `FOLLOWUP-WUA-H42-UNKNOWN-VERSION-RACE-001` OPEN.

## Обязательные OPEN и следующий gate

1. **STANDARD P0:** обычный рабочий диалог с включённой реальной LLM. H42 добавил EVM маршрут для CHECK, но **не доказал** реальную отправку обычного чата; 24-часовой session grant не пересмотрен. Пользователь запретил новые самовольные trial ограничения, но фактические ключи/OAuth, провайдерские ограничения, бюджет/ledger, безопасность и идемпотентность сохраняются.
2. **EVM paid diagnostic:** настоящий проверочный Turn, RAW, usage/ledger, API color/F5 и no auto-retry — только отдельный USER GO и фиксируемый безопасный scope.
3. **Windows independent:** guarded Python+S1+S2/negative, JS, Tk cleanup на точном H42 SHA; сохранить run id/logs/artifacts. Результат авторского теста — не independent PASS.
4. **Окна:** пользовательский физический multi-monitor/PiP/topmost над Blender и дальнейшая архитектура одной удобной карточки; не создавать нативный manager без согласования. Причина проблемы Snipping Tool двух мониторов не доказана связанной с Web Alarm.
5. **History:** `task_slot_rotate.py finish` сообщил H42, БЛОК 1 WAITING/1.1 H42. Глобальный `task_history.py validate` по авторскому протоколу ещё сообщает H36 review-source drift; адресная H42 сохранность авторски PASS, independent global validation NOT RUN.

**Documentation result:** task_record H42, №05 (52 зарегистрированные H-записи + прямые документальные записи, открытые FOLLOWUP), №001 (последние десять), №06, №34, №40 и №37 подготовлены согласованно. Технические H41/H42 статусы и прежние ошибки не затирались. Ни новой Codex TASK, ни LIVE вызовов, ни изменений runtime этим review не производилось. Весь документальный closeout — только после одного атомарного коммита в GPT, пользовательский merge в main отдельно.
