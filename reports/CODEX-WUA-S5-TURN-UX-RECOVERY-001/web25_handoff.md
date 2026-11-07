WEB25, передаю по прямому поручению пользователя сдачу Codex 007 на независимую приёмку.
TASK: CODEX-WUA-S5-TURN-UX-RECOVERY-001
HISTORY ID: H-CODEX-000022
Статус автора: PARTIAL / RESULT READY / LOCAL ONLY; независимый PASS не заявлен.
finish: ROTATED / exit 0; БЛОК 1 WAITING, БЛОК 1.1 SUBMITTED / REVIEW PENDING.
Пакет: reports/CODEX-WUA-S5-TURN-UX-RECOVERY-001/; report.md, manifest.json, source snapshots/diff, RAW/HTTP/браузерные evidence и followups.json. Полный report приведён ниже.
Report SHA-256: f55b44d0e51ec3bf29cc9f77f9800a0dbb04128545bd6999e5842a1d7a90ec58
Финальные рабочие файлы: web_alarm/ui.py SHA-256 3b640ca58d062cce518d91169560c87f3756530963e4f01ffccbaa8797fa010b; web_alarm/ultra_chat.py SHA-256 91917a43846fa9f7830cdaaf8464e6d8473d10deae4629d582a0ccbe477fb825; test_web_alarm_ultra_chat_ui.js SHA-256 97c37ee6e7c8ce53e50b2d25046408ea2e44b1b64828a58eaf5ecc9c10d24ed7; test_web_alarm_ultra_chat_s5_recovery.py SHA-256 8cb69eb3451e8bb3b493407c071b1802cd81079d2412ed38150f0466bf265974.
Проверки: 52 JS PASS; 63 web Python PASS; 2 Tk отдельно PASS. Исходные RED, ImportError неверной среды и Tcl abort смешанного процесса сохранены. Не суммировать перекрывающиеся прогоны.
OPEN: исторический F3 RAW loss не воспроизведён (не закрывать автоматически), 480px визуальный gap, смешанный Tcl-process abort. F1/F2/F5 и выбранный Chat/немедленная метка отмены исправлены по bounded evidence, ожидают независимой проверки.
Git CLI/commit/push не выполнялись. Для требуемой исходной сверки использован только read-only GitHub GET main@1c43a3cb6f6fa0c1dcd6e96f265a8a33f37a7467. Пакет ещё не опубликован: не считать локальные пути доступными из веба или сам факт передачи независимой приёмкой. Публикация возможна только уполномоченной стороной одним атомарным нумерованным commit по назначению. Новую TASK и Stage6 автоматически не запускать.

--- ПОЛНЫЙ ОТЧЁТ ---
# Понятное состояние запроса и восстановление OFFLINE-чата

**TASK ID:** `CODEX-WUA-S5-TURN-UX-RECOVERY-001`  
**Дата / версия:** 2026-11-07 / 1.0, Codex 007  
**Статус:** PARTIAL / RESULT READY / AWAITING WEB25 INDEPENDENT REVIEW  
**Область:** Stage 5 OFFLINE, синтетические данные, fake transport.  
**Публикация:** LOCAL ONLY. Commit/push не выполнялись.  
**Baseline:** опубликованный main `1c43a3cb6f6fa0c1dcd6e96f265a8a33f37a7467`; адресная сверка read-only GitHub GET по требованию БЛОКА 1, без Git CLI.  
**Версия результата:** exact-byte SHA-256 и копии в `evidence/source_final.json`, manifest.  
**Независимый verifier:** ChatGPT WEB25; авторские проверки не являются независимой приёмкой.

## Результат

Исправлены недостаточный отклик проверки, ложная подпись прерывания активного
запроса, воспроизведённая гонка истории, потеря выбора Chat при F5 и задержка
обновления метки сообщения после отмены. Проверка по-прежнему читает сохранённое
состояние; Turn ID, idempotency, машина состояний и политика контекста не менялись.

Контролируемые отмены до старта и после старта сохранили user RAW побайтово,
HTTP-историю и идентичность запроса после повторного открытия. Историческое
наблюдение пользователя о потере RAW НЕ подтверждено и не объявлено закрытым.
На исходном UI воспроизведён переход в другой, самый новый Chat при reload;
это объясняет исчезновение в нашем контролируемом сценарии выбора, но не
доказывает причину прежнего эпизода пользователя без его исходной трассы.

