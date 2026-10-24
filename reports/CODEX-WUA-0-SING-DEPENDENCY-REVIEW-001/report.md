# CODEX-WUA-0-SING-DEPENDENCY-REVIEW-001

**Codex 007 / 2026-10-25 — BLOCKED / DOWNLOAD_GO_REQUIRED. LOCAL ONLY / NOT SYNCED.**

Отдельного USER GO на один source-only download зависимости `github.com/sagernet/sing` в переданном контексте и действующем БЛОКЕ 1 нет. Назначение TASK прямо отделено от разрешения на загрузку. Предыдущее разрешение касалось только sing-box v1.13.4 и уже использовано. Загрузка, проверка доступности URL и проверка прокси в этой TASK не выполнялись. HTTP CONNECT/auth/JSON dependency closure не завершена.

## Подтверждённые факты и происхождение

- Замороженная постановка сохранена дословно из текущего БЛОКА 1 в `evidence/task_snapshot.md`; исходная карточка и её БЛОК 4 остаются без изменений. Правила, источники и SHA-256 прочитанных файлов — `evidence/read_set.json`.
- `34_TACTICAL_CONTEXT.md`, разделы `WEB_11 → NEXT MCP CHAT` и `WEB_11 / CURRENT 2026-10-24`, прямо фиксируют расход предыдущего download GO и необходимость нового. Точное старое разрешение и download receipt прочитаны локально; их хеши включены в read set. Оно не разрешает скачивание sing.
- В сохранённых локальных `go.mod:36` и `go.sum:239` sing-box подтверждены module/version и ожидаемый ZIP h1: `github.com/sagernet/sing@v0.8.3-0.20260315153529-ed51f65fbfde`, `h1:RNQzlpnsXIuu1HGts/fIzJ1PR7RhrzaNlU52MDyiX1c=`. Отдельная строка `/go.mod` имеет другой checksum и не заменяет ZIP h1.
- Локально сверены шесть адресных sing-box файлов с прежним tree manifest: `go.mod`, `go.sum`, HTTP inbound, options, config loader и UoT router. Это ограниченная сверка непрерывности исходников, не повторная независимая приёмка предыдущей TASK и не проверка новой зависимости.
- Внешний известный source root `M:/WUA_SOURCE_REVIEW` адресно просмотрен на уровне каталогов; там обнаружен только `sing-box`. Произвольные диски, Go caches и пользовательские папки не сканировались. Отсутствие зависимости во всей системе не утверждается; соответствующий подлинный bundle для данной TASK не предоставлен.

**Прежний принятый baseline сохранён:** WEB_11 `PARTIAL / BOUNDED SOURCE REVIEW ACCEPTED`, 76/76 manifest paths, 7/7 выбранных hashes, Codex-run 30/30; независимый Windows/Go запуск NOT RUN. Это прежние результаты, а не новые прогоны этой TASK. SHA main, приведённый координатором, не перепроверялся через Git. Историческая самостоятельная ротация не является действующим разрешением на изменение карточки.

## Source findings

| Область | Что действительно установлено | Статус текущего исследования |
| --- | --- | --- |
| Provenance зависимости | Точный pin есть в сохранённых sing-box go.mod/go.sum | Pin SOURCE CONFIRMED; получение BLOCKED |
| HTTP CONNECT | Inbound передаёт поток в внешний `http.HandleConnectionEx` | Парсинг authority/IPv4/IPv6/EOF/methods BLOCKED |
| Authentication | `auth.NewAuthenticator(options.Users)` передаётся обработчику | Пустой/неверный auth и порядок относительно dial BLOCKED |
| JSON | `Options.UnmarshalJSONContext` вызывает внешний decoder с `DisallowUnknownFields`; CLI использует `badjson.MergeJSON` | Реальные duplicate keys/null/types/nested defaults/merge semantics BLOCKED |
| Маршрут | Прежние source findings о DIRECT default, DNS, UoT и условных egress сохранены | Полный strict route UNVERIFIED / BLOCKED |
| SID/WFP/B-owned socket | Не исследовались запуском и не следуют из source call graph | NOT VERIFIED |

Точные текущие строки и граница доверия — `source_callgraph.md`, `evidence/source_boundary.json`. Наличие переданного authenticator не доказывает enforcement, а `UserFromContext` и ветка без user не доказывают обход auth: для обоих выводов нужно тело внешнего handler. Вызов `DisallowUnknownFields` не доказывает поведения всех вложенных декодеров. Строгую конфигурацию, новый parser или второй validator при отсутствии исходников не разрабатывал.

## Проверки и TEST GAP

Новых программных/source/native тестов **0**: collection 0, PASS/FAIL/ERROR/SKIP 0; обязательные source-сценарии **NOT RUN / BLOCKED**, а не PASS. Сценарии: source pin mutation, module h1 mismatch, пропуск auth, parser/route anchor mutation, DIRECT admission и unknown default. Без точного bundle эти оракулы не установлены. RED/PASS-прогоны не выдумывались; обязательных работающих тестовых процессов нет.

Выполнена соразмерная проверка документационного пакета: JSON/readback, pin/locators, шесть SHA исходных файлов, сохранность адресных read-only inputs, допустимость output root и финальный manifest readback. Результаты и команда — `checks.json`; файл manifest проверяется отдельно после его записи. Эти проверки не являются HTTP CONNECT/auth/JSON или Desktop E2E тестами. Полный Web Alarm suite не запускался: runtime/source/tests не менялись (`36.1`, scope для noncode).

