# Manual engineering / adversarial review

Codex 007, 2026-10-24. Самостоятельный source/control-flow review после тестов; **не независимая приёмка WEB_11**. Изучены все новые исходники/schema/templates, применимые прежние common/security/route contracts, NPFS activation contract, WFP/toolkit disabled sources, cached engine metadata. Настоящий engine source отсутствует: review его поведения BLOCKED.

|Угроза / вопрос|Инженерный вывод и действие|
|---|---|
|F2 wrapper под B, socket пользователя|Base validator связывает process role v2ray с B SID; новый guard требует один PID listener/egress. User SOCKS layout/extra companions запрещены. Реальный effective token всё ещё NOT VERIFIED.|
|Routing precedence / default / fallback|Schema допускает только exact-route затем deny remainder, один outbound; любые fallback/direct/secondary flags отвергаются. Python-модель делает один literal loopback connect без retries. Реальные engine defaults неизвестны.|
|Подмена всего config вместе с receipt hash|Найдено при review: нельзя рассчитывать expected hash из предъявленного профиля. Исправлено: независимые controller-pinned profile/source hashes обязательны; отдельный regression `test_whole_config_substitution_still_uses_controller_pin`.|
|JSON schema пытается загрузить remote reference|Найдена зависимость offline validator от возможного `$ref`. Добавлен обход schema, запрещающий non-local `$ref/$dynamicRef` до jsonschema. Test с controlled local URL доказывает ноль dial attempts. Supply-chain самого jsonschema не доказан.|
|Повторный запуск stale fixture / claim|Добавлен exclusive claim до socket bind; повторная та же directory → FRESH_FIXTURE_REQUIRED. Новая попытка требует новый UUID/root. Same-user file deletion остаётся вне этой защиты.|
|Owner guard случайно удалён|Реальная source mutation удаляет combined PID/SID require. Неверная attestation проходит mutant, inner assertRaises получает 1 FAIL/0ERROR; внешний oracle замечает это. Никакой реальной B identity это не доказывает.|
|DIRECT в клиенте|Копия call заменена реальным direct GET к собственному T при отказавшем broker P. Независимый receiver видит parent PID, policy observer фиксирует DIRECT_OR_SECOND_PROXY. Поэтому oracle реагирует на effect, а не просто на JSON-флаг.|
|Listener takeover и PID reuse|Controlled P takeover parent process + wrong nonce отклонён; snapshot owner mismatch зафиксирован. Для реального B нужны held process/token/image и защищённая handshake/observer continuity; PID-alone недостаточен.|
|DNS/UDP/IPv6/env overrides|Generic contract запрещает; instrumentation rejects DNS/new UDP/IPv6; client запрещает proxy override/NO_PROXY. Domain names только `.invalid` payload. Native engine/environment behavior не выводится из Python tests.|
|Redirects/timeout/partial/reset|Bounded client/header/relay deadlines, single connect, без follow redirect/alternate proxy; exception прекращает собственную fixture. Нативные retry semantics не проверены.|
|Startup/restart/inheritance|Нет engine spawning/install/service APIs. Worker наследует очищенное окружение и запускается isolated Python; children запрещены audit hook. Future child effective SID/handle inheritance/logon rights требуют ОС и лаборатории.|
|Observer/policy loss, pre-existing flows|Contract требует STOP/NO_AUTO_RESUME, fresh generation, LAB_PROOF_REQUIRED. Synthetic stale/epoch check не является teardown настоящих flows. Нет тайного «успеха» по свежему JSON.|
|Source/config race и roots|Hash/attribute checks полезны для контролируемых tests, но same-user mutation между проверкой и выполнением остаётся TOCTOU. Поставку/ACL/config-open handles нельзя объявлять защищёнными до OS proof.|
|Заявленные engine metadata/approvals|Версия99.99, fake signature, all approvals=true не меняют постоянные gates. Native config всегда null; автоматической подстановки sing-box/Xray нет.|
|Resource lifetime|Own receiver sockets/threads/processes ограничены timeout, finally/terminate/wait; no auto resume. Exclusive reserved failed ports не дают отрицательному тесту случайно соединиться с новым чужим listener.|
|Regression isolation|54 byte-exact copies только необходимых legacy files. Hardcoded report roots старого runner оказываются внутри текущей TASK/mirror; прежние source/evidence сохраняются. Это не копия всего repo/.git.|
|Initial FAIL|CLI import defect и mutant harness missing __file__ исправлены отдельно; исходные результаты не удалены. Guard не был ослаблен ради зелёного теста.|

**Открытые блокеры:** выбранный V2Ray source/schema/binary; remote encrypted proxy protocol и peer trust; exact B token и socket owner; protected deployment/credentials; native WFP loopback/arbitration/DNS/IPv6/UDP/children/boot/observerloss/preexistingflows. Ни один не закрывается synthetic evidence. Следующий набор native selectors/prerequisites перечислен в `next_user_go.md`; на рабочем хосте они не запускались.

**Заключение исполнителя:** offline-кандидат годится для независимой проверки как версия контракта/fixture/preflight. Operational deployment, native compatibility, live F2 closure и ordinary Chat E2E остаются BLOCKED/NOT VERIFIED. Общие security/runtime компоненты менять для этой сдачи не понадобилось.
