# Задачи Codex

**Назначение:** персональная карточка локального Codex CLI для задач проекта `ag_llm`. Авторизована пользователем 2026-10-08. Проектный маршрутизатор — [[000_Задачи для агента]]; общий регламент — `18_Регламент сопровождения документации.md`. Codex и Claude не используют общие TASK ID и не пишут отчёт за другую модель.

## Правила

**Приоритет USER GO 2026-10-24:** в этой персональной карточке БЛОК 1 и БЛОКИ 2–4, а также личный архив `001` обновляет ChatGPT-координатор **только после** пользовательской публикации и верификации/решения terminal BLOCKED. Локальному исполнителю запрещено изменять любые БЛОКИ карточки, `001` или самостоятельно запускать ротацию. Отчёт/manifest/evidence в разрешённой папке сохранять обязательно; до приёмки БЛОК 1 остаётся за текущей TASK. Источник: `DOC-TASK-CLOSEOUT-OWNER-01@1` (18); старые правила самоличной ротации более не действуют.

**USER GO 2026-10-23 (приоритетная адресная политика этой карточки):** [[001_История выполненных задач Codex]] — полный архив; БЛОКИ 2–3 — лишь пять последних кратких задач и итогов, постоянно обновляемых. БЛОК 4 — отдельная независимая проверка. Старые вложенные правила и статусы внутри исторического архива не являются новой инструкцией; архив читать только адресно по TASK ID, никогда автоматически целиком.


- **`DOC-TEST-LIFECYCLE-01@1` (18) — длительные тесты и честная сдача.** Не выдавать копируемый финальный результат или `RESULT READY` до окончания обязательных тестов. Если управление возвращено до их окончания, начинать сообщение с `# 🔴 ТЕСТЫ НЕ ЗАВЕРШЕНЫ — ЗАДАЧА В РАБОТЕ — ОТЧЁТ ПРЕДВАРИТЕЛЬНЫЙ`; сообщить TASK ID, проверенный статус и как возобновить. Черновой `report.md` помечать `DRAFT`, не обещать автоматического пробуждения без доказанного транспорта. Перед технической сдачей проверить exit code, итоговый файл, изоляцию, manifest и evidence; архив/ротацию выполняет только координатор после приёмки; при FAIL/BLOCKED сообщить факты, а не объявлять PASS.
- **`DOC-VERIFIER-BLOCK4-01@1` (18): БЛОК 4 независимого verifier.** БЛОКИ 1–3 прежние; БЛОК 4 — READ-ONLY для исполнителя, его пишет назначенный независимый проверяющий (пока ChatGPT) после фактического review/test. Память — последнее полное заключение + до двух кратких прежних, постоянный архив всех verdict в 06. Новая TASK не обнуляет БЛОК 4. При отсутствии независимого результата — NOT VERIFIED, не PASS.

**Единая граница Git (`rule-ref:DOC-GIT-01@1` в 18, пользовательское решение 2026-10-10):** локальный Codex не обращается самостоятельно к Git/GitHub ни для чтения `status/diff/log/show`, ни для записи, через CLI/UI/scripts/API/тест. Если нужна история или сверка committed версии, запросить exact path/range у пользователя либо ChatGPT-координатора в момент работы; если интерактивно нельзя — в отчёте с пометкой BLOCKED по зависимой операции. Исторические отчёты о прошлых Git-проверках сохраняются как события прошлого, а не как разрешение на новые.

