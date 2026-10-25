# Следующий этап независимой проверки

1. Проверить `manifest.json` и исходные 110 файлов: `python -B verify_package.py --repo <repo>`. Требовать нулевые расхождения. Без exact source SHA не применять patch автоматически.
2. Создать новую TEMP-копию только Web Alarm и выбранных тестов; не использовать live storage. Скопировать `research_tests.py` в неё. Установить TEMP/TMP/PYTHONPATH на лабораторию, запретить bytecode. В корне lab нужен `session.json`, каталог `tmp` и `runs`, как ожидает run_checks.py.
3. В baseline воспроизвести четыре safety RED из research_red_corrected и отдельный replay_red. Отдельно проверить F01/F02 и итоговые коды/счётчики: тесты этих рисков намеренно проходят при воспроизведении проблемы.
4. `prepare_candidate.py --lab <lab>` создаёт новую candidate и неприменённый patch; существующую candidate не перезаписывает. Убедиться в ровно двух изменённых production файлах по candidate-files.json. API/schema/claims/recovery модель не меняются.
5. Запустить final research и 14 core-модулей из candidate_core.json. Ожидается 17 PASS и 240 PASS/1 SKIP в данной среде, exit=0 обоих прогонов. Symlink SKIP не считать доказанной защитой.
6. Независимо проверить исходники и допустимость metadata checks на поддерживаемых Windows/Python/filesystems. Отдельно проверить leaf symlink в разрешённой среде, timestamps/ABA и варианты sharing flags; Linux и power-loss остаются отдельными направлениями.
7. До внедрения решить F01/F02: необходима привязка действия к проверенному родителю/объекту и явная модель некооперативных писателей. Рассмотреть ограничения low-level CLI restore. Не принимать дополнительный path check за атомарное решение.
8. Только после независимого решения пользователя — отдельное внедрение patch и профильная проверка внедрённых bytes. Текущая задача не меняет shared source, документацию, карточки и статус WA4-R и не разрешает STRICT/rollout.
