# 🟨 Web Alarm Ultra: первый веб-интерфейс подключений, вкладка EVM (`CLAUDE-WUA-1-EVM-CONNECTIONS-001`)

**ARCH CLASS:** Web Alarm Ultra / Connections (WUA-1). **PRIMARY:** 36.2 (Web Alarm testing); **SECONDARY:** 37 (стратегия «одно ядро Ultra»), 23 (серверные границы), 11/19 (модели и API — только чтение). **Платформа:** Windows 10 Pro 19045, Python 3.12.10 (`.venv`), node v22.20.0; guarded runner `wa4a_acceptance.py` через `tools/run_gate.py` (одноразовый TEMP). Git/GitHub, сеть, credentials, MCP, Windows/proxy не использовались.

## 1. Итог

| | |
|---|---|
| Статус | **RESULT READY / AWAITING INDEPENDENT VERIFICATION** (не DONE/VERIFIED). Полная регрессия в окружении как в CI: **1004 = 1002 PASS / 0 FAIL / 0 ERROR / 2 SKIP (symlink), isolation 0**; JS 9/9 + 77/77; мутанты 16/16 |
| Что сделано | Вкладка «EVM · Подключения Ultra» в верхней панели Web Alarm; три колонки **API · MCP / Агенты · Локальные LLM**; в API — все модели общего `model_registry.py` (сейчас 6 GigaChat) с реальными `model_id` и `provider_model_id`, выбор модели для будущего Ultra Web Chat, отображение сохранённого выбора, возврат к операторской панели |
| Архитектура | **Одно ядро:** каталог на каждом чтении строится из `model_registry.list_model_specs()`, проверка выбора — `get_model_spec()` (его же правила disabled/unknown). Новый слой хранит **только ссылку** (`connection_id` + `model_id`) в хранилище Web Alarm. Второго реестра, копии OAuth, импорта `gigachat_transport.py`, чтения credentials, сетевых вызовов нет; Tkinter `ui_state.json` не читается и не пишется |
| Статусы | Честные локальные факты: `REGISTERED` / `DISABLED` (из реестра), `verification: UNVERIFIED` всегда; в UI — «В реестре» + «API не проверено». Наличие в реестре не выдаётся за подключение |
| Изменённые файлы | `web_alarm/ui.py`, `web_alarm/server.py`; новые `web_alarm/ultra_connections.py`, `test_web_alarm_ultra_connections.py`, `test_web_alarm_evm_ui.js` |

## 2. Source preflight (адресно, без повторного исследования)

- `model_registry.py`: `ModelSpec(model_id, display_name, provider, provider_model_id, enabled, is_local)`, `MODEL_REGISTRY` (`MappingProxyType`), `get_model_spec()` (ValueError пусто / KeyError неизвестно / RuntimeError отключено), `list_model_specs()`. Чистый модуль: без I/O и сети.
- `gigachat_transport.py`: импортирует `httpx` на уровне модуля, credentials читаются только внутри `get_access_token()` из `GIGACHAT_CREDENTIALS` / `GIGACHAT_SCOPE`. **Не импортируется** новым слоем.
- `ultra_ui.py`: `_open_model_registry(assignment)` и `_set_main_chat_model()` берут модели из того же реестра; назначение хранится в `_ui_state["main_chat_model_id"]` → `ui_state.py` `STATE_PATH = …/ui_state.json`. Веб-выбор хранится **отдельно** и это назначение не меняет.
- `server.py` (старая Ultra): `run_agent_task()` → `get_model_spec(selected_model_id).provider_model_id` (стр. ~3740–3746) — тот же контракт разрешения переиспользован в `resolve_provider_model_id()`.
- Запуск Web Alarm (`python -m web_alarm` из корня, `wa4o_ui_launcher.py` с `cwd` = корень) кладёт корень в `sys.path` → обычный `import model_registry`; при неудаче — честный `REGISTRY_UNAVAILABLE`, без запасной копии.
- Параллельные работы: БЛОК 1 Codex — `CODEX-WUA-0-WINDOWS-ISOLATION-READINESS-001` (HOLD), `web_alarm/` не затрагивает; TOCTOU-направление (LLM 15) касается механизмов мутаций — они не менялись.

