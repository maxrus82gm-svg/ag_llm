# Задачи Claude

**Назначение:** отдельный оперативный handoff для задач, которые передаются Claude Desktop / Claude Code в проекте `ag_llm`.

Основной проектный handoff: [[000_Задачи для агента]]
Персональная история выполненных Claude TASK: [[001_История выполненных задач Claude]]

## Правила

- Здесь фиксируются только конкретные задачи, делегированные Claude.
- Этот файл **не заменяет** `000_Задачи для агента.md`, `05_Реестр задач.md`, `06_Журнал выполнения и отчёты.md` и профильные документы проекта.
- Если Claude выполняет значимое изменение проекта, итог после проверки должен быть отражён и в канонической документации проекта по обычным правилам.
- До начала mutation-задачи явно указывать scope, запрещённые действия и критерии проверки.
- Секреты, токены, cookies, Organization ID и платёжные данные сюда не записываются.
- Технические наблюдения по моделям, лимитам и сети вести в `27_Claude.md`.
- БЛОК 2 — только быстрый указатель на последнюю завершённую Claude TASK, а не единственное хранилище истории.
- До замены содержимого БЛОКА 2 завершённая TASK обязана получить постоянную append-only запись в `06_Журнал выполнения и отчёты.md`, краткую запись в `001_История выполненных задач Claude.md`; для профильной подсистемы дополнительно обновляется её профильный журнал (например, Web Alarm → `25`).
- Полная постановка TASK может дополнительно фиксироваться в обычном Chat как человеческий резерв/след обсуждения, но каноническим источником остаются проектные документы.
- После завершения собственной TASK Claude сам готовит её documentation closeout: обновляет этот `000`, персональную историю `001`, постоянный журнал `06`, затронутые профильные документы и реестры только по фактически подтверждённому результату. До независимой проверки не объявляет неподтверждённое `DONE`.

---
# БЛОК 1 — ТЕКУЩАЯ ЗАДАЧА
---

**Статус:** READY / NOT STARTED.
**TASK:** CLAUDE-WA-003 — RC-1: Durable Operation Contract + backward compatibility.
**Дата постановки:** 2026-10-04.
**Модель:** Claude Opus 5.5.

**Источник:** RC-0 / CLAUDE-WA-002 независимо проверен ChatGPT и закрыт DONE / VERIFIED. Каноническая byte/hash policy перенесена в `23/24`: authority = физические bytes + размер; Git normalization — внешний writer. `.gitattributes` FOLLOW-UP отложен и RC-1 не блокирует.

**Цель:** сделать Operation Contract самодостаточным, durable и restart-safe до появления Resolver/Executor: новая операция должна после нового process/Chat восстанавливаться с точным target, pre/post contract, payload/ref, fingerprint, provenance и revision без внешней памяти исполнителя.

**Обязательный контекст:**
1. `08_Старт.md`, `000_Задачи для агента.md`, этот файл.
2. `23_Архитектура Web Alarm Workspace.md` — инварианты 23–33.
3. `24_План реализации Web Alarm Workspace.md` — RC-1 exit proof и границы.
4. `25_Журнал Web Alarm Workspace - выполненные задачи и аудит.md`.
5. Отчёты `TASK_CLAUDE-WA-001/preflight_report.md` и `TASK_CLAUDE-WA-002_RC0/rc0_report.md` — evidence/rationale, не отдельный authority.

**Что реализовать:**
- отдельную version/revision operation-contract схему; не поднимать глобальную `SCHEMA_VERSION` всех хранилищ;
- backward-compatible чтение существующих legacy OperationRecord без обязательной перезаписи; legacy record не должен внезапно получить право на unsafe replay;
- единый canonical target identity для Windows path/case/spelling, используемый Operation Contract последовательно;
- durable expected pre-state и expected post-state для файлового target по physical bytes: exists/size/SHA-256; EOL/BOM — только diagnostic metadata;
- durable mutation payload или immutable payload reference в machine-local WEB-02 storage вне repo/vault; hash+size verification, explicit scope/secret/size/retention checks;
- стабильный request fingerprint/idempotency identity для одного logical operation;
- provenance/agent identity, contract/schema version, timestamps/revision и persistent result/receipt fields, достаточные для следующего RC-2;
- минимальную межпроцессную сериализацию записи Operation Store/revision, чтобы два process не теряли revision/record. Это защита storage integrity, **не** RC-3 conflict gate по physical target;
- fresh-process reopen: новый process без памяти старого исполнителя читает тот же operation contract/payload identity/revision.

