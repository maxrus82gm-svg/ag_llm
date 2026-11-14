# H35 — AUTHOR RESULT READY / PARTIAL

**TASK ID:** `CODEX-WUA-CHAT-GIGACHAT-ONE-MODEL-REAL-PREFLIGHT-001`  
**Дата:** 2026-11-14. **Автор:** Codex 007. STRICT OFFLINE разработка и испытания.  
**HISTORY ID:** назначается исключительно штатным finish; окончательная запись — [task_record.json](task_record.json), квитанция — closeout.json.  
**Итог:** исправлен маршрут STANDARD → Ordinary Core; первый настоящий ответ GigaChat ещё технически не готов. REAL authority и реальный клиент остаются заблокированы. Никакого REAL PASS по synthetic ответам не заявляется.

| Критерий | Фактический статус |
|---|---|
| Общая задача H35 | **PARTIAL** — законченная OFFLINE-интеграция, точный REAL blocker |
| TECHNICAL | **NOT READY** для первого настоящего диалога |
| PROVIDER CONTRACT | **PARTIAL** |
| REAL FACTORY | **BLOCKED**, authority не выдаётся |
| REAL APPLICATION OFFLINE | **PASS** — настоящий application entrypoint, synthetic HTTP; это не LIVE |
| USER UX | **PENDING** |
| LIVE / OAuth / API / paid | **NOT RUN** |
| Независимая Windows-проверка H35 | **PENDING**, авторский результат её не заменяет |
| RELEASE | **HOLD** |

## Что изменено

Найденный разрыв STANDARD был реальным: браузер строил `local-test:v1 / empty:v1 / test-only:v1`, а Ordinary bridge работал только в disposable TEST-сервисе. Теперь обычный `web_alarm.server.create_server` создаёт тонкий `OrdinaryApplicationChatService`. Он переиспользует OrdinaryCoreChatService, OrdinaryCoreAdapter, TurnService, Model Registry, Run Store, RAW, S2/S3a и H33 HTTP boundary. Никакого нового Chat core, OAuth cache, ledger, сериализатора, каталога моделей или общего бюджета Workspace нет.

Добавлены два исходных файла:

- `web_alarm/ordinary_provider.py`: один кандидат из Model Registry, серверный preflight/factory с неизменным REAL denial, нормальный application adapter, per-chat model metadata и явное отключение TEST-аллокатора Workspace в STANDARD.
- `test_web_alarm_ordinary_application.py`: 9 проверок actual normal application, включая HTTP, terminal, хранение, отмену, UNKNOWN и восстановление.

Изменены шесть существующих файлов:

- `web_alarm/server.py`: штатная точка сборки сервиса; отдельный exact-type TEMP fixture factory только как внутренний OFFLINE test seam. CLI/env/браузерного переключателя REAL нет.
- `web_alarm/ui.py`: серверный Ordinary mode, выбранный model_ref вместо TEST references, per-chat сохранение/восстановление модели, настройки/usage, HOLD и отдельные per-chat browser keys. Глобальный EVM choice больше не подставляется в Ordinary-запрос. Компоновка/размеры/порядок кнопок не менялись.
- `test_web_alarm_ultra_chat_ui.js`: четыре новых STANDARD-сценария, всего 61.
- `test_web_alarm_ultra_chat_s5.py`, `test_web_alarm_ultra_chat_turn_http.py`: адресно обновлены ожидания нового STANDARD contract; read capability всё ещё не разрешает cancel.
- `test_rt002_s2_budget_policy.py`: добавлен только точный AST-pin нового reviewed OFFLINE adapter. Его узел и ledger edge сохранены в графе; все предыдущие pins/capsules и policy не менялись.

DEFAULT STANDARD показывает одну модель `GigaChat 2 Pro` и явный HOLD; отправка закрыта **до принятия Turn/RAW и до token/cache/env/OAuth/HTTP**. История читается прежним bounded reader. Настройки сохраняются в существующих метаданных чата, но не выдаются за параметры провайдера. Для неавторизованного production usage возвращается unavailable/UNKNOWN, без придуманного нуля. Реальная production Turn/recovery/usage-авторизация не реализована и не подменена временным fixture.

Оба штатных TEST-профиля, `Start_WebAlarm_Test.cmd`, `Start_WebAlarm_Standard.cmd`, `Start_WebAlarm.bat`, конфигурации launcher, H31 guard и Stage5 rollback сохранены. STANDARD operator routes доступны. Tkinter исходники не менялись.

## Сквозное доказательство через приложение

Тест вызывает настоящий `create_server` с обычной страницей и нормальными HTTP routes, без `offline_chat` и без DOM Stage5. Exact factory привязан к своему registry и TEMP root; реальные данные не используются. Создание чата также идёт через нормальный HTTP create route, включая принятый first-chat enrollment.