## 3. Реализация

### 3.1 `web_alarm/ultra_connections.py` (новый, ~265 строк)

- `connection_id = api:<provider>:<model_id>`; строгий разбор (ASCII, ≤ 200, ровно 3 части, kind `api`); provider сверяется с реестром.
- `catalog()` — три колонки; API = вид каждой `ModelSpec` (+ `selected`); MCP / Локальные — `NOT_CONNECTED`, пусто; `network_calls: 0`. Чистое чтение: не создаёт ни каталогов, ни файлов.
- `selection(role="chat")` — состояния `NOT_SELECTED` / `SAVED` / `CORRUPT` (файл не читается или схема чужая — **не подменяется значением по умолчанию**) / `INVALID_REFERENCE` (модель исчезла или отключена в реестре) / `REGISTRY_UNAVAILABLE`.
- `select(role, connection_id)` — только роль `chat` (другие роли старой Ultra не переносились); проверка через реестр; запись под `InterProcessLock`, temp + fsync + `os.replace`; повреждённый прежний файл **сохраняется рядом** (`connections.json.corrupt-<id>`); роли более новой версии в файле сохраняются.
- `resolve_provider_model_id(role)` — для будущего Ultra Web Chat: существующий `provider_model_id` сохранённого выбора, иначе отказ.
- Хранилище: `<storage_root>/ultra/connections.json` (локальное хранилище Web Alarm, вне Git и вне Workspace проекта).

### 3.2 `web_alarm/server.py` (+ ~40 строк)

- `GET /ultra/connections` — каталог (только GET, иначе 405).
- `GET /ultra/connections/selection[?role=chat]`, `POST /ultra/connections/selection {"role":"chat","connection_id":…}` (иначе 405). POST идёт через существующий `_read_body` (только `application/json`, лимит размера) — тот же механизм, что у всех POST Web Alarm, второго не вводилось.
- Ошибки: 400 `invalid_connection_request`, 404 `unknown_connection`, 409 `connection_disabled`, 503 `model_registry_unavailable`, 409 `connections_state_error`; `/status` → capability `ultra_connections`.
- Механизмы mutation / recovery / CAS / WA4-R не затронуты: новые маршруты стоят перед прежними и не вызывают их сервисы.

### 3.3 `web_alarm/ui.py` (+ стили, разметка, ~95 строк JS)

- Верхняя панель: группа «Операторская панель | EVM · Подключения Ultra» (`aria-pressed`) в свободной средней области между брендом и правыми действиями (**допущение**: скриншот пользователя с отмеченным местом мне недоступен — взято описание из 37).
- Представление `#evmView` — отдельная `<section>` (регионы `aside/main` прежние); три колонки `repeat(3, minmax(0,1fr))`, на ≤ 850 px — одна колонка; «+ Добавить — следующий этап» — неактивная подпись, не кнопка.
- JS: запросов нет, пока вкладка не открыта; ответ строго проверяется; весь текст — `textContent`; на время сохранения кнопки заблокированы (один POST); после любого исхода список перечитывается с сервера; при возврате — прежняя операторская панель без запросов к подключениям.
- В странице нет ни одного `model_id` / `provider_model_id` — список приходит только с сервера.

## 4. Тесты

