# Scope — CLAUDE-WA4-R-AUD01T02B-REPAIR-001

Ремонт AUD-01T (глобальное transport-evidence) и AUD-02b (переходы микрозадач). Зафиксировано **до первой правки исходников** (2026-10-16). Обновляется только дописыванием раздела «Окончательный scope» после результата.

## Baseline gate (пройден до правок)

- `tools/baseline_gate.py` → `baseline-gate.json`: **PASS**. 103 ожидаемых файла (pin R-006 + три файла и тест прошлого ремонта AUD-01/02/05 с их итоговыми SHA) совпадают побайтно; лишних и отсутствующих нет; дрейфа нет.
- Пакет R-006: 64/64, `manifest.json` = `b14c366452547de2d4a102a5c50b4c7da0ad01dc539e7ded629f1a3fee46f84e`.
- Целевые файлы равны pin R-006: `transport_event_store.py` `107a8e89cff2ffaae2a6eb899d0028e1c2a46788e12edfc3de5b9448a3b020cf`, `state_machine.py` `0bec1f270ac957fff279d3cf1de13201421600b6b173ef0f17b983c57bfac2fb`. Оба LF, без «сырых» U+0085/U+2028/U+2029. Байты — в `baseline/web_alarm/`.
- Ориентир постановки: `main@3482216…`, кодовая база коммита №352 `7778c9e…`. Git не использовался: источник сверен только по байтам и pin-карте.

## Разрешённые изменения (write-scope)

| Файл | SHA-256 до ремонта | Назначение |
|---|---|---|
| `web_alarm/transport_event_store.py` | `107a8e89…` | AUD-01T: LF-framing и экранирование U+0085/U+2028/U+2029; отказ на оборванном хвосте; межпроцессная сериализация read-check-append; откат собственной неудачной записи |
| `web_alarm/state_machine.py` | `0bec1f27…` | AUD-02b: проверка читаемости истории до любой записи (в том числе до REJECTED-события) и под тем же lock, что CAS; событие перехода — в той же критической секции; честный результат при сбое истории после commit; входные строки, которые нельзя записать в UTF-8, отклоняются до записи; prepare — та же проверка на входе |
| `web_alarm/event_checkpoint_store.py` | `7342b221e6663bee65bef116f57507b0de84b74269cb7541f4955b527eb91304` | **Связанное изменение (обосновано ниже):** межпроцессная сериализация `append_event` для одной TASK |
| `test_web_alarm_aud01t02b_repair.py` | новый | адресные regression/negative/concurrency тесты |
| `Alarm/ALARM_TASK_SESSION/TASK_CLAUDE-WA4-R-AUD01T02B-REPAIR-001/**` | новый | отчёт, evidence, manifest, scope, baseline, probes, tools |
| `Документация/000_Задачи Claude.md` | — | только ротация БЛОКОВ 1–3 после результата |

### Почему нужен `event_checkpoint_store.py` (связанное изменение)

- **Факт платформы.** `probes/probe_append_atomicity.py` (TEMP, без web_alarm): 8 процессов × 250 записей через тот же шаблон `open("a"/"a+b") → write → flush → fsync` без lock. Ожидалось 2000 записей. Получено: text — 826 уникальных + 4 испорченные строки; binary — 616 + 2 (`runs/append-atomicity-*.json`). O_APPEND на этой Windows/Python 3.12.10 **не атомарен между процессами**: записи молча теряются или склеиваются.
- **Связь с AUD-02b.** Писатели событий TASK держат разные lock: OperationStore — TASK-lock; переходы и `_reject`/prepare в `state_machine` — ни одного; closeout пишет `TASK_COMPLETED` после снятия lock; `POST …/report` — без lock. Если событие перехода параллельно с другим писателем потеряется, статус микрозадачи останется сохранённым **без события** — тот же дефект AUD-02b, только молча. Без сериализации записи гарантия «статус ⇔ событие» недостижима.
- **Минимальная правка.** Leaf-lock `locks/events/<task_id>.lock` только на время одной записи внутри `append_event`, после проверки `task_id` (путь к TASK уже валидирован, AUD-04 не повторяется). Внутри lock других lock не берётся — циклов нет. Чтение (`read_events`) остаётся без lock: projection/inspect по контракту «pure, no lock, no write».
- **Последствия.** Новый lock-файл на TASK; каждая запись события ждёт lock (таймаут — общий `DEFAULT_LOCK_TIMEOUT_SECONDS`, отказ → `EventCheckpointStoreError`). Формат журнала не меняется.

## Расширение scope: два существующих профильных теста (записано до правки)

Предварительный полный прогон `full1` на исправленных исходниках: 846 = 843 PASS / 2 FAIL / 1 SKIP. Оба FAIL — тесты, которые используют внутренний шов `TaskStore.compare_and_set_microtask_status` как точку «решение принято, заблокированная запись ещё не начата»:

