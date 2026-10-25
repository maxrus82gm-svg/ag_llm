# Strict route gap matrix — USER GO amendment 01

| Gate | Реальное source/evidence | Условие / открытый риск | Статус |
| --- | --- | --- | --- |
| Exact sing module | Version, raw ZIP SHA, Go h1, 322 hashes | Не binary reproducibility/полный upstream revision | SOURCE CONFIRMED (content pin) |
| Enabled auth before callbacks | Verify/407 до CONNECT/Upgrade/HTTP | Empty users даёт nil и no auth | SOURCE CONFIRMED / strict config CONDITIONAL |
| Secret-safe auth failure | Error включает password/header; parent logger | Нужна remediation/доказанная redaction до эксплуатации | BLOCKED for strict acceptance |
| Basic interoperability | URL-safe decode/error ignored vs client standard encode | Нет Go native oracle malformed/+slash inputs | SOURCE CONFIRMED / behavior TEST GAP |
| CONNECT success | 200 до route callback | Не считать его downstream/route/owner proof | SOURCE CONFIRMED |
| CONNECT-only admission | Есть plain HTTP/Upgrade | Отдельный строгий method/destination allowlist | NOT IMPLEMENTED / CONDITIONAL |
| Authority and port | Atoi ignored, uint16 cast/defaults | Exact Go parser grammar/range validation не закрыты | BLOCKED for full parser claim |
| Source identity | XFF source override | Не использовать forwarded IP как SID/authority | SOURCE CONFIRMED / OS UNVERIFIED |
| Default deny | Прежний accepted DIRECT default | Empty/missing/unmatched config должен отдельно отвергаться | SOURCE CONFIRMED unsafe capability / strict UNVERIFIED |
| No secondary/direct fallback | Normal injected callback есть; отдельный client nil→SystemDialer | Все callers/groups/resolvers исключить/доказать | UNVERIFIED |
| TCP-only logical operations | UoT packet routing существует | Отсечь UDP/UoT и magic destination, не только UDP socket | CONDITIONAL / enforcement UNVERIFIED |
| DNS/IPv6/background | Прежние optional DNS/health/rules/NTP paths | Exact permitted subset и полный closure | UNVERIFIED |
| JSON strictness | Unknown struct error есть; duplicates/null/default/merge permissive | Canonical single protected config, reject ambiguity before engine | CONDITIONAL / admission NOT IMPLEMENTED |
| Merge/reload protection | Multi-file sort/merge и recreate capability | Защитить inputs/CLI; Windows runtime не тестирован | UNVERIFIED |
| Stdlib/platform | Go linkname, x/sys Windows imports | Exact additional source input + отдельный GO при необходимости | BLOCKED |
| Existing proxy path for one fetch | Metadata + one audited loopback connect + TLS200 | Не remote V2Ray/B owner proof | BOUNDED OBSERVATION |
| C/B owner/WFP/fail-closed | Source не устанавливает OS guarantees | Lab isolation + отдельный USER GO + negative controls | NOT VERIFIED / BLOCKED |
| Engine selection | engine.family=V2Ray не менялся | Пользователь после независимого bounded review | PENDING USER |
| Hosted/ordinary Chat | can_apply=false, can_start_tunnel=false | Separate permissions and actual calls/receipt | HOLD / NOT VERIFIED |

51/51 Python source/intent controls не являются Go execution или native enforcement. Никакая policy не применялась. Показанные capabilities не доказывают их включение в рабочем profile.
