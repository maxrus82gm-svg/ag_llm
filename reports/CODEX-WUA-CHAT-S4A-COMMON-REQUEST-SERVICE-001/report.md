# CODEX-WUA-CHAT-S4A-COMMON-REQUEST-SERVICE-001

**STATUS: READY FOR INDEPENDENT VERIFICATION — bounded OFFLINE S4A.**

Автор: Codex 007. Координатор/independent verifier: ChatGPT. Пользователь публикует одним коммитом. Это авторская сдача, не VERIFIED и не завершение всего этапа 4. Штатный finish и HISTORY ID фиксируются отдельно в `evidence/finish.result.json`, `evidence/finish.stdout.txt`, `finish_receipt.json` и native `task_record.json`; report после регистрации не переписывается.

## Результат и scope

Созданы `ordinary_chat_service.py` и `test_ordinary_chat_service.py`. Сервис формирует неизменяемый запрос из явно разрешённого снимка контекста, фиксирует модель из model_registry, вызывает обязательный fake async transport один раз и разбирает ответ/usage в структурированный результат. Нет sender по умолчанию, хранения, агентского workflow, Turn state machine, HTTP route, Tk/UI, retry, OAuth или budget implementation.

WRITE соблюдён: два новых файла, этот пакет; карточку и штатные history metadata меняет только native finish. Существующие production исходники не редактировались. Git/GitHub/реальные LLM/Colibri/Ollama/MCP не использованы. Заявленный в постановке published SHA `66775c257db0a415104ea20db6c72bb4c1cb33fd` не проверялся удалённо; доказательства привязаны к локальным SHA-256.

До реализации прочитаны назначение в БЛОКЕ 1, ограничения shared scope №40, №37 stage 4 и профиль №36.3; применён действующий адресный порядок №18/карточки. H14/H15 закрыты как диагностические пакеты, их кампании не повторялись. Прямой GO пользователя и БЛОК 1 разрешают только автономный S4A; старые HOLD для реальной интеграции этим не снимаются.

## Проверенные действующие интерфейсы

model_registry.get_model_spec возвращает frozen ModelSpec из единственного MappingProxy registry; неизвестный/disabled ID уже отвергается. Подтверждены шесть существующих enabled GigaChat моделей, в том числе gigachat_2_pro → GigaChat-2-Pro и gigachat_ultra → GigaChat-3-Ultra. Дублирующего списка в сервисе нет. Изменение выбора в оболочке влияет на следующий prepare, а не на подготовленный запрос; отзыв/изменение самого registry spec запрещает send без подмены.

gigachat_transport содержит OAuth helper и чистый extract_usage, но не общий sender обычного чата. Новый сервис переиспользует parser; OAuth helper не вызывается. Фактический wire формат model/messages/stream/max_tokens проверен в существующем server.py, который не импортируется новым сервисом. canonical_json_text переиспользован из provider_accounting; attempt/usage ledgers сервис не создаёт. Зафиксирован отсутствующий пока chat_context.py. Подробный контракт и условия Tk/HTTP/Turn подключения — `interface.md`.

## Тесты и сохранённые отклонения

Среда: Windows 10 build 19045, Python 3.12.10 x64, pytest 9.1.1. Exact commands/version/duration/exit сохранены в каждом `evidence/*.result.json`; полные stdout/stderr лежат рядом. Все данные синтетические, временные storage fixtures у существующих regression tests. Изолированный unittest runner не запускает discovery всего репозитория, Final Audit или Git.

| Запуск | Результат | Смысл |
|---|---|---|
| initial_red | 1 loader ERROR, exit 1 | ModuleNotFoundError до появления нового модуля; исходные три contract tests сохранены |
| unit_first | 23 PASS / 14 ERROR, exit 1 | Guard запретил stdlib Windows socketpair, которую asyncio использует для wake-up pipe |
| unit_after_guard | 37 PASS, exit 0 | Адресная поправка task-local guard, production не менялся |
| model_regression | 38 PASS, exit 0 | Все model cards + connection CatalogTests/SelectionTests |
| accounting_regression | 9 PASS, exit 0 | provider_accounting + usage_accounting, verifier sender замещён штатным mock теста |
| stage3_regression | 24 PASS / 6 ERROR, exit 1 | Guard ошибочно счёл Windows Popen executable=None не-Python процессом |
| stage3_after_guard | 30 PASS, exit 0 | Полные Turn service/HTTP/prerequisite suites с Python-child guard |
| review_usage_red | 1 FAIL, exit 1 | Независимый negative oracle: отклонённый answer терял валидный supplied usage |
| unit_final | 39 PASS, exit 0 | Исправлено сохранение known usage при malformed answer, добавлен storage no-open oracle |
| compile_final | 2 файла compile PASS, exit 0 | Compile в памяти без pyc; AST imports проверены |

**Итог выбранных финальных suites: 116 PASS, 0 FAIL, 0 ERROR, 0 SKIP** (39 + 38 + 9 + 30; compile отдельно). Предыдущие ERROR/FAIL остаются частью истории; повторный PASS не подменяет их. Сводка точных case IDs/guards — `evidence/test_summary.json`. Новое ядро не импортируется прежними suites; после локальной usage-поправки повторён весь новый suite, существующие regression modules остаются byte-identical. Полный Ultra regression, CI, браузер, real API и physical restart текущего live приложения **NOT RUN**: это автономный OFFLINE scope без UI подключения.