- **Перед TASK / `DOC-TASK-READ-SCOPE-01@1`:** собственные Правила, активный БЛОК 1 и относящийся БЛОК 4 (READ-ONLY), затем указанные в TASK актуальные разделы `08_Старт`, `34_TACTICAL_CONTEXT`, `01`/профиль темы, `36/36.1/36.2` (Web Alarm) или `36.3` (Ultra). Координатор даёт матрицу `файл → точный раздел/Rule-ID → зачем → обязательно/условно/полностью`. Весь глобальный `000_Задачи для агента` и весь `18` не читать механически; при пробеле/конфликте прав, security или отчётности требуется конкретное нормативное правило `18` вместе с зависимостями. Обязательные правила остаются в силе, Git-права не появляются. Codex приступает только к утверждённому БЛОКУ 1; права на мутации определяются scope.
- **Локальный режим.** Codex CLI не использует аварийный handoff ChatGPT через Desktop Commander Remote. Не создавать `Alarm/ALARM_TASK_SESSION/TASK_*`, `session.jsonl`, `context.md`, `history.md`, пооперационный `INTENT/DONE/VERIFIED`, массовые резервные копии tracked-файлов и сырые stdout-логи в репозитории. Использовать локальный контекст, прямую работу с исходниками и временные изолированные пробы **без Git/GitHub по умолчанию** — `rule-ref:DOC-GIT-01@1` из документа 18. Исключение — явно утверждённая пользователем задача с особыми требованиями аудита и защиты.
- **Безопасность.** Не экспериментировать на живом storage; Git не заменяет защиту нерегистрируемых в Git пользовательских данных. Не отключать штатный runtime backup/rollback Web Alarm и не удалять существующую историю автоматически.
- **Обязательная отчётность внутри проекта (`rule-ref:DOC-LOCAL-REPORT-HANDOFF-01@1`, 18).** По каждой TASK — в том числе PARTIAL, FAIL, BLOCKED и исследовательской — всегда сохранять полный factual `report.md`, manifest и необходимые безопасные evidence по разрешённому относительному пути внутри локального `ag_llm`, обычно `reports/<TASK-ID>/`. Итоговые файлы нельзя оставлять только во внешнем TEMP/кэше или в пути, исключённом `.gitignore`; при исключении сохранить очищенную публикационную копию в допустимой части проекта и отметить недоступный оригинал. Не публиковать секреты и приватные raw-логи. Git-коммиты/публикацию обычно делает пользователь; Codex не использует Git/GitHub и не имеет постоянного права самостоятельно отправлять сообщения в ChatGPT без конкретного USER GO для TASK/AMENDMENT. Допускаются временные изолированные пробы и минимальные технические файлы, но не вместо обязательного итогового отчёта.
- По завершении: один самостоятельный копируемый блок `text` в Chat (TASK ID, статус, изменения, проверки с точными числами, обнаруженные риски, DOC IMPACT, NEXT). Не смешивать итоговый блок с промежуточным ходом работы.
- Внутри scope самостоятельно проверить релевантные edge cases; проблемы вне scope сообщить с evidence и предложением, не менять другие подсистемы без разрешения.
- Не выполнять commit/push и не объявлять `DONE / VERIFIED` без явного разрешения и независимой приёмки.
- **Ротация и архив (USER GO 2026-10-24):** Codex сохраняет только техническую сдачу (`report.md`, manifest, evidence, точные проверки). Запись в персональный `001`, окно из пяти кратких TASK/итогов в БЛОКАХ 2–3, независимый БЛОК 4 и закрытие БЛОКА 1 выполняет ChatGPT-координатор после независимого review. Старый порядок самостоятельной ротации отменён; при ошибке архивирования — `CARD CLOSEOUT BLOCKED`, без очистки.

---

# БЛОК 1 — ТЕКУЩАЯ ЗАДАЧА

# 🟨 Подготовка защищённой Windows-изоляции MCP — проверка готовности и план нативных испытаний

**TASK ID:** `CODEX-WUA-0-WINDOWS-ISOLATION-READINESS-001`

**ARCH CLASS:** Web Alarm Ultra / ChatGPT MCP / STRICT_V2RAY_BROKER / Windows Native Security Readiness

**Режим:** READ-ONLY HOST INSPECTION + OFFLINE SECURITY ENGINEERING

Уважаемый агент 007 (Codex)!

