# История выполненных задач Claude

**Назначение:** короткая личная история задач, которые фактически выполнил Claude.

Связанный оперативный файл: [[000_Задачи Claude]]

## Правило

- Claude после выполнения обновляет свой оперативный handoff (`000_Задачи Claude.md`, БЛОКИ 2–3) и task-report, но **не закрывает здесь TASK самостоятельно**.
- Запись в эту историю добавляет независимый verifier/ChatGPT только после PASS и канонического `DONE / VERIFIED`.
- Писать максимально лаконично: без копирования постановки, длинных отчётов и технической хроники.
- Обычно достаточно: дата, TASK, что сделано, итог независимой проверки.
- Здесь хранится именно подтверждённая история работ Claude, а не общий журнал проекта.

## Формат

### YYYY-MM-DD — TASK-ID — краткое название
- **Сделано:** 1–2 коротких предложения.
- **Итог:** краткий подтверждённый результат.

---

## 2026-10-04 — CLAUDE-WA-004 — RC-2: Persistent Resolver + evidence revision binding
- **Сделано:** реализован persistent Resolver для ADOPT / RETRY / ROLLBACK / ABORT с binding к evidence fingerprint и operation revision; Recovery Report выводит persistent resolver outcomes и Resolver-authoritative NEXT SAFE ACTION. После первого review исправлены два blocker-а: ABORT больше не даёт RETRY-совет, STALE/REJECTED не теряются в report. Отчёт — `Alarm/ALARM_TASK_SESSION/TASK_CLAUDE-WA-004_RC2/rc2_report.md`.
- **Итог:** DONE / VERIFIED 2026-10-04 на commit 148 `0b7cb7d`; ChatGPT независимо подтвердил focused+concurrency 25/25, full Web Alarm 266/266, дополнительные concurrency 5/5, compileall/diff-check и ручные ABORT/STALE/REJECTED сценарии. Context Pack projection follow-up перенесён в RC-5/RC-6; RC-3 разрешён как следующий этап, но не запущен.

## 2026-10-04 — CLAUDE-WA-003 — RC-1: Durable Operation Contract
- **Сделано:** реализован Operation Contract v2: каноническая цель, pre-state и receipt, которые сервер читает сам, payload вне репозитория, fingerprint v2, revision. Legacy v1 читается без перезаписи; запись хранилища сериализована между процессами. Отчёт — `Alarm/ALARM_TASK_SESSION/TASK_CLAUDE-WA-003_RC1/rc1_report.md`.
- **Итог:** DONE / VERIFIED 2026-10-04; ChatGPT независимо повторил full regression 241/241, focused 44/44, 5 повторов multiprocess concurrency и fresh-process чтение живых legacy WA-3.7 records без изменения storage. RC-2 разрешён.

## 2026-10-04 — CLAUDE-WA-002 — RC-0: Baseline и normalization policy
- **Сделано:** снят baseline (197/197 OK), изучена реальность Git и переводов строк, измерены 3 из 4 метрик, сформулированы policy байтов / хешей и ограничения для снимков; отчёт — `Alarm/ALARM_TASK_SESSION/TASK_CLAUDE-WA-002_RC0/rc0_report.md`.
- **Итог:** DONE / VERIFIED 2026-10-04; ключевые baseline/manifest/Remote-call факты независимо воспроизведены ChatGPT. `.gitattributes` FOLLOW-UP отложен; RC-1 разрешён.

## 2026-10-03 — CLAUDE-WA-001 — Preflight плана EP-RT001-001
- **Сделано:** read-only сверка утверждённого RT-001 и плана `33` с кодом, тестами и storage WEB-02; отчёт — `Alarm/ALARM_TASK_SESSION/TASK_CLAUDE-WA-001/preflight_report.md`.
- **Итог:** DONE / VERIFIED 2026-10-04; preflight подтверждён независимо, D1–D3 приняты в корректировку planning layer; runtime не изменён.

## 2026-10-03 — CLAUDE-TEST-001 — Read-only анализ репозитория
- **Сделано:** Claude изучил реальный `ag_llm`, описал архитектуру, ключевые точки входа, зависимости и несколько рискованных мест без изменения файлов.
- **Итог:** задача завершена; пользователь подтвердил выполнение.
