# Подготовка и rollback — проект независимых разрешений

TASK: CODEX-WUA-0-WINDOWS-ISOLATION-READINESS-001. Установка, удаление, рестарт и native tests НЕ выполнялись. Точный системный rollback ещё не реализован/не испытан: **ROLLBACK EXECUTION BLOCKED / KEEP DENY**. Нельзя обещать гарантированное восстановление только по этому документу.

## Отдельные USER GO

| Gate | Что можно рассматривать после нового явного GO | Что gate не разрешает |
| --- | --- | --- |
| READ_ONLY | Текущая ограниченная инвентаризация и report-only/offline checks | Setup, rule apply, elevation, listeners и probes |
| LAB_SETUP | Отдельное решение о disposable lab, локальных identities, source/store ACL и trusted startup; ревью точного dry-run diff/backup/ownership | Автоматическое применение WFP, egress probes, рабочий proxy и tunnel |
| RULE_APPLY | Только reviewed lab-owned filter objects/transactions и адресный readback | Глобальные firewall defaults, сетевые тесты, production |
| NATIVE_EGRESS_TEST | Отдельная конечная матрица наблюдаемых lab probes, positive/negative controls и fault injection с endpoint/лимитами | Реальный hosted tunnel, OpenAI/API credentials, рабочий proxy, reboot если не включён в GO |
| TUNNEL_START | Только после независимой native security приёмки и нового согласованного live scope | Не следует из предыдущих gates; текущее HOSTED_TUNNEL_ON_HOLD_BY_USER сохраняется |

## Future baseline до любой мутации

USER_DECISION: transport C→B (узкий loopback или новый NPFS), engine/source compatibility, выбор отдельной lab с подтверждённым внешним containment. Ни VM, ни физическая lab этой TASK не создавались и не объявлены готовыми.

Сохранить под будущим scope только task-owned/preexisting-to-be-touched objects: account preexistence/SID provenance, exact ACL bytes/owners, approved binary/config pins, owned startup entries, provider/sublayer/filter keys+security descriptors+flags, baseline effective constraints. Реальные secrets не копировать в evidence; recovery secret escrow отдельно с ACL и сроком. Compare-and-swap readback перед изменением: при drift/чужом owner STOP, не затереть чужие изменения. Сам UUID из ledger не доказывает владение. Если account уже существует — не adopt/delete по совпадению имени.

Out-of-band operator recovery и lab containment проверяются до допуска C/B. При невозможности независимо управлять lab без снятия deny — LAB NOT READY. Снимок VM/restore point не заменяет scoped rollback/readback; VM actions сейчас не разрешены. Проверка того, что рабочий U proxy не затронут, потребует отдельного согласованного observer; новых production сетевых проверок этот план не разрешает.

## Safe rollback order

1. Freeze admissions; запретить новые owned startup actions. Не снимать deny, не останавливать BFE/Firewall, не менять U proxy.
2. Quiesce C/B: остановить только owned process trees/jobs и делегированную работу, закрыть inherited/duplicated handles/sockets/queues. Проверить actual tokens/image/process creation lineage; PID из старого ledger недостаточен.
3. Независимый trusted observer подтверждает zero live C/B processes, flows, handles/queued delegated work; повторная проверка непосредственно перед удалением deny. Unknown/timeout/error => KEEP DENY, escalation оператору, не best-effort delete.
4. Проверить exact ownership, свежесть snapshot, filter keys/current readback, отсутствие ссылок чужих объектов. Удалять exact owned startup/resources и восстанавливать только затронутые ACL по approved preimage при отсутствии drift. Защищённые evidence сохранить.
5. Deny objects удалять **последними** в рассмотренной transaction, только при независимо подтверждённой quiescence и заблокированном повторном запуске. Provider/sublayer — после проверки отсутствия чужих references. Нет global firewall reset, service disable, wholesale import профилей или delete-by-prefix.
6. Временные accounts удалять только после закрытия доступа/ресурсов и доказанного создания текущей установкой. Не удалять preexisting account; неизвестная provenance => BLOCKED. Отдельно аккуратно утилизировать собственный secret store, не включать bytes в отчёт.
7. Independent readback: точные owned изменения отменены; C/B не могут resurrect; UI proxy configuration/objects не изменены; при новом запуске admissions по-прежнему BLOCKED. Publish sanitized receipt отдельной будущей TASK. Persistent denial после сбоя безопаснее неподтверждённого снятия.

## Failure/recovery cases

- Apply crash до commit: transaction outcome readback, не assume rollback. Partial/unknown policy => no Resume, keep-deny/containment. Trusted recovery не запускает повторный apply автоматически.
- Crash после commit до receipt: восстановить ownership по trusted readback и preimage, не по reported success. Frozen startup, quiescence обязательно.
- Controller/B crash: job lifecycle — вспомогательный контроль. Нельзя считать отсутствие controller доказательством отсутствия descendants/delegation.
- BFE stop, policy-provider loss, reboot/boot gap: отдельный native GO/fault test; current PERSISTENT candidate boot coverage не доказывает. Пока нет независимого boot guarantee C/B startup запрещён.
- Concurrent account/filter/config/ACL replacement: STOP, сохранить scoped evidence, никаких автоматических resets или «починок» рабочего proxy.
- Upstream loss: не ослаблять policy ради доступности. Отсутствие прокси не даёт C прямой выход, B secondary/DNS route не добавляется.

Rollback receipt — независимый raw readback + actual process/flow quiescence + exact before/after mapping. Offline JSON «zero=true» не authority. Synthetic oracle tests в этом пакете проверяют отказ неполным receipts, а не реальное восстановление Windows.