## F1–F6: отдельные авторские статусы

| Пункт | Статус | Доказательства / границы |
| --- | --- | --- |
| F1: отклик проверки | FIXED / VERIFIED bounded | Начало «Проверяем состояние запроса…», блокировка повторного нажатия до ответа, результат с номером проверки даже для неизменившегося статуса; отдельные no-request и error. JS RED 2 FAIL → GREEN; реальный браузер дважды проверил успех и показал ошибку после остановки собственного стенда. Новых POST при check нет |
| F2: активный запрос назван прерванным | FIXED / VERIFIED bounded | Stage5 берёт состояние у владельца TurnService, не выводит прерывание из одного RUNNING в индексе. READY→pending, ATTEMPTING→running, lost-owner→UNKNOWN/unknown, CANCELLED/FAILED имеют отдельные метки. Реальный fake barrier: interrupted RED → running GREEN; lost-owner сохраняет UNKNOWN; браузер показывает «Выполняется» |
| F3: отмена/F5 | FIXED selection + cancel badge / NOT REPRODUCED RAW loss / STILL OPEN historical cause | HTTP отмены до/после старта, hash RAW, та же identity, новая оболочка сервиса, replay, история и пагинация проверены отдельно. JS RED доказывает выбор newest вместо selected; pointer теперь восстанавливается по проверенным спискам. Реальный браузер сохранил A после F5 и отменённый user. Историческая потеря RAW не доказана |
| F4: RAW, история и контекст | VERIFIED / policy UNCHANGED | Отменённый/UNKNOWN user сохранён и виден, но отсутствует в payload следующего запроса. Следующий контекст в двух контролируемых случаях: system + новый user. Одна подтверждённая завершённая пара по-прежнему подбирается существующим Stage5-селектором; молчаливого включения UNKNOWN нет |
| F5: гонка GET истории и проверки | FIXED / VERIFIED deterministic | Старый GET истории, начатый проверкой, удержан барьером; новый POST/GET показал NEW ANSWER, затем старый ответ затирал его: RED. Номер history request отбрасывает поздние данные/ошибки/older pages. Дополнительно проверены устаревший Turn GET и поздняя ошибка проверки после успешного POST |
| F6: русские надписи, ширина, клавиатура | VERIFIED bounded / STILL OPEN 480px capture | Реальный Chromium: название, tooltip через accessibility Help, Enter, Tab на «Новый отдельный запрос», normal и 720px, error при обрыве. Скриншоты сохранены. Первый full-page снимок 480px некорректен; уточняющее чтение раскладки получило timeout инструмента. Причина не установлена, 480px PASS не заявлен; viewport возвращён в обычный режим |

Все шесть исходных FOLLOWUP передаются WEB25, а не автоматически закрываются.
Точные остатки и критерии приёмки: [followups.json](followups.json).

## Реализация и scope

Изменены четыре рабочих файла:

- `web_alarm/ui.py`: компактная область состояния между историей и composer;
  русские ответы проверки; защита устаревшей проверки по ticket/revision;
  последовательность history requests; Stage5-only preference выбранных
  Workspace/Chat; немедленное чтение истории после подтверждённой отмены.
- `web_alarm/ultra_chat.py`: Stage5 user outcomes выводятся из проверенного
  TurnService view, включая active owner и UNKNOWN. Assistant по-прежнему
  требует сохранённый подтверждённый ответ. RAW не переписывается чтением.
- `test_web_alarm_ultra_chat_ui.js`: восемь адресных JS-регрессий с управляемыми
  обещаниями; выполняется реальный поставляемый inline-клиент в прежнем DOM adapter.
- `test_web_alarm_ultra_chat_s5_recovery.py`: три новых integration cases на
  собственных TEMP Workspace, HTTP, fake/barriers, hashes и context payload.

Других рабочих файлов не меняли. Новые отчётные driver/validator scripts и
evidence находятся только в собственной папке задачи. Diff создан `difflib`,
не Git: `evidence/changes.diff`. Точные before/final snapshots сохранены.

В Stage5 TEST проверка остаётся доступной как диагностика; постоянной тяжёлой
панели не добавлено. Это разрешённое TASK исключение для TEST. Готовый Stage6/live
UX, автоматический polling и перенос в всплывающее уведомление не вводились.

## Отмена, RAW, HTTP и контекст

