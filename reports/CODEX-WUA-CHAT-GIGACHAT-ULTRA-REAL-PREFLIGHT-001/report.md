# AUTHOR RESULT READY — PARTIAL/BLOCKED (REAL HOLD)

**TASK ID:** `CODEX-WUA-CHAT-GIGACHAT-ULTRA-REAL-PREFLIGHT-001`  
**Автор:** Codex 007, 15.11.2026, Windows / STRICT OFFLINE engineering.  
**HISTORY ID:** выдаёт штатный finish; окончательные номер/адрес — task_record.json и evidence/finish.json.  
**Итог:** проверяемая закрытая подготовка Ultra сохранена; рабочий production REAL factory и LIVE **BLOCKED**. Авторская сдача ожидает независимой проверки, REAL READY не заявляется.

## Реализовано

Изменены только `gigachat_transport.py`, `ordinary_gigachat_transport.py`; добавлен адресный `test_web_alarm_gigachat_ultra_preflight.py`. Остальные изменения — этот пакет и штатные артефакты finish. Shared Turn/Run Store/schema/HTTP router/UI/CI/model registry/budget policy не менялись.

`gigachat_transport.real_preflight('gigachat_ultra')` проверяет registry ID/provider binding и возвращает изолированный factual snapshot: PARTIAL, неподтверждённый account, отсутствие исполнимых context/output caps и перечень HOLD. Неподдерживаемая модель/подмена registry дают безопасный код без отражения входного текста. Snapshot не является authority и не принимается как конфигурация отправки. Данные пользователя 250000/10000/20000 не используются как caps.

`ordinary_gigachat_transport.create_real_transport(model_id)` — закрытая серверная точка подготовки. Первым действием вызывает существующий unconditional `require_real_authority`, до contract/cache/env/token/HTTP. Даже при тестовом аварийном возврате этого gate функция заканчивается `real_transport_not_implemented`, client не создаётся. Нет параметра authority, env/URL/browser switch, второго OAuth или cache. Штатный STANDARD продолжает единственную Pro и прежний HOLD; Ultra не включена в физические STANDARD-запросы.

Существующий byte transport `GigaChatTransport` полностью сохранён по AST, как и все общие S1/S2/admission/Turn gates. Положительный Ultra сценарий использует **этот же** Ordinary Core → Turn → immutable bytes → durable reserve/SENT → httpx.MockTransport → terminal → RAW/history. Одна synthetic попытка, reasoning subset без второго начисления, повтор/reopen без второй отправки. Никакого нового Chat Core, ledger или параллельного storage нет. Подробности инвентаризации **до правок** — [REUSE CHECK](reuse-check.md).

## Объективные блокировки REAL