**Новые Python (`test_web_alarm_ultra_connections.py`, 15 методов):** каталог = реестр (сравнение с `list_model_specs()`, не с копией; изменение реестра видно сразу); 6 GigaChat; страница без копии моделей; выбор **каждой** модели и `model_id → provider_model_id` = `get_model_spec()`; GigaChat 2 Pro / 3 Ultra переживают перезапуск; хранится только ссылка; отказы (10 неверных `connection_id`, чужая роль, отключённая модель) без записи; исчезнувшая/отключённая сохранённая модель → `INVALID_REFERENCE`; 7 видов повреждения файла → `CORRUPT`, чтение не чинит файл, новый выбор сохраняет испорченный оригинал; роли новой версии сохраняются; 12 конкурентных выборов → один валидный файл; недоступный реестр (с сохранённым выбором и без); чтение не пишет и не открывает сеть (`socket` заблокирован) и не импортирует транспорт; Tkinter `ui_state` не читается/не пишется; настоящий HTTP: секрет-маркер в `GIGACHAT_CREDENTIALS` не появляется ни в телах ответов, ни в stdout/stderr, ни в `logging`, ни в хранилище; `text/plain` POST → 415.

**Новые JS (`test_web_alarm_evm_ui.js`, 9 тестов, исполнение настоящего скрипта страницы в `node:vm` с фиктивным DOM, модели в фикстурах вымышленные):** E1 по умолчанию операторская панель, 0 запросов к подключениям; E2 открытие → ровно каталог сервера, пустые MCP/Локальные; E3 один POST `{role, connection_id}`, кнопки заблокированы на время сохранения, сохранённый выбор показан; E4 отказ сервера → ошибка и перечитывание; E5 искажённый/ошибочный ответ → ошибка, 0 карточек; E6 честные тексты `CORRUPT / INVALID_REFERENCE / NOT_SELECTED / REGISTRY_UNAVAILABLE`; E7 отключённая модель не выбирается, разметка из сервера остаётся текстом; E8 возврат к операторской панели и «Обновить»; E9 в странице нет списка моделей и `innerHTML`.

**Качество (TEST-QA, `tools/mutants.py`, копии кода в TEMP):** P1 каталог-копия, P2 неверный `provider_model_id`, P3 повреждение как «не выбрано», P4 отключённая модель принимается, P5 выбор не сохраняется, P6 чтение создаёт хранилище, P7 испорченный файл не сохраняется, P8 «VERIFIED» вместо UNVERIFIED, P9 роль игнорируется; U1 запрос при загрузке, U2 нет защиты от двойного клика, U3 нет перечитывания после отказа, U4 разметка через `innerHTML`, U5 нет проверки ответа, U6 нет пути назад, U7 отключённая модель выбирается — **16/16 убиты**, оба контроля (`P0`, `U0`) PASS.

| Прогон | Итог |
|---|---|
| JS до изменений `test_web_alarm_operator_ui.js` | 77/77 PASS (наблюдение в сессии) |
| `existing-ui-server` — UI, UX, operator UI, server, launcher (после изменений, до новых тестов) | 49/49 PASS, isolation 0 |
| `new-py-1` — новые Python | 14/14 PASS (до добавления 15-го метода) |
| `focused-2` — новые Python + прежние UI/server | **64 = 64 PASS**, isolation 0 |
| `node-final` — `test_web_alarm_evm_ui.js` / `test_web_alarm_operator_ui.js` | **9/9** / **77/77** PASS |
| `mut1` | 16/16 мутантов убиты, контроли PASS |
| **`full-ci` — `all`, окружение как в CI (`TMPDIR=TEMP=TMP`)** | **1004 = 1002 PASS / 0 FAIL / 0 ERROR / 2 SKIP, isolation 0, exit 0** — 989 прежних + 15 новых методов; SKIP — 2 symlink-теста (нет привилегии на этом хосте), как в прошлых прогонах |

**NOT RUN:** визуальная проверка в настоящем браузере (встроенный браузер этой сессии не открывает локальные серверы, а запуск через `.claude/launch.json` — вне write-scope); реальные API/token/health-проверки GigaChat (запрещены на этом этапе); новый JS-файл **не входит** в шаг CI `node --test test_web_alarm_operator_ui.js` — CI YAML менять запрещено (см. §7).

## 5. MANUAL ENGINEERING REVIEW / adversarial pass

