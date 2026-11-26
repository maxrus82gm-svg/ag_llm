# CODEX-WUA-WINDOWS-CI-ACL-REPAIR-001

**Статус** RESULT READY / AWAITING INDEPENDENT VERIFICATION  
**Дата** 26.11.2026, Asia/Yekaterinburg  
**Исполнитель** Codex 007  
**Независимая проверка** WEB 36

## Исходная версия и исходные отрицательные результаты

Штатный `check` подтвердил TASK ID, SHA-256 карточки `7d47f4b6a5a170709811176a1dbd37e5c65a797f891e7fcf79cb6ce5eaf7f26c` и предыдущую запись H-CODEX-000046. Перед правками зафиксированы SHA-256 рабочей копии затронутых и контрольных файлов. В ней присутствуют managed Client Binding, Windows-фикстуры и адресный workflow с дефектами из задания.

Версии по постановке WEB 36: main №677 `3ee748e19dc0ad1f28f4ed2344c79978b3145bac`, GPT №682 `4f2d6cb5240f51ff98b1e052e4b104bcacfc61ec`, техническая база №681 `d0d8927c94673ea22b675fc1751e3274b31ce170`. Идентичность локального дерева коммиту проверкой Git не устанавливалась согласно запрету. Воспроизводимая локальная исходная версия зафиксирована по файлам в [evidence.json](evidence.json).

Исходный hosted Windows CI по данным БЛОКА 1: run `45702959182`, attempt `2`, job `139714802863`. Обе попытки дали 28 PASS, 4 FAIL и 5 ERROR. JavaScript — NOT RUN. Сохранены сообщения `BridgeFault: unsafe_discovery`, `"identity_mismatch" does not match "unsafe_discovery"`, `"redirect_refused" does not match "unsafe_discovery"`, `409 != 200` и ошибка отсутствия `demo_ultra_chat.py`. Текущая задача не запрашивала логи у GitHub. Источник этих данных — утверждённая постановка.

## Установленные причины и исправления

**ACL.** Прежний `protect()` брал владельца объекта из файлового дескриптора и выдавал ему DACL ACE. В native-вызове указывалась только DACL, поэтому владелец оставался прежним. `_windows_private_acl()` сначала сравнивает владельца с `TokenUser` текущего процесса. При владельце Administrators или ином SID, отличном от `TokenUser`, чтение отклоняется именно в этой ветви даже с частной DACL. Поэтому проверки discovery identity, редиректа и managed binding не доходят до своих ожидаемых результатов. Локальный исходный прогон 37/37 показал, почему дефект не проявляется на этом аккаунте: `TokenOwner == TokenUser`, все три объекта при создании получили этого владельца и три наследованные ACE.

На синтетическом профиле воспроизвели `unsafe_discovery` с дескриптором Windows, у которого изменён только владелец на Administrators. DACL получена непосредственно с тестового объекта. В той же модели перехват аргументов старого вызова показал ACE для Administrators и отсутствие флага записи владельца. Новый вызов указывает `TokenUser` и как записываемого владельца, и как единственного grantee нормальной фикстуры. Повторное чтение реальных файлов и каталога подтвердило совпадение владельцев, защищённую DACL и отсутствие наследованных ACE. На текущем неэскалированном аккаунте назначение Administrators реальному тестовому файлу вернуло WinError 1307, поэтому для отрицательного owner oracle используется подмена только owner в нативном дескрипторе. Фактический owner SID старого hosted раннера недоступен в БЛОКЕ 1. Механизм отказа доказан локально, фактический hosted повтор остаётся WEB 36.

В первом прогоне исправления обнаружен один дополнительный ERROR, WinError 5 на `protect(token)` в `DecodeTests.test_discovery_strict_loopback_and_expected_identity`. Этот тест создавал token перед изменением DACL родительского каталога. Изменение ACL родителя могло убрать с уже созданного файла наследованное право, необходимое для новой операции записи владельца. Установленный порядок теперь такой же, как в остальных фикстурах: сначала защитить каталог, затем создать и защитить каждый файл. Повтор полного адресного набора дал 39/39. Raw первого результата сохранён и учтён в evidence.

**Sparse checkout.** Прежний cone не включал `reports/CLAUDE-WUA-CHAT-S1-READONLY-UI-001/tools/demo_ultra_chat.py`. В изолированной проекции прежнего состава штатный `load_launch()` воспроизвёл точный `LaunchConfigError` для `ultra-chat-demo`. После включения `reports/CLAUDE-WUA-CHAT-S1-READONLY-UI-001/tools` все три shipped-профиля в том же оракуле приняты. В режиме cone это самый узкий каталог для этого файла. Прямые зависимости `context_storage.py`, `run_store.py` и `web_alarm/server.py` уже входят в прежний cone. Смежные вложенные исторические каталоги по-прежнему исключены. Проверено, что остальные строки workflow идентичны, включая Windows Long Paths, cone mode, `persist-credentials: false`, `contents: read`, изоляцию и шаг JavaScript.

