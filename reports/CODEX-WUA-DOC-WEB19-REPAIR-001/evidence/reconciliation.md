# Противоречия, источники и сохранность — 01.11.2026

Основание: текущий БЛОК 1 `CODEX-WUA-DOC-WEB19-REPAIR-001`; это ремонт после №482, не продолжение оптимизации Astra. Номера публикаций и Git SHA взяты из пользовательской постановки и локальных документов, без обращения к Git. Состояние локальных файлов соответствует описанным признакам базы; независимо удостоверить Git object/dirty state запрещено. Подтверждены два engineering SHA №479 (см. source_pins.json), записи №481/482 и отсутствие другой активной TASK Claude. Несохранённые редакторские изменения не наблюдались.

## Таблица дефектов и решений

| Дефект до ремонта | Источник истины | Применённая дельта |
| --- | --- | --- |
| №03: `# 21. MESSAGE CONTEXT STATE## 20.2...`, дополнения 479/475 в обратном порядке внутри State | Исходные полные абзацы; WEB18 review 475/479 | §20.1 → §20.2 → самостоятельный §21; оба текста сохранены, добавлен адрес последующей focused проверки WEB19 |
| №05: FOLLOWUP разорван пустыми строками/пояснением, фраза `successor_task_id = UNASSIGNED` разделена | Исходные 7 FOLLOWUP-строк, DOC-CONTEXT-OPS-01/OPS-FOLLOWUP | Одна таблица 6 колонок/7 строк; все строки, ID, статусы и successor сохранены дословно; пояснение собрано после таблицы |
| №05: заголовок №473 непосредственно перед записью №479 | REG-WEB18-S2-REVISE/REPAIR/HARDEN и REG-WEB19-S2-INDEP-WINDOWS | Порядок 482 → WEB19/481 → 479 → 475 → 473; каждый заголовок над собственной записью, factual тексты не переписаны |
| №06: три склеенных заголовка №473/475/479 над единственным событием №479; №482 вставлен во вводную часть | EVT-WEB18-S2-REVISE/REPAIR-PASS/HARDEN-PASS; EVT-WEB19-ASTRA-SLOT | Вводная часть завершена перед №482; каждый заголовок непосредственно перед своим event_id. Все event payloads и остальная история сохранены |
| №34: F-01 показан текущим неисправленным, NEXT повторно назначает уже закрытый REPLACE-HARDEN | WEB18 repair/harden review, WEB19 focused Windows report; №05 FOLLOWUP | F-01 CLOSED по 475, REPLACE-HARDEN CLOSED по 479 в принятой границе; staging OPEN/UNASSIGNED, P9 — приоритет рассмотрения, Tk P1–P6 OPEN; Stage3/live/paid HOLD |
| №34/40: Astra WAITING смешан с новой задачей Codex, Stage1/Stage2 старые ограничения читаются как текущее запрещение уже выполненной работы | №482/№001 Codex; текущий БЛОК 1; карточка Claude | Astra архивирована административно, остаточные проверки OPEN; новая работа Codex документационная, Core не назначен. После сдачи слот читается по карточке, его перенос не становится independent PASS |
| №37: техническое дополнение №479 вклеено в заголовок Stage3, repair 475 находится в Stage3 | Исторические дополнения 475/479; утверждённый Stage3 contract | Дополнения 475/479 размещены в Stage2; восстановлен заголовок Stage3, весь его архитектурный текст сохранён дословно |
| №40: blanket `independent runtime NOT RUN` скрывает последующий WEB19 focused Windows run | reports/CHATGPT-WEB19-S2-INDEPENDENT-WINDOWS-20261101.md; WEB18 review | Различены WEB18 source+author-evidence и поздний WEB19 focused execution. Full independent regression/CI NOT RUN сохранён |
| №40: внутренний Wiki-указатель исчез, хотя правило о единственной связи осталось | Проверенный preservation snapshot 40 от 27.10 и его manifest, текущая условная авторизация БЛОКА 1 | Восстановлено ровно прежнее ребро `№40 → 000_Задачи для агента` с исходным alias; существующие Wiki/Markdown targets и конфигурация графа сохранены. Live Graph NOT RUN |

## Адресная сверка девяти исторических случаев

Полные адресованные выдержки, hashes файлов-владельцев и диапазоны до ремонта: history_sources.json. Это самостоятельная локальная сверка Codex документации и provenance; инженерные проверки повторно не запускались, новый independent verifier verdict не выпускается.

