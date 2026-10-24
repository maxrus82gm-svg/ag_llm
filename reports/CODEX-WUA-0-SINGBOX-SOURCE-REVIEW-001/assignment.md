# БЛОК 1 — ТЕКУЩАЯ ЗАДАЧА

# 🟨 CODEX-WUA-0-SINGBOX-SOURCE-REVIEW-001

## Проверка официальных исходников sing-box v1.13.4 и совместимости со строгим MCP-брокером

Уважаемый агент 007 (Codex)!

Продолжаем инженерную разработку защищённого подключения обычного ChatGPT к Web Alarm Ultra.

**Исполнитель:** Codex 007  
**Координатор и независимый verifier:** ChatGPT WEB_11  
**ARCH CLASS:** Web Alarm Ultra / ChatGPT MCP / Proxy Engine Source Review  
**Опубликованный baseline:** `main@bc0a1be97e7a44a0869310e6961e77ff6c841073`

### 1. Исходные подтверждения

Предыдущая TASK `CODEX-WUA-0-PROXY-ENGINE-SNAPSHOT-001` завершена исполнителем.

WEB_11 провёл ограниченную независимую проверку опубликованных исходников/evidence:

- 70/70 manifest-listed paths существуют.
    
- 10/10 выборочных SHA-256 независимо совпали.
    
- Codex-run 44/44 PASS (25 новых и 19 regression).
    
- Две контрольные мутации обнаружены.
    
- Независимый Windows-run NOT RUN.
    
- 95/95 защищённых файлов неизменны по отчёту Codex; полный независимый пересчёт 95 не выполнялся.
    

**Verdict: PARTIAL / BOUNDED STATIC-SNAPSHOT ACCEPTED.**

Установленный через v2rayN движок — `sing-box.exe`, локальный SHA-256:

`ca74563c93440a2e9cb73eae6a04c109d3f5efce36a385f8261a654e362d2ea3`

Встроенные metadata:

- sing-box `v1.13.4`;
    
- Go `go1.25.8`;
    
- VCS revision `d09182614c7778c1e0f51d990635c5d4249c437e`.
    

**Новое независимое подтверждение координатора:** официальный GitHub-tag `SagerNet/sing-box v1.13.4` действительно указывает на этот VCS commit.

Официальные upstream references, переданные координатором:

