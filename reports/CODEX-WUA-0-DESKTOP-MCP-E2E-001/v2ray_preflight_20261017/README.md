# AMENDMENT 05 — комплект для независимой проверки WEB_10

Начать с `report.md`, затем `checks.json`, `manual_engineering_review.md`,
`manifest.json` и нужного source/trace.

**PARTIAL / AWAITING INDEPENDENT VERIFICATION.**

- SOCKS5 inbound 10808 подтверждён без CONNECT или remote destination.
- 19/19 Python reference TLS/CONNECT tests PASS: 17 сценариев + 2 quality controls.
- Real Go client transport tests не выполнялись: 8 fault groups BLOCKED.
- Remote V2Ray route, real fail-closed и ordinary Chat E2E — NOT VERIFIED.
- Hosted tunnel не запускался; прежняя блокировка не изменена.

Все данные для публикации очищены. Raw private GUI/DB и TEMP private TLS key не
включены; см. `not_published.json`. Проверка project ignore без Git —
`publication_precheck.json`; окончательный состав commit/push проверяет пользователь.
Это LOCAL ONLY, не подтверждённая публикация GitHub.

Повторять tests на копии `isolated_proxy_suite.py` в новом disposable TEMP, чтобы
не перезаписать сданные результаты. Команда/версии/source pin в `final_execution.json`
и `versions.json`. Stdio WUA, production, другие MCP и живой V2Ray стендом не изменяются.