**Инженерная граница:**
- не раздувать `server.py`: новую contract/payload/locking логику держать в узких модулях с одной ответственностью; server integration — только минимальная, если реально нужна для тестируемого контракта;
- не реализовывать Resolver decisions/ADOPT/ROLLBACK/RETRY execution — это RC-2;
- не реализовывать canonical-target conflict admission / mutation CAS / ownership reservation — это RC-3;
- не выполнять физическую project mutation из operation contract — authoritative executor только WA4-E;
- не менять UI;
- не менять `.gitattributes` и не нормализовать line endings;
- не делать commit / push.

**Совместимость и безопасность:**
- текущие 2 legacy operation records должны оставаться читаемыми после fresh process;
- новый contract не должен требовать миграции всех 8 storage schemas;
- payload/snapshot content не писать в events/reports/logs — только metadata/hash/size/path-id;
- secret-like target/payload scope fail-closed по policy RC-0;
- при неизвестной/повреждённой версии contract или payload hash mismatch — fail-closed, без угадывания.

**Проверка:**
1. focused tests для operation contract, legacy read, payload integrity, canonical identity, revision serialization;
2. отдельный multiprocess/race test именно на storage integrity: concurrent writers не теряют record/revision;
3. fresh-process reopen test;
4. negative tests: unknown contract version, corrupted payload, forbidden secret scope, duplicate fingerprint mismatch;
5. полный Web Alarm regression;
6. `python -B -m compileall -q web_alarm`;
7. `git diff --check`;
8. подтвердить, что `.gitattributes`, UI и tracked project targets вне scope не менялись.

**Критерий RC-1 PASS:** persisted operation содержит достаточный durable contract; legacy state читается безопасно; payload/ref проверяем; canonical target стабилен; concurrent Operation Store writes не теряются; fresh process восстанавливает тот же contract/revision; physical mutation ещё отсутствует.

**Closeout:** отчёт сохранить в `Alarm/ALARM_TASK_SESSION/TASK_CLAUDE-WA-003_RC1/`; обновить `000_Задачи Claude`, `001`, `06`, `25` только по фактическому результату. До независимой проверки статус только `RESULT READY / AWAITING INDEPENDENT VERIFICATION`.

**NEXT SAFE ACTION сейчас:** выполнить только CLAUDE-WA-003 / RC-1. RC-2 не начинать.

---
# БЛОК 2 — ПОСЛЕДНЯЯ ЗАВЕРШЁННАЯ ЗАДАЧА
---

**TASK:** CLAUDE-WA-002 — RC-0: Baseline и normalization policy.
**Статус:** DONE / VERIFIED — 2026-10-04.
**Модель:** Claude Opus 5.5.

**Результат:** независимая проверка ChatGPT подтвердила RC-0. Повторный Web Alarm regression на текущем HEAD `8029a69` — 197/197 PASS. Manifest-аудит воспроизведён точно: 121 записи, 115 текущих byte-hash совпадений, 6 missing snapshots; simulated fresh checkout при `core.autocrlf=true` сохраняет только 1 hash. Remote-call metrics также воспроизведены: WA-3.6 = 375/32 = 11,7; WA-3.7 = 126/18 = 7,0.

**Принято:** file-state authority = physical bytes SHA-256 + size; Git/EOL normalization не authority; normalized-EOL comparison только diagnostic/manual review. `.gitattributes` не меняется сейчас — отдельный FOLLOW-UP отложен и RC-1 не блокирует. Snapshot/payload constraints перенесены в каноническую архитектуру.

**Отчёт:** `Alarm/ALARM_TASK_SESSION/TASK_CLAUDE-WA-002_RC0/rc0_report.md`. Постоянная история остаётся в `001`, `06`, `25`.

## Правило круговорота

1. Новую активную задачу записывать в БЛОК 1 до исполнения; при необходимости её постановка дополнительно фиксируется в обычном Chat.
2. После фактического завершения Claude готовит closeout, но статус `DONE` считается каноническим только после требуемой независимой проверки.
3. До ротации БЛОКА 2 сохранить постоянную append-only запись TASK в `06_Журнал выполнения и отчёты.md` и нужном профильном журнале/реестре.
4. Только после сохранения permanent history перенести краткий итог последней завершённой TASK в БЛОК 2 и очистить БЛОК 1 под следующую задачу.
5. Долговременные технические наблюдения и метрики переносить в `27_Claude.md`.
6. Значимые изменения самого проекта синхронизировать с канонической проектной документацией строго по фактически подтверждённому результату.
7. БЛОК 2 никогда не используется как единственное доказательство существования или содержания старой TASK.
