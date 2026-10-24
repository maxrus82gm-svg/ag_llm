# Manual engineering review

Codex007, 2026-10-24; review доступных постановки/evidence/preparatory runner, **не review sing-box source и не независимая приёмка**.

- Разделены official tag mapping со слов WEB_11, локальные source bytes и EXE provenance. Совпадение revision не повышает последние два уровня.
- Проверен exact-path scope. Нет bundle path в B1/сообщении, proposed archive отсутствует. Не делается вывод о всём диске; никаких профилей/кэшей/памяти не исследуется.
- Ветви HTTP/default/fallback/DNS/helpers/config loader не реконструируются по названиям Go dependencies. Source locators остаются null, source tests/mutations NOT RUN.
- Existing pure regression использует прежний validator, свежий output и source pins; engine/CLI/loopback selectors исключены. 19 PASS означает сохранение guard behavior, не способность sing-box удовлетворять strict policy.
- Runtime/config/engine family не менялись. Новый bundle admission framework без архива не создавался. Это экономнее и точнее, чем synthetic source audit без подлинного source.
- Для будущего архива отдельно нужны безопасная bounded распаковка/проверка traversal/reparse links, независимый package pin и review real source branches. Нынешний отчёт не обещает, что архив с правильным именем автоматически доверенный.
- WFP, токены/наследование/loaded image, actual socket owner и no-DIRECT остаются native lab gates даже после будущего source review. Git/download/Windows mutations не разрешены отсутствием входа.

Вывод: разрешённый fallback **BLOCKED / SOURCE_BUNDLE_REQUIRED** обоснован. Истинные возможности движка пока не установлены; правильный следующий шаг — получить ровно запрошенный source input и возобновить source-only review.