## 1. Цель задачи

Подготовить проверяемый и безопасный план перехода от уже принятой offline admission-policy к реальной изоляции MCP-соединений средствами Windows.

Нужно определить, какие именно технические идентичности, ACL, IPC/NPFS и WFP-правила потребуются, какими независимыми испытаниями можно доказать отсутствие прямого сетевого выхода и какие предварительные условия необходимо выполнить.

**Это задача подготовки нативного тестового стенда. Не задача включения туннеля или настройки рабочей Windows.**

Исходный независимый результат:

`CODEX-WUA-0-STRICT-ADMISSION-CONTRACT-001`

Вердикт WEB_12:

`PASS / INDEPENDENT BOUNDED OFFLINE SOURCE & EVIDENCE ACCEPTED`

Документационный source:

`GPT@f50387e4a16e564049e34943a44d9112e2f8fcfa`

До начала исполнитель обязан получить от пользователя подтверждение, что изменения `GPT` объединены с `main`, а локальная копия синхронизирована. Самостоятельные Git/GitHub-действия запрещены.

## 2. Исходные ограничения

Сохранить без изменений:

- `engine.family=V2Ray`
    
- `can_apply=false`
    
- `can_start_tunnel=false`
    
- `install_uninstall=BLOCKED`
    
- `STRICT_ADMISSION_BLOCKED`
    
- `HOSTED_TUNNEL_ON_HOLD_BY_USER`
    

Название целевого профиля `V2Ray` не является доказательством того, что на текущем хосте используется V2Ray Core: ранее был обнаружен работающий через v2rayN движок sing-box. Ни выбор нового движка, ни его переключение настоящей задачей не разрешаются.

Риск раскрытия паролей в upstream HTTP CONNECT authentication/error logging остаётся отдельным **SECURITY BLOCKER**.

## 3. Матрица чтения

Читать адресно:

1. `Документация/000_Задачи Codex.md` — действующие правила и БЛОК 1.
    
2. `Документация/08_Старт.md` — приоритетные USER GO и полномочия.
    
3. `Документация/18_Регламент сопровождения документации.md` — действующие правила инженерной работы и закрытия.
    
4. `Документация/19_Архитектура внешних AI-интеграций - Codex CLI и ChatGPT MCP.md` — STRICT_V2RAY_BROKER и §7.7–7.8.
    
5. `Документация/34_TACTICAL_CONTEXT.md` — последний WEB_12 CURRENT.
    
6. `Документация/36.1_Обязательный регламент тестирования для LLM.md` и применимые разделы `36.2`.
    
7. `reports/CODEX-WUA-0-STRICT-ADMISSION-CONTRACT-001/report.md` и `admission_matrix.md`.
    
8. Применимые исходники существующих `security_contract.py`, `broker.py` и NPFS relay/security-механизмов.
    

Не читать весь архив `001`, другие проекты и unrelated technical reports без адресной необходимости.

## 4. Разрешённые операции

После назначения пользователем БЛОКА 1 и отправки сообщения-активатора разрешены:

- локальное чтение уже имеющейся документации и кода;
    
- точечные read-only запросы Windows для определения доступных механизмов;
    
- проверка наличия предполагаемых технических учётных записей `wua-client` (C) и `wua-broker` (B) по точным именам;
    
- проверка доступности Windows Firewall/WFP management interfaces и возможностей ACL/NPFS без их изменения;
    
- анализ необходимых прав доступа и разработка изолированного test/rollback plan;
    
- offline-тестирование созданной модели политик и тестовых оракулов без сетевого запуска.
    

Read-only инспекция не должна запрашивать повышение привилегий или запускать службы, трассировки либо listeners. Если требуются административные полномочия, сторонние утилиты, изменение среды или чтение защищённых материалов — остановиться и запросить отдельное USER GO.