`evidence/controlled/cancel_before.json` и `cancel_after.json` содержат:
Workspace ID, Chat ID, Turn ID, message ID; HTTP-представления до отмены и
после нового экземпляра сервиса; точные user RAW UTF-8 байты и hashes до/после;
outcomes, replay того же ключа, число fake sends и следующий model payload.

До исполнения барьер удерживает существующий `_execute` при READY. Cancel
даёт CANCELLED, physical fake sends = 0. После старта барьер удерживает fake
transport при ATTEMPTING. Cancel даёт UNKNOWN, physical fake sends = 1;
поздний ответ не публикуется как успех. Повтор исходного ключа не вызывает
новую физическую попытку. Хеш user RAW до/после совпадает в обоих случаях.

После повторного открытия сервер возвращает тот же message ID; маленькая
страница limit=1 может его не содержать, но older pagination возвращает его.
Ни classifier, ни отмена не удаляли RAW в этих тестах. Это bounded результат,
не доказательство сохранности исторического сообщения пользователя.

Сохранённый RAW — история исходных данных. Видимость — выбранный Chat,
страница и представление истории. Контекст — отдельный ограниченный подбор
данных следующего запроса. Эти три слоя проверены раздельно. Неподтверждённое
сообщение нельзя считать включённым в контекст лишь потому, что RAW сохранён.

## Браузерные доказательства

Встроенный Chromium управлял только `browser_fixture.py` этой TASK: собственные
TEMP root, синтетические A/B и fake replies. Это временный test driver, не
третья постоянная точка запуска и не изменение профиля пользователя.

Первый запуск с pipe получил EOF и завершился до браузерных действий. Рабочий
PTY-стенд использовал порт 65326; финальная версия после правки cancel badge —
50606. URL/identity и source hash сохранены в соответствующих session.json.
Оба стенда штатно остановлены через Enter; синтетические RAW/истории и payloads
скопированы в пакет до уборки только собственных TEMP fixture roots.

Ранний прогон показал SUCCESS, две явные проверки, active→running, отмену→UNKNOWN,
F5 в том же A, пустой B и возврат в A. Его картинки: `evidence/browser/`.
Именно там замечено запаздывание message badge после cancel; отдельный RED
тест добавлен до минимальной правки и затем прошёл. Финальный браузерный
прогон на текущем ui.py подтвердил немедленный UNKNOWN в message badge,
reload выбранного A, читаемую ширину 720px и error при выключенном своём сервере.

Финальные доказательства: `evidence/browser_final/cancel_badge_immediate.jpg`,
`reload_dom.txt`, `narrow_720.jpg`, `check_error.jpg`, `check_error_dom.txt`,
`session.json`, сохранённые RAW и `fake_transport_requests.json`.
Никакие сообщения/RAW из пользовательского TEST или STANDARD не читались и
не менялись для этого прогона. Screenshot 480px и timeout сохранены как ограничение,
не как успешная визуальная проверка. Нативный Chrome не использовался.

## Проверки: команды, counts и исходные неуспехи

Сводка: [test_summary.json](evidence/test_summary.json), исходные stdout/stderr
в `evidence/`. Не складывать перекрывающиеся target и regression runs.

| Прогон | Результат |
| --- | --- |
| F1 RED, `node --test --test-name-pattern="S5 UX" test_web_alarm_ultra_chat_ui.js` | 2 FAIL; нет отклика/результата проверки |
| F2 первый запуск system Python 3.13 | ERROR импорта: отсутствует httpx; это ошибка выбора среды, не product assertion |
| F2 RED в проектной .venv Python 3.12.10 | 1 FAIL: interrupted != running |
| F1/F2 target GREEN | 2 JS + 1 Python PASS |
| F3/F5 JS RED | 2 FAIL (stale history, newest Chat) + 1 PASS (старый Turn GET) |
| Cancel badge RED | 1 FAIL: после отмены оставалась старая running-метка |
| Финальный JS, `node --test test_web_alarm_ultra_chat_ui.js` | 52 PASS, 0 FAIL/SKIP/CANCELLED |
| Guarded web Python: `run_python_checks.py --web-only test_web_alarm_ultra_chat test_web_alarm_ultra_chat_s5 test_web_alarm_ultra_chat_s5_recovery test_web_alarm_ultra_chat_turn_http test_web_alarm_ultra_chat_turn_service` | 63 PASS, 0 FAIL/ERROR/SKIP; две Tk cases явно не входят в этот процесс |
| Две Tk cases отдельно, каждая своим guarded .venv child | 1 + 1 PASS; не являются новым browser proof |
| Финальный recovery selector после усиления сохранения RAW evidence | 3 PASS, входит в те же 63 случая, не дополнительные случаи |
| Python AST и `node --check -` inline-клиента | PASS; сводка `evidence/syntax.json` |
| Пакет до/после finish | Scope, hashes, RAW, counts, ссылки и сохранность слотов; `package_check_*.json` |

