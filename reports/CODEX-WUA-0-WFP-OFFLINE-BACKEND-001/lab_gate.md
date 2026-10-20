# Future laboratory gate — proposal, NOT USER GO

Сейчас лаборатория **не создана**, OS-level изоляция **не доказана**, native
вызовы/сетевые проверки **NOT RUN**. Ни один пункт ниже не разрешено исполнять
в рабочей Windows на основании этой TASK.

1. **Отдельный USER GO и независимый WEB_11 review.** Зафиксировать exact source,
   binary hash/toolchain, Windows edition/build/architecture, privileges,
   владельца lab и границы test-only accounts/resources. Новый review должен
   создать исполняемый lab host; текущая NativePreview намеренно не имеет такого.
2. **Доказать изоляцию до запуска backend.** Выбранная disposable Windows должна
   быть физически/OS-level лишена внешнего egress, host relay, shared proxy/DNS,
   integration services/network shares/host mediation. Нужны независимые evidence
   и negative controls. Если proof отсутствует — STOP; не проверять изоляцию
   пробным внешним запросом из MCP-цепочки.
3. **PRE и recovery.** Trusted baseline объектов/flow состояния, private ledger с
   authenticated host binding, snapshot только lab, точный план восстановления.
   Технические identities новые локальные, disabled до подтверждения guards,
   минимальные rights/ACL, отдельный trusted controller. Не применять users/ACL
   policy из неподписанного публичного JSON.
4. **Native API acceptance.** На lab-only subjects проверить data types, SD
   AccessCheck semantics и layer-supported comparators; независимый decoder
   условий/readback, включая byte order, SD/SID, flags, provider/sublayer keys,
   actual weight/context. Ошибка API/unknown code — STOP, без смены comparator
   на широкий fallback или автоподнятия privileges.
5. **Отдельные behavioral oracles.** Controlled local endpoints, subjects под C/B
   и unaffected UI/control identity. Фиксировать attempt intent, фактический token,
   процесс/child identity, observer receipt, bind/listener identity, результат
   connect/send/receive, packet/flow/drop events и потери observer. Selected edge
   должен успешно достигать правильного receiver; отрицательный endpoint должен
   быть доступен control subject и недоступен C/B. Отсутствие пакетов не PASS.
6. **Матрица endpoints.** Exact P и другой P; другая loopback address; arbitrary
   localhost proxy; R:Q и другой R/Q; v6/v4-mapped-v6, IPv4 UDP/RAW/ICMP,
   UDP/TCP DNS; broker R соединение с проверкой remote identity. Без настоящих
   внешних адресов/доменов. DIRECT/fallback — разрешённый receiver в lab с явным
   negative receipt oracle, а не внешний интернет.
7. **Concurrency/lifecycle.** Existing flows до/после создания filters;
   reauthorization; competing block/soft permit/hard permit/callouts с разными
   sublayer weights; spoofed providerData/ledger; чужой object under expected key;
   partial transaction, commit acknowledgement loss, controller crash/restart,
   BFE stop/restart, reboot/boot timing, broker unavailable и port takeover.
   Сначала определить независимые ожидаемые исходы; unsupported/ambiguous — STOP.
8. **Delegation/children.** Потомки с inherited SID, изменение logon/impersonation,
   system DNS resolver, BITS/COM/службы/локальные IPC посредники. Если любой путь
   не наблюдается или достигает forbidden receiver — отдельный BLOCKER, не T1/T2 PASS.
9. **Rollback proof перед delete.** Freeze admissions; disable own startup /
   account logon; quiesce own trees и delegated queues; два независимых readbacks
   zero processes + flow/queued-work с отсутствием новых admissions; exact owned
   object readback + trusted lineage. Только затем reviewed deny-last removal.
   Не считать bool/ledger counter quiescence token. Unknown → сохранить deny.
10. **Отдельные более поздние gates.** Реальный native client, V2Ray remote route,
    hosted reachability и четыре ordinary Chat MCP calls с independent receipt
    требуют своих разрешений. Тест WFP не доказывает MCP transport/reachability.

Немедленный STOP: неподтверждённая внешняя изоляция; unknown identity/observer
loss; forbidden successful receipt; wrong receiver; потеря deny; unexpected
objects outside owner; policy/SDK mismatch; stale evidence; любое расширение scope.
Report должен сохранять исходные FAIL и неопределённые outcomes, без автоматического
retry/cleanup, способного временно открыть маршрут.
