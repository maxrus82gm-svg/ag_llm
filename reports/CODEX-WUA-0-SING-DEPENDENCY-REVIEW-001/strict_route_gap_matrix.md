# Strict route gap matrix

TASK: CODEX-WUA-0-SING-DEPENDENCY-REVIEW-001 / BLOCKED / DOWNLOAD_GO_REQUIRED.
Статусы относятся к доказательствам, а не к применённой системной политике.

| Gate | Сохранённое основание | Чего не хватает / требование | Статус |
| --- | --- | --- | --- |
| Exact dependency | go.mod/go.sum pin, шесть parent file hashes | Отдельный download GO, origin/ZIP h1 | BLOCKED |
| HTTP CONNECT | Parent передаёт поток в sing handler | Authority/port/IPv6/malformed/methods/EOF и порядок dial | BLOCKED |
| Authentication | Parent создаёт и передаёт authenticator | Реальное reject-before-upstream, empty/wrong credentials, alternate handlers | BLOCKED |
| JSON/options | Parent вызывает DisallowUnknownFields и MergeJSON | Вложенные decoder/default/null/types/duplicate keys/merge/reload | BLOCKED |
| Default deny | Ранее принято: native default может быть DIRECT | Explicit final + deny unmatched/incomplete config; unknown defaults отвергать | CONDITIONAL / FULL POLICY UNVERIFIED |
| No fallback | Ранее просмотрен ограниченный normal dial failure path | Все protocol/group/detour/resolver/failover branches | UNVERIFIED |
| TCP-only logical traffic | Ранее принят UoT packet path | Отсечь packet/UDP/UoT отдельно от запрета UDP sockets | CONDITIONAL / ENFORCEMENT UNVERIFIED |
| DNS/IPv6 | Ранее выявлены local DNS/resolver paths | Исключить неутверждённые пути и все дополнительные socket families | UNVERIFIED |
| Background egress | Ранее выявлены conditional health/rules/NTP/etc | Exact disabled subset и полный closure; источник не равен active config | UNVERIFIED |
| One B-owned socket | Архитектурный целевой контракт | Фактический token/process/socket owner, SID и WFP containment | BLOCKED / NOT VERIFIED |
| Proxy route получения | Предыдущий localhost:10808 receipt | Текущая разрешённость и актуальность; сейчас не проверять сеть без GO | BLOCKED |
| Real fail-closed | Ни source, ни pure model не доказывают OS | Изолированная lab + отдельный GO + negative controls | NOT VERIFIED |
| Engine selection | engine.family=V2Ray сохранён | Отдельное решение пользователя после closure | PENDING USER |
| Hosted / ordinary Chat | Старые gates сохранены | Отдельные разрешения и реальные tool calls/receipt | HOLD / NOT VERIFIED |

Никаких изменений policy или ослабления gate. При последующем обнаружении дополнительных dependencies — адресный blocker без auto-fetch. Негативные сценарии текущей TASK NOT RUN, прежний 30/30 не переносится как их результат.
