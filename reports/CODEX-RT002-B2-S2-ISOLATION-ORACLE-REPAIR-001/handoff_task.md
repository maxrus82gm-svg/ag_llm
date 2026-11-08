# Снимок постановки `CODEX-RT002-B2-S2-ISOLATION-ORACLE-REPAIR-001` — перенос БЛОК 1 → БЛОК 1.1

| Поле | Значение |
|---|---|
| TASK ID | `CODEX-RT002-B2-S2-ISOLATION-ORACLE-REPAIR-001` |
| Карточка | `Документация/000_Задачи Codex.md` |
| Дата переноса | 2026-11-08 |
| Статус | `SUBMITTED / REVIEW PENDING` — сдано исполнителем; независимая приёмка не выполнена |
| SHA-256 постановки (UTF-8, концы строк LF) | `37aa98e28f268540a02d78275a3f623b5727950adf68b6f0a4dc9b7faf00cf87` |
| Строк постановки | 154 |
| CHAT-ONLY AMENDMENT | нет (заявлено исполнителем) |
| Отчёт | `reports/CODEX-RT002-B2-S2-ISOLATION-ORACLE-REPAIR-001/report.md` |
| Инструмент | `tools/task_slot_rotate.py` — побайтовое копирование без пересказа |

Текст между строками-маркерами ниже — побайтовая копия содержимого БЛОКА 1 (концы строк приведены к LF).

<!-- TASK-SNAPSHOT:BEGIN -->
**TASK ID:** `CODEX-RT002-B2-S2-ISOLATION-ORACLE-REPAIR-001`

# Web Alarm Ultra — RT-002/B2 S2: исправление isolation oracle для OFFLINE ledger

**Исполнитель:** Codex 007  
**Координатор / независимый verifier:** ChatGPT WEB26  
**Приоритет:** HIGH  
**ARCH CLASS:** Ultra Runtime / RT-002 B2 / S2 Policy Isolation  
**Режим:** STRICT OFFLINE / LOCAL ONLY  
**Тип:** узкая корректирующая TASK  
**Исходная версия:** `main@0ee846a1159c690d2bc29eab46fca807e4027541`  
**Предыдущая TASK:** `CODEX-RT002-B2-S1-INVENTORY-RECON-001` / `H-CODEX-000024`

## 1. Основание

WEB25 независимо принял исправление S1:

- S1: 69/69 PASS, guarded, exit 0.
- Дополнительные reconciliation checks: 23/23 PASS, включая 18 мутаций.
- S2: 72/73 PASS, один подтверждённый FAIL.
- S3a: авторские 35 PASS, независимый runtime ещё не выполнен.

Оставшийся FAIL:

`IsolationTests.test_no_production_module_imports_the_policy_yet`

Текущий S2 oracle использует `s1._production_modules()`, который включает standalone OFFLINE `ultra_budget_ledger.py`. Этот ledger намеренно импортирует чистую `ultra_budget_policy.py`, хотя подключение бюджетной политики к рабочим физическим маршрутам отправки ещё не выполнено.

Тест смешивает наличие модуля в инвентаризации S1 и фактическое использование политики производственным runtime.

**Цель:** исправить классификацию в S2 oracle, сохранив запрет на преждевременное production enforcement до принятия S3b.

## 2. READ / WRITE scope

**READ разрешён:**

- `test_rt002_s2_budget_policy.py`
- `test_rt002_s1_routes.py`
- `test_rt002_s3a_ledger.py`
- `ultra_budget_policy.py`
- `ultra_budget_ledger.py`
- Production-модули, относящиеся к import closure и использованию политики.
- №08, №20 §5а, №21, №34, №37, №36.1/36.3.
- Отчёт и review H24, `amendment_request_s2.md`, действующие FOLLOWUP.

**WRITE разрешён:**

- `test_rt002_s2_budget_policy.py`
- Новые адресные тесты, helpers, report, manifest и evidence только внутри `reports/CODEX-RT002-B2-S2-ISOLATION-ORACLE-REPAIR-001/`.
- Штатное механическое завершение собственного БЛОКА 1 через `finish`.

**WRITE запрещён:**

- `ultra_budget_policy.py`, `ultra_budget_ledger.py`.
- `test_rt002_s1_routes.py`, `test_rt002_s3a_ledger.py`.
- Production runtime, transport, launcher, UI, Run Store.
- №05/06/20/21/34/37, другие общие документы, чужие TASK и БЛОКИ 2–4.
- STANDARD/TEST CMD, параметры сети, реальные Workspace и секреты.

Git и GitHub, включая чтение через Git-инструменты, запрещены без отдельного USER GO.

При локальном расхождении обязательных исходников с опубликованной базой — STOP и точный отчёт о drift. Не откатывать пользовательские изменения.

## 3. Реализация

