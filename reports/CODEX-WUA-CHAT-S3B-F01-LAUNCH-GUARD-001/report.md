# CODEX-WUA-CHAT-S3B-F01-LAUNCH-GUARD-001

12.11.2026, Codex 007. **P0 + P1 BOUNDED OFFLINE PASS / RESULT READY. Independent review pending.**

F-01 устранена в пределах `--require-test` по авторским адресным проверкам: только два утверждённых сочетания профиля, типа, скрипта и аргументов достигают dispatch. Полный S3b, Stage6/7 и реальные провайдеры остаются OPEN/HOLD. Код ядра не менялся.

## База и вход

`git rev-parse HEAD` подтвердил назначенную базу `0ff9ab67f060be3c0de5521ce4ac18875a689aa8` / №572. Адресный `git diff` по пяти назначенным объектам пуст до правок. Git read-only использован по явному требованию БЛОКА 1 §2; commit/push/публикация не выполнялись. До начала уже изменены `.obsidian/graph.json`, `.obsidian/workspace.json` и пользовательская карточка Codex с назначением; они не перезаписывались инженерными правками. Карточку в конце меняет только штатный finish.

Адресно сверены №08/000/34/40, шаг 3 №37 §3а, применимые ограничения №20 §5а, FOLLOWUP S3B-S3C-S9 и STATIC-DYNAMIC-COVERAGE №05, F-01 в отчёте H30. Все эти документы сохранены. REUSE CHECK: используется существующий путь `main → load_launch → _profile → run_script`, его JSON/path validation и обработка LaunchConfigError. Создавать новое ядро, launcher, транспорт или систему прав не требуется.

## Причина и изменение

Ранее `--require-test` проверял лишь `launch.standard`. Любой существующий `.py` в репозитории проходил общий `python_script` путь, а offline guard устанавливал сам выбранный fixture. Подмена script могла миновать fixture.

Изменены **только**:

- `web_alarm/launcher.py`: доверенная неизменяемая таблица `_OFFLINE_TEST_PROFILES` (`frozenset`); `_require_offline_test(launch)` сверяет полное сочетание и отказывает через LaunchConfigError; `main()` вызывает проверку внутри существующего error handler перед dispatch только при `--require-test`.
- `test_web_alarm_launcher.py`: четыре новых адресных метода, усиление проверки отсутствующего/standard/битого config утверждениями no subprocess, согласование старого Stage5 dispatch-теста с текущим утверждённым Web-only rollback.

| active | kind | script | args |
| --- | --- | --- | --- |
| ordinary-core-offline | python_script | web_alarm/ordinary_test_fixture.py | [] (в том числе существующий default при отсутствии поля) |
| stage5-offline | python_script | reports/CODEX-WUA-CHAT-S5-OFFLINE-FULL-CHAT-001/review_fixture.py | ["--web"] |

Прочие имена, другой script, перекрёстная перестановка approved scripts, изменённые args, другой kind, алиас пути через `..` и абсолютный путь не проходят. JSON не может расширить таблицу. При отказе возвращается exit 2 и русское пояснение; ни `run_script`, ни `run_web_alarm`, ни subprocess не вызываются. Существующие `_profile`/`load_launch`, resolve/проверка нахождения файла внутри репозитория и строгий JSON-парсер не изменены.

`--standard` и общий launcher без `--require-test` продолжают прежнее поведение. Общий режим намеренно допускает другие repository scripts: это не штатная TEST-граница. Оба постоянных CMD, оба JSON config, оба утверждённых fixtures, storage и TEMP cleanup не изменены. Архивный `launch_stage5.json` не содержит `--web`: с `--require-test` он теперь отклоняется согласно точному контракту задачи; исторический общий запуск без флага сохранён. Штатный Stage5 rollback в `web_alarm/launch_test_config.json` содержит `--web` и разрешён.

## Проверки и evidence

Команда: `.venv/Scripts/python.exe -B -X utf8 reports/CODEX-WUA-CHAT-S3B-F01-LAUNCH-GUARD-001/run_checks.py final2`.

**18 tests / 18 PASS / 0 FAIL / 0 ERROR / 0 SKIP, exit 0**, Python 3.12.10 Windows. Включены ConfigTests (4), BannerAndPageTests (2), StableEntryTests (8), два соседних RunTests и два адресных ActivationTests. В substitution-тесте 11 отрицательных subcases; дополнительно 4 повреждённых/недопустимых JSON и 3 missing/standard/broken cases. Оба approved dispatch проверены вплоть до точного argv `subprocess.call`, который заменён mock. Отрицательные случаи проверяют отсутствие вызовов обоих dispatch и subprocess.call/Popen. Не выполнялся даже тестовый запуск подозрительного Python-файла.

