# CLAUDE-WA-003 — RC-1: Durable Operation Contract + backward compatibility

**Исполнитель:** Claude Opus 5.5, Claude Code (desktop), локальный доступ.
**Дата:** 2026-10-04.
**Статус:** RESULT READY / AWAITING INDEPENDENT VERIFICATION.
**ARCH CLASS:** Web Alarm Workspace runtime (WEB-02). **PRIMARY PROFILE:** `23`; план и acceptance — `24`; история — `25`.
**База:** HEAD `c5dfd1a`. Commit / push не выполнялись. `.gitattributes`, UI и переводы строк не менялись. Физических мутаций проекта код RC-1 не выполняет.

---

## 1. RESULT

Новая операция теперь сохраняется как самодостаточный **Operation Contract v2**. Новый процесс или Chat восстанавливает его без памяти исполнителя:
- точная каноническая цель;
- pre-state, который сервер прочитал сам;
- ожидаемый post-state;
- ссылка на payload;
- fingerprint;
- provenance;
- revision;
- receipt при DONE, который сервер тоже читает сам.

Legacy-записи WA-3.7 читаются как contract v1 без перезаписи и никогда не считаются достаточными для RETRY re-arm. Запись Operation Store защищена межпроцессной блокировкой; гонки проверены реальными процессами.

**Регрессия:** 241/241 OK — 197 прежних + 44 новых, 1 skip: на машине нет привилегии создавать symlink, случай reparse point покрыт тестами с junction.

## 2. ЧТО СДЕЛАНО

**Новые узкие модули** (`server.py` не раздувался — в нём +21 строка):

| Модуль | Одна ответственность |
| --- | --- |
| `web_alarm/file_state.py` | Физическое состояние файла. Authority: `exists` / `size` / `sha256` по точным байтам, чтение потоковое. Диагностика: `eol` (`lf` / `crlf` / `mixed` / `none`), `bom`, `normalized_sha256` (CRLF→LF, без BOM) — только для `EOL_ONLY_DRIFT`. |
| `web_alarm/target_identity.py` | Одна каноническая функция `canonical_target(root, raw)` и ключ сравнения `target_key`; правила — ниже. |
| `web_alarm/storage_policy.py` | Policy RC-0: deny-list секретов, лимит payload 1 МиБ, retention `KEEP_UNTIL_EXPLICIT_CLEANUP`. |
| `web_alarm/payload_store.py` | Content-addressed immutable blob `<task_dir>/payloads/<sha256>.bin`. Запись один раз, без перезаписи; проверка hash+size при каждом чтении; размещение внутри workspace/vault запрещено. |
| `web_alarm/store_lock.py` | Межпроцессная блокировка: `msvcrt` / `fcntl`, таймаут → fail-closed. После падения процесса блокировку снимает ОС. |
| `web_alarm/operation_contract.py` | Версии контракта, fingerprint v1/v2, проверка запроса, сборка контракта, receipt, fail-closed валидация сохранённых записей, `assess()`. |

**Правила `canonical_target`:**
- путь относительно workspace, разделители POSIX, `normcase` (регистр не важен на Windows); у существующих компонентов — написание с диска;
- junction в родительских папках разрешаются по физическому пути, но цель обязана остаться внутри workspace;
- сама цель не может быть symlink или reparse point;
- запрещены ADS `:`, имена устройств (`NUL`, `CON`, `COM1`…), точка или пробел в конце компонента, символы `<>"|?*`, управляющие символы, пути вида `C:foo`, папка вместо файла;
- проверка идёт и по введённому написанию: Windows-резолв может молча отбросить ADS или точку в конце.

**Изменённые файлы:**
- `models.py` — у `OperationRecord` 4 новых поля с legacy-значениями по умолчанию: `contract_version=1`, `revision`, `contract`, `receipt`;
- `operation_store.py` — путь v1 сохранён, v2 добавлен, блокировка, `read_payload`, `contract_status`;
- `reconciliation.py` — минимальная интеграция, см. §4;
- `server.py` — необязательные поля в существующем `POST /operations`: `expected_pre_state`, `expected_post_state`, `payload` (`utf-8` / `base64`), `agent`, `channel`, `allow_secret_target`; `contract_status` в `GET`; ошибки 400 / 403;
- `__init__.py` — экспорт.

**Contract v2** (`record.contract`, после INTENT не меняется):
- `workspace_id`, `target_key`;
- `mutation_kind` (`CREATE` / `WRITE` / `DELETE` по `action`);
- `pre_state` — сервер читает его сам при INTENT;
- `declared_pre_state`;
- `expected_post_state` — из payload или объявленный (pre-commitment);
- `payload_ref` (`sha256`, `size`, `store`, `retention`);
- `provenance` (`agent`, `channel`, `authority="claimed"`);
- `policy` (`secret_pattern`, `secret_override`, `max_payload_bytes`, `retention`);
- `fingerprint_version=2`, `complete`, `issues`.

