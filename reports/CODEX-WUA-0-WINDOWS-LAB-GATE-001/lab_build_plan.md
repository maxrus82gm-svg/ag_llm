# Неисполняющий план отдельной Windows-лаборатории

TASK `CODEX-WUA-0-WINDOWS-LAB-GATE-001`. Plan only; `can_apply=false`. Ничего из таблицы не применялось. На текущем host нет подтверждённой готовой платформы, VM или доверенного offline media.

Машинный `lab_build_plan.json` получен действующей функцией `plan`, привязан canonical SHA-256 к read-only inventory. **Owner `555…`, `C:\ProposedLab\owned-new` и media digest `222…` — явно синтетические placeholders**; это пример, не параметры будущей установки и не файл ISO, обнаруженный на диске. Имя получается из owner; настоящий VM GUID можно получить только из результата будущего разрешённого создания. Generation 2 / 4 GiB / 2 vCPU / 64 GiB — неподтверждённое предложение, ресурсы не резервировались. JSON не является установочным сценарием и не имеет apply executor.

## Параметры перед будущим адресным GO

Выбрать отдельный уже подготовленный lab host с известным Hyper-V build/module и доверенной административной плоскостью. Новые owner UUID, private ledger и local resource root назначаются для одной disposable VM. Root: новый пустой каталог на локальном fixed volume, не project/Users/Windows/Program Files, не UNC/reparse/cloud path, не shared/base-disk directory. Проверить quota/free space/ACL/backup interference. Фактический root и host identity остаются в приватном ledger; публично — hashes/aliases. Syntax-only проверка `plan` не проверяет реальное существование, свободное место или ACL.

Легитимное Windows offline media: утверждённые источник, лицензия, edition/build/arch, размер и raw SHA-256. Отдельно staged exact dependencies, observer binaries, fixtures и WFP source/binary/reference manifest. Никаких downloads, real credentials/tunnel IDs/V2Ray profiles или mounts рабочего host disk. Выбранные fixture ports должны принадлежать guest-only receivers; заранее заданный 54321 в synthetic sample не является разрешённым рабочим портом.

Нужны три различных решения: (1) безопасный read-only preflight; (2) отдельный USER GO на конкретное provisioning/controlled baseline boot/owned cleanup; (3) ещё один USER GO на bounded native cases после independent acceptance. Включение Hyper-V/драйверов/reboot на рабочем компьютере — **отдельный запрос на изменение host**, не скрытый пункт provisioning GO.

## Последовательность и откат

Выполнять в будущей отдельной TASK, только после утверждения конкретных параметров. Права ниже описаны, не запрошены и не использованы сейчас. На любом неизвестном readback, смене owner/GUID, дополнительном устройстве или отсутствии stop authority — STOP/BLOCKED, без fallback.

