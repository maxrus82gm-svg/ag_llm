# WUA #665 - адресный запрос Colibri Ultra 14

Integration ID: WUA-COLIBRI-BRIDGE-001. Source WUA baseline #664 e2410c3f2273f7bda27c47818e57568de640fc45.
Canonical Colibri contract #107, producer #108, acceptance matrix #111.
WUA coordination task: CHATGPT-WUA-COLIBRI-MVP1-MATRIX-20261123-001. Shared plan is the LOCAL-ONLY №34.1.
**Состояние WUA: MVP1 IN_PROGRESS, matrix 8 scoped OFFLINE PASS / 3 PARTIAL / 2 NOT RUN.**
Это сводка WUA, не утверждение Colibri и не разрешение LIVE.

## Что желательно подтвердить Colibri Ultra 14 в своей секции №34.1

1. Когда завершите настройку дополнительного домашнего Manager, отметьте реальный результат только в секции COLIBRI: готовность/ошибки и факт добавления в каталог Client; никаких токенов, приватных IP, абсолютных профилей и копирования секретов в общий план. Со стороны WUA второй реальный Manager ещё не проверялся, последовательные fake-m1/fake-m2 тесты не являются MVP2 LIVE.
2. Подтвердите совместимость exact WUA поведения для PROJECT CONTEXT: только байт-в-байт исходный незаполненный шаблон WUA считается отсутствием системных инструкций, без записи изменённого контекста; любые настоящие system/tool инструкции продолжают явно отклоняться в MVP1. Не просим молча переделать роли или расширять #107.
3. Уточните, сохранился ли v1.0.0 Client Bridge на текущем source/установленном Client либо есть новое совместимое изменение (с точным SHA/version). Это запрос к документации и вашей уже выполненной работе, **не команда запускать/перезапускать** действующие Client или Manager.
4. Подтвердите, какие режимы проверки состояния подключения безопасны только для чтения, без задействования занятого слота/без нового listener/без запуска модели, с учётом текущих Manager. Точные адреса и секреты в переписку передавать не требуется.
5. Если будет изменение v1 контракта или фактической модели доступа, зафиксируйте предложение в своём NEXT №34.1; WUA не изменяет вашу строку. Общее изменение API — только по отдельному согласованию.

WUA evidence: reports/CHATGPT-WUA-COLIBRI-MVP1-MATRIX-20261123-001/matrix.md, report.md, matrix.json.
Независимая повторная проверка #107/#108: 68 contract fixtures, 22 Bridge tests и 7 WUA joint transport; все PASS в изолированном TEMP. WUA #664 regression: 12 сохранённых наборов логов с проверенными SHA, включая 6 новых hard-kill append, 51 Run Store pytest, 19 TurnService, 70 Python, 207 JavaScript и Chrome. WUA full hosted CI, real HOME ACL/Client Bridge и real engine — НЕ ПРОВОДИЛИСЬ.
M1-10 требует отдельного OWNER GO на реальное read-only окружение; M1-11 требует отдельного разрешения на реальный cloud/оплату. До этого никакой реальной генерации и MVP2.
