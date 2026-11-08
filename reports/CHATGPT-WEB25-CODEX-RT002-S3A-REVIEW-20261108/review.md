# WEB25 — H-CODEX-000023 / RT-002 B2 S3a — independent GitHub review, 08.11.2026

**TASK:** `CODEX-RT002-B2-S3A-DURABLE-LEDGER-001`  
**Pinned publication:** `main@53d7ce91cae37b9eee1fb6fa5f417c0cc669f8b4`, working commit №539 (parent №538).  
**Вердикт:** **PARTIAL / BOUNDED SOURCE+AUTHOR-EVIDENCE ACCEPTED** для нового OFFLINE ledger S3a. **НЕ** S3a independently executed/ACCEPTED predecessor для S3b; **НЕ** Stage6 DONE, S3b/real-provider GO. H23 документальная итерация закрыта, все отрицательные результаты сохранены.

## Независимые действия WEB25

- Проверены GitHub HEAD/commit №539, область изменений, `H-CODEX-000023`, `finish ROTATED / exit0`, БЛОК1 WAITING / БЛОК1.1 H23. На уровне рабочих исходников появились лишь `ultra_budget_ledger.py` и `test_rt002_s3a_ledger.py`: `run_store.py`, `ultra_budget_policy.py`, S1/S2, server/UI/launchers не изменялись. В №539 также попал динамический `.obsidian/workspace.json` вне инженерного scope — не считать изменением Codex и не редактировать из review.
- Сверены SHA-256/размеры 16 адресных GitHub артефактов: оба source файла, их финальные snapshots, report, handoff, ordinary-chat proposal, followups и key evidence. 11 точных совпадений с опубликованным LF, 5 JSON evidence имеют **только Git CRLF→LF** преобразование; реконструированные CRLF-байты подтверждают все пять исходных SHA/size. По всем 99 файлам manifest независимого byte audit не проводилось; 16/16 focused checks, не 99/99.
- Изучены source paths `BudgetLedger.initialize/reserve/mark_sent/mark_not_sent/terminal/recover`, event replay, S2 `AttemptRecord`/policy, общий `run_store._index_lock/_save_index`, 35 тестов, author stdout/JSON/XML и контролируемые snapshots от RESERVED до ANOMALY. Нет нового production import/adapter/physical provider send.
- **Author evidence:** S3a 35 PASS; Run Store 51 PASS; S2 guarded 73 PASS, exit0, guard0; negative mutation controls 3/3 expected FAIL; S1 guarded 69: **67 PASS, 2 FAIL**, exit1, evidence/guard violations 0. Сохранены первые S3a RED 13/29 и 25/29, впоследствии исправлены fixture assumptions. Это **авторские** результаты; ChatGPT в этой проверке **не запускал** Python/Windows/CI, независимое runtime = **NOT RUN**.

## Подтверждённое ограничение S1 (не скрывать)

`test_production_send_sites_match_inventory_with_multiplicity` нашёл неизвестные `web_alarm/launcher.py` import/`urllib.urlopen` и `ordinary_chat_service.py` transport.send; `test_every_endpoint_constant_read_is_an_inventoried_send_url` нашёл хранящиеся в `web_alarm/model_cards.py` буквальные OAuth/LLM URL. Все три файла существуют в текущем коде. По исходникам launcher `_get` обслуживает UI health/loopback, model_cards задаёт metadata без отправки, ordinary_chat_service принимает инъектируемый transport, который в будущем может быть реальным сетевым адаптером. **Нельзя** единым UNKNOWN-exemption маскировать физические отправки. Нужен отдельный узкий S1 reconciliation: доказать classification/callers/endpoint use с негативными тестами. S1 = FAIL и S3b physical-route coverage **BLOCKED**, независимо от успеха S3a.

## Положительные границы S3a и отдельные риски

Источник поддерживает общую авторитетную Workspace-index запись под существующим writer lock, не отдельный Web ledger, атомарный check→reserve, event revision/readback, rehydrate S2, conservative SENT/UNKNOWN, original attempt IDs, replay and late usage. Marker-first enrollment и corrupted/missing store отказывают, но не являются полным crash/power-loss proof. `NOT_SENT` сейчас принимает **заявление** `PROVEN_PRE_SEND_NOT_SENT` с текстовым reference: доказательство того, что физическая отправка не происходила, должен проверять доверенный S3b, иначе возможен ложный release. Обязательно проверить его contract перед integration.

**NEW reviewer risk — RAW wire retention:** `wire_utf8` хранит полное сериализованное тело запроса, включая потенциально чувствительный промпт/историю, в общем Run Store `index.json` и его generations. При S3b production нужны privacy/retention, read-scope, backups, размер/перезапись и отсутствие выдачи тела из диагностических API. Нельзя считать hash/checksum защитой от владельца, переписавшего оба файла; автор открыто отмечает full rollback и cloned-root owner fencing как непроверенные.

**OPEN H23 author:** S1 inventory; Ordinary Chat route/scope/profile и числовые параметры требуют USER approval; historical ledger adoption/migration и policy-engine upgrade без обнуления; 4096-events cap без compaction; power-loss/directory durability, hostile TOCTOU, cross-machine fencing; S3b/S3c/S9 не реализованы. `FOLLOWUP-WUA-S5-` остатки сохраняются. Test guard и safety suites не дают разрешения на paid/live.

## Решение и NEXT

**DOC CLOSEOUT H23: PARTIAL / BOUNDED.** Не отказывать в наблюдаемой OFFLINE работе S3a из-за постороннего S1 drift, но не выдавать bounded source-review за обязательный `independently ACCEPTED S3a` по №20 §5а. Перед S3b нужна адресная S1 inventory repair (предложение `amendment_request_s1.md`; пока не назначено), отдельный независимый guarded runtime S3a с точным SHA и USER решение о S2 Ordinary Chat policy, плюс решение по безопасной интеграции `NOT_SENT`/RAW wire. Перед Stage7 отдельно принять всю необходимую B2 цепочку и разрешить конкретные live/paid calls с бюджетом. **Никаких новых TASK или live-вызовов этим review не назначено.**

**Sources:** `reports/CODEX-RT002-B2-S3A-DURABLE-LEDGER-001/{task_record.json,report.md,manifest.json,followups.json,amendment_request_s1.md,evidence/}`, `Документация/20 §5а`, №21, №37, №36.3.
