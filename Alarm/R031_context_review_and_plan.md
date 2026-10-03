# Независимая проверка R-031 и план ограничения контекста

Дата: 2026-10-01. Основание: запрос пользователя проверить отчёт и предложить решение.
Это аналитический документ, не запуск 151G и не изменение канонического порядка работ.

## 1. Вывод

Основной диагноз отчёта верен. Runtime сохраняет полные результаты инструментов в `messages` и повторно отправляет накопленную историю. У длинной stage отсутствует общий предел контекста. Два одинаковых полных чтения большого `ultra_ui.py` объясняют основную часть роста R-031. Уменьшение вывода модели или оптимизация Dredd это не исправят.

Однако отчёт требует уточнений: provider cache реально работал; Guard P1 допускает два чтения даже подряд; ограничение релевантности чтения нельзя автоматически приравнять к запрету читать зависимости; tool reserve гарантирует только резерв слотов, а не успешное выполнение обязательств. Точная доля токенов, вызванная конкретным файлом, не измерена отдельным provider replay.

Проверялись текущие рабочие файлы, включая уже существовавшие незакоммиченные изменения. Исторические сообщения и usage взяты непосредственно из Run Store. По одному текущему `git diff` нельзя установить, какие изменения принадлежали предыдущему диагностическому сеансу. Утверждение того сеанса «runtime не менял» здесь не считается независимо доказанным.

## 2. Проверенные артефакты и числа

R-031: `.ultra/audit/chat_b36a4eba7fdf47f98b1d71507bc2938d/20261001_182057_e90f93/`.
Проверены `summary.json`, `task.json`, `server.jsonl`, `executor.jsonl`, `planner.jsonl`, `executor_base.json`; контексты восстановлены через base + последовательные delta.

| Метрика | Подтверждённое значение |
|---|---:|
| Сумма provider `total_tokens`, все роли | 668 898 |
| Executor `total_tokens` | 665 505 |
| Executor `prompt_tokens` | 664 439 |
| Executor `completion_tokens` | 1 066 |
| Planner `total_tokens` | 3 393 |
| Dredd attempts | 0 |
| Executor provider attempts | 15 |
| Физически начатые tool calls | 14 |
| Executor `precached_prompt_tokens`, дополнительно | 179 456 |
| Статус | BLOCKED / Final Audit PENDING |

Все 16 provider attempts имеют terminal event; `unknown_usage_calls=0`. Сумма terminal usage совпадает с summary. Executor потратил 99,84% своих учитываемых токенов на вход.

| Запрос Executor | Размер `messages` + schemas, символов | Что произошло перед запросом |
|---|---:|---|
| #1 | 27 734 | Начальный контекст |
| #7 | 40 045 | Несколько поисков и небольшое чтение |
| #8 | 319 581 | Первое полное чтение root `ultra_ui.py` |
| #12 | 324 424 | История продолжает накапливаться |
| #13 | 603 960 | Второе полное чтение того же файла |
| #14 | 605 191 | Дополнительный поиск |
| #15 | 604 865 | Reserve сокращает schemas; история остаётся |

Оба больших чтения выполнены по пути `ultra_ui.py`, не по пути fixture. Их SHA-256 совпадает: `7bd32cad56c6f94056a291cc7beb570475be4bb3af88fd6749d66ceb021e547d`.
Содержимое каждого результата: 238 540 символов; сериализованное function message вместе с метаданными: 279 325 символов. Разница включает JSON escaping, в частности CRLF, и вложенную сериализацию. Это не число токенов.

Первый блок присутствует в запросах #8–#15, второй — #13–#15: всего 11 пересылок по 279 325 символов. Получается 3 072 575 символов из 3 669 107 суммарных символов `messages` + schemas за 15 запросов, то есть 83,74%. В #14 два блока занимают примерно 92,3% этого размера.

Это точная атрибуция сериализованного текста. Из неё нельзя автоматически получить такой же процент денежных или токенных сбережений: влияют токенизация, cache hits и изменение поведения модели после компиляции контекста. После первого большого чтения пришёл 620 741 некэшированный prompt token, но весь этот расход нельзя приписать только файлу.

Согласно официальной документации GigaChat, `prompt_tokens` в примере accounting исключает cache, `total_tokens` — количество токенов для тарификации, а `precached_prompt_tokens` учитывается отдельно. Значит, полный вход Executor с cache составляет 843 895 токенов; сумма входа и выхода всех ролей с cache — 848 354. Денежная стоимость этим анализом не рассчитывалась.