Ограничение проверки scope: хеши подтверждают только перечисленные файлы между сборкой и окончательной сверкой пакета. Ноль сетевых/системных действий — учёт действий этого исполнителя; это не OS-level мониторинг всей машины. Старый расход download GO установлен по существующему receipt, без повторной загрузки ZIP.

## MANUAL ENGINEERING REVIEW

1. Проверен порядок authority: назначение → отдельный точный download GO → проверка разрешённого маршрута → одно получение → checksum → source review → tests. Сейчас остановка до сетевого шага. Старый sing-box GO, упоминание URL в карточке и прежний PASS тестов не дают недостающего разрешения.
2. Рассмотрены альтернативы: автоматический `go mod download`, иной ZIP/tag, GitHub fallback, поиск неограниченных caches, повтор использования старого downloader. Они не выполнялись. Без pin/provenance другой локальный пакет не закрывает проверку.
3. Проверены опасные неверные выводы: raw ZIP SHA-256 не равен Go module h1; соответствие строки go.sum не равно вычислению h1; короткий commit suffix pseudo-version не является полным доказательством revision; source findings не доказывают PID/token/WFP/real traffic.
4. Просмотрена реальная boundary sing-box: фабрика auth, TLS error close, внешний HTTP handler, stream/packet callbacks, вызов внешнего JSON decoder и merge. Ветка callback без user и логический UoT требуют исследования, не механического PASS/FAIL по имени функции.
5. Переиспользование: существующий `singbox_source_review.py` — bounded lexical tripwire, не Go parser и не module h1 verifier. Его `archive_identity` проверяет sing-box raw ZIP SHA/comment; применять эту функцию к Go module h1 как эквивалент нельзя. Изменения validator/tests сейчас не обоснованы.
6. Остаточные риски: unknown transitive dependencies/build tags, auth bypass через альтернативные handlers, duplicate keys/config merge/reload, DNS/UoT/IPv6 и дополнительные egress. Они остаются открытыми, не маскируются прежней ограниченной приёмкой.

## Статусы и ограничения

```text
TASK: BLOCKED / DOWNLOAD_GO_REQUIRED
SING MODULE ZIP: NOT ACQUIRED IN THIS TASK
MODULE ZIP H1: NOT VERIFIED
HTTP CONNECT/AUTH/JSON DEPENDENCY CLOSURE: BLOCKED
PREVIOUS SING-BOX BOUNDED SOURCE ACCEPTANCE: PRESERVED
STRICT ROUTE / REAL CLIENT FAIL-CLOSED: NOT VERIFIED
V2RAY REMOTE ROUTE / B-OWNED EGRESS / WFP: NOT VERIFIED
HOSTED TUNNEL: ON HOLD BY USER / NOT STARTED
ORDINARY CHAT E2E: NOT VERIFIED
engine.family=V2Ray; can_apply=false; can_start_tunnel=false
CARD / BLOCK 4 / 001: NOT MODIFIED
GIT / GITHUB: NOT USED
INDEPENDENT VERIFICATION OF THIS PACKAGE: PENDING
```

Никаких live settings, Windows identities, proxy/WFP/DNS/permissions, рабочего sing-box, Web Alarm production и файлов других агентов не изменено действиями исполнителя. Исходники и тесты интеграции также не менялись; запись ограничена новой TASK-папкой. Секреты, credentials и полные host/config/raw logs не собирались. Git-публикация и самостоятельная отправка в ChatGPT не выполнялись.

## NEXT USER GO / read-only план

Нужен отдельный USER GO на **один** source-only ZIP exact module/version с URL, указанным в `NEXT_USER_GO.txt`. Это заготовка формулировки, **не полученное разрешение**. После получения GO сначала адресно подтвердить актуальный разрешённый proxy path. Предыдущий literal `127.0.0.1:10808` не объявляется текущим рабочим маршрутом без проверки. При недоказанном маршруте — STOP; без DIRECT, системного обхода, retries через иной маршрут и других загрузок.

Далее сохранить ZIP вне repo в новом каталоге `M:/WUA_SOURCE_REVIEW/sing/v0.8.3-0.20260315153529-ed51f65fbfde/`, не перезаписывая данные. Зафиксировать URL/redirect/time/size/raw SHA/route receipt; проверить module archive constraints, CRC и безопасную распаковку. Вычислить Go module ZIP h1 по соответствующему алгоритму отдельно от raw ZIP hash; при невозможности — CHECKSUM_UNVERIFIED. Не запускать Go/build/runtime. Затем замкнуть настоящий HTTP/auth/JSON call graph и адресно расширить существующие source checks; всё отсутствующее транзитивное — новый blocker, без auto-fetch.

`strict_route_gap_matrix.md` задаёт необходимые доказательства. `DOC_IMPACT.md` содержит предложения координатору для №19/34/06 без их изменения. Конкретное место test suite (`integrations/wua_chatgpt_mcp/tests/...` в существующей реализации против сокращённого `tests/...` в постановке) нужно уточнить перед будущей правкой, если это останется неоднозначным; сейчас ни один test file не изменён.

Технический BLOCKED-пакет передаётся пользователю для независимой проверки WEB_11. Закрытие/архивация — координатор после установленного gate; БЛОК 1 остаётся назначенным. Ни engine selection, ни активация, ни независимая приёмка исполнителем не объявлены.