## Изменённые файлы

| Файл | Изменение |
| --- | --- |
| `test_web_alarm_colibri_bridge_transport.py` | Добавлен `windows_process_user()`. `protect()` назначает owner и защищённую DACL для текущего `TokenUser`, сохраняя отдельный Everyone negative control. `DecodeTests` защищает каталог до создания файлов. Два теста проверяют реальные owner/DACL всех трёх объектов и отказ для чужого владельца до любого HTTP. |
| `.github/workflows/gpt-wua-666-safety-gates.yml` | Одна строка cone sparse checkout для каталога скрипта демо. |

Побайтно сверены production-транспорт, managed binding, launcher, S1 fingerprint-manifest и оба постоянных CMD. Защитные политики и контракт v1 сохранены.

## MANUAL ENGINEERING REVIEW

- Прослежен порядок `_discover → _private_temp_file → _windows_private_acl` для каталога, discovery и token. Owner проверяется до разбора DACL, проверка до и после чтения сохранена. Настоящая ACE Everyone дала `unsafe_discovery` с совпавшим владельцем. Подмена только owner при сохранённой реальной DACL дала тот же отказ. Подмена не заменяет результат production-валидации.
- Передача token handle завершается через `finally`. Fixtures работают только в одноразовом TEMP. Неподдерживаемый Windows security descriptor приводит к явной ошибке фикстуры. Проверки ACL, SID и transport guard в программе сохранены. Тесты подтверждают отказ на hardlink, неизвестную identity, внешний origin, редирект, запрещённый маршрут и наличие тела.
- Прослежены reconnect и ошибка refresh. Transport читает только два GET. При отказе refresh уже известные карты остаются UNKNOWN без операций выполнения. При ошибочном reconnect сохранён прежний binding, при повреждённом файле нет перезаписи. Проверки HTTP Origin и write token сохраняют запрет в TEST и для неподтверждённых вызовов.
- Проверен fail-closed путь `_profile()` при отсутствующем скрипте и разрешение пути внутри проекта. Исправление в составе checkout сохраняет эту проверку. Варианты полного checkout, обхода профиля и расширения доверенных SID отвергнуты как необязательные для задачи и ослабляющие её границы.

## Итоговые проверки OFFLINE

| Проверка | Результат |
| --- | --- |
| Bridge Transport, managed binding, Launcher | 39 PASS, код 0, в том числе 2 новых Windows ACL теста |
| Реальные синтетические ACL/owner, public ACE и модель чужого владельца | PASS, код 0 |
| Проекция cone sparse checkout | Прежний состав дал ожидаемый отказ, новый принял 3/3 профиля, код 0 |
| S1 STATIC | 16 PASS, код 0, нарушений 0 |
| S1 полный | 69 PASS, код 0, защищённые RAW pins 6/6, нарушений 0 |
| S2 FULL | 73 PASS, код 0, нарушений 0 |
| D8 и существующие negative controls | 6 PASS, код 0 |
| Ultra Chat HTTP и Ordinary Application | 36 PASS, код 0 |
| JavaScript UI | 211 PASS, код 0 |
| Импорт MCPServer | PASS, код 0, SDK 2.2.0 |
| Изолированный smoke двух CMD | STANDARD и TEST PASS, код 0. TEST отказал EVM GET/POST и убрал временное хранилище |

Команды, версии среды и местоположение лога каждого набора — в [tests.md](tests.md) и [evidence.json](evidence.json). Реальных сетевых вызовов, OAuth и платных запросов — 0. Рабочие STANDARD, Client, Manager, модели, подключения и пользовательские данные не задействованы.

## OPEN, NOT RUN, DOC IMPACT и NEXT

- Hosted Windows CI на точном SHA, публикация и независимый readback — NOT RUN в локальной задаче. Локальные версии Python и pywin32 зафиксированы, а jsonschema отличается от pinned версии workflow. SAFE hosted rerun проверяет фактические runner ACL, sparse checkout и прохождение JavaScript в штатной последовательности. Содержимое приватных RAW в отчёт и hosted CI не перенесено.
- M1-10 LIVE остаётся HOLD. Настоящие Client Bridge, рабочие модельные профили и GUI владельца — NOT RUN. Известное ограничение файловой ACL проверки по имени сохраняется для отдельного LIVE preflight.
- DOC IMPACT: отчёт, команды, безопасные подтверждения, штатный снимок задачи и HISTORY ID. SHARED DOC DELTA: отсутствует. Git/GitHub, публикация, merge и push со стороны исполнителя не выполнялись.
- NEXT: WEB 36 проверяет пакет и после публикации владельцем подтверждает новый точный SHA, hosted workflow и независимый verdict.