**Изменяемые поля:**
- `revision`: 1 при INTENT, +1 на каждый сохранённый переход;
- `receipt` — при DONE сервер сам читает target. Если состояние противоречит контракту, DONE отклоняется: статус не меняется, пишется событие `OPERATION_RECEIPT_MISMATCH` с признаком `EOL_ONLY_DRIFT`, если различие только в переводах строк.

**Fingerprint v2** строится только из того, что объявил вызывающий:
- `task` / `micro` / `action`;
- `target_key`;
- объявленные pre- и post-state;
- `sha256` и `size` payload;
- override секрета;
- непрозрачный `request`.

Наблюдения сервера, provenance и время в fingerprint не входят. Поэтому повтор из нового процесса даёт тот же fingerprint, а любое написание той же цели — тот же ключ. Fingerprint v1 для legacy не изменён — это закреплено golden-тестом по коду HEAD.

## 3. СОВМЕСТИМОСТЬ

- **Глобальная `SCHEMA_VERSION = 1` не поднята.** У контракта своя версия; 8 хранилищ не мигрировались.
- **Legacy v1.**
  - Отсутствие полей v2 в JSON означает contract v1. Такие записи читаются как есть.
  - Переходы legacy-записи в активной TASK сохраняют прежнюю форму JSON: ключи v2 не добавляются.
  - Повтор legacy-записи сравнивается старым алгоритмом. Попытка «дописать» к ней payload — конфликт.
  - `assess()` возвращает `rearm_contract_sufficient=false`, `issues=["legacy_contract_v1"]`.
- **Живые записи WA-3.7 (read-only).** Свежий процесс прочитал `WA37-CTRL-001` (VERIFIED) и `WA37-CTRL-002` (FAILED):
  - `contract_version=1`, `RETURN_KNOWN_STATE`, `rearm=false`;
  - SHA-256 до и после: `083bdf8f…6096` и `319ca763…f489`;
  - дерево storage до и после совпадает: 136 файлов, `88fc4f99…4149`.
- **Запросы в старом стиле** (без payload и объявленных состояний) по-прежнему принимаются. Это нужно всем 197 прежним тестам. Такая запись создаётся как v2, но `complete=false` с явными `issues`, и для re-arm недостаточна.
- **Ужесточение — fail-closed.** Новая операция теперь требует доступный workspace и валидную файловую цель внутри него. Нефайловые и многофайловые «цели» контракт v2 не представляет: каждый mutating step — отдельная операция, в духе инварианта 17 и WA-4.2.
- **Rollout.** Старый код WEB-02 не прочитает записи v2: из-за строгого `**raw` он упадёт fail-closed. После принятия RC-1 все процессы WEB-02 нужно перезапустить. Сейчас запущенных процессов WEB-02 нет — проверено.

## 4. РЕШЕНИЯ ВНУТРИ SCOPE (инженерная свобода)

1. **Receipt — наблюдение сервера при DONE** (предложение P5 из preflight). Противоречие с контрактом → DONE отклоняется, нужна reconciliation. Это проверка заявления по байтам, а не Resolver и не CAS по target.
2. **Reconciliation читает post-state из контракта.** Если вызывающий post не передал, используется post из контракта v2, источник `operation.contract`. Если передал противоречащий — ошибка evidence и `MANUAL_REVIEW_REQUIRED`. Свежий процесс без входных данных от вызывающего получает `RETRY_SAFE`, пока target в pre-state, и `ADOPT_CURRENT_STATE`, когда достигнут post. Это и был исходный дефект архитектурного обзора («expected post-state не хранится вместе с операцией»). Для старых записей поведение не изменилось.
3. **Scope-gate секретов проверяется на каждом запросе, включая повторы.** Повтор без override получает 403 (fail-closed), а не 409.
4. **Блокировка — на одну TASK**, файл `<storage>/locks/operations/<task_id>.lock` вне каталога TASK. Он не мешает переносу TASK из `active` в `completed`. Внутри блокировки: проверка существующей записи, наблюдение pre-state, запись payload и записи, событие, checkpoint.
5. **Payload лежит в каталоге TASK** и переносится вместе с ним. Retention простой: без автоудаления.

## 5. ПРОВЕРКА

| № | Проверка | Результат |
| --- | --- | --- |
| 1 | Focused: `test_web_alarm_operation_contract` (19), `test_web_alarm_target_identity` (13, 1 skip), `test_web_alarm_payload_store` (7) | PASS |
| 2 | Multiprocess: `test_web_alarm_operation_store_concurrency` (5), 8 реальных процессов с барьером старта: один `operation_id` → ровно 1 запись; один переход → применён 1 раз, revision не потеряна; независимые писатели → все записи, revision и события целы, `events.jsonl` строго парсится; блокировка упавшего процесса снимается ОС; таймаут — fail-closed | PASS; 10/10 повторов стабильны |
| 2a | Чувствительность: те же 3 гоночных сценария с отключённой блокировкой (скрипт в scratchpad, вне набора тестов) | Падают **5/5** каждый: тест действительно ловит потерю записи |
| 3 | Fresh process: свежий Python-процесс читает тот же контракт, revision, fingerprint, хеш payload; reconcile без входных данных от вызывающего | PASS |
| 4 | Negative: неизвестная или bool-версия контракта, лишнее или пропущенное поле, дрейф `target_key`, `complete` против `issues`, плохой хеш, `revision=0`, legacy с полями v2, несоответствие `payload_ref`, повреждённый или пропавший payload, секретная цель, превышение размера, payload внутри workspace, тот же `operation_id` с другим payload или `request`, CREATE существующего, DELETE отсутствующего, DELETE с payload, post против payload, неверный declared pre | все fail-closed |
| 5 | Полная регрессия `python -B -m unittest test_web_alarm_*.py` | **241/241 OK** (skip 1), 24,6 с |
| 6 | `python -B -m compileall -q web_alarm` | OK |
| 7 | `git diff --check` | OK; новые файлы — LF, без хвостовых пробелов |
| 8 | Границы | `.gitattributes` отсутствует; `ui.py`, `state_machine.py`, `manifest_store.py` не тронуты; tracked-цели проекта вне scope не менялись. `.obsidian/*` и `22_…` изменены другими писателями до или во время сессии |