Не собирать массовые дампы Windows firewall/WFP, полные списки пользователей, приватные пути, credentials, сетевые адреса сторонних соединений или содержимое секретного хранилища. Публиковать только минимально необходимую обезличенную evidence.

## 5. Абсолютные запреты

Без отдельного разрешения пользователя нельзя:

- создавать или изменять Windows accounts, группы, SID или ACL;
    
- менять Windows Firewall/WFP, маршрутизацию, DNS, proxy, v2rayN или сетевые интерфейсы;
    
- устанавливать или запускать сетевой движок;
    
- создавать слушающий порт, внешнее соединение, MCP tunnel или выполнять реальный CONNECT;
    
- выполнять позитивные или негативные egress probes;
    
- отключать существующие защитные механизмы;
    
- перезапускать Windows либо изменять службы;
    
- открывать или копировать реальные пароли, токены и ключи;
    
- изменять production Web Alarm, конфигурации брокера и карточку Codex;
    
- выполнять Git/GitHub commit, pull, push, merge или иные Git-операции.
    

Разрешено создавать **только отчётный пакет**, а не устанавливаемые правила, выполняемые скрипты настройки или изменения production.

## 6. Инженерная программа

### Этап A — безопасная инвентаризация

Определить и зафиксировать:

- какие Windows security/WFP/Firewall/NPFS возможности доступны;
    
- существуют ли целевые C/B identities, не раскрывая персональные данные других пользователей;
    
- какие ограничения текущих прав пользователя мешают дальнейшим нативным тестам;
    
- какие части существующей реализации уже готовы к отдельным security identities;
    
- где в действующей схеме заканчивается проверенный Python admission contract и начинается недоказанная OS security boundary.
    

Для каждого факта указать: `OBSERVED_READ_ONLY`, `CODE_CONFIRMED`, `USER_DECLARED`, `UNKNOWN` или `BLOCKED`.

Не выдавать гипотезу за фактическое состояние Windows.

### Этап B — модель двух идентичностей

Подготовить целевую архитектуру:

- **C / wua-client** — минимальные права для запуска клиентской части MCP;
    
- **B / wua-broker** — отдельный владелец допустимого сетевого выхода;
    
- отсутствие у C разрешённого внешнего сетевого egress;
    
- ограниченная связь C → B через разрешённый локальный IPC/NPFS;
    
- исключение запуска B под основной интерактивной пользовательской идентичностью без явного решения;
    
- контроль наследования прав, запуска дочерних процессов и использования чужих credentials.
    

Отдельно установить, что невозможно доказать лишь по коду без реального Windows access token, process owner и SID.

### Этап C — проект WFP/default-deny

Разработать полную матрицу требований для будущего нативного теста:

- IPv4 и IPv6;
    
- TCP и UDP;
    
- DNS/резолвинг;
    
- loopback и NPFS/IPC;
    
- разрешённый B-owned upstream;
    
- запрет DIRECT и альтернативных прокси;
    
- блокировка неизвестных процессов, дочерних процессов и необъявленных egress paths;
    
- отказ при потере upstream/proxy;
    
- устойчивость правил к перезапуску/сбою;
    
- безопасное восстановление исходного состояния.
    

Не считать Windows Firewall profile enabled доказательством того, что все WFP-гарантии выполнены.

Результат этапа — **проект правил**, без записи в Windows.

### Этап D — программа негативных native-тестов

Подготовить независимые оракулы для последующего отдельного задания.

Минимальные сценарии:

1. C пытается выйти напрямую — ожидаемый запрет.
    
2. B использует утверждённый upstream — ожидаемый разрешённый маршрут при выполнении всех gates.
    
3. B пытается обратиться к неутверждённому адресу — запрет.
    
4. Утверждённый прокси недоступен — fail-closed, а не fallback.
    
5. IPv6 и DNS не обходят разрешённый маршрут.
    
6. UDP и вторичные подключения не обходят правила.
    
7. Неавторизованный процесс пытается подключиться к NPFS — отказ.
    