1. Публичные [документы Ultra](https://developers.sber.ru/docs/ru/gigachat/models/gigachat-3-ultra) подтверждают `GigaChat-3-Ultra` и категорию Freemium физлиц; конкретные account/scope/entitlement **UNVERIFIED**. Ни один account endpoint не вызван.
2. Контекст публично описан как «128 тыс.», но exact executable combined/input/output/reasoning bounds и calibration **не подтверждены**. В runtime они не придуманы. Полная датированная таблица — [provider-contract.md](provider-contract.md).
3. **Shared accounting contract BLOCKED:** публичная [OpenAPI](https://developers.sber.ru/docs/files/openapi/gigachat/api.yml) описывает total после вычета cached; `_usage` и `ultra_budget_policy.validate_usage` требуют prompt+completion и имеют своё uncached assumption. Синтетический `7/5/cached2/total10` по прямому прочтению схемы даёт expected RED. Это выявленная несовместимость/неопределённость mapping, **не полученный ответ реального Ultra**. Нельзя нормализовать её скрытно или менять sealed ledger/policy в этой TASK. Реальная формула и migration требуют отдельного shared-scope решения и проверки.
4. Response model/version binding, единственный account stream, production enrollment/ownership/recovery, TLS/proxy/redaction и безопасная адаптация старого OAuth/cache/expires_at остаются OPEN. Старый OAuth за HOLD не признан готовым путём. Реальный клиент и выдача server authority не реализованы.
5. Полный S3b/S3c/S9/S13a и применимость S4/S5/C1/C2 к ordinary MVP не закрываются этими авторскими тестами. Координатору требуется адресная сверка №20 §5а, независимый Windows OFFLINE review и отдельный USER GO; см. [real-readiness.md](real-readiness.md).

## База, слот и сохранность

Штатный check до правок: OK, точный TASK ID, отсутствие конфликта БЛОКА 1, предыдущая 1.1 — H-CODEX-000036. Слот занят именно назначенной задачей, не чужой/ожидающей TASK. Прежняя карточка сохранена byte snapshot в before; check/readback — evidence.

Ориентир assignment `main@02e219f5fcecc046a42a5a34749ee4bb3e4ac067`. **Точный Git HEAD/branch/remote NOT VERIFIED** вследствие прямого запрета Git/GitHub/.git. Вместо запрещённого чтения проверены локальные продуктовые fingerprints опубликованных H35/H36: **17/17 exact match**, конфликтов в проверенной базе нет (evidence/base_fingerprints.json). Это подтверждение файлов, не утверждение о remote HEAD. Необязательный Git-вопрос владельцу: подтвердить соответствие указанному SHA перед публикацией/independent review; инженерная подготовка основана на сохранённых local hashes.

До изменений сохранены разрешённые source copies и fingerprints **299** защищённых файлов; финальная проверка — evidence/preservation_final.json. При finish персональная карточка изменяется только скриптом; БЛОКИ 2–4 и прежний H36 snapshot проверяются отдельно. Рабочие Workspace/история/права/секреты не использовались. Start_WebAlarm_Standard.cmd, Start_WebAlarm_Test.cmd, launcher configs и пустой исторический BAT сохранены; возврат единого BAT не требуется по актуальному DOC-WUA-LAUNCH-01. Физические CMD/browser NOT RUN, профиль проверен исходниками и имеющимися isolated Python tests.

## Точные авторские испытания

Python 3.12.10, httpx 0.28.1, pytest 9.1.1 (subtests встроены), Node v22.20.0. Все инженерные Python-прогоны — ранний guard до production imports; real credentials/DNS/external socket/Git/чужие live roots/non-Python process запрещены. Local HTTP/self-pipe — только disposable fixtures. Публичные страницы и статический api.yml читались **отдельно** от tests. Реальных запросов OAuth/API/models/completions/paid: **0**.

| Evidence stage | Exit / фактический результат | Граница |
| --- | --- | --- |
| `red_contract` | 1, ожидаемый initial RED: 5 method FAIL + 5 subtest FAIL; 2 method PASS | API подготовки ещё отсутствовал; исходник before сохранён. |
| `green_contract` | 0, 9 PASS + 5 subtests | Первоначальный classmethod вариант. |
| `regression` | 0, 173 PASS + 255 subtests; 3 exact expected guard denials, unexpected 0 | Широкий первоначальный transport/application/H36/H29/S3a/Ordinary/launcher набор. Новый canary добавлен после collection, отдельно проверен далее. |
| `target_final` | 0, 10 PASS + 5 subtests | Canary и initial transport вариант. |
| `s1` | 1, 67 PASS / 2 FAIL / 0 ERROR / 0 SKIP / isolation 0 | Истинный census RED: class AST drift и дополнительное endpoint reference; не маскируется поздним PASS. |
| `s1_final` | 0, 69 PASS / 0 FAIL/ERROR/SKIP / isolation 0 | Итоговый module factory, unchanged pinned transport class. |
| `target_revised` | 0, **68 PASS + 100 subtests**, 0 FAIL/ERROR/SKIP, guard 0 | Итоговый runtime: новые 10 + H33/H34/actual application. |
| `s2`, `s2_final` | 0, **73 PASS** каждый, 0 FAIL/ERROR/SKIP / isolation 0 | Shared tests/pins не менялись; последний — итоговый runtime. |
| `quality` | 0, 47 PASS, guard 0 | Existing isolation quality selectors; не 52 метода другого исторического набора. |
| `ui` | 0, **69 PASS**, 0 fail/cancel/skip | Shipped unchanged JS/per-chat UI. |
| `authority_mutation_red`, `authority_mutation_revised_red` | 1, по 1 expected FAIL | In-memory bypass authority обнаружен oracle, source не мутировал. |
| `accounting_expected_red` | 1, **1 expected FAIL** | Неразрешённый REAL mapping blocker, не GREEN и не исключённая ошибка. |
| `syntax_final`, pinned-class preservation | 0 / PASS | Final source/test compile без pyc, transport AST идентичен исходному. |

Наборы пересекаются, числа **не суммируются**. Полные exact commands/selected IDs/cases/counts/elapsed/exit, stdout/stderr и guard events лежат в `evidence/*.result.json`, `.cases.json`, `.stdout.txt`, `.stderr.txt`; S1/S2 имеют собственные `.unittest.txt` и physical trace. Матрица требований — [safety-matrix.md](safety-matrix.md), ручной анализ — [manual-review.md](manual-review.md). Broad initial и окончательный affected suite различены; после изменения формы constructor повторены именно затронутые transport/application и S1/S2 gates.

Первый S1 исправлен уменьшением изменения: закрытый constructor вынесен из pinned class, диагностическое чтение endpoint удалено; actual send endpoint и его checks не менялись. Никакие safety pins/expected selectors не переписаны ради PASS. Первоначальные исходники этого варианта сохранены `evidence/initial_s1_red__*.txt`. Отдельная metadata collection сначала дала PackageNotFoundError для pytest-subtests; повтор корректно зафиксировал отсутствие отдельного distribution, не устанавливал пакеты. Это не test failure; ошибка сохранена отдельно.

## NOT RUN, риски и следующий шаг

NOT RUN: REAL GigaChat/OAuth/models/API/paid, реальный account probe, independent GitHub Windows review, Git/GitHub operations/publication/merge, физический CMD/браузер/F5, production storage/recovery, hardware power-loss, полный S3b/S3c/S9/S13a. Synthetic не является LIVE, авторский PASS не является независимым VERIFIED, прежняя owner GUI-приёмка H35/H36 не переназначена этой TASK.

Локальный результат пригоден к независимой проверке **закрытой подготовки**, но **LIVE-task сейчас не готова к исполнению**. [next-live-procedure.md](next-live-procedure.md) — только проект будущего отдельно разрешённого one-attempt испытания, не разрешение его запустить.

**FOLLOWUP / NEXT:** (1) согласовать shared cached/total/reasoning и response-model contract с versioned migration и explicit scope; (2) получить недостающие caps/account/trust evidence разрешённым способом; (3) отдельно реализовать production authority/enrollment/factory/recovery на том же ядре и пройти independent OFFLINE; (4) лишь затем решать вопрос отдельного USER GO для LIVE. Workspace-less Chat остаётся отдельным незапущенным UX FOLLOWUP.

**DOC IMPACT / SHARED DOC DELTA:** координатору после независимой проверки адресно отразить PARTIAL/BLOCKED, новые account/cached-usage/model-version/constructor OPEN в №05/34/40, history review и БЛОКЕ 4. Не закрывать полный B2/REAL по synthetic PASS. Новые тесты уже в общей корневой коллекции test_web_alarm_*; каталог/профили/общие реестры здесь не редактировались. .gitignore прочитан локально: отчётный путь не подпадает под видимые root exclusions; Git check-ignore и опубликованность NOT VERIFIED, пользователь проверяет точный состав перед публикацией.

Пакет: manifest.json, before, evidence, contract/readiness/procedure/reuse/matrix/review, сохранённые RED и финальные GREEN. После его готовности — штатный finish, check/readback HISTORY ID, обновление manifest без изменения этого отчёта. Локальная регистрация не означает независимого закрытия.