Отдельно: три написания реального файла `Документация/08_Старт.md` (обратные слэши; строчная кириллица с `.MD`; абсолютный путь) дают одну идентичность. Среди 157 реальных файлов репозитория reparse point нет.

## 6. ИЗВЕСТНЫЕ ГРАНИЦЫ (не входят в RC-1)

- Resolver, ADOPT / ROLLBACK / ABORT и re-arm для RETRY — RC-2. RC-1 выдаёт только факт достаточности контракта (`rearm_contract_sufficient`).
- Conflict gate и CAS по канонической цели — RC-3. Блокировка RC-1 защищает только целостность хранилища.
- Переход VERIFIED не перечитывает target: дрейф между DONE и VERIFIED — вопрос RC-2 / RC-5.
- Под блокировкой не находятся:
  - другие писатели `events.jsonl` и checkpoint (state machine, manifest);
  - `complete_task`;
  - чтения. Pre-existing риск Windows: `os.replace` может получить sharing violation, если файл в этот момент открыт читателем. Это давняя особенность всех хранилищ WEB-02, не регресс; ошибка выходит fail-closed.
- `ManifestStore` ещё не использует `canonical_target`: его формат `source_path` не менялся ради legacy manifest. Сравнение в reconciliation уже идёт по `target_key`.
- Deny-list секретов статичен: правила `.gitignore` не разбираются, содержимое payload не сканируется. Для этого репозитория `.env*` покрывает правила `.gitignore`.
- Любой reparse point у самой цели — fail-closed. На облачных дисках (placeholder-файлы OneDrive) это заблокирует цели. В текущем репозитории таких файлов нет.
- Новый служебный каталог `<storage>/locks/` — маленькие файлы-замки, не удаляются.

## 7. PROPOSALS (вне scope, на решение)

1. **RC-2:** привязать `contract.pre_state` к pre-state снимка manifest (drift между снимком и INTENT → MANUAL), при VERIFIED заново читать target.
2. **RC-3 / hardening:** перевести `ManifestStore._resolve_target` на `canonical_target`. Повторять `os.replace` при sharing violation или брать блокировку и на чтения. Поставить под ту же сериализацию запись events / checkpoint из state machine.
3. **Политика reparse point:** при необходимости разрешить reparse-теги облачных файлов, запрещая только symlink и mount point.
4. **Документы:** строка Web Alarm в `01` устарела ещё до RC-1 (WA-3 «IN PROGRESS», 197 тестов). После проверки RC-1 обновить `01`, статус RC-1 в `24` / `05` и при необходимости кратко записать в `23` факт о contract v2.

## 8. DOCUMENTATION BLOCK / CLOSEOUT

```text
DOCUMENTATION BLOCK
TASK TOPIC: Web Alarm Workspace — Durable Operation Contract (RC-1)
PROFILE DOCUMENTS: 23 (инварианты 23, 25, 29, 31–33 — реализация соответствует, текст не меняется), 24 (статус RC-1), 25 (история)
CHECK 01: YES — строка Web Alarm устарела ещё до RC-1; правка после независимой проверки (PROPOSAL 4)
OTHER AFFECTED DOCUMENTS: 000_Задачи Claude, 001, 06; после проверки — 05, 24
REGISTRY IMPACT: NO — новых Markdown в Документация/ нет
CONTEXT LIBRARY IMPACT: NO
```

Выполнено в этой TASK:
- `000_Задачи Claude.md`, БЛОК 1 — статус `RESULT READY / AWAITING INDEPENDENT VERIFICATION` и итог;
- `001` — краткая запись;
- `06` — запись сверху;
- `25` — запись в конец.

`23`, `24`, `05`, `01` не менялись: статусы меняются после независимой проверки.

## 9. NEXT SAFE ACTION

Независимая проверка RC-1 (ChatGPT / пользователь): перепрогнать 241 тест, проверить чувствительность гоночных тестов и read-only чтение живых записей WA-3.7, прочитать дифф пяти изменённых и шести новых модулей. До проверки RC-2 не начинать. После принятия — перезапустить процессы WEB-02, если они будут запущены, и закоммитить (коммит делает пользователь).