8. Подмена конфигурации после preflight — отказ.
    
9. Credential/auth failures не раскрывают секреты в доступных диагностических каналах.
    
10. Аварийное восстановление не снимает ограничения с C и не повреждает рабочее подключение пользователя.
    

Для каждого сценария описать **источник наблюдения**, конкретное ожидаемое поведение, отрицательный контроль, риск ложного PASS и безопасную процедуру подготовки/отката.

В рамках текущей задачи эти тесты не запускать.

### Этап E — план изолированного испытания и отката

Предложить безопасный порядок будущих операций:

- проверка исходной конфигурации и создание точек восстановления;
    
- изоляция тестового окружения от текущего рабочего proxy;
    
- создание временных C/B identities под отдельным GO;
    
- применение ограниченных тестовых правил только под отдельным GO;
    
- проведение наблюдаемых нативных испытаний;
    
- гарантированный rollback и независимая проверка восстановления.
    

Разделить разрешения для `READ-ONLY`, `LAB SETUP`, `RULE APPLY`, `NATIVE EGRESS TEST` и `TUNNEL START`. Одно разрешение не должно автоматически включать остальные.

## 7. Проверка качества

Нужны проверяемые выводы, а не только общее архитектурное описание.

Если создаются offline тесты модели, обеспечить позитивные и негативные случаи, mutation/negative controls, точные counts, коды отказов, команды и сохранённые результаты.

Не создавать второй runtime broker или дублирующую систему admission.

Непроверенные native свойства отмечать `NOT VERIFIED`. Если read-only доступ к Windows недоступен, честно фиксировать `BLOCKED / HOST_READ_ONLY_UNAVAILABLE`, не имитировать результаты.

## 8. Write scope

Разрешён только:

`reports/CODEX-WUA-0-WINDOWS-ISOLATION-READINESS-001/**`

Содержимое отчётного каталога может включать Markdown, JSON, обезличенные read-only observations, offline test fixtures и результаты.

Исходные файлы программ, конфигурации, документация, БЛОКИ 1–4, архив `001`, установленное ПО и сама Windows — READ-ONLY.

## 9. Обязательная сдача

- `report.md` — фактический итог, возможности и ограничения.
    
- `readiness_matrix.md` — что подтверждено, что неизвестно и что заблокировано.
    
- `windows_identity_design.md` — C/B, tokens, SID, ACL, NPFS.
    
- `wfp_policy_plan.md` — требования IPv4/IPv6/DNS/default-deny.
    
- `native_test_plan.md` — негативные тесты и независимые оракулы.
    
- `rollback_plan.md` — безопасный порядок подготовки и восстановления.
    
- `manifest.json` — bytes и SHA-256 опубликованных артефактов.
    
- `checks.json` — реальные read-only/offline проверки, counts, exit codes и ограничения.
    
- `DOC_IMPACT.md` — предложения для №19/34/06, без редактирования этих документов.
    

## 10. Критерии завершения

**PASS / BOUNDED READINESS**, если готов проверяемый план Windows-изоляции и контролируемых native-тестов, фактическая read-only инвентаризация отделена от предположений, а все blockers и rollback-gates сохранены.

**PARTIAL / BLOCKED**, если для завершения нужных данных требуется изменение Windows, повышение прав, доступ к секретам или другой запрещённый шаг.

**Никакая успешная проверка в рамках этой задачи не разрешает запуск MCP-туннеля.**

После выполнения пользователь самостоятельно публикует техническую сдачу в GitHub и передаёт WEB_12. ChatGPT независимо проверяет опубликованный пакет, обновляет документацию после принятия, а Codex не ротирует карточку и не объявляет самостоятельно `VERIFIED`.

---

# БЛОК 2 — ПЯТЬ ПОСЛЕДНИХ ЗАДАЧ (КОМПАКТНО)

Полный архив — [[001_История выполненных задач Codex]].

