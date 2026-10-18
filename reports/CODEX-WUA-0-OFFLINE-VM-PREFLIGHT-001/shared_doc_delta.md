# DOC IMPACT / SHARED DOC DELTA — proposal for WEB_10 only

Фактически изменены только новая TASK report folder и собственная карточка Codex
(правило ротации + её БЛОКИ 1–3). Общие 18/19/34/000/05/06 не редактировались.
Фактический результат не является independent PASS.

## Документ 18

Прямого противоречия ротации в действующих нормах не установлено: DOC-TASK-BLOCK1-01
(строки 340/346), Per-model routing (362) и общий personal-card порядок (437)
сохраняют safe rotation. Противоречие прежде возникало между узким task write_scope
и этим порядком. Последнее прямое USER GO разрешает его **для этой TASK**.

Точное предлагаемое добавление WEB_10 в DOC-TASK-BLOCK1-01 после абзаца
«После фактической сдачи» (не применено агентом):

> При выдаче TASK явно включать безопасную ротацию собственной персональной
> карточки исполнителя в write_scope дополнительно к отчётной папке. Ротация
> обязательна и для PARTIAL/BLOCKED, когда разрешённый объём исполнения завершён
> и полный итоговый отчёт готов; это не означает независимую приёмку или закрытие
> незавершённого внешнего gate. Полная постановка и все AMENDMENT сохраняются
> в БЛОКЕ 2, factual result и причины блокировки — в БЛОКЕ 3; только после
> успешной проверки их сохранения БЛОК 1 переводится в ОЖИДАНИЕ НОВОЙ ЗАДАЧИ.
> При невозможности ротации указывать CARD ROTATION BLOCKED; предыдущая история
> сохраняется. Это право не распространяется на общие документы, чужие карточки
> или выполнение следующего этапа.

Это предложение уточняет scope и completed execution vs blocked external gate;
не изменяет статус незавершённой/приостановленной в середине исполнения TASK.

## 19 / 34 после независимого review

Предлагаемая factual запись: «CODEX-WUA-0-OFFLINE-VM-PREFLIGHT-001:
preflight PARTIAL; exact source archive, готовая VM/platform/media и backend-
specific isolation proof не предоставлены. Новый Windows/virtualization inventory,
cached ZIP→EXE identity, проект zero-NIC Hyper-V VM, I01–I12 contract,
16 native case contracts (NOT RUN), owner-only rollback и manual review сохранены.
Нет native/VM/network activation. User GO для own-card rotation исполнен с
сохранением исходной постановки/истории; независимая приёмка ожидается».

Для 000/05/06: только coordinator-reviewed factual status/NEXT, не автоматическое
DONE. Не расширять это на WUA production, LLM12, Claude или Web Alarm rollout.
Source pin `795e1fddf6741169f006caf8ba9430e4d22fca0f` получен из постановки;
локальный агент GitHub не сверял и ничего не публиковал.