Регрессионный контроль **до production-исправления**: `run_checks.py red` дал ожидаемый exit 1, один метод с **10 отрицательными subcase failures**, 0 errors/guard violations. Mock перехватил dispatch, сторонний код не выполнялся. Первая проверка после исправления: **17 PASS / 1 FAIL** из 18 — старый Stage5 тест использовал архивный Web+Tk config без утверждённого `--web`. После перевода теста на текущий rollback config итоговый прогон 18/18 PASS; production-правила не ослаблялись. Все исходные FAIL и логи сохранены, не заменены итоговыми.

Runner явно устанавливает ранее проверенный H27 guard **до импорта тестов**, удаляет GIGACHAT_* из дочерней среды и направляет LOCALAPPDATA в новый synthetic TEMP. Физическая сеть/DNS запрещены, исключение — stdlib asyncio self-pipe; credentials/.env/.git и repository live storage закрыты. На всех трёх прогонах **guard violations=0**. Реальные LLM/OAuth/API не вызывались. Нулевой трафик относится к этим guarded прогонам, а не к произвольному общему launcher без TEST-флага.

Логи и команды: `evidence/{red,final,final2}.{result.json,stdout.txt,stderr.txt}`. Исходные SHA и pre-existing changes — `evidence/baseline.json`; локальный diff из резервной копии — `evidence/source.diff.txt`; проверки сохранности — `evidence/checks.json`. До finish из **121 pinned files** изменены только два разрешённых source/test файла, остальные **119 совпали**; H30 report/evidence тоже совпали. AST edited modules PASS. Выполнен собственный review: guard вызывается перед обоими dispatch, exact args включены в ключ допуска, отсутствие config не возвращает STANDARD под TEST, generic path не ограничен новым guard.

**NOT RUN:** физический permanent CMD/browser/F5 smoke и ActivationTests.test_permanent_cmd_chat_flow_and_cleanup; loopback/server/CTRL_BREAK серии RunTests; полный launcher module/full CI; настоящие LLM/OAuth/paid; независимая проверка. Два ActivationTests относятся к активной конфигурации/rollback и missing-config fail-closed. CMD и fixtures не менялись; результат физического H28 smoke не выдаётся за новый прогон.

## Backup, ограничения и сдача

До первой правки создана отдельная резервная копия четырёх запланированных существующих файлов: launcher, тестовый модуль, карточка Codex, служебный HISTORY sequence. SHA-256 и побайтовый readback PASS; пути/хеши — `evidence/backup.json`. Секреты/Workspace/настоящие чаты не копировались.

**RETAINED / CLEANUP PENDING UNTIL INDEPENDENT ACCEPTANCE:**

`C:\Users\REX\AppData\Local\Temp\codex-wua-f01-launch-guard-backup-ymnr7i3y`

Резервная TEMP-копия **H30 не открывалась, не менялась и не удалялась**. Новую копию после независимой приёмки проверяет и удаляет координатор по точному пути; сейчас она сохранена.

Граница исправления — только конфигурационная подмена под `--require-test`. Редактирование доверенного Python-кода/approved fixture или обход флага не относится к этому допуску; он не является Python sandbox, полной динамической инвентаризацией либо S3b pre-HTTP guard. Никаких изменений OAuth, providers, Model Registry, Tk, Blueprint, Colibri, бюджетов Workspace, OS/ACL и нормативных документов.

**DOC IMPACT:** новый отчёт, manifest/evidence; штатная сдача меняет только слоты 1/1.1 своей карточки и служебную HISTORY sequence, создаёт task snapshot/record. БЛОКИ 2–4 и прежний H30 должны сохраниться; фактический finish/readback и HISTORY ID находятся в `finish_receipt.json`, `task_record.json`, `closeout.json`. Отчёт после регистрации не изменять.

**NEXT:** независимая проверка F-01 по diff, двум approved dispatch и отрицательным oracles; затем отдельное назначение следующего узкого Ordinary S3b wire/reserve/one-send binding. Этот результат не разрешает реальные вызовы и не закрывает весь S3b. Полномочия на следующие стадии не расширялись.