- **2026-10-25 / CODEX-WUA-0-STRICT-ADMISSION-CONTRACT-001** — admission policy inside existing broker/security pipeline; Codex 52/52 offline, 51/51 regression (19 overlap), 7/7 mutants, WEB_12 independent 53/53 manifest; **PASS / BOUNDED OFFLINE ACCEPTED**, native/WFP/Chat NOT VERIFIED.
- **2026-10-25 / CODEX-WUA-0-SING-DEPENDENCY-REVIEW-001** — source-only exact sing dependency; Codex 51/51, WEB_12 87/87, six upstream files and 33 locators. **TERMINAL PARTIAL**, native blocked.
- **2026-10-24 / CODEX-WUA-0-SINGBOX-SOURCE-REVIEW-001** — source-only sing-box v1.13.4, defaults DIRECT/DNS/UoT; WEB_11 bounded source accepted, native not run.
- **2026-10-24 / CODEX-WUA-0-PROXY-ENGINE-SNAPSHOT-001** — embedded sing-box local snapshot, WEB_11 bounded, installed executable not attested.
- **2026-10-24 / CODEX-WUA-0-V2RAY-BROKER-OFFLINE-001** — disabled broker preflight, WEB_11 bounded offline, engine/WFP blocked.

---

# БЛОК 3 — КРАТКИЕ ФАКТИЧЕСКИЕ ИТОГИ

- **CODEX-WUA-0-STRICT-ADMISSION-CONTRACT-001** — new `strict_preflight`, separated structural vs strict policy statuses; controller-owned canonical/source pins, opaque auth refs, CONNECT-only exact destination and deny DIRECT/fallback/secondary/DNS/UDP/UoT/IPv6/merge/reload. Codex 52/52 offline, 51/51 overlapping compatible tests, 7 mutants caught, preserved RED 19/21, WEB_12 53/53 manifest SHA. **OFFLINE PASS only**, upstream credentials in 407/error logs still SECURITY BLOCKER. Real C/B SID/NPFS, WFP, secret-store and ChatGPT E2E NOT VERIFIED. `reports/CODEX-WUA-0-STRICT-ADMISSION-CONTRACT-001/report.md`.
- **CODEX-WUA-0-SING-DEPENDENCY-REVIEW-001** — WEB_12 terminal bounded source-only PARTIAL, 87/87 files and 6/6 upstream SHA/33 locators; no native/real egress. `reports/CODEX-WUA-0-SING-DEPENDENCY-REVIEW-001/report.md`.
- **CODEX-WUA-0-SINGBOX-SOURCE-REVIEW-001** — WEB_11 bounded 30/30 Codex, sing-box defaults DIRECT/DNS/UoT/other conditional route risks. `reports/CODEX-WUA-0-SINGBOX-SOURCE-REVIEW-001/report.md`.
- **CODEX-WUA-0-PROXY-ENGINE-SNAPSHOT-001** — WEB_11 bounded snapshot, Codex 44/44, actual engine attestation/native not run. `reports/CODEX-WUA-0-PROXY-ENGINE-SNAPSHOT-001/report.md`.
- **CODEX-WUA-0-V2RAY-BROKER-OFFLINE-001** — WEB_11 bounded 33/33 broker, 63/63 MCP, 24/24 security Codex evidence, no native WFP. `reports/CODEX-WUA-0-V2RAY-BROKER-OFFLINE-001/report.md`.

---

# БЛОК 4 — НЕЗАВИСИМАЯ ПРИЁМКА / VERIFIER
---

**Verifier:** WEB_12 / ChatGPT. Codex — READ-ONLY. Исторические вердикты в №06.

## 1. Последний вердикт — WEB_12 / 2026-10-25 / CODEX-WUA-0-STRICT-ADMISSION-CONTRACT-001

**PASS / INDEPENDENT BOUNDED OFFLINE SOURCE & EVIDENCE ACCEPTED**, `main@6456d669a8a804ddd75a0dbca242782c18d914da`.

