# WEB26 — H-CODEX-000025 / S2 isolation oracle — независимая приёмка

**TASK:** `CODEX-RT002-B2-S2-ISOLATION-ORACLE-REPAIR-001`; **HISTORY:** `H-CODEX-000025`; 08.11.2026.
**User publication:** main №544 `f52363a1bd1507d9cc62f9ce5b7ca5d08375000e`, parent `0ee846a1159c690d2bc29eab46fca807e4027541`.
**VERDICT:** **PASS / TARGETED INDEPENDENT WINDOWS OFFLINE S2**. Документационная итерация H25 закрыта; S3a/Stage6/S3b/live не приняты.

## Опубликованные исходники и фактические проверки

GitHub №544 изменил один инженерный файл `test_rt002_s2_budget_policy.py`; standalone S1/S3a suites, ledger, policy, transport и production runtime не менялись. Reviewer сверил SHA-256 S2 `a7fa9b5d2bcf56dc8f037dd726679a8439c4b1f3135de969b9084bf8d3870d2c` с task manifest и Windows Get-FileHash, S1 `35426388b49eb4a8154f5dfe8717ff4f3796b315ce3b391a71db6834e4a09696`. Не заявляется независимая побайтовая проверка всех 202 файлов или 122 manifest entries. `.obsidian/workspace.json` не затрагивался verifier.

**Инструмент:** авторизованный Windows DESKTOP-SC96D3U, Python 3.12.10. **Независимо исполнено:** полный S2 guarded **73/73 PASS**, gate PASS, exit0, 0 ERROR/SKIP/isolation (log SHA-256 `c52d2912cacd3e75696666c42d318bad2033a88f744e2b3043df193ca96a6d4e`); S2 import quality **47/47 PASS**, без ERROR/SKIP/isolation; три ослабления oracle обнаружены как **43 FAIL/47, 1 FAIL/47, 1 FAIL/47**, все exit1; неизменный S1 полный guarded **69/69 PASS**, exit0, 0 ERROR/SKIP/isolation (log SHA-256 `082194f8d71d8cb86752352bb3c9b6079f729f3a56f80139740117cf6c04be0e`). Сводка команд и статусов: `reports/CHATGPT-WEB26-CODEX-RT002-S2-REVIEW-20261108/independent_runs.json`. Полные независимые test logs лежат в TEMP Windows, не выдаются за опубликованные GitHub artifacts.

**Авторский baseline:** S2 72/73 FAIL до исправления; WEB25 независимо воспроизвёл его на предыдущей H24 ревизии. H25 pre-repair source отдельно WEB26 не переисполнялся. **Не повторены WEB26:** H25 S1 extra 23 (WEB25 раньше независимо 23/23 на неизменном S1), S3a 35 (только авторская regression), full CI, S2 optional provenance, UI, GigaChat/OAuth/paid/live, hardware power-loss, clean-host portability.

## Инженерный verdict и NEXT

Новый S2 oracle отделяет точную standalone OFFLINE ledger capsule по фиксированному AST hash от производственных consumers; отрицательные проверки обнаруживают прямую и транзитивную цепь `production → ledger → policy`, aliases/dynamic loaders и изменённую capsule. Это **static snapshot/source guard**, не реальное блокирование POST, не гарантия для произвольного runtime monkeypatch, native/remote plugins, hostile source replacement. H24 исторический S2 FAIL не переписывается, а `S2-OFFLINE-LEDGER-ISOLATION-ORACLE` закрывается в ограниченном объёме.

**OPEN:** отдельная независимая S3a 35-test acceptance; Ordinary Chat route/profile/numeric policy USER decisions; RAW wire retention, ledger adoption, fencing, trusted NOT_SENT, dynamic S3b physical-send coverage; S2 static import limits. **Stage6 S3b/Stage7/paid/live HOLD**. Следующий безопасный шаг — отдельное USER GO на независимую S3a приёмку и policy decisions; S3b implementation только после обязательных предшественников и отдельного назначения.
