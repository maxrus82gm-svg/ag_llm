# CODEX-WUA-0-SINGBOX-SOURCE-REVIEW-001 — USER GO amendment 01

**2026-10-24 / Codex007 — PARTIAL / BOUNDED SOURCE REVIEW; RESULT READY / AWAITING WEB_11.**

Предыдущий SOURCE_BUNDLE_REQUIRED снят дополнительным разрешением пользователя на один официальный source ZIP. Initial BLOCKED report/manifest и checks сохранены в `amendment_01/`; прежняя архивная запись не переписана. B1 уже был освобождён; продолжение санкционировано прямым USER GO, сохранённым в `amendment_01/USER_GO.md`.

## Полученный материал

С [официального релиза v1.13.4](https://github.com/SagerNet/sing-box/releases/tag/v1.13.4) получен один source ZIP по GitHub archive URL с единственным redirect на codeload. Файл: `M:\WUA_SOURCE_REVIEW\sing-box\v1.13.4\sing-box-v1.13.4-source.zip`. Получен `2026-10-24T21:25:51.265099+05:00`, **1,438,060 bytes**, SHA256 **`ecf6cbedda4c35073656c902722b74daaf9fb89bb6f52de9ed0bdfd3a7729c1c`**. ZIP comment **`d09182614c7778c1e0f51d990635c5d4249c437e`** совпал с заданной полной revision. Распаковано **1013 файлов / 3,870,530 bytes** вне репозитория; CRC, archive paths, duplicate/case collisions, symlinks/reparse destination и запрещённые executable members проверены до записи. Исполняемые файлы отдельно не скачивались, зависимости не устанавливались.

Это bounded chain of custody: официальный HTTPS endpoint, TLS verification, requested exact version, archive revision comment, CRC и фактический package hash. **Tag mapping не единственное основание**, но ZIP comment тоже не цифровая подпись. Detached signature архива, независимый официальный package digest и source→установленный EXE reproducibility не проверены. Go minimum в go.mod —1.24.7; ранее embedded build toolchain1.25.8 не противоречит minimum, но не доказывает воспроизводимость.

Downloader использовал только существующий literal127.0.0.1 HTTP CONNECT proxy10808, с явным HTTPS tunnel и без NO_PROXY/DIRECT fallback. Это не доказательство actual remote V2Ray route или B-owned egress. Ни proxy settings, ни рабочий sing-box не менялись. Receipt/время/URL/redirect/hash — `amendment_01/evidence/download_receipt.json`.

## Основные source findings

1. **Пустой outbound не fail-closed:** default factory создаёт DIRECT (`box.go:319` / `New default fallback factories`); при отсутствии explicit final выбирается первый outbound (`adapter/outbound/manager.go:69` / `Manager.Start/Create`). Unmatched connection использует default (`route/route.go:103` / `Router.routeConnection`). Нельзя принимать empty/minimal config за strict profile.
2. **Есть явные route/reject primitives** и возврат ошибки при missing selected outbound. В просмотренном обычном connection path ошибка dial закрывает соединение (`route/conn.go:102` / `ConnectionManager.NewConnection`); это не глобальная гарантия отсутствия fallback у всех protocol/group/transport/dependencies.
3. **HTTP inbound — TCP listener с delegated handler:** `protocol/http/inbound.go:60` / `Inbound.NewConnectionEx`. Реальный HTTP parsing/CONNECT/auth расположен во внешнем `github.com/sagernet/sing`, отсутствующем в единственном разрешённом архиве. Полный HTTP_CONNECT_SOURCE_SUPPORTED **не объявляется**.
4. **TCP listener не исключает logical UDP:** HTTP использует `uot.NewRouter`, а UoT callback переводит поток в packet routing (`common/uot/router.go:29` / `Router.RouteConnectionEx`). Для strict intent нужен TCP-only route admission плюс reject остатка, не только запрет UDP socket в Windows.
5. **Есть дополнительные сетевые пути:** local DNS default, resolver selection, health/urltest, remote ruleset fetch/update, NTP, ECH DNS, Tor helper и REALITY cover HTTP на существующем conn. Это conditional features, а не утверждение, что они включены в рабочем config. Подробности — `network_egress_review.md`.
6. **Config loader умеет больше одного файла:** default config.json, stdin, -c array, -C directory, sort/merge и SIGHUP reload. Параметры и protected config roots нужно закрепить отдельно; source/config hash не проверяется движком как наша installation authority.

Принцип «один B-owned process принимает CONNECT и делает actual socket к R:Q» не опровергнут просмотренным обычным in-process path. Пример Trojan outbound отделяет proxy server address от logical destination, но protocol **не выбран**, TLS опционален, dependencies не замкнуты. Same PID/token/OS security по source не доказываются. Текущий `engine.family=V2Ray` **не менялся**.

## Реализация и проверки

Добавлены только `integrations/wua_chatgpt_mcp/singbox_source_review.py` и `tests/singbox_source_review_suite.py`: release-pinned source tripwires и negative controls с reuse common/broker. Это не Go parser/interpreter, не второй broker и не native schema validator.

**30/30 PASS: 11 новых source checks +19 прежних pure broker regression; FAIL/ERROR/SKIP0.** Final run `runs/source-20261024-213332-1493e644` внутри amendment01. Проверяются revision/archive/hash/source-file drift, missing required files, critical go.mod/go.sum version/checksum, top-level option field addition, config-default/merge drift, hidden-path anchors, family/secondary proxy refusal и сохранение blocked gates.

Два адресных mutation controls: (a) explicit selected outbound заменён на literal unapproved в **копии Go source** — lexical source-contract отказ; (b) default DENY→DIRECT в **существующем synthetic broker intent** — старый validator отвергает. В нативном Go empty default **уже DIRECT**; эти tests не выдают его за безопасный и Go не исполняют. Source hashes плюс review защищают known snapshot, а lexical anchors сами по себе не универсальный анализ semantics/веток.

Initial source runs оба30/30 PASS сохранены; второй после удаления unused imports, без ослабления oracle. Ошибки навигации к несуществующим именам файлов перечислены в `review_navigation_errors.json` и исправлены адресным rg. Никакого initial red test не скрыто. Старый blocked-phase19/19 не суммируется с финальным30.

## Статусы и NEXT

`OFFICIAL_SOURCE_REVISION_VERIFIED` — bounded GitHub ZIP origin/comment/hash, не detached signature. `HTTP_CONNECT_SOURCE_UNVERIFIED`; strict route primitives условно подтверждены, **STRICT_ROUTE_SOURCE_UNVERIFIED для полного профиля**. `HIDDEN_EGRESS_PATHS` bounded-reviewed, dependency/global absence BLOCKED. Engine selection PENDING_USER; B owner/WFP/ordinary Chat NOT VERIFIED; hosted tunnel HOLD; **can_apply=false; can_start_tunnel=false; native_config=null**.

Нужный следующий материал — source-only dependency bundle **github.com/sagernet/sing@v0.8.3-0.20260315153529-ed51f65fbfde** (HTTP/auth/JSON/control helpers). Скачивание dependencies **не входит** в одноразовое разрешение и не выполнялось. Затем возможен bounded review строгого native mapping proposal, без немедленного engine switch. Windows/WFP/native/hosted — отдельный будущий USER GO.

DOC IMPACT: общие18/19/34/37 не изменялись; предложить WEB_11 добавить факты о default DIRECT/DNS, UoT и dependency gap, сохранив gates. Все107 ранее защищённых файлов сверяются в final integrity; original source tree сверяется по1013 hashes. Полный ZIP/source остаётся вне repo, **не входит в пользовательский commit автоматически**; в проекте есть receipt, tree hashes, 54 locators и bounded excerpts. Независимый verifier должен получить этот exact ZIP либо отдельно разрешённый source channel.

Повторный append-only amendment handoff/ротация сохраняет B4 byte-identical, не читает старые001 bytes и не дублирует TASK в compact five. Receipt — `amendment_01/evidence/card_rotation.json`. Независимую приёмку и отправку WEB_11 исполнитель не объявляет; пользователь публикует/передаёт комплект.

Фактическая amendment-ротация **CARD ROTATION VERIFIED**: добавлено/сверено **22,053** новых байт, old archive bytes read/written0; B2/B3 по пять уникальных TASK, текущая строка обновлена без дубля. B4 byte-identical, SHA256 `608c49b5be482fc6c7ccb7db2c5898bf8c6f9143fbf1d2c02a1c14f4e9fbb089`; B1 остаётся `ОЖИДАНИЕ НОВОЙ ЗАДАЧИ`. Предыдущая BLOCKED-запись в001 не изменена.