| № | TASK / источник | Сохраняемый verdict и ограничения | №05 / №06 |
| --- | --- | --- | --- |
| 457 | CLAUDE-WUA-EVM-COMPACT-LAYOUT-001; №001 Claude → 2026-10-29; собственный report/manifest/handoff | Исторический REVISE / PRODUCT NOT ACCEPTED. Поздний USER ACCEPTED successor не переписывает его; GUI/regression gaps остаются | WEB16 Compact EVM №457; EVT-WEB16-EVM-COMPACT-REVISE-20261029; все четыре FOLLOWUP-EVM-457 сохранены |
| 461 | CLAUDE-DOC-TASK-SLOT-ROTATION-001; №001 Claude → 2026-10-29; собственный пакет | Автор 43/43, 24/24 mutants; независимый runtime/Obsidian NOT RUN, concurrent/unsaved edit gap OPEN | WEB16 Compact EVM №457 и ротация №461; EVT-WEB16-TASK-SLOT-20261029 |
| 464 | CLAUDE-WUA-EVM-INTERACTION-DND-001; №001 Claude → 2026-10-30; собственный пакет | USER ACCEPTED interaction UX; DOC ITERATION CLOSED. Независимые/platform gaps не закрываются | REG-WEB17-EVM-DND-20261030; EVT-WEB17-EVM-DND-ACCEPT-20261030 |
| 467 | CLAUDE-WUA-EVM-PINNED-MULTIWINDOW-001; №001 Claude → 2026-10-31; собственный пакет | USER ACCEPTED pinned windows UX; идея FUTURE реализована. Full regression/platform matrix не объявлены проверенными | REG-WEB17-EVM-PINS-20261031; EVT-WEB17-EVM-PINS-ACCEPT-20261031 |
| 473 | CLAUDE-WUA-CHAT-S2-SHARED-STORAGE-001; №001 Claude → 2026-10-31; WEB18 S2 review | REVISE / F-01 source defect, historical verdict неизменён. Его F-01 continuation отдельно принят №475 | REG-WEB18-S2-REVISE-20261031; EVT-WEB18-S2-REVISE-20261031 |
| 475 | CLAUDE-WUA-CHAT-S2-CONTEXT-PATH-REPAIR-001; №001 Claude → 2026-10-31; WEB18 repair review | PASS / SOURCE+AUTHOR-EVIDENCE только F-01. Первый run 1075 PASS/1 ERROR/2 SKIP, run2 1076 PASS/2 SKIP; старое неверное 1077 не принимается за факт. Автор mutants 8/9, R01c SURVIVED; independent runtime NOT RUN на дату | REG-WEB18-S2-REPAIR-20261031; EVT-WEB18-S2-REPAIR-PASS-20261031 |
| 479 | CLAUDE-WUA-CHAT-S2-REPLACE-HARDEN-001; №001 Claude → 2026-11-01; WEB18 harden review | BOUNDED PASS / DOC ITERATION CLOSED. Автор focused 161 PASS/5 SKIP, full run2 1076 PASS/2 SKIP, mutants 9/9; первый ERROR и 8/9 mutants не скрыты. Staging, same-user post-final-check TOCTOU, P9 и readers остаются | REG-WEB18-S2-HARDEN-20261101; EVT-WEB18-S2-HARDEN-PASS-20261101 |
| 481 | WEB19 independent focused Windows verification по №479; собственный локальный report и событие №06 | Python 3.12/3.13 каждый 68 run = 64 PASS/4 SKIP; subset 17 = 16 PASS/1 SKIP; reviewer probes 4/4. Full regression/CI/GUI/paid/live NOT RUN. Отдельная №001 запись не выдумана | REG-WEB19-S2-INDEP-WINDOWS-20261101; EVT-WEB19-S2-INDEP-WINDOWS-20261101 |
| 482 | ASTRA-DOC-CONTEXT-OPTIMIZATION-001; №001 Codex → 2026-11-01 и постоянный handoff_task.md | USER-DIRECTED ADMINISTRATIVE SLOT RELEASE, не PASS миграции. Старая TASK сохранена; semantic/graph/cold-start PARTIAL/OPEN, RISK-DOC-CURRENT-001 OPEN | REG-WEB19-ASTRA-SLOT-20261101; EVT-WEB19-ASTRA-SLOT-20261101 |

## Граница ремонта

№05/06 продолжают хранить исторические утверждения NOT RUN / прежние successor / состояние слотов на дату события. Их не заменяли новыми итогами задним числом. Текущую картину задают №34/40 и поздние отдельные события. Персональные №001, карточка Claude, №18/41 и пакеты Astra неизменны. Сохраняемые архивные главы №34 не перечитываются на обычном старте.

SHARED DOC DELTA / OUT OF SCOPE: вводный абзац карточки Codex говорит, что БЛОК 1 освобождён 01.11, хотя ниже уже назначена новая TASK. На следующем closeout координатору уточнить датированную формулировку; рабочие слоты ремонтируются только штатным механизмом. Исторические записи №001, включая ссылки на прежние версии БЛОКА 1.1, сохраняют смысл на дату события и не переписываются как текущий статус.