| № / WHAT / WHY | TARGET; BEFORE → AFTER | PRIVILEGES / VERIFY / ROLLBACK |
|---|---|---|
| 1. Read-only platform preflight: подтвердить реальный backend | Только selected lab host; неизвестная платформа → установленный поддерживаемый Hyper-V с версией | Read-only metadata. Нужен exact command/parameter review. Отсутствует → BLOCKED, не устанавливать автоматически |
| 2. Зарезервировать один owner/root/quota/ledger | Новый local root; ничего не существует → задокументированы новые принадлежащие lab ресурсы | Будущие адресные filesystem rights. Проверить отсутствие ancestors/reparse/чужих данных. Откат только созданного пустого root по ledger, не рекурсивно вычисленного пути |
| 3. Проверить offline assets | Локальное отдельное media и staged files; untrusted → source/size/hash/license/closure independently reviewed | File read. Без сети/install. Любой mismatch → BLOCKED, не чинить загрузкой зависимостей |
| 4. Создать одну **выключенную** VM | Возвращённый VM GUID, не совпадение имени; VM отсутствует → owned OFF VM | Отдельный provisioning GO + Hyper-V admin. Не создавать switches/NAT. Сразу записать actual GUID в ledger; никогда не boot до шагов 5–8. При сбое — оставить OFF/quarantine |
| 5. Убрать **все NIC objects** до любого boot | Exact owned GUID; возможный default adapter OFF VM → полный hardware/backend census даёт zero NIC/passthrough/switch/bridge | Будущее право менять только lab VM. Отсутствие switch или disconnected NIC недостаточно. Неполный census → OFF/BLOCKED |
| 6. Закрыть data/integration channels | Та же OFF VM; defaults/неизвестно → доказанные zero shared-folder/clipboard/enhanced-console/serial/USB/GPU/hostbus/PSDirect/agent relay | Per-VM changes по одобренным documented mechanisms. Только basic console без redirects. Если запрет требует изменения host-wide policy или не доказан для версии — BLOCKED, запросить отдельный scope; не отключать службы рабочего host |
| 7. Подготовить owned disk/media chain | Новый guest system disk + offline readonly input; неизвестные parents → весь DAG локален/owned/exclusive, нет writable shared base или simultaneous host mounts | Только owned resources. Проверить raw hashes/bytes/parent IDs, backing sources и no remote/reparse без открытия непроверенного remote path. Никакого live writable export bridge. Откат: OFF, evidence retain, не трогать исходный ISO |
| 8. Host-side preboot review | Exact VM/config/devices/channel/disk snapshot; конфигурация подготовлена → verifier отдельно подтвердил отсутствие внешних edges | Readback + независимый review. Частичный нынешний adapter не даёт такого доказательства. Host-side stop authority известна заранее. Иначе не boot |
| 9. Controlled baseline guest boot | Только эта VM; OFF → fresh guest baseline | Provisioning GO должен явно разрешать этот boot. Ни MCP, ни WFP/native subject. Если нельзя заранее доказать virtual boundary → boot запрещён. Fault → независимый stop/quarantine по отдельному разрешению |
| 10. Guest/observer readiness | Fresh empty guest; нет proof → PnP/routes/DNS/relay/profile census, attempts coverage и принадлежащие loopback fixtures подтверждены | Только будущие guest privileges. Без public-IP/DNS/proxy probes. Проверить DNS/socket/refused/process/child attempts, monotonic correlation, loss/heartbeat и positive/negative receiver receipts. Unknown sensor → BLOCKED |
| 11. Baseline/checkpoint + gate | Clean owned checkpoint/chain/recovery, signed host+guest + independent review одного request; unverified → evidence validation | Guest collectors/observer implementations и key ceremony требуют отдельного review. Pin approved request, source/helper/observer hashes; no self-trust. Continuous watch и независимый stop обязательны. Receipt сам не включает native |
| 12. Дождаться точного native USER GO | Reviewed VM с frozen config; native disabled → остаётся disabled до новой TASK | WEB_11 сверяет live evidence; пользователь утверждает exact cases, attempts/time/quota, identities/privileges/ACL/source/binary/rollback. `can_apply=false` текущего комплекта не снимается этим JSON |
| 13. Owned exit/recovery/cleanup | Только exact ledger GUID/root; run stopped → evidence retained, lab OFF/quarantine, затем разрешённый owned cleanup | Stop/delete — будущие отдельные полномочия. Проверить original host state, child termination и checkpoint integrity. Не удалять по имени/маске, не следовать reparse/foreign parent. Никакого reset рабочей сети |

## Два состояния конфигурации

Preboot host proof относится к OFF VM. Полный I01–I12 snapshot с guest/observer proof относится к контролируемой **Running** VM после разрешённого baseline boot и до subject. Подстановка guest-live claim при host OFF отвергается тестом. Config normalization обязана разделять стабильные параметры от state transition, связывать actual boot ID и baseline digest. Текущий частичный adapter хеширует лишь core metadata, не полный normalized VM config, и всегда оставляет proof BLOCKED.

## Точный откат текущей TASK

Host/VM/network изменений не делали; откатывать системные настройки нечего. Файлы предыдущих TASK сверяются по `protected_inputs.json`. Собственная карточка ротируется отдельно с hash-guard/readback; receipt и точное восстановление описаны в `card_rotation.json` и `report.md`. Текущий комплект не содержит исполняемого provisioning/cleanup/rollback executor. Будущий откат VM обязан проектироваться и проверяться до boot; JSON-флаги его не обеспечивают.