| Файл | SHA-256 до | Тест | Что меняется |
|---|---|---|---|
| `test_web_alarm_state_machine_cas.py` | `7a2ce35e5342667d490c3494666fbec0b43af4d883f815f23a472f6d092e1dff` | `test_c_two_transitions_from_one_observed_status_only_one_applies` (через `SM_CHILD`) | к старому барьеру добавляется барьер на `ServerStateMachine._commit` — новую заблокированную секцию (история → CAS → событие); старая строка остаётся |
| `test_web_alarm_recovery_coordinator_repair3.py` | `bf316497034a0f28f211ad27e25e079dc2bf3f3dd575a72aeff08c7e2d983811` | `test_f4_activation_rechecks_earlier_microtasks_under_the_lock` | инъекция «параллельный replan» переносится с `TaskStore.compare_and_set_microtask_status` на `ServerStateMachine._commit` (вход в ту же секцию до mutation lock) |

- **Почему.** Ремонт AUD-02b переносит проверку истории, CAS и событие в одну секцию под mutation lock. CAS теперь вызывается через `compare_and_set_microtask_status_locked`, а нелоковый вариант, на который ставили барьер, больше не вызывается. Смысл тестов («решение по наблюдённому статусу, потом заблокированная запись») сохраняется, меняется только точка инъекции. Для VERIFIED так уже было сделано раньше: барьер на `ServerStateMachine._admit_verified`.
- **Проверка, что тесты не ослаблены.** Отдельные source-мутанты: `_commit` с `activate=False` (без повторной проверки предыдущих микрозадач под lock) должен ловиться `test_f4`. Для `_commit` без CAS (принимает любой текущий статус) `test_c` недетерминирован — порядок двух дочерних процессов после барьера случаен. Поэтому добавлен детерминированный тест в новом модуле: `test_plain_step_decided_on_a_stale_status_is_rejected_under_the_lock`.
- Исходные байты обоих файлов — в `baseline/tests/`.

## Вне scope (не изменяется)

- `server.py`, `closeout.py`, `operation_store.py`, `projection.py`, `task_store.py`, `manifest_store.py`, `microtask_gate.py` и прочие модули `web_alarm`.
- AUD-03 (crash между INTENT и событием) и AUD-04 (lock до валидации ID) — только анализ.
- `wa4a_acceptance.py`, CI/workflows, общие runner'ы, общая документация (08/18/23/24/25/34/36.x/05/06 и др.).
- Рабочая область Codex 007 (`reports/CODEX-WUA-*`, MCP-плагин, `C:\Users\REX\.codex\config.toml`) — не читается и не меняется. Его активная TASK `CODEX-WUA-0-DESKTOP-MCP-E2E-001` запрещает ему менять `web_alarm/*.py`; пересечения по записи нет. Его плагин использует собственную vendored-копию web_alarm, поэтому правки в репозитории его runtime не затрагивают.
- Ultra/Tkinter, сеть, прокси, credentials, live Workspace и production storage. Тесты — только disposable TEMP.
- WARN / GATEWAY REQUIRED / STRICT / Final Audit не включаются.

## Окончательный scope (после результата)

Gate E (`gate-e.json`): **PASS**. Изменены ровно 5 файлов из таблиц выше, новый — 1 тест. Ничего вне scope не записано.

| Файл | До | После |
|---|---|---|
| `web_alarm/transport_event_store.py` | `107a8e89…` | `cbd74a2526932f2063fef4ea73bf31b53fdab3504abe5ff6ac5a611769a91d95` |
| `web_alarm/state_machine.py` | `0bec1f27…` | `3164383a1a881c6dfcac86678b746d01c038f1b4ccb988fbda5a6074a262f408` |
| `web_alarm/event_checkpoint_store.py` | `7342b221…` | `9cf9e3ed45a415bfcab139bdb24fc88af65c7ece8723f1f5192c3e9a0ab8bf45` |
| `test_web_alarm_state_machine_cas.py` | `7a2ce35e…` | `e00c5f1bbce9c5900887b767bc52195737a783f3cac15baa8f84459e55ca7e77` |
| `test_web_alarm_recovery_coordinator_repair3.py` | `bf316497…` | `76244e276ffeb53737723a361c26b52479c39302b3d93ce68f22e074dc3b3016` |
| `test_web_alarm_aud01t02b_repair.py` | новый | `b96c2b0cec62b05998075e068a4c13edb0969dadfa6210d20aecd53b25ff0ef3` |

- **Порядок.** Черновик `transport_event_store.py` один раз был записан до красного прогона и сразу возвращён к baseline-байтам (SHA проверен). Тестов на черновике не было; красный baseline получен на исходных байтах.
- **Чтение вне scope (случайное).** Один `Grep` по имени `transport_event_store` по всему репозиторию вывел **имена файлов** из `reports/CODEX-WUA-0-DESKTOP-MCP-E2E-001/…/vendor/web_alarm/`. Содержимое не открывалось; дальше поиск по `reports/CODEX-WUA-*` не делался.
- **Карточка.** Только ротация БЛОКОВ 1–3 (`tools/rotate_card.py`, две фазы с проверкой на диске).