- Release: [https://github.com/SagerNet/sing-box/releases/tag/v1.13.4](https://github.com/SagerNet/sing-box/releases/tag/v1.13.4)
    
- Source revision: [https://github.com/SagerNet/sing-box/tree/d09182614c7778c1e0f51d990635c5d4249c437e](https://github.com/SagerNet/sing-box/tree/d09182614c7778c1e0f51d990635c5d4249c437e)
    

Это подтверждает наличие upstream source revision, **но не подтверждает подлинность установленного** `**.exe**` **или соответствие официальному binary release**.

### 2. Цель

Провести **source-only engineering review** конкретной версии sing-box v1.13.4 и установить, можно ли принципиально использовать отдельный экземпляр этого движка как будущий защищённый MCP-брокер.

Не выбирать sing-box окончательно и не менять действующий `STRICT_V2RAY_BROKER`.

Текущая цель — получить проверенные source-level технические основания для следующего решения пользователя.

### 3. Адресная матрица чтения

|Источник|Раздел / назначение|Режим|
|---|---|---|
|`Документация/000_Задачи Codex.md`|Правила, БЛОК 1, относящийся БЛОК 4|Обязательно|
|`08_Старт.md`|Актуальный start-route|Адресно|
|`34_TACTICAL_CONTEXT.md`|MCP security/current|Адресно|
|`01_Архитектура и текущее состояние.md`|Web Alarm Ultra authority|Адресно|
|`19_Архитектура внешних AI-интеграций - Codex CLI и ChatGPT MCP.md`|§3–5, §7.1–7.5 при локальной доступности|Обязательно|
|`37_Старт перехода - Web Alarm Ultra.md`|§9|Обязательно|
|`36_Единая архитектура тестирования.md`|CURRENT/test lifecycle|Адресно|
|`36.1_Обязательный регламент тестирования для LLM.md`|TEST-COLLAB/AREA/ENG/DEV/COV/EXEC/QA/EVID/SCOPE|Обязательно|
|`36.3_Профиль тестирования Ultra.md`|Изоляция offline test|Адресно|
|`18_Регламент сопровождения документации.md`|DOC-GIT-01, DOC-PARALLEL-01, DOC-TASK-READ-SCOPE-01, DOC-VERIFIER-BLOCK4-01@2, DOC-HISTORY-ACCESS-01, DOC-TASK-BLOCK1-01, DOC-LOCAL-REPORT-HANDOFF-01|Только точные определения и зависимости|
|`reports/CODEX-WUA-0-PROXY-ENGINE-SNAPSHOT-001/`|Итоги идентификации, capability gates, source metadata|Обязательно|
|`reports/CODEX-WUA-0-V2RAY-BROKER-OFFLINE-001/`|Existing broker/preflight requirements|Адресно|
|`integrations/wua_chatgpt_mcp/`|Existing validators, broker, source checks|Затронутые файлы|

Не читать архив `001` самостоятельно. Не использовать Git/GitHub, включая read-only.

### 4. Получение исходной базы

Первым действием установить, предоставлен ли пользователем **локальный доверенный source bundle** официального sing-box `v1.13.4`.

Требования:

- версия v1.13.4;
    
- соответствующий upstream commit `d09182614c7778c1e0f51d990635c5d4249c437e`;
    
- источник получения, package hash и chain of custody;
    
- matching `go.mod`, `go.sum` и относящийся source tree;
    
- versioned documentation/schema, если реально имеются.
    

Не подменять факт наличия upstream tag фактом проверки локальных source bytes.

**Если локальный bundle отсутствует:** остановить зависящий от него source review, составить точный запрос пользователю на один официальный source archive и указать безопасный путь его размещения. Допустимы только независимые preparatory checks в уже разрешённом scope. Не имитировать чтение upstream исходников.

Самостоятельно скачивать архив, выполнять Git/GitHub или устанавливать зависимости нельзя.

Нельзя читать действующие v2rayN profiles/subscriptions/secrets.

### 5. Source review: семь обязательных тем

После получения соответствующих исходников исследовать:

**A. HTTP CONNECT inbound**

- Настоящую реализацию HTTP proxy inbound.
    
- Условия принятия TCP CONNECT.
    
- Связь с конкретным локальным listener.
    
- Request parsing, authentication и ошибки.
    

**B. Route selection**

- Правила выбора outbound.
    
- Default/final route.
    
- Unmatched destinations.
    
- Retry/fallback/selector/group behaviour.
    
- Возможность запретить все неожиданные маршруты.
    

**C. Один допустимый upstream**

- Реальную возможность отдельного encrypted/authenticated outbound к `R:Q`.
    
- Разницу между логическим proxy destination и фактическим next-hop socket.
    
- Кто вызывает сетевой dial.
    

Не выбирать upstream protocol по догадке, поскольку пользовательские конфигурации недоступны.

**D. DNS/IPv6/UDP**

- Возможные host/system DNS calls.
    
- DNS через engine.
    
- IPv4/IPv6 transport.
    
- UDP, QUIC и дополнительные протоколы.
    
- Можно ли полностью отключить нежелательные обращения на уровне конфигурации.
    

**E. Hidden connections**

- Health checks.
    
- Background updates.
    
- Telemetry, remote rulesets, remote resources.
    
- Companion processes.
    
- Неявные bootstrap/auto-detection flows.
    

**F. Config loader**

- Exact configuration path.
    
- Include/import/merge behaviour.
    
- Environment and CLI overrides.
    
- Доступные способы исключить пользовательский default profile.
    
- Возможность строгой source/config pinning.
    

**G. Process ownership**

- Какие сетевые сокеты открывает сам engine.
    
- Нужны ли helper-процессы.
    
- Что необходимо для будущего запуска под отдельным непривилегированным SID `wua-broker`.
    
- Какие свойства невозможно установить без native OS наблюдения.
    

Для каждого пункта дать точный source file/function и локатор к исходной версии, а не утверждение из общей документации.

### 6. Анализ совместимости

Сопоставить фактическую реализацию с инвариантами:

- C-owned tunnel-client → единственный локальный B CONNECT endpoint;
    
- B-owned engine → фактический единственный approved remote upstream;
    
- отсутствие DIRECT/fallback;
    
- отсутствие неразрешённых дополнительных сетевых соединений;
    
- fail-closed при сбое broker/route/credentials;
    
- переносимость без исходного пользовательского профиля;
    
- сохранение независимости MCP/NPFS от engine.
    

Рассмотреть неизменяемый сейчас `engine.family=V2Ray` в существующем broker contract.

**В этой TASK не менять engine family.** Если sing-box способен удовлетворить требованиям, представить минимальный migration proposal и дифференцированный план изменения контракта **для решения пользователя**.

Выявить, какие свойства подтверждены по коду, а какие лишь подразумеваются документацией. Даже качественный source review не может доказать реальный WFP enforcement.

### 7. Offline-проверки

При наличии source bundle создать targeted source-contract checks:

- revision/tag/source hash mismatch;
    
- source tree недостаёт обязательных файлов;
    
- несогласованный go.mod/go.sum;
    
- неизвестный config default;
    
- неожиданная route/fallback branch;
    
- неявные DNS/UDP/companion paths;
    
- несанкционированные schema fields;
    
- тестовая мутация default route в DIRECT;
    
- тестовая мутация выбора другого outbound.
    

Использовать independent expected outcomes, конкретные source locations и отрицательные контроли. Static analysis не считать заменой native runtime test.

Провести пропорциональную regression существующих pure validators в пределах разрешённой среды.

Нельзя запускать действующий sing-box.exe, выполнять `--version`, настоящий CONNECT, внешний сетевой dial или живой proxy test.

### 8. Архитектурная экономия

Не создавать ещё один абстрактный proxy broker.

Переиспользовать:

- `broker.py`;
    
- `engine_snapshot.py`;
    
- `security_contract.py`;
    
- действующие schema/preflight;
    
- существующие testing conventions.
    

Добавлять только то, что необходимо для version-pinned source review и будущего проверяемого engine-selection decision.

Не создавать production config или runtime launcher до подтверждения совместимости и выбора пользователя.

### 9. Права и write scope

**Разрешено:**

- необходимые новые source-review проверки в `integrations/wua_chatgpt_mcp/`, без изменения runtime broker/NPFS;
    
- новый отчёт `reports/CODEX-WUA-0-SINGBOX-SOURCE-REVIEW-001/`;
    
- собственная ротация БЛОКОВ 1–3 в `000_Задачи Codex.md`;
    
- узкий append-only handoff собственной TASK в `001_История выполненных задач Codex.md`.
    

**Не разрешено:**

- менять общую документацию, чужие TASK или БЛОК 4;
    
- читать персональные архивы без разрешения;
    
- использовать Git/GitHub любым способом;
    
- читать рабочие прокси-профили или секреты;
    
- изменять Windows users/SID/WFP/Firewall/services;
    
- запускать V2Ray/sing-box, tunnel-client или OpenAI connection;
    
- скачивать/устанавливать ПО;
    
- выполнять native network tests на рабочем ПК;
    
- автоматически переключать выбранный engine.
    

Пользовательский V2Ray продолжает работать без изменений.

Сохранять:

`can_apply=false`  
`can_start_tunnel=false`  
`HOSTED_TUNNEL_ON_HOLD_BY_USER`

### 10. Сдаваемые результаты

В отчётной папке:

- `report.md`;
    
- `source_bundle_provenance.md`;
    
- `http_connect_review.md`;
    
- `route_and_fallback_review.md`;
    
- `network_egress_review.md`;
    
- `config_loader_review.md`;
    
- `compatibility_matrix.md`;
    
- `test_results.json`;
    
- `manual_engineering_review.md`;
    
- `next_user_decision.md`;
    
- `manifest.json`.
    

Объединять близкие отчёты, если это уменьшит дублирование и не потеряет доказательства.

При отсутствии обязательного исходного пакета сдать короткий factual `BLOCKED / SOURCE_BUNDLE_REQUIRED` с точным перечнем отсутствующего, без пустых псевдоотчётов и фальшивых тестов.

### 11. Критерии приёмки

Результат может быть передан WEB_11, когда:

- указана exact upstream revision;
    
- source provenance подтверждена либо обоснованно BLOCKED;
    
- каждая network capability привязана к source code;
    
- рассмотрены normal/failure/default/hidden network paths;
    
- определена возможность одной B-owned native engine instance на уровне кода;
    
- выделены свойства, для которых обязательна настоящая Windows-лаборатория;
    
- сохранены source-specific negative checks;
    
- предоставлена минимальная рекомендация без автоматического engine switch.
    

Отдельные статусы:

`OFFICIAL_SOURCE_REVISION_VERIFIED / BLOCKED`  
`HTTP_CONNECT_SOURCE_SUPPORTED / UNVERIFIED / UNSUPPORTED`  
`STRICT_ROUTE_SOURCE_SUPPORTED / UNVERIFIED / UNSUPPORTED`  
`HIDDEN_EGRESS_PATHS_REVIEWED / BLOCKED`  
`ENGINE_SELECTION_PENDING_USER`  
`B_EGRESS_OWNER_NOT_VERIFIED`  
`WFP_NATIVE_ENFORCEMENT_NOT_VERIFIED`  
`HOSTED_TUNNEL_ON_HOLD_BY_USER`  
`ORDINARY_CHATGPT_E2E_NOT_VERIFIED`

### 12. Завершение и ротация

Сохранить фактический отчёт, source locator, tests, evidence и manifest.

Штатно дописать в собственный архив 001 только новую запись, проверить её адресно, затем обновить окно пяти TASK в БЛОКАХ 2–3. БЛОК 4 оставить побайтно, БЛОК 1 освободить только после успешного сохранения.

Не выполнять Git/GitHub commit/push.

Передать в чат короткий итог: TASK ID, факты, exact source revision, counts, OPEN/BLOCKED, рекомендация и NEXT USER DECISION.

**Цель:** выяснить, способен ли конкретный sing-box v1.13.4 соответствовать нашей архитектуре, прежде чем тратить время на настройку Windows и WFP.
---