- **Второе ядро?** Нет: каталог не хранится, каждое чтение идёт в `model_registry`; мутант P1 (зашитый список шести моделей) убит.
- **Тихая подмена при повреждении?** Нет: `CORRUPT`, файл не трогается до явного выбора, оригинал сохраняется (P3, P7).
- **Найдено и исправлено в ходе pass:** при сохранённом выборе и недоступном реестре весь каталог отвечал бы 503 → добавлено состояние `REGISTRY_UNAVAILABLE` у выбора и тест.
- **Секреты / сеть:** модуль не содержит `os.environ`/`getenv`/`gigachat_transport`/`httpx` (проверяется тестом по исходнику); HTTP-ответы — только поля `ModelSpec` (не секретны) и выбор.
- **Чужой источник:** POST требует `application/json` → межсайтовый запрос невозможен без preflight; сервер OPTIONS не обслуживает. Проверка Host/Origin для обычного API Web Alarm (DNS rebinding) — существующая общая граница, не изменялась (см. §7 P2).
- **Конкурентность:** межпроцессная блокировка + атомарная замена; последний выбор побеждает; временных файлов не остаётся.
- **Совместимость:** прежние UI/server/operator тесты и JS 77/77 зелёные; регионы, уникальность `id`, отсутствие `innerHTML`/`https://` сохранены; `/status` — только добавлена capability.

## 6. Защищённое и неизменённое

Старая Ultra — только чтение: `model_registry.py`, `gigachat_transport.py`, `ultra_ui.py`, `server.py`, `ui_state.py` (SHA в `manifest.json` → `read_only_ultra_core`). Не менялись: механизмы mutation/recovery/CAS/TOCTOU, режимы WA4-R, `wa4a_acceptance.py`, существующие тесты, CI YAML, MCP, credentials, карточки и `001`, общая документация.

## 7. Находки / предложения

- **F1 (карточка, координатору):** в БЛОКЕ 1 `000_Задачи Claude.md` после постановки WUA-1 (стр. 44–195) остался хвост прежней постановки `CLAUDE-WA4-R-TOCTOU-RACE-REVIEW-001` (стр. 197–248, разделы «1. Цель … 7. STOP»). Исполнялась только WUA-1; карточку не правил.
- **P1 (CI, нужен GO):** добавить `node --test test_web_alarm_evm_ui.js` в шаг WA4-O JS workflow `.github/workflows/web-alarm-tests.yml`.
- **P2 (будущее):** при переходе к Web Chat (реальные платные вызовы) — проверка Host/Origin для маршрутов `/ultra/*`, как у folder picker.
- **P3 (будущее):** общий UI-independent помощник в `gigachat_transport` (например, «credentials настроены: да/нет» без значения) — чтобы статус `CONFIGURED` брался из ядра, а не дублировался в веб-слое.
- **Визуальная проверка:** пользователю/verifier — открыть Web Alarm, вкладку EVM, проверить три колонки на широком и узком окне.

## 8. DOC IMPACT / SHARED DOC DELTA (координатору)

- **37:** WUA-1 реализован (EVM, три колонки, выбор `chat`, `connection_id = api:<provider>:<model_id>`, хранилище `<storage_root>/ultra/connections.json`, статусы REGISTERED/DISABLED + UNVERIFIED).
- **23:** новые read/selection маршруты `/ultra/connections*`, не имеющие mutation authority.
- **36.2:** новые тесты `test_web_alarm_ultra_connections.py` (15), `test_web_alarm_evm_ui.js` (9); локальная база full = 1004 (1002 PASS / 2 SKIP).
- **11 / 19:** без изменений (реестр и транспорт не менялись).
- **34 / 05 / 06:** по итогам независимой проверки.

## 9. Комплект

`source-baseline.json` / `source-final.json`; `runs/` (только через `web_alarm.evidence_sanitizer`, LF; `runs/runs-map.json`, `runs/census.json`); `tools/` (`run_gate.py`, `census.py`, `snapshot.py`, `mutants.py`, `node_runs.py`, `collect_runs.py`, `make_manifest.py`); `manifest.json`.
