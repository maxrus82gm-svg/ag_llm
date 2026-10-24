# NEXT USER DECISION

**Рекомендуемый следующий шаг:** разрешить **только source-only проверку sing-box v1.13.4 как кандидата**, не меняя пока engine family/контракт и работающий экземпляр. Для этого нужен один недостающий input: **локальный подлинный release/source bundle для v1.13.4 / заявленного revision d09182614c7778c1e0f51d990635c5d4249c437e**, с проверяемым upstream digest/signature/provenance, matching source/dependency locks и versioned configuration docs/schema. Текущий file SHA256: `ca74563c93440a2e9cb73eae6a04c109d3f5efce36a385f8261a654e362d2ea3`.

Передать только разрешённый локальный путь к очищенному bundle и его происхождение; рабочие profiles/subscriptions/API keys/passwords не нужны. Несоответствие официальным source/hash должно стать finding, а не поводом подогнать метаданные. Сетевой поиск/загрузка/запуск core этой TASK не разрешены.

Если пользователь принципиально сохраняет требование именно **V2Ray Core**, альтернативное решение — явно назвать release и предоставить аналогичный local source/binary/schema bundle **вместо** sing-box направления. До этого не выбирать версию по памяти и не искать установленный core по всему диску. Наличие нынешнего sing-box само по себе не разрешает его deployment.

После source review пользователь принимает отдельное engine-selection решение. Если sing-box выбран, нужен адресно согласованный minimal schema/native mapping change; название STRICT_V2RAY_BROKER и общие docs также согласуются с координатором. Если V2Ray выбран, проверяется его exact binary/source/config. Общая C/B/NPFS архитектура не переписывается.

Любое последующее provisioning, account/SID/ACL/WFP изменение и native/network запуск — **другой USER GO после доказанной OS-level лабораторной изоляции**. Два обязательных доказательства: один настоящий B process владеет CONNECT listener и remote R:Q socket; независимая политика исключает DIRECT/DNS/UDP/IPv6/companion/fallback и останавливает цепочку при drift/observer loss. Hosted tunnel остаётся HOLD, ordinary Chat E2E NOT VERIFIED.