**Независимый вердикт WEB_12:** **PASS / INDEPENDENT BOUNDED OFFLINE SOURCE & EVIDENCE ACCEPTED** — только `strict admission` Python, source и опубликованная evidence на `main@6456d669a8a804ddd75a0dbca242782c18d914da`; актуальная база при документационном closeout `main@124b43ed47ec5b2b40217324345ddbdd88066a19`. **Не** является native/Windows/WFP, физическим no-DIRECT, credential-safe upstream или ChatGPT MCP E2E pass.

**Проверено самостоятельно WEB_12:** manifest **53/53** опубликованных файлов по размерам и SHA-256 (с учётом CRLF/LF); frozen task B1 совпадает с `reports/CODEX-WUA-0-STRICT-ADMISSION-CONTRACT-001/evidence/task_snapshot.md`, blob `fb13fa784b168c371db87f6f2d750fa0dbc85b13` (manifest SHA256 `9e9c8b73f2496093924e6c50ca0eefea9148002a888c65ae6e2b5865e4ae843a`, 14632 байт), 4/4 исходных файлов `source_before/` по blob SHA совпали с предшествующим изменению HEAD; просмотрены `broker.py`, `security_contract.py`, schema, новая `admission_suite.py` и decision flow, source pin, red/green evidence, mutant outputs. **Codex-run** 52/52 PASS, 51/51 совместимая source/pure regression PASS, **7/7** executed Python mutants caught, initial **19 PASS / 21 FAIL / 0 ERROR** saved. Counts **перекрываются на 19 legacy pure tests**, не складывать их как уникальные. WEB_12 **не запускал** этот suite на независимой Windows или нативном движке; integrity 53/53 не означает native proof.

**Реализовано:** `strict_preflight(raw_bytes, controller_config_pin, controller_source_pin, request_metadata)` повторно использует existing common/parser, schema, `security.validate` и `validate_admission`; structural valid ≠ strict admitted; `strict_policy_status=VALID` может сочетаться с `STRICT_ADMISSION_BLOCKED`. Opaque `wua-secret-ref:` (без чтения credential store), mandatory/nonempty/unique auth declaration, отдельный upstream reference, protected canonical single source, exact controller-owned SHA pin, CONNECT-only request metadata/host/port, deny unknown auth/outbound/DIRECT/fallback/DNS/UDP/UoT/IPv6/secondary/merge/reload/environment override; negative tests/explicit rejection codes. **Не превращать декларативную проверку в утверждение, что реальный native движок/OS соблюдают запрет.**

**Остаточные блокировки:** опасность upstream `sing` при ошибках 407 (credentials/`Proxy-Authorization` in error/log) сохраняется **SECURITY BLOCKER**, не устранена Python offline-контрактом; secret store access control, native listener/auth, exact installed binary/engine compatibility, real Windows identities C/B, SID/NPFS cross-user, WFP IPv4+IPv6/DNS/IPC, B-only egress and fail-closed/physical no DIRECT, native route and ordinary ChatGPT MCP E2E **NOT VERIFIED**. `engine.family=V2Ray` unchanged, `STRICT_ADMISSION_BLOCKED`, `can_apply=false`, `can_start_tunnel=false`, `install_uninstall=BLOCKED`, `HOSTED_TUNNEL_ON_HOLD_BY_USER`. No live tunnel, proxy, Windows, WFP or engine change was authorized. Publication commit also included unrelated user-side `.obsidian/workspace.json` metadata: does not affect source acceptance; keep extraneous files out of future scoped technical publications.

**Terminal disposition authorized by user:** offline TASK accepted/archived, old B1 cleared to WAITING. No automatic engine/native/WFP/network/tunnel GO; next task goes in chat only. Full archives in 001, `reports/CODEX-WUA-0-STRICT-ADMISSION-CONTRACT-001/`, journal №06.