1. Воспроизвести исходный S2 FAIL полным guarded selector. Сохранить первичный RED и исходные хеши до исправления.
2. Изучить AST/import graph, используя фактические production entrypoints и runtime-зависимости.
3. Различить standalone OFFLINE helper, допустимо импортирующий чистую policy library, и производственный runtime, прямо либо косвенно получающий доступ к ней до S3b.
4. Исправить S2 oracle минимальным изменением, не ослабляя S1 inventory и не отключая fail-closed поведение.
5. Учитывать транзитивные импорты: production → ledger → policy нельзя автоматически считать безопасным.
6. Проверять прямые `import` и `from ... import`, aliases, новые модули и другие варианты, которые могут обходить oracle.
7. Сохранить полный S2 core MANIFEST из 73 тестов; новые adversarial quality tests разместить отдельно в task-local пакете, если это не требует изменения действующего MANIFEST.

Не применять blanket allowlist по имени `ultra_budget_ledger.py`, игнорирование UNKNOWN, широкие исключения модулей или отключение проверки production imports.

Способ реализации выбрать после самостоятельного анализа исходников; не считать предложенную гипотезу причиной без проверки.

## 4. Обязательные отрицательные проверки

Тесты на синтетических исходниках должны подтверждать:

- Прямой production import policy → RED.
- Транзитивный production → ledger → policy → RED.
- Импорт через `from ... import` и aliases → RED.
- Неизвестный или новый production consumer → RED либо явно обоснованный безопасный результат.
- Самостоятельное использование policy разрешённым OFFLINE ledger без production reachability → PASS.
- Изменение допустимой import closure, из-за которого policy становится достижима из production, → RED.
- Отключение или ослабление самого oracle должно обнаруживаться quality control.

Сохранять фактические результаты каждого negative oracle, а не только итоговые заявления PASS.

## 5. Регрессия и качество

Обязателен защищённый OFFLINE-прогон:

| Набор | Критерий |
|---|---|
| S2 core | 73 PASS, exit 0 |
| S1 exact guarded | 69 PASS, exit 0 |
| S1 extra reconciliation | 23 PASS |
| S3a ledger | 35 PASS |
| Новые негативные оракулы | Все ожидаемые RED обнаружены |
| Source/guard | 0 нарушений изоляции |

Использовать существующие штатные selectors и guard. При необходимости создать task-local wrapper только для фиксации результатов, не меняя содержание тестов и не перезаписывая evidence H24.

Не суммировать пересекающиеся прогоны в выдуманный счёт уникальных тестов.

Сохранить команды, Python/OS, exit-коды, counts, оригинальный RED, stdout/stderr, source SHA-256 и точную классификацию каждого отклонения.

**Запрещены:** real HTTP, OAuth, paid API, production storage writes, network access, real model inference, несанкционированные Git-операции.

## 6. Критерии завершения

Задача готова к сдаче, когда:

1. Причина исходного S2 FAIL документирована и подтверждена.
2. S2 73/73 PASS без ослабления isolation oracle.
3. Негативные сценарии подтверждают запрет раннего production import.
4. S1 и S3a сохраняют соответствующие PASS либо любое отклонение честно зафиксировано.
5. Изменения находятся строго в WRITE scope.
6. В report перечислены все OPEN, ограничения, риски и NEXT.
7. Manifest, исходные и итоговые evidence готовы к readback.

**Не считать результатом задачи:**

- Независимую приёмку S3a.
- Разрешение S3b.
- Реальную защиту HTTP-запросов бюджетным ledger.
- Принятие числовой политики Ordinary Chat.
- Готовность Stage6/Stage7 к live.

При недоказанной безопасности, повторяющемся FAIL или необходимости изменить production — STOP / PARTIAL или BLOCKED, без расширения полномочий.

## 7. Сдача

Создать:

`reports/CODEX-RT002-B2-S2-ISOLATION-ORACLE-REPAIR-001/`

Внутри сохранить `report.md`, `manifest.json`, необходимый task-local test/evidence пакет и `followups.json`.

После окончательной проверки выполнить штатный `tools/task_slot_rotate.py finish` с точным TASK ID, получить постоянный HISTORY ID и подтвердить readback.

Ожидаемое состояние после успешной механической сдачи:

- БЛОК 1 — WAITING.
- БЛОК 1.1 — сохранённая новая TASK.
- БЛОКИ 2–4 неизменны.
- Никакой автоматической независимой приёмки.

Публикацию одним атомарным нумерованным коммитом выполняет пользователь по действующему `DOC-COMMIT-01`, после проверки пакета. Исполнитель Git не использует.

**В итоговом сообщении Codex:** TASK ID, RESULT READY/PARTIAL/BLOCKED, изменённые файлы, исходный и итоговый S2, S1/S3a regression, quality negatives, NOT RUN, OPEN/NEXT, HISTORY ID и путь полного отчёта.
<!-- TASK-SNAPSHOT:END -->
