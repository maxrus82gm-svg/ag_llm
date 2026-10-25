# Предложение исправления и инженерная оценка

**UNAPPLIED / AUTHOR TESTED / AWAITING INDEPENDENT VERIFICATION.** Общие production/test файлы не изменены.

## F03: ограниченное усиление observation

`observe_path` раньше выполнял lstat и отдельный reparse check, затем open/read без проверки открытого объекта и стабильности прочитанных bytes. Изолированные тесты дают replacement digest или смешанное содержимое двух streaming reads.

Предложение переиспользует существующую функцию: сравнить dev/ino/mode/size/mtime/reparse bit исходного lstat и fstat открытого handle; после чтения повторить fstat, сравнить размер digest и актуальный lstat имени. При дрейфе — существующий FileStateError. Поля FileState, контракты и persistent schema прежние. Высокоуровневые вызывающие стороны уже обрабатывают FileStateError.

Не сравнивается atime, изменяемый самим чтением. ctime исключён после фактического Windows FAIL: в данной среде lstat и fstat давали разный ctime для одного и того же стабильного файла после write. Условия ошибки не расширялись под конкретные expected result codes: исправлен именно несопоставимый metadata field. Сохранён `research_green.txt` с первым неуспешным кандидатом.

Ограничения: не atomic filesystem snapshot; mtime может быть восстановлена, обновиться с задержкой либо недостаточной точностью. Некоторые filesystems не дают надёжный file ID. Последующее внешнее изменение после последнего stat остаётся возможным. Patch **не исправляет F01/F02** и не связывает write с проверенным handle.

## F04: verify exact consumed bytes

В low-level `restore_microtask` verify читает snapshot раньше, чем отдельное чтение data для actions. После verify другой писатель меняет snapshot; baseline пишет новые data и только затем сверяет restored SHA, когда исходные current bytes уже потеряны.

Перед `actions.append` добавить проверку размера/SHA-256 прочитанного data против SnapshotRecord. Список всех actions создаётся до destructive loop; при отказе не выполняется ни одна запись из этой попытки. Проверяемый data — тот же immutable bytes buffer, который затем передаётся `_atomic_write_bytes`; последующее изменение пути снимка не меняет buffer. Existing exception/status handling сохраняется.

Negative controls: одинаковый размер с другим hash; другой размер; повторный вызов с испорченным snapshot. RED baseline воспроизведён и сохранён, GREEN проверен в candidate. Нормальный restore и rollback проходят существующий профиль.

Этот узкий fix не добавляет в low-level restore RC-3 ownership, APPLYING receipts или lifecycle gates tracked rollback. Доступность CLI `snapshot restore` и желаемый режим его эксплуатации — отдельное архитектурное решение. Утверждать, что patch делает эту primitive production recovery транзакцией, нельзя.

## Почему не исправлены F01/F02

Добавление ещё одного path resolve/hash перед файловым вызовом не закрывает следующее окно. Нужна согласованная модель работы с родительским directory/file handle, rename/delete/replace и внешними писателями. Переносы и атомарная compare-and-swap по произвольным внешним редакторам требуют platform-specific дизайна и проверки. В этой задаче новая система locks/claims/recovery и изменение контрактов не разрешены.

## Границы тестирования

Все новые schedules исполняют настоящие локальные файловые действия в лаборатории; точки вмешательства заданы mock wrapper, возвращающимся в настоящий код. Кооперативные locks/contract store не подменяются успешными заглушками. Это воспроизводимое расписание гонки, не статистический нагрузочный тест.

Итог: baseline core 240 PASS/1 SKIP; candidate core 240 PASS/1 SKIP; final research 17 PASS. Последние включают проверки воспроизводимости оставшихся рисков, поэтому общий security verdict PARTIAL.