Цепочка: per-chat model → POST только `{idempotency_key, model_ref, text}` → существующий context/prepared snapshot → final serializer bytes → S2/S3a reserve/SENT/readback → H33 MockTransport POST → terminal/readback → Turn/RAW/history/usage. Независимый observation непосредственно в HTTP boundary сверяет actual request.content с сохранёнными ledger wire bytes и SENT. Один physical **synthetic** POST, provider ID `GigaChat-2-Pro`, два RAW сообщения, usage 12. После нового экземпляра сервера прежний key возвращает тот же результат без token/HTTP resend. См. [physical trace](evidence/core_reviewed.http_trace.json).

Отдельно проверены неверная модель/лишние поля и forged factory, чужой scope, два Workspace, настройки без применения к провайдеру, token-boundary failure, HTTP 401/403/429/500/invalid JSON, cancel во время HTTP, timeout/UNKNOWN, terminal storage failure. После SENT/UNKNOWN повтор не отправляет запрос и не снимает неизвестную liability. Сбой terminal не публикует assistant RAW. Полный перенос REAL provenance и non-TEMP recovery остаётся successor, а не заявленным результатом этих tests.

## Provider contract и настоящий blocker

По отдельному разрешению владельца прочитаны **только четыре** публичные страницы БЛОКА 1; дополнительные ссылки/schema не открывались. OAuth/API/models probing/credentials не использовались. Датированные первичные ссылки и границы сведений — [provider_contract.md](provider_contract.md).

Подтверждены публичный ID `GigaChat-2-Pro`, текстовый v1 endpoint `https://api.giga.chat/v1/chat/completions`, OAuth endpoint и варианты scope. Это не подтверждает доступность в аккаунте. **ACCOUNT / SCOPE / MODEL AVAILABILITY UNVERIFIED**. В доступном тексте четырёх страниц не раскрыты достоверные context/output bounds и полная usage/cache/reasoning schema. Цены, chat rate, approved first-attempt liability/cost и TLS trust/proxy contract также не верифицированы. UI 250000/10000/20000 и H34 synthetic profiles не использованы как provider caps.

Factory выполняет preflight и сохраняет H34 unconditional `require_real_authority()` до доступа к token cache/env. Настройка модели, JSON real/scope/endpoint/authority, cached token и произвольный client не дают REAL. Exact fixture допускается только в isolated TEMP application tests. Единственный доступный byte transport по-прежнему требует exact OfflineHTTPFixture и ephemeral Turn/server admission. Легаси семь LLM-send остаются под H34 gate.

**Не реализовано/не допущено:** выдача production server REAL authority, построение реального HTTP/OAuth клиента с проверенными scope/cache/TLS/proxy/redaction, production enrollment и подтверждённый provider profile. В частности, холодный прежний OAuth cache не превращён в готовый release mechanism. Нельзя открыть его, просто сняв denial: его admission/trust/cache isolation требует отдельной OFFLINE-проверки. Это сознательно незакрытая P1, а не скрытый enable-флаг или объявление полного S3b.

Минимальный successor — [next.md](next.md): authoritative contract/account evidence, применимые predecessor gates, затем закрытый server REAL constructor на той же H33 границе и единственном OAuth/cache, production recovery; после независимой проверки — отдельное OWNER GO. H35 сейчас не запрашивает LIVE GO.

## Проверки, первые FAIL и evidence

Все Python engineering tests запускались с ранним guard до production imports: external sockets/DNS, чтение credentials, Git/non-Python process и live/project writes блокируются; допустимы только явно изолированные TEMP и локальный HTTP/self-pipe. Pytest plugins отключены. Самостоятельные S1/S2 используют собственные acceptance runners. Node исполняет поставляемый JS в детерминированном DOM без сети. Это авторская Windows OFFLINE-проверка.

| Набор | Результат |
|---|---|
| Actual application, initial и first-chat HTTP rerun | 7 PASS + 10 subtests каждый |
| Final Ordinary/Core/H29–H34/S3a/Turn/RAW/launcher regression | 263 PASS + 266 subtests, 9 exact expected negative guard probes, unexpected 0 |
| Legacy seven-site/runtime regression | 244 PASS + 110 subtests, guard 0 |
| Standalone S1, с имеющимся локальным historical RAW | 69 PASS, isolation violations 0 |
| Standalone S2 после reviewed AST pin | 73 PASS, isolation violations 0 |
| Import graph / isolation quality | 52 PASS + 7 subtests, guard 0 |
| Shipped UI | 61 PASS, 0 fail |
| Negative mutations | 4 ожидаемых RED, source files unchanged, guard 0 |
| Адресный HTTP contract follow-up | 8 PASS + 11 subtests |
| Terminal storage / cancel application follow-ups | 1 PASS каждый, guard 0 |
| Штатные python_compile / Tk constructor smoke | PASS / PASS, guard 0 |

