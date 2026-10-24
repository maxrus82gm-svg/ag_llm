# Provenance: embedded claims отдельно от доверенного source

1. **CURRENT observation:** `evidence/binary_snapshot.json`, canonical pin в `inventory_receipt.json`, связь exact path с текущим дочерним процессом в `process_link.json`.
2. **Historical observation:** `reports/CODEX-WUA-0-V2RAY-BROKER-OFFLINE-001/evidence/engine_cached_metadata.json`; source SHA и совпадение engine SHA закреплены в receipt. Исторический hash не является официальным release digest.
3. **Module/build claims:** sing-box v1.13.4, Go1.25.8, VCS d09182614c7778c1e0f51d990635c5d4249c437e, modified=false. Эти строки содержатся внутри того же файла; независимого trusted source отсюда не возникает. Basename/module strings/version/build tags можно подделать.
4. **PE identity:** version resources отсутствуют, embedded certificate отсутствует. Catalog signing/издатель/release signature не проверены. Нельзя объявить signature-verified или source-match-verified.
5. **Matching sources/schema:** не предоставлены по известному разрешённому пути. Пять exact adjacent docs/source candidates отсутствуют; никаких disk/directory/package-cache searches или network fetch не было. Не делается вывод об отсутствии материалов в иных местах.

Go reader поддерживает только распознанный inline build-info layout в AMD64 PE, bounded varints и module sentinels. Другой layout, повреждение или неоднозначные markers → отказ, не guessing. Это небольшой metadata extractor с inert fixtures, а не официальный Go verifier/PE loader. Формат и извлечённые значения сопоставлены с отдельной read-only byte inspection; подлинность compiled code этим не проверена.

**Точный недостающий материал:** локальный очищенный release/source bundle **sing-box v1.13.4**, соответствующий заявленному revision **d09182614c7778c1e0f51d990635c5d4249c437e**, с подлинным upstream release digest/signature/provenance, matching source и dependency locks, configuration docs/schema для этой версии. Если официальная поставка не соответствует указанным claims/hash — явно зафиксировать mismatch, не подгонять digest и не заменять core. API keys, subscriptions, рабочий config и passwords не нужны.

Если пользователь решит исследовать V2Ray Core вместо существующего sing-box, нужен другой явно выбранный release и его аналогичный локальный bundle; имя продукта не заменяет exact version. Самостоятельно выбирать/скачивать его эта TASK не разрешает.
