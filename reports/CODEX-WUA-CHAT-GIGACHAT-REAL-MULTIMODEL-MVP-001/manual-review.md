# Manual engineering review — author, not independent acceptance

Прослежен путь HTTP token/Origin → OrdinaryApplicationChatService → saved per-chat model → existing snapshot loader → Turn owner → exact S2 bytes → ledger RESERVED/SENT/readback → shared OAuth → final physical check → common parser → ledger terminal → event → RAW → restart read. Run Store/context writer implementations не переписывались.

Найденные и исправленные проблемы:

1. Старый OAuth cache не связывал account/scope/credential и игнорировал expires_at. Исправлено в существующем owner, default access по-прежнему закрыт. Потокобезопасный nonblocking lock исключает event-loop deadlock и двойной refresh.
2. Parser отбрасывал usage раньше transport error envelope. Теперь получает допустимый numeric usage даже при model-version/HTTP rejection; total не складывается с cached/reasoning повторно. Злонамеренная version не публикуется.
3. Session expiry/close первоначально закрывал также обычные read-only history routes. Исправлено: registry/root binding отделён от active-send authority, для recovery используется no-sender Turn reader.
4. Token acquisition после SENT может окончиться ошибкой/отменой. Такой исход не объявляется NOT_STARTED: reserve остаётся и результат UNKNOWN. Перед physical send снова проверяются deadline/task cancel, durable owner, wire, session/counts.
5. Отличие response byte-bound от Turn/RAW bound могло оставить ответ без публикуемого RAW. Малый provider adapter приведён к существующему 8192 B response limit. Oversize становится ошибкой с сохранённой liability.
6. Required observed provider version проверялась, но первоначально терялась после нормализации. Теперь optional ProviderResponse.observed_model → result metadata → Turn response_model; event проверяет его по сохранённому model_contract, RAW producer distinguishes REAL.
7. Процессные call counters не обеспечивали restart fence. В существующем writer добавлены single-use grant и account-owner record; ACTIVE после crash требует отдельной reconciliation. Duplicate grant и parallel grant не отправляют запрос.
8. Optional cached field сначала менял старые usage dictionaries даже при отсутствии метрики. Восстановлена совместимость: cached subclass появляется только при известном значении. Сводка cache/full input дополнительна к старой known/missing форме.
9. S1/S2 closed-source pins обнаружили новые physical sinks. Добавлена адресная статическая reconciliation, полного исключения модулей из графа нет. Existing negative isolation/AST-mutant scenarios сохранены.

Риски, оставленные явно: server approval — доверенная Python composition, не криптографический approval service; actual caps/entitlement/цена не установлены; один Workspace/account/process; stale account marker не снимается автоматически; existing historical audit не adopted; legacy Tk context не угадывается; большого контекста/automatic compression/SSE нет. Проверка shared H37 accounting blocker не переоткрывает отозванную ошибку.

Мутации version/reserve выполнены in-memory в отдельных guarded processes. Обе обнаружены: вторичная durable binding/reservation проверка прерывает небезопасное исполнение; ожидаемые tests дают RED. Это отказ защиты, не успешный внешний запрос. Source files не мутировали. Финальные позитивные suites проходят без таких подмен.

Native Windows/Chromium визуальный осмотр и GitHub-hosted independent review остаются NOT RUN. Синтетический actual-app HTTP тест не называется LIVE; техническое состояние приложения отделено от owner UX.