Источники: [подсчёт токенов GigaChat](https://developers.sber.ru/docs/ru/gigachat/guides/counting-tokens), [история и кэширование запросов](https://developers.sber.ru/docs/ru/gigachat/guides/keeping-context).

В Executor headers (`server.py:3283–3286`) сейчас нет явного стабильного `X-Session-ID`. Официальный API поддерживает этот заголовок для повышения вероятности cache reuse. Его можно проверить отдельным A/B экспериментом с изоляцией сессий по run/role/model; гарантировать cache hit нельзя. Кэширование уменьшает повторные вычисления, но не размер пересылаемого body и не заменяет compiler. Поля cached и full-input стоит явно агрегировать в новых summaries, сохранив исходный raw usage и provider semantics.

R-027 также проверен: run `20261001_002149_2d20df`, 1 736 351 provider total tokens, 20 Executor attempts и 5 Planner attempts. Размер `messages` + schemas доходит до 925 305 символов. Между запросами #5 и #6 контекст уменьшился до 25 509, после чего снова вырос. Даже произошедший reset не предотвращает повторное накопление.

## 3. Проверка выводов по коду

| Утверждение | Оценка и основание |
|---|---|
| Полный result попадает в модель | Подтверждено: `server.py:4981–4998`, `dict(result)` и `json.dumps(result_for_model)` без общего ограничения |
| Один read может быть огромным | Подтверждено: `server.py:139`, `1098–1111`, `1212–1219`; предел logical UTF-8 content — 2 MiB, а не предел prompt |
| Очистка зависит от lifecycle transitions | Подтверждено: `server.py:3618–3679`; reset возвращает base messages, обычный проход stage не компактизирует историю |
| В provider уходит полная история | Подтверждено: `server.py:3812–3821`, `3925–3927`; JSON body содержит текущие `messages` |
| Base + delta экономят storage | Подтверждено: `audit_storage.py:312–351`, `run_store.py:510–526`; это формат записи и восстановления контекста, не provider protocol |
| READ ограничен capability, а не stage target | Подтверждено: `server.py:809–827`, `3685–3694`; physical permission scope проверяется отдельно |
| Guard не ограничивает общий контекст | Подтверждено: `server.py:163`, `1927–1951`, `4253–4264`, `4854–4882` |
| Reserve ограничивает размер контекста | Не подтверждено: он считает remaining slots и обязательные вызовы (`task_planner.py:926–944`, `server.py:3762–3788`) |

Guard проверяет только `read_file` и `list_dir`. Порог равен двум успешным одинаковым вызовам: вмешательство начинается на третьем. Другой успешный инструмент или другой repeat key сбрасывает серию. `find_text` и `read_file_range` этим guard вообще не контролируются. В ключ входит глобальная write revision, mtime и size. Это защита от узкого loop pattern, а не дедупликация материала по содержимому.

У `read_file_range` уже есть предел 200 строк / 64 KiB (`server.py:142–143`, `1253–1275`). Но многократные разные range reads тоже будут накапливаться. Замена `read_file` на ranges без общего compiler не решает проблему полностью.

`_safe_tool_result_summary()` существует (`server.py:1954`), однако используется как краткая диагностика; полный result всё равно добавляется в model transcript. Использовать только такую строку вместо материала тоже недостаточно: модель потеряет код, необходимый для точной правки.

Большими могут быть не только function results: assistant `write_file` arguments содержат генерируемый файл; `git_diff`, stdout/stderr, project/global context и множество completed stage results также требуют общего бюджета. `max_tokens` ограничивает генерацию ответа, не вход. Accounting использует `utf8_bytes_div_4_v1` (`provider_accounting.py:11,41–44`), что является оценкой, а не гарантированным tokenizer count.

## 4. Что означают дефекты T-031

Уже в первом успешном поиске fixture находилась строка READY, поиск PENDING давал ноль. План содержал root-relative artifact `b2_logic.py`, а Executor фактически обращался к `Alarm/TASK151B_BENCH/B2_live_01/b2_logic.py`. Финальная предложенная mutation не совпала с path stage obligation; текущий `TaskLifecycle.new_candidate()` при таком несовпадении выдаёт ошибку до dispatcher.

В журнале непосредственно зафиксированы `candidate_preparation_failed` и затем `mandatory_tool_budget_exhausted`. Полный текст первичной preflight exception в этом event отсутствует, поэтому точный исторический exception не объявляется доказанным. Path mismatch подтверждён планом и аргументами. Отсутствие PENDING также делает предложенную замену неприменимой.

Planner выбрал `verify_file_content(kind='equals', value='STATUS_PREFIX = "READY"')`, хотя файл содержит дополнительный код. Это ошибочная семантика проверки наличия строки. Но stage этой проверки не достигнута: equals не был непосредственной причиной BLOCKED R-031.

Дефекты исходного состояния и контракта увеличили число бесполезных действий и помешали progress. Размер контекста вырос из-за независимого архитектурного дефекта. Исправление fixture должно сопровождаться отдельным regression длинной stage: clean benchmark может пройти быстро и скрыть проблему.

`allow_already_satisfied=false` запрещает автоматически считать baseline READY новой выполненной mutation. Политика no-op / replan должна быть явно определена и протестирована; оптимизатор контекста не должен задним числом менять её или выдавать старое состояние за новый receipt.

## 5. Предлагаемая архитектура

Разделить три вида данных:

1. Неизменяемый архив операций и полного материала в Run Store.
2. Авторитетное состояние lifecycle, requirements, receipts и freshness на Server.
3. Ограниченный material working set, который compiler выбирает для следующего provider request.

Не делать полный transcript источником server decisions. Новый чистый модуль `stage_context_compiler.py` получает snapshot состояния, ссылки на observations/material и budget, возвращает готовые messages плюс manifest отбора. Точка вызова — перед сборкой provider body. Оригинальные результаты архивируются до проекции; для ошибок, preflight rejection и tool results, после которых сразу происходит stage transition, тоже нужна самостоятельная durable запись полного результата.

Состав provider context:

- RAW TASK один раз без смысловой переписи; необходимые системные правила и permissions.
- Свежие server facts: run/plan/stage identity, открытые обязательства, доступные действия, актуальный tool budget и статусы проверок.
- Данные текущей работы: точные ranges, определения и search matches, выбранные для stage.
- Точный материал актуальных ошибок и negative evidence, влияющих на следующий шаг; остальные записи доступны через архив.
- Небольшое число завершённых tool exchanges, когда они нужны протоколу/пониманию следующего действия.

Контрольные facts строятся из Server state при каждом запросе. Исторические `_verification_state` и `_tool_budget` не должны бесконечно дублироваться и конкурировать с актуальным состоянием.

Для large reads модель получает явный envelope: path, размер, число строк, whole-content SHA-256, source record/material reference, `representation`, `content_included`, `complete=false` при частичном материале, конкретные ranges и способ дочитать. Не скрывать обрезку. У ссылки должен быть работающий retrieval path: существующие `find_text`/`read_file_range` читают текущий файл; для сохранённой исторической версии потребуется отдельное чтение material по reference, если это нужно задаче.

Дедупликация model material по canonical path + logical content SHA + range/representation. Повторный вызов сохраняется как отдельное событие, но одинаковый текст не дублируется в working set. SHA позволяет переиспользовать материал; право удовлетворить requirement определяется всей evidence identity. Факты отрицательного поиска сохраняют query/arguments identity и content hash. После изменения файла старые observations помечаются stale и больше не служат доказательством текущего состояния. Изменение unrelated файла не должно автоматически инвалидировать все read materials.

Relevance — правило отбора, а не замена permissions. Первыми выбираются artifact targets и evidence dependencies текущей stage. Разрешённые зависимости можно добавить в working set с provenance/reason и в пределах бюджета. Жёсткий запрет всех файлов вне artifact list сломает задачи с imports, callers, tests и конфигурацией. Для compile-only требования полный исходник UI обычно не нужен модели.

Compiler сохраняет допустимый порядок assistant/function exchanges. Старые завершённые пары можно убрать целиком и заменить честными server facts с references. Нельзя оставить orphan function result, изменить оригинальный proposed mutation payload в lifecycle или представить сокращённый result полным. Особенно проверить `functions_state_id` и transitions на provider adapter. Сгенерированные большие write arguments тоже архивируются и исключаются из исторической пересылки после обработки.

## 6. Бюджеты и порядок реализации

Предлагаемые стартовые значения для offline эксперимента: 8 KiB serialized UTF-8 на inline tool material, 32 KiB на весь stage material working set, 128 KiB на полный сериализованный provider body. Это проектные значения, не свойства модели и не уже доказанный оптимум. Budget измеряется после JSON escaping, с schemas и control blocks. Профиль задаётся конфигурацией; при наличии проверенного tokenizer дополнительно контролируется полный вход плюс резерв ответа и margin.

Если обязательные RAW TASK / policy / server facts сами превышают hard budget, завершать запрос до provider с конкретной причиной `context_budget_unrepresentable`. Нельзя молча обрезать требование или разрешения. Большой материал обрабатывается диапазонами и отдельными шагами; переход stage ради очистки не должен фальсифицировать её завершение.

Отдельно нужен RUN budget: total provider attempts, накопленные учитываемые токены, repair/replan limits и проверяемый progress. `tool_limit` не ограничивает ответы без tools или retries. Перед очередным provider call проверяется остаток бюджета; расходы всех ролей и неизвестный usage учитываются явно. Оценка входа не гарантирует верхнюю денежную границу, поэтому при необходимости строгой стоимости потребуется отдельный проверенный accounting policy. Identity и cache metrics добавляются без переписывания исторических totals.

Рекомендуемые шаги:

1. **Воспроизводимость.** Закрепить R-027/R-031 как неизменяемые negative inputs. Сделать fresh fixture из template, baseline hashes, fixture-relative paths, правильный contains, явную no-op policy. Dirty case оставить отдельно.
2. **Compiler contract и offline replay.** Реализовать чистую функцию/manifest, сериализованный byte budget, typed projections и материал по references. Replay измеряет размер и сохранность фактов; не объявлять сохранённые ответы модели ответами новой реализации.
3. **Интеграция large outputs.** Archive-before-projection для всех результатов, включая mutation arguments, ошибки и stage-ending results. Inline envelope и range retrieval; полноценный per-request budget. Убедиться, что запись архива при сбое не заменяется фиктивным usable reference.
4. **Bounded in-stage working set.** Отбор relevance, dedup, freshness, актуальные control facts, protocol validation на каждом запросе. Это ядро 151G.
5. **RUN protection и наблюдаемость.** Manifest каждого запроса с included/evicted refs и причинами, compiled bytes/tokens estimate, largest blocks, preserved negatives, cache usage и cumulative spend. No-progress оценивается по новым полезным observations/receipts, а не длине прозы или простому числу повторов.
6. **Валидация и включение.** Offline negative cases → mock integration → controlled clean/dirty provider cases → flag rollout. Rollback восстанавливает прежнюю сборку, но сохраняет архив и новые диагностические данные.

Канонический NEXT в `000` и `20/21` — 151C. Этот документ его не меняет. 151C полезна для Dredd packet, 151D снижает ненужные decision calls при exact evidence, 151F уменьшает постоянный baseline; они не обеспечивают bounded in-stage Executor context. Если до 151G продолжаются оплачиваемые stress runs, рекомендуемый приоритет — отдельно оформить ранний ограниченный этап защиты large results / request size. Если порядок остаётся строгим, большие live stress cases стоит выполнять уже после появления такой защиты; до этого можно разрабатывать acceptance и offline replay.

## 7. Acceptance tests

| Сценарий | Обязательный результат |
|---|---|
| Два одинаковых large reads с другими tools между ними | Нет двух копий полного текста; каждый provider body в budget |
| 20–100 разных reads/ranges в одной stage | Working set достигает плато; длинная stage не накапливает transcript без предела |
| Большой read / write arguments / diff / stderr | Архив полон; проекция помечена; serialized escaping входит в budget |
| Увеличение размера файла 0,3 → 2 MiB | Размер запросов остаётся ограниченным; доступ к нужному диапазону работает |
| Mutation или внешний edit после отрицательного поиска | Старое count=0 не используется как свежее evidence |
| Replan / repair с одинаковым stage_id | Старое evidence generation не закрывает новое requirement |
| Eviction + повторная потребность в коде | Доступен точный материал нужной версии или явное stale состояние |
| Dependency вне списка artifacts | Разрешённое нужное чтение работает; scope denial не обходится |
| Неприменимая mutation / denied permission | Negative evidence сохраняется; оптимизация не превращает отказ в SUCCESS |
| Большой immutable baseline | Явный локальный отказ до provider, RAW TASK не обрезан |
| Повторение компактных запросов без прогресса | RUN budget останавливает расход с диагностируемой причиной |
| Restore из base + delta | Восстанавливается именно отправленная compiled проекция; полный архив доступен отдельно |

Тесты должны проверять перехваченный provider body и server state, а не только вспомогательный compiler. Отдельно доказать, что compiler не вызывает скрытые дополнительные LLM requests. Для clean task сравнивать конечное состояние файла и реально выполненные проверки; token/call reduction не заменяет correctness. Процент экономии определяется после новых provider runs с указанием cache conditions.

## 8. Выполненная проверка текущей базы

Команда: `.venv/Scripts/python.exe -m pytest -q test_provider_accounting.py test_provider_attempt_integration.py test_usage_accounting.py test_executor_context_delta.py test_executor_diagnostics.py test_stage_tool_visibility.py test_stage_evidence_contract.py test_file_editing_toolbox.py test_task_planner.py`.

Результат: **120 passed, 37 subtests passed**. Эти тесты подтверждают текущие контракты, а не предложенное исправление. В проверенном наборе нет integration regression, гарантирующего bounded in-stage provider context после накопления больших результатов.

Runtime в рамках этой проверки не редактировался. Добавлен только этот самостоятельный аналитический документ.
