# H33 — независимая Windows-приёмка HTTP GigaChat MockTransport

**Дата:** 13.11.2026 · **Независимый проверяющий:** ChatGPT / WEB29.  
**TASK:** `CODEX-WUA-CHAT-GIGACHAT-TRANSPORT-OFFLINE-GATE-001` · **HISTORY:** `H-CODEX-000033`.  
**Вердикт:** **PASS / BOUNDED INDEPENDENT WINDOWS OFFLINE; H33 DOC CLOSED только в узком synthetic/mock HTTP scope.** Полный S3b/Stage6 и реальный GigaChat/OAuth/paid остаются **HOLD**.

## Источник и проверка публикации

Авторский пакет `reports/CODEX-WUA-CHAT-GIGACHAT-TRANSPORT-OFFLINE-GATE-001` опубликован пользователем в `main@56e7f33c351624de94db77e080767930b8cf3d38`, рабочий коммит №592. Отдельный CI-only коммит №593 `397040862b63fb23f7f3b51e1e1e1d793fee5179` добавил лишь `.github/workflows/gpt-web29-h33-independent.yml`; продуктовый код после №592 не менялся. `task_record.json` имеет `H-CODEX-000033`, БЛОК 1 WAITING, 1.1 хранит дословную сданную H33. SHA256 исходной assignment совпал с GitHub. Авторский `report.md` на Windows хешировался с **CRLF**: после восстановления CRLF из отданного коннектором LF-текста его SHA-256 совпал с `task_record.sources.report.sha256`. Исходный файл не переписывали и digest не подменяли.

Принятые инварианты: сервер формирует immutable final bytes, S2 Ordinary + durable S3a reserve/SENT связывают точный wire/endpoint/Turn, транспорт пересылает `content=wire` без второго JSON serializer, ответ/ошибка/UNKNOWN и usage проходят терминальный Turn/RAW/reopen. Реализация `ordinary_gigachat_transport.py` принимает только `OfflineHTTPFixture` и создаёт **`httpx.MockTransport`**, а не сетевой client factory; `real_available=false`. Browser/config/env не дают server-side допуска к реальному запросу. Это защита штатных путей, а не sandbox против злонамеренного кода Python с полномочиями процесса.

## GitHub-hosted Windows: действительно запущенные проверки

[Actions run **43478748679**](https://github.com/maxrus82gm-svg/ag_llm/actions/runs/43478748679) = **SUCCESS**, job 132069412034; checkout на `windows-latest` через sparse paths, изолированный Windows TEMP `C:\h33`, Python 3.12/Node; artifact `h33-independent-windows` **ID 14062849789**, 29 файлов. Log и case/result/guard evidence сохранены. Никакие реальные GigaChat credentials, OAuth, API, биллинг или production Workspace не использовались.

| Набор | Результат |
| --- | --- |
| H33 mock HTTP exact-wire, authority, errors, recovery | **18 PASS + 36 subtests**, неожиданных guard0 |
| H29/H31/H32/common core/S3a/Run Store регрессия | **236 PASS + 220 subtests**, неожиданных guard0 |
| S2 standalone (не pytest discovery) | **73 PASS**, exit0 |
| H25/H33 isolation / quality | **52 PASS + 5 subtests**, guard0 |
| Node.js UI | **57 PASS**, 0 FAIL, 0 SKIP |
| Ослабление S2 и финальных HTTP bytes | **2 expected RED**, 0 ошибок, без изменения источников |
| S1 historical pinned RAW | **NOT RUN** в CI: RAW нет в checkout; авторские 69 PASS — отдельное evidence |

Данные пересекающихся suites **не суммируются**. Синтетический HTTP trace автора: **2 Workspace, 4 чата, 4 Mock POST, replay +0**; независимо повторены H33 tests, но авторский trace не выдаётся за отдельное сетевое измерение. Общий `Web Alarm smoke` ранее завершился FAILURE до тестов из-за MAX_PATH при полном Git checkout: [run 43477326561](https://github.com/maxrus82gm-svg/ag_llm/actions/runs/43477326561). Отдельный sparse workflow №593 успешно устранил препятствие для **независимых H33 тестов**; старый общий workflow этим не исправлялся.

## Границы, безопасность и обязательный NEXT

**NOT RUN / NOT VERIFIED:** исторический S1 R031/R026 RAW на GitHub; физический CMD/Chrome/F5/чистая Windows и локальный backup cleanup; реальные OAuth/endpoint/TLS/proxy; коммерческие provider caps, reasoning/usage semantics, billing/calibration; старый audit adoption/engine migration; ledger capacity/power-loss/fencing и RAW-wire retention/privacy; полноценный pre-send guard всех семи legacy LLM POST sites, S3c/S9/S13a. REAL transport factory не реализован: отдельное доверенное server authority и проверенный provider contract ещё не утверждены.

№20 §5а остаётся каноном predecessor gates, №37 §3а — маршрут CHAT FIRST, все `S3A-ADOPTION-UPGRADE`, `S3A-CAPACITY`, `S3A-DURABILITY-FENCING`, `S3A-RAW-WIRE-RETENTION`, `S3B-S3C-S9`, `STATIC-DYNAMIC-COVERAGE` OPEN; в №05 сохраняются `FOLLOWUP-WUA-H32-S1-RAW-CI-001`, `FOLLOWUP-WUA-H32-REAL-CONTRACT-001`, `FOLLOWUP-WUA-H31-PHYSICAL-SMOKE-001`, добавляется `FOLLOWUP-WUA-H33-SERVER-REAL-AUTHORITY-001`. Не строить отложенный совокупный бюджет Workspace и не считать preference 250k/10k/20k подтверждёнными caps.

**СЛЕДУЮЩИЙ ШАГ:** один полный документальный closeout в GPT → пользователь принимает GPT→main. Затем отдельно обсудить технические REAL-provider safety gates, ограниченный физический Windows GUI smoke и конкретное новое поручение Codex. Первый настоящий GigaChat вызов — только после полного согласования применимых gates и отдельного USER GO по endpoint/model/attempts/stop limits. Никакого автоматического LIVE или назначения новой задачи. Авторские исходники и TEMP backup не удалены. Полный прежний БЛОК 4 и текущие шапки №34/№40 архивированы в `reports/CHATGPT-WEB29-H33-REVIEW-20261113/prior_closeout_snapshot.md`, graph.json/Obsidian не затронуты.