Критические oracle: конкретный wire payload с буквальным provider ID; точные UTF-8 границы JSON/messages; unknown/disabled/foreign-provider model без fallback; повреждённые роли/порядок/Unicode и лишние поля; immutable исходный context/payload/model; отзыв модели → 0 fake calls; response choices/assistant/tools/finish/model/metadata corruption; missing/partial/invalid usage не становится нулём; отмена до вызова → 0 fake calls; exception/timeout/Task.cancel после входа → неопределённость, 1 вызов без retry; swallowed timeout не публикует поздний answer; error/metadata не возвращают secret sentinel. Валидный usage у отклонённого ответа сохраняется независимо от answer success.

## Изоляция и сохранность

Ранний `guard/sitecustomize.py` ставится до runtime imports; external sockets/DNS, credential reads, Git metadata и любые процессы, кроме точного sys.executable, запрещены. Child environment runner теперь формируется без чтения значений GIGACHAT credentials/scope/token. Режим новых unit tests запрещает также обычный loopback; единственное узкое исключение — синхронный stdlib socketpair для Windows asyncio. Existing Stage3/model HTTP regression допускает только loopback старых fixture servers. Нового HTTP кода нет.

Negative controls новых unit tests дают ровно три ожидаемых ранних отказа (direct socket.connect, DNS, credential value); OAuth и HTTPX дополнительно vetoed до fresh import/execute и их veto проверены отдельными probes. Эти deliberate probes не являются реальными отправками. В остальных успешных regression logs guard denials отсутствуют. Доказательств внешних provider/OAuth отправок нет, успешных внешних вызовов — **0**. Guard — тестовая изоляция, не production sandbox для произвольного внедрённого Python adapter.

В `evidence/baseline.json` до реализации зафиксированы SHA-256 11 read-only source/card файлов и 605 protected файлов: 595 live user data + 10 editor config. Снимки исходников сохранены в before/, пользовательская история туда не копировалась. `evidence/before-finish.json`: все 595 пользовательских файлов совпадают по имени/размеру/SHA, additions/deletions нет; read-only sources и card до finish совпадают. `.obsidian/workspace.json` изменился внешней активностью и сохранён без вмешательства, поэтому byte-identity всех editor files не заявляется. До/после native finish проверяется отдельно. Start_WebAlarm.bat и launch_config неизменны, active=standard, переключений не было. Другие незакоммиченные изменения не сбрасывались; Git для их перечисления не применялся. Для публикации — только allowlist в manifest, editor/live data исключены.

## Инженерное ревью и ограничения

Просмотрены новый код, source snapshots и запрещённые границы: только registry lookup, pure usage/canonical JSON helpers, asyncio и stdlib. Вызовов storage, agent, HTTP/OAuth, импорта server/Tk/Turn нет. PreparedRequest связан с frozen inputs детерминированным hash, execution повторно проверяет binding и registry; подмена/ref forgery/refused model не вызывает transport. Результаты — локальные значения одной попытки, не новая машина состояний. SHA reference не даёт идемпотентности и повтор execute не дедуплицируется.

Manual adversarial review выявил и проверил отдельным RED потерю known usage при invalid answer; исправлен именно новый модуль. Остальные рассмотренные границы описаны явно: context authorization принадлежит caller; message profile только text pairs; input Python objects/adapter должны быть доверенными; response ограничивается уже после decode; cooperative timeout не может физически остановить некооперативный adapter. Типизированный transport_error после входа несёт may_have_executed и должен консервативно маппиться будущим интегратором в UNKNOWN, а не безопасный retry. Missing finish_reason допускается совместимо с текущим parser, metadata=None не доказывает полный ответ. Результат не обещает exactly-once, zero cost или внешнее non-execution после send.

## OPEN / NEXT / документационное влияние — до сдачи

1. Исторический WorkspaceBusyError Stage3 остаётся **UNKNOWN / OPEN**. Эти suites не являются его расследованием/ремонтом; H14/H15 не переоцениваются.
2. Реального общего chat sender пока нет. Его выделение/подключение существующего OAuth требует отдельного WRITE scope и GO; новая реализация OAuth запрещена.
3. Tk/HTTP/Turn integration **NOT IMPLEMENTED**. До неё принять storage/P9/Stage3 зависимости и B2/route/budget gates; назначить owner durable attempt/context revision, проверить late callback/cancel/restart и safe mapping результатов. Текущий TEST продолжает пользоваться прежним ядром.
4. Контекстный projection owner/chat_context и max wire response до decode — задача будущего адаптера. Сервис не открывает Workspace и не выбирает чужой контекст.
5. Независимая приёмка ChatGPT после одной публикации пользователем. Авторский READY не заменяет решение координатора; весь Stage4 и real/paid sending не разрешены.

DOC IMPACT: только локальные interface/report/evidence и штатная карточка/историческая запись finish. Общие №001/05/06/34/40 и БЛОКИ2–4 не редактируются. Координатору передать эти OPEN и решение о следующем scope. Полный перечень публикуемых файлов и SHA-256 — manifest.json; finish_receipt подтверждает readback и сохранность старого слота.