Первый объединённый Python-процесс с Tk и последующими многопоточными HTTP
тестами аварийно завершился с exit 2147483651: Tk Variable destructor,
`RuntimeError: main thread is not in main loop`, `Tcl_AsyncDelete: async handler
deleted by the wrong thread`. Этот прогон НЕ PASS и не замаскирован повтором.
Рабочий код Tk не меняли. Web выбран отдельным процессом; две исключённые Tk
cases отдельно прошли. Причина смешанного process-level Tcl abort не исследована
вне необходимого разделения и остаётся OPEN для воспроизводимости regression runner.

Существующий ранний OFFLINE guard установлен до imports: сеть только loopback,
блокируются credentials и Git metadata/live writes. Зарегистрированные deny
события принадлежат намеренным negative controls прежнего Stage5 guard-test;
реальные запросы провайдерам не выполнялись. Числа/границы сохранены в сводке.

NOT RUN: полный Web Alarm/всего репозитория suite, CI, реальный LLM/OAuth,
другие платформы, подтверждённая исправность 480px, исторический пользовательский
эпизод с его исходными RAW/Turn IDs. Ручная приёмка WEB25 ещё не выполнена.

## Инженерный review и остаточные риски

Проверены: неизменяемость ключа при recovery; отсутствие POST при check;
консервативная отмена; lost owner не становится running; SUCCEEDED требует
проверенного assistant RAW; старые status/history replies и errors не затирают
новые; stale older pages не держат olderBusy навечно; corrupt/foreign selection
не порождает чтение произвольного Chat; два Chat изолированы; standard/read-only
регрессия проходит. Pointer выбора — только Stage5 preference и принимается
после проверки по текущим спискам Workspace/Chat, не новый источник полномочий.

OPEN: историческая причина F3 (не считать RAW loss закрытым), 480px render/capture
gap, смешанный Tcl-process abort. F1/F2/F5 и воспроизведённые части F3 исправлены
по авторским тестам, но ожидают независимого WEB25 verdict. Текущий блок TASK
не даёт GO на Stage6, новую систему контекста, production или broad refactor.

## Сохранность, DOC IMPACT и сдача

`Start_WebAlarm_Standard.cmd`, `Start_WebAlarm_Test.cmd`, старые launchers/config,
`web_alarm/turn_service.py`, `context_storage.py`, `web_alarm/server.py` и прежний
Stage5 Python suite не менялись. Защищённые рабочие файлы сверяются с before
побайтово. Пользовательские профили не переключались и не перезапускались;
STANDARD не запускался исполнителем. Собственные временные HTTP servers остановлены.

Некоторые legacy traceback содержали локальный home path. В публикуемых логах
он заменён на `<USER_HOME>`; исходные hash и mapping сохранены в
`evidence/sanitization.json`, оригиналы только в частном TEMP task-archive.
Runtime tokens/секреты в пакет не включены. `.gitignore` не изменялся;
Git tracking/publication остаются NOT VERIFIED, Git CLI не использовался.

DOC IMPACT: общая документация, БЛОКИ 2–4 и независимый verdict не редактируются.
Штатный finish меняет только разрешённые слоты/служебную историю. Дословная TASK,
прежний слот и readback сохраняются штатным скриптом. USER launch не менял scope,
поэтому `--no-chat-amendment`; текст запуска сохранён отдельно.

NEXT: WEB25 проверяет локальный пакет по report/source hashes; после публикации
уполномоченной стороной одним атомарным нумерованным commit — независимая
приёмка конкретной версии. F1–F6 не переводить все в CLOSED автоматически.
Новый TASK не назначался. Финальные HISTORY ID и состояние карточки —
`closeout.json` / `finish_protocol.json`; квитанция передачи WEB25 —
`web25_delivery.json`. Передача сообщения не означает независимый PASS.

