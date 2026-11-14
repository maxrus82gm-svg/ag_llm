# H35 — независимая приёмка STANDARD Ordinary Chat (BOUNDED OFFLINE)

**Дата:** 2026-11-14. **Review owner:** ChatGPT / WEB29.  
**TASK:** `CODEX-WUA-CHAT-GIGACHAT-ONE-MODEL-REAL-PREFLIGHT-001`, **HISTORY:** `H-CODEX-000035`.  
**VERDICT:** **PASS / BOUNDED INDEPENDENT WINDOWS OFFLINE for STANDARD→Ordinary integration**; исходная авторская сдача **PARTIAL**, полный настоящий GigaChat **TECHNICAL NOT READY**, **REAL FACTORY BLOCKED**, **LIVE/RELEASE HOLD**, **USER GUI/UX PENDING**. Это доказательство внутреннего offline application, не полного S3b/S3c/S9/S13a и не REAL.

## Исходники, назначение, архитектура

Источник принят для анализа из опубликованного `main@cd0e4d943bb8d341baf07eef2a1d5c2a1619035a` (№604), один коммит после H34. Защитные S2/S3a, H33/H34 `gigachat_admission.py`, `ordinary_gigachat_transport.py`, `ordinary_chat_service.py` неизменны. Изменены `web_alarm/server.py`, `web_alarm/ui.py`, `test_rt002_s2_budget_policy.py`, смежные тесты, добавлены `web_alarm/ordinary_provider.py` и `test_web_alarm_ordinary_application.py`. Работа пользователя со STANDARD идёт через `create_server` и `OrdinaryApplicationChatService`, перчатовый registry/model metadata, прежние Turn/RAW/usage. TEST профили и launcher names не переписаны. Две коммитированные `.obsidian` конфигурации в №604 — отдельное локальное представление, не подтверждение UX.

Проверен строго закрытый путь: `OrdinaryProviderFactory.require_real()` обращается к H34 `require_real_authority()`, который **безусловно DENY** до token/cache/OAuth/network; даже подмена внешнего model/capability JSON не выдаёт разрешение. Единственный исполняемый транспорт по-прежнему `OfflineHTTPFixture` в TEMP и с exact registry/root checks. Нормальный STANDARD отправку блокирует (до Turn/RAW и сетевого запроса), показывает `GigaChat 2 Pro` из общего реестра, сохраняет model preference и читает историю. `context/output`, account scope, model availability, usage schema, TLS/proxy/cost/caps не подтверждены и не выдаются за READY; синтетические caps и настройки UI 250000/10000/20000 не принимаются за provider policy.

## Собственный GitHub Windows CI и контроль достоверности

Финальный [run 43598906253](https://github.com/maxrus82gm-svg/ag_llm/actions/runs/43598906253) — **SUCCESS, 3/3 jobs** на `GPT@1c2930e0aedcebbcae01dd6455e8a6a532cf1d6e` (№607), `windows-latest`, Python 3.12, Node 22, guarded TEMP, no real GigaChat/OAuth/paid/credentials. Сверено **18/18 SHA-256** исходных файлов H35 manifest с разрешённой LF/CRLF нормализацией. Отдельные artifacts/точные job ID в `independent_runs.json`. Исходники продукта не менялись ни в одном CI-only №605–607.

| Набор | Независимый результат |
| --- | --- |
| STANDARD normal application entrypoint, model, HOLD, 1 synthetic HTTP, Turn/RAW/history/usage, reopen/no resend, workspace isolation, token/HTTP/terminal errors | **9 PASS + 10 subtests**, guard unexpected0 |
| H29–H35 / Core/Turn/RAW/S3a/launcher | **263 PASS + 266 subtests**, 9 expected guard controls, unexpected0 |
| Legacy 7 physical send boundaries | **244 PASS + 110 subtests**, unexpected guard0 |
| S2 dedicated original runner | **73 PASS**, fail/error/skip0 |
| S2/H35 isolation negative quality | **52 PASS + 7 subtests** |
| Node shipped UI | **61 PASS** |
| Mutants: budget, exact wire, terminal readback, STANDARD hold | **4 expected RED**, 0 unexpected errors |
| Server compile / isolated Tk constructor smoke | **PASS** |
| Historical S1 pinned RAW on GitHub | **NOT RUN**; author local S1 69 separate |

Результаты разных строк частично пересекаются и не суммируются. Первый диагностический [run 43598557934](https://github.com/maxrus82gm-svg/ag_llm/actions/runs/43598557934) сохранил наш source pin RED 17/18 из-за отсутствия `reports/task_history_sequences.json` в sparse checkout; сравнение опубликованного файла показало подлинное совпадение SHA. В [run 43598736087](https://github.com/maxrus82gm-svg/ag_llm/actions/runs/43598736087) pin **18/18 PASS**, application **9+10 PASS**, но CI-ожидание ещё было устаревшим `7`, отчего job стал RED. №606 добавил только необходимый файл checkout, №607 поправил только count в CI. Оба RED сохранены; №607 повторён полностью и SUCCESS.

Независимо замечен **посторонний долг CI**: общий `Web Alarm smoke` run [43598557901](https://github.com/maxrus82gm-svg/ag_llm/actions/runs/43598557901) упал на Windows checkout с `Filename too long` внутри старого вложенного `reports/.../mirror/...`; тесты того workflow **NOT RUN**. Это не runtime regression H35 и не доказательство его FAIL, но глобальный smoke gate остаётся непроверенным до отдельной коррекции checkout.

## Честные приёмочные статусы и следующая работа

- **TECHNICAL BOUNDED OFFLINE:** PASS; **H35 overall:** PARTIAL, REAL TECHNICAL NOT READY.
- **Windows CI independent:** PASS, все 3 jobs №607; user runtime physical GUI: **NOT RUN / OWNER PENDING**.
- **Provider contract:** PARTIAL, account/model/scope/caps/rate/cost/usage/reasoning/TLS unverified.
- **REAL factory/OAuth/API/paid:** BLOCKED / NOT RUN, no OWNER GO.
- **Full S3b/S3c/S9/S13a, production audit enrollment, capacity/fencing/RAW privacy:** OPEN.
- **S1 historical exact pinned RAW:** independent NOT RUN; author S1 69 PASS отдельно.
- **Release/Stage7/LIVE:** HOLD.

**OWNER GUI NEXT:** после сверки локальной source №604 открыть штатный `Start_WebAlarm_Standard.cmd`, оценить NORMAL Web Chat, `GigaChat 2 Pro`, явный HOLD и недоступную отправку, существующую историю, выбор/настройки по чатам, переключение и F5 без подмены чужих данных. Не менять реальные пользовательские чаты ради теста. В `Start_WebAlarm_Test.cmd` разрешён только изолированный TEST Workspace с одним коротким синтетическим запросом, usage/F5/reopen. Владелец оценивает компоновку, понятность и ненужные элементы; обратная связь `USER UX ACCEPTED / ISSUE / CHANGE REQUEST`. **Этот review не присваивает UX PASS**.

**NEXT engineering:** отдельное согласование verified GigaChat account/scope/model/caps/price/usage/TLS, пересмотр §5а predecessor gates и trusted server REAL factory на существующих H33/H34/S2/S3a, после этого независимый Windows и отдельный owner GO на единственный bounded LIVE. Никакого второго ядра, транспорта, OAuth cache, ledger; secrets не передавать в чат. По итогам personal GUI могут появиться пользовательские UX followups.

Эта запись — независимая техническая приёмка, не авторский self-PASS; публикация GPT→main остаётся действием владельца.