## 2. Последний вердикт — 2026-10-25 / CODEX-WUA-0-SING-DEPENDENCY-REVIEW-001 / amendment01

**TERMINAL PARTIAL / INDEPENDENT BOUNDED SOURCE & EVIDENCE ACCEPTED**, `main@257084ae6e8b7e81d82f1987a80ac2bc5e67fb34`; user explicitly approved terminal PARTIAL closeout, not full security approval.

Codex 007: exact source-only `github.com/sagernet/sing@v0.8.3-0.20260315153529-ed51f65fbfde`; one GET via explicitly approved HTTP CONNECT according to agent audit, 0 redirects/fallback, 322 module files, ZIP raw SHA-256 `dfb3b8c7cbc603602c6cf453161d319209e5610477e1118354dd449bd9409659`, Go module h1 `h1:RNQzlpnsXIuu1HGts/fIzJ1PR7RhrzaNlU52MDyiX1c=`. Baseline 30/30, first RED 49/50 (Windows ZIP name normalization; preserved), intermediate 50/50, final **51/51 PASS** (11 source +19 pure +21 dependency), per Codex logs; not independently rerun on Windows.

WEB_12: `main@257084ae6e8b7e81d82f1987a80ac2bc5e67fb34`; **87/87** published manifest paths bytes+SHA independently matched (LF/CRLF-aware); **6/6** independently fetched official `SagerNet/sing@ed51f65fbfde` source files and **33/33** locators match; Go module h1 recomputed from **published SHA values of 322 members**, not independently from original ZIP. Stored FAIL/final result and tests inspected. Physical egress/installed executable/ZIP itself, native Go/Windows/WFP, C/B SIDs/sockets, no-DIRECT proof and ordinary ChatGPT MCP E2E **NOT VERIFIED**.

Source risks: `users=[]` disables proxy authentication; 407/error logs can expose username/password or `Proxy-Authorization`; CONNECT sends `200` before dial/route; HTTP Upgrade/plain alternatives and X-Forwarded-For source override; URL-safe-vs-standard Basic Base64 ambiguity and ignored port-parse error; permissive JSON duplicates/null/case/merge/reload; prior default DIRECT, local DNS/UoT/optional other egress; Go stdlib/x/sys source/native behavior incomplete. No proven native bypass asserted. `engine.family=V2Ray` unchanged, `can_apply=false`, `can_start_tunnel=false`, `HOSTED_TUNNEL_ON_HOLD_BY_USER`; no install/engine switch/proxy/system activation.

Full report `reports/CODEX-WUA-0-SING-DEPENDENCY-REVIEW-001/amendment_01/report.md`, manifest `reports/CODEX-WUA-0-SING-DEPENDENCY-REVIEW-001/manifest.json`; pinned complete task in personal 001. No permission to enable/alter engine, Windows, proxy, WFP, local identities, hosted tunnel, ordinary ChatGPT connection or network route.

## 3. Предыдущий — WEB_11 / CODEX-WUA-0-SINGBOX-SOURCE-REVIEW-001

**PARTIAL / INDEPENDENT BOUNDED SOURCE REVIEW ACCEPTED**, `main@e0c89b3536cb030edc4fa905a8e00f1047788c4c`, 76/76 paths, 7/7 selected hashes, Codex 30/30 offline, native NOT RUN. Missing sing module source was historical state later narrowed by WEB_12.

## 4. Позапрошлый — WEB_11 / CODEX-WUA-0-PROXY-ENGINE-SNAPSHOT-001

**PARTIAL / BOUNDED STATIC-SNAPSHOT ACCEPTED**, `main@bc0a1be97e7a44a0869310e6961e77ff6c841073`, 70/70 paths, 10/10 hashes, Codex 44/44, native NOT RUN.

---

**Status:** source-only partial, not production. Full earlier NPFS/broker independent verdicts remain permanently archived №06; B1 waiting only after user-approved terminal closeout.
