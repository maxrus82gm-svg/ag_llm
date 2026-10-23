# Следующий безопасный шаг

Сейчас разрешены handoff пользователю и независимое source/evidence review WEB_11; production activation не требуется. Пользователь публикует проверенный комплект обычным способом. Codex не выполнял Git/GitHub и не утверждает, что отчёт уже доставлен координатору.

WEB_11 может независимо сопоставить manifest, финальную source snapshot, exact selectors, SDK results, authority receipt/storage hashes, реальный DACL/token marker, OS wait и два security mutation controls. Повторный текущий-user fixture запуск — самостоятельное evidence, не обычный ChatGPT E2E. Отдельно проверить обратную совместимость и изменение allowlisted fixture roots в common.py.

Затем нужны отдельные адресные решения, а не разрешение «включить всё»:

1. Подготовленная изолированная Windows-лаборатория: разные реальные C/U tokens, least-privilege ACL + protected grant delivery, OpenProcess/token query rights, inherited/impersonated tokens, wrong peer/restart/session revoke, negative IPC and DNS/delegation. Рабочие accounts не использовать для такого эксперимента без нового USER GO.
2. Independent continuous native process/network observer от старта C relay и official Go client, положительные и отрицательные controls, actual WFP policy/fail-closed/boot ownership. До отдельного GO ничего не применять на рабочей Windows.
3. Самостоятельный B gate: выделенная V2Ray instance под B, native HTTP CONNECT и настоящий внешний socket того же B token → только approved literal R:Q. Никакого B-wrapper → пользовательский V2Ray/SOCKS и DIRECT/fallback. Текущий V2Ray не изменять.
4. Только после независимого принятия предыдущих границ и нового точного USER GO — официальный tunnel/Platform/workspace auth и ordinary ChatGPT E2E с четырьмя реальными вызовами (включая отказ other_task) и независимой сверкой серверного receipt.

Пока: CanApply=false, Install/Uninstall BLOCKED, HOSTED_TUNNEL_ON_HOLD_BY_USER. API keys и пароли в чат не передавать.