Counts разных строк частично пересекаются и не суммируются. Точные команды, cases/counts, stdout/stderr и guard observations находятся в `evidence/*.result.json` и соседних файлах. Повторение первых FAIL сохранено, успешный итог их не стирает.

Первый `adjacent_first`: 94 PASS, 2 FAIL, 108 subtests. Один FAIL — старый STANDARD 400 expectation против нового правильного 403 HOLD; второй — ошибочно включённый физический CMD test, остановленный guard до создания процесса (`non_python_process`, один unexpected denial). Это не разрешённый negative control и не PASS. Физический CMD не запускался, guard не ослаблялся; финальный набор использует адресные принятые activation tests.

Первый S2: 72/73, новый путь до policy через application adapter. После ручного review полного AST добавлен один exact reviewed gate, а не исключён весь Web graph. Quality проверяет мутации всех пяти gates, посторонние direct/transitive consumers и новый ledger edge.

Первый quality collection: одинаковые имена `isolation_checks.py` конфликтовали в pytest; исправлен только режим запуска `--import-mode=importlib`, затем 52+7 PASS. `core_final`: 261 PASS + 266 subtests, один FAIL на втором старом TEST-body expectation. Исходник отдельно скопирован с SHA **перед** обновлением expectation; новая проверка явно различает 400 obsolete shape и 403 valid Ordinary HOLD. Финальный широкий повтор вынесен в `core_reviewed`.

Negative mutations выполнялись в памяти: ослабление budget, exact HTTP wire check, terminal confirmation и STANDARD HOLD дают RED на реальных oracle tests. Источники на диске не модифицировались. Полные S3b/S3c/S9/S13a и privacy/durability acceptance этим не закрываются.

## Source, backup, регламенты и ограничения

Изучены применимые №08/34/40/37 §3а/20 §5а/36/36.1/36.3, H32/H33/H34 и независимый [H34 bounded review](../CHATGPT-WEB29-H34-REVIEW-20261114/review.md). Исходные 16/16 H34 fingerprints совпали (exact либо LF/CRLF), см. [base_fingerprints](evidence/base_fingerprints.json). Удалённый main **NOT VERIFIED**: синхронизацию владелец взял на себя, затем явно разрешил продолжать; fetch/pull/status/.git не использовались. Это не утверждение о синхронности remote HEAD.

До правок создана `C:\Users\REX\AppData\Local\Temp\codex-h35-backup-4b3ekej1`; всего 16 исходных файлов проверены SHA-256, в том числе дополнительные два test-файла перед их исправлением. Манифест копии — [preservation.json](preservation.json). Копия оставлена до независимой приёмки; H30/H31/H32/H33/H34 backup не затронуты. Проверка 163 защищённых файлов — [source_review.json](evidence/source_review.json). Финальные hashes и пакет — manifest.json.

NOT RUN: реальные OAuth/API/GigaChat/платные запросы, account/model probe, внешняя сеть кроме четырёх публичных страниц, физические CMD/browser/F5, independent GitHub Actions, Git/GitHub/коммиты/публикация, production writes, release. Cold TLS/proxy/real-client behavior не объявлен проверенным. Локальные S1 69 не подменяют отсутствующий независимый RAW CI gate.

## Сдача, DOC IMPACT и проверка владельцем

[MANUAL ENGINEERING REVIEW](manual_review.md) и [GUI handoff](gui_handoff.md) фиксируют ограничения, 5 действий STANDARD/TEST и будущий одно-attempt LIVE smoke с остановкой/rollback. USER UX ACCEPTED не присвоен. В STANDARD физический тест должен начать с чтения; запись пользовательских данных автором не производилась.

Координатору: внести фактический bounded H35 результат/REAL factory blocker в №34/40 и review block после независимой проверки. Общие утверждённые документы, чужие карточки, БЛОКИ 2–4, CI и Git не редактировались. Операции собственной карточки/истории — только штатный finish, exact chat authorization сохранён в snapshot. History readback и hashes после finish — closeout.json / manifest.json. Report после регистрации immutable.

**NEXT:** независимо принять сделанную STANDARD-интеграцию; получить недостающий provider/account/trust contract и решения §5а; реализовать и OFFLINE-проверить недостающий production REAL constructor/recovery на существующем ядре. До этого LIVE и RELEASE остаются HOLD.
