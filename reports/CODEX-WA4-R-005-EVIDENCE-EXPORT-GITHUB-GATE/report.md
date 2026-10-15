# CODEX-WA4-R-005-EVIDENCE-EXPORT-GITHUB-GATE

**Статус: RESULT READY / AWAITING INDEPENDENT VERIFICATION.**
**Публикация: LOCAL ONLY / NOT SYNCED.** Исполнитель Codex 007; независимая приёмка ChatGPT / WEB_07 → WEB_08. Дата: 2026-10-15.

ARCH CLASS: Web Alarm Workspace / WA4-R Reliability / Evidence Handoff. PRIMARY PROFILE: 23; TEST PROFILE: 36.2. Это экспорт существующих доказательств. Production, тесты, runners, CI, Ultra и общие документы не изменялись. R-003/R-004 не повторялись; новые runtime PASS здесь не заявляются.

## 1. Результат и порядок чтения

Подготовлены **43 исходные test records**: четыре final F1, шестнадцать final F2/F3, двенадцать negative controls и одиннадцать исходных RED/ERROR. Вместо нового ZIP представлены адресные UTF-8 JSONL. Все факты в выбранной записи сохранены, включая первичные исключения/frames, PRE/intermediate/terminal, timestamps, phase arrays, stdout/stderr, receipts, checkpoints и физические bytes там, где источник их записывал. Пропуски не достраиваются.

Начать с индексов:

- [f1-raw.jsonl](f1-raw.jsonl) — четыре final F1.
- [f2f3-raw.jsonl](f2f3-raw.jsonl) — шестнадцать F2/F3.
- [negative-controls.jsonl](negative-controls.jsonl) — шесть R-003 + шесть R-004.
- [historical-red.jsonl](historical-red.jsonl) — все найденные самостоятельные FAIL/ERROR из results.json обоих архивов и оригинальный исторический F3.
- [provenance.json](provenance.json) — полный source index: архивы, размеры/SHA каждого member, exact selector/attempt/JSON pointer каждой записи, source file pins и контекст каждого использованного прогона.
- [observations.json](observations.json) — **вычисленный навигатор**, не RAW: фазовые последовательности, workers, фактические состояния, счётчики apply/events и явные пропуски. Все указатели относительно соответствующего исходного test record.
- [checks.json](checks.json) — проверки экспорта и дополнительная сверка сохранённых F1-инвариантов.
- [manifest.json](manifest.json) — SHA-256 и размер каждого файла пакета; сам manifest не входит в собственный hash. Публиковать перечисленные в нём файлы, включая `records/`; не ограничиваться четырьмя индексами.

В индексе поле `file` ведёт к небольшому отдельному JSONL в `records/<group>/E###.jsonl`. Первая строка — ROOT с источником. Далее RAW означает точное **parsed JSON subtree** из оригинального member; STRUCTURE задаёт ключи/индексы контейнера, разбитого на части. JSON Pointer вместе с shape nodes позволяет восстановить полную запись и проверить её canonical SHA. Порядок phase arrays сохранён через числовые индексы. Порядок между разными workers не выдумывается.

Три контрольные суммы различаются: исходные **ZIP bytes**, исходные **member bytes**, canonical **parsed test record**. Четвёртая — bytes экспортированного JSONL. Canonical JSON: UTF-8, `ensure_ascii=False`, `sort_keys=True`, `separators=(',', ':')`, без NaN/Infinity. Это не утверждение о побайтном сохранении пробелов/порядка ключей оригинального JSON-файла. Исходные target/event/snapshot bytes сохранены именно через оригинальные hex-поля.

## 2. Источники и актуальность

| Источник | Bytes | SHA-256 |
|---|---:|---|
| R-003 `evidence.zip` | 939743 | `91f66480f2b40019086904d886cea9bef50664e725bcd43920d6f04f67680189` |
| R-004 `evidence.zip` | 1297650 | `a28f1df2fdc4cb5b5a7fddff9ce6635dc4d5344cba4ed57acd001850b9cb40b5` |
| Вложенный original F3 `wa4r002-independent-38379575748-1.zip` | 52853 | `020d2770b48f90e0d24df071b10c2ad5fe5caa2972d8d3070445ac875963e120` |

Первые два SHA/размера совпали с **доступными локальными** manifest R-003/R-004; CRC всех трёх ZIP проверен. Независимое чтение опубликованных manifest на GitHub агент не выполнял. Original F3 извлечён только в памяти из `R004:historical/original-wa4r002-independent-38379575748-1.zip`; исходный файл не перепаковывался.

Утверждённый БЛОК 1/координатор передал published baseline `main@38e7164b1ab3af6131d65cfc9dc8760ee426dd1e` (#336), затем docs-only #337. Это **supplied Git identity**, а не локально проверенный Git HEAD. Никаких Git/GitHub-операций не было.

Все семь final R-004 file-byte pins совпадают с текущими локальными файлами:

| Файл | SHA-256 |
|---|---|
| `web_alarm/closeout.py` | `398fcaebebaab0efeb4fea4489dbfb1b8c49ed4e4bd23a005d3b660291504603` |
| `web_alarm/task_store.py` | `6d63670db24e7b8a11c6f2d8981cce7043f499684890ef99f87f319023ce20c3` |
| `web_alarm/operation_store.py` | `d7088a782c280fca4423f681d23657e88ea1d8e021bdb43ca449bb4875316764` |
| `web_alarm/mutation_executor.py` | `7e34e77e5339f10cdfc48a2439d589ac4c652907613184f1b70cfc460bbcd854` |
| `test_web_alarm_wa4r002_diagnostics.py` | `1d7a23480b726b4835692b53b3e80b72ead980907e145a3ffdbb85ff74083254` |
| `test_web_alarm_reliability_wa017.py` | `edb7d2b0bc65568d3be3fc33f39b3c808f790c4906991e4b63c17c974489fabd` |
| `wa4a_acceptance.py` | `198d0b8f7822fa29f9f59a00f15b9087313e244a95bf6b1d2d4757fb1be4cffc` |

В R-003 относительно текущего дерева отличаются `web_alarm/server.py`, `web_alarm/ui.py` и общий diagnostic test; это более поздние изменения, не правки этой TASK. Четыре core runtime pins совпадают. Старый full PASS нельзя переносить на всё нынешнее дерево. Каждый выбранный attempt сохраняет **свой** исходный `source_sha256`; первый RED и поздний PASS не смешиваются.

## 3. F1 — четыре финальных случая R-004

Все четыре взяты из `attempts/focused-final/results.json`, исходный прогон 92 PASS / 0 FAIL / 0 ERROR / 0 SKIP. Это сохранённый результат Codex, не новый независимый запуск.

| ID / файл | Наблюдённая последовательность и конечное состояние |
|---|---|
| [E004](records/f1/E004.jsonl) — native pre-move | `before_directory_move → native_pre_handle_open`; close exit 2, настоящий WinError 5; в trace нет `directory_moved`. Intermediate целиком равен quiescent PRE, active/PLANNED. `raw_before_retry` читает PRE; отдельный `fresh_retry` завершает TASK; raw reopen completed/COMPLETED. |
| [E003](records/f1/E003.jsonl) — native post-move | `directory_moved → status_write_with_native_reader`; exit 2, WinError 5. Intermediate completed/PLANNED; весь `files_sha256` равен closeout PRE. `raw_pending` читает pending; late mutation REFUSED, pending replay возвращает прежний receipt. `recover` сообщает `resumed=MOVED_STATUS_PENDING`, затем completed/COMPLETED; `again` REJECTED. |
| [E002](records/f1/E002.jsonl) — completion first | `operations_lock_acquired → before_directory_move → fresh_gate_before_move → directory_moved`. Closer COMPLETED; reader и plan exit 2/TaskStoreError, новый writer REFUSED. Fresh reopen completed/COMPLETED; прежний receipt REPLAYED. Source assertions о parent lock probes существуют в тесте, но **отдельных parent-probe RAW records нет**. |
| [E001](records/f1/E001.jsonl) — admission first | Reader берёт operations lock и открывает RAW, возвращает BEGUN; close после lock acquisition достигает `fresh_reject_gate`, возвращает REJECTED. Terminal равен `admission_committed_before_closeout_refusal`, active/PLANNED, нет completion event. |

Важно различать первоначальный `PRE` с original target и **`F1_quiescent_PRE_with_receipt_checkpoint_snapshot` после единственной разрешённой fixture mutation**. Значения непосредственно из RAW: исходный target `5052450d0a00ff`, closeout target `504f53540a00fe`. При admission-first legitimate begin добавляет op_late/обновляет checkpoint; применимый barrier — post-admission, не прежний checkpoint. Ранний ошибочный oracle сохранён в E042.

Дополнительный анализ сохранённых данных, воспроизводимый валидатором:

- Во всех четырёх есть ровно **один записанный `apply_enter`** от fixture; повторного marker нет. Это ограниченное instrumentation evidence, не абсолютное наблюдение всех возможных внешних writers.
- Полный исходный `operations.op_diag`, включая receipt/revision/identity/timestamps, неизменен; receipt SHA соответствует **фактическим** terminal target bytes.
- Snapshot hex соответствует original PRE target; claims, snapshot и restore records сохранены. Checkpoint сравнивается с применимым barrier.
- Original events bytes являются точным prefix terminal events bytes; данные events_hex повторно распарсены и сверены с parsed events. Completion count: E001=0, E002/E003/E004=1.
- stdout отдельного raw-reader worker совпадает с terminal; его оригинальные PID/exit сохранены. Replay receipt точно равен прежнему.

## 4. F2/F3 и первичные RED

Адресные final F2/F3 взяты из `R003:focused-final-2/results.json`. Полная исходная test record каждого случая сохранена: важен не только enum, но raw files, claims, checkpoint, операции и markers. Индекс ниже связывает каждый случай с exact selector/member/pointer через provenance.

- Phantom duplicate real move: E010 final; E033 первоначальный ERROR `task exists in active and completed`; настоящий duplicate fail-closed — E011.
- Bounded destination recheck: E013 final; E035 первоначальный ERROR `unknown task_id`.
- Direct close / operations-lock serialization: E005, E007–E009, E014 и E017; release-after-DONE replay и cached-read/snapshot branches сохранены раздельно.
- Native RAW read-before-lock: **E034 сохраняет исходный FAIL**, `blocked_closeout_chain → PermissionError/WinError 5` на pre-move. Исправленный locked admission — E018; не утверждается, что источник установил владельца handle исторического CI.
- Executor preflight lock refusal/no apply — E015. Projection cached snapshot failure/fresh reopen — E016; этот read-only error не скрыт и не объявлен repaired.
- WA-017 crash race — E006; отдельный marked post-move crash/recovery — E019; writer-first refusal без выдуманного crash phase — E020.
- E036 — NameError тестового harness; E037 — исходный two-EXECUTED FAIL старого CAS oracle; E038–E041 — первоначальные restart/encoding errors. Они сохранены как original RED, без автоматической атрибуции product defect. Подробная прежняя классификация остаётся в R-003 report; R-005 её не переписывает.
- E042 — R-004 admission-first TEST/ORACLE FAIL до корректировки допустимого checkpoint update.
- **E043 — оригинальный исторический F3**, run `38379575748`, round 0: c0 `FAILED:CloseoutError`, returncode 0, stderr пустой; error frames указывают `os.replace` до move, errno 13 / WinError 5. Terminal active=true/completed=false, PLANNED; b1/b2 BEGUN, m3 CREATED; два исходных project hex и семь events сохранены. `c0.trace`, PID, raw stdout, full event bytes, receipts/checkpoint/snapshot этого раунда: **NOT PRESENT IN SOURCE**. Error frames не переименованы в отсутствующий trace.

Original F3 source commit `37123b176097c15c8d21e0040bdf7d7f3e8072a3` — coordinator-supplied. Member `wa4r002-focused/results.json` дополнительно содержит собственные file pins. Исходный результат: 63 tests, 62 PASS, 1 FAIL; последующие PASS его не отменяют.

## 5. Negative controls и предел сохранённого evidence

E021–E026: шесть R-003 outer PASS с **исходным intentional_inner_red traceback**. Для пяти controls полные inner raw facts и численные inner counters не были сохранены: **NOT PRESENT IN SOURCE**. E023 дополнительно содержит raw records двух законных последовательных контрактов с разными CAS bases. Контроль counterfeit receipt R-003 подменял результат чтения, а не сохранял испорченный файл — не смешивать с persisted corruption R-004.

E027–E032: шесть R-004 outer PASS, каждый с исходными `inner_tests=1`, `inner_failures=1`, `inner_errors=0`, `inner_skips=0`, failure traceback и inner_facts. Проверены persisted receipt corruption, false SUCCESS после status refusal, checkpoint identity, отсутствие closeout operations lock, отсутствие native trigger, переписывание event prefix при равном parsed JSON. Intentional inner RED — доказательство чувствительности oracle, не новый production FAIL.

R-003 не записывал events_hex и PID common workers; их нельзя получить обратным преобразованием parsed events или из предположений о процессе. Часть raw TASK JSON доступна как parsed object + file SHA, **оригинальные task.json bytes не записаны**. Это явно отмечено в observations, а не выдано за восстановленные bytes. Глобальная временная последовательность разных workers не выводится из порядка сбора facts.

**Исходный F1 CI artifact и исторический F2 80-round ZIP не найдены в разрешённых R-003/R-004 источниках.** Первичная выписка координатора/старый report не заменяет эти архивы. Новые тесты для заполнения пробелов не запускались. Если WEB_08 нужны отсутствующие исторические поля, сначала получить оригинальные artifacts; новый rerun не восстановит старое расписание или handle owner.

## 6. Команды и проверки

Все команды из `M:\GitHub\ag_llm`; Python 3.13 используется только для обработки JSON/ZIP. Оригинальные Windows runtime результаты сохраняют собственную Python 3.12.10/platform provenance.

```powershell
python -B reports/CODEX-WA4-R-005-EVIDENCE-EXPORT-GITHUB-GATE/export_evidence.py
python -B reports/CODEX-WA4-R-005-EVIDENCE-EXPORT-GITHUB-GATE/validate_export.py --sources M:\GitHub\ag_llm --self-check --checks
python -B reports/CODEX-WA4-R-005-EVIDENCE-EXPORT-GITHUB-GATE/validate_export.py
python -B reports/CODEX-WA4-R-005-EVIDENCE-EXPORT-GITHUB-GATE/validate_export.py --sources M:\GitHub\ag_llm --self-check
```

Экспорт: 43 root records / 1230 RAW+STRUCTURE nodes; nodes losslessly восстанавливаются и равны оригинальным selected records, exact selectors/status/member pointers сверены. Strict JSON parsing отвергает duplicate keys/NaN. Source member SHA и размеры, весь inventory и CRC сверены; индексы покрывают все roots без дубликатов. Derived observations независимо пересчитаны. Финальные counts файлов и результаты обоих режимов — `checks.json` / `final-validation.json`.

Adversarial TEMP: изменён raw status; обнаружены (1) несовпадение text byte pin, (2) несовпадение исходного root SHA даже после пересчёта node SHA; (3) удаление обязательного RAW child обнаружено shape coverage. **3 PASS / 0 FAIL / 0 SKIP** проверок чувствительности экспорта. Это не запуск production negative controls заново. При одновременной злонамеренной замене source ZIP, manifest и всех pins самопроверка не служит цифровой подписью: verifier должен сверить pinned sources с доверенным опубликованным источником.

В text-only режиме ZIP не нужен: проверяются tree reconstruction, canonical hashes, файлы/индексы, metadata и manifest. В source режиме дополнительно сравниваются все выбранные записи с оригиналами ZIP. Text-only integrity сама по себе не устанавливает истинность origin claims. `--checks` нужен для подготовки; после seal скрипт отказывает в перезаписи checks.json. Экспортёр также отказывает при существующем manifest: новая ревизия требует отдельного контролируемого сохранения.

Production tests: **NOT RUN** по утверждённому scope. Исторические R-003 768 PASS / 1 SKIP full и R-004 92 focused PASS / 4+4 bounded PASS / 6 outer PASS сохранены с их source; 791 R-004 collected IDs — **NOT RUN**, не full regression.

## 7. MANUAL ENGINEERING REVIEW

Проверен транспортный механизм: ZIP читается через `ZipFile.read`, без извлечения путей на диск, импорта runtime/test modules или subprocess. Все постоянные записи принадлежат новой папке отчёта; ротация затрагивает только персональную карточку. Проверены отдельность archive/member/canonical/text hashes, root coverage, пустые списки, отсутствие полей, original errors, соответствие snapshot/receipt/event bytes и обе ветви closeout.

Отвергнуты восстановление PID из trace, events bytes из parsed events, receipt из expected post, слияние initial RED с final PASS, интерпретация moved+PLANNED как SUCCESS и подмена исторического F3 crash фазой. Самый существенный сохраняющийся пробел — неполный historical instrumentation, который экспорт исправить не может.

В пакет входят synthetic local TEMP fixtures и synthetic Windows CI evidence. Первичные error frames/recorded claim/contract paths сохраняют только необходимые исходные TEMP/repository locators; массовые логи/Downloads/private Workspace не экспортируются. Секреты/ключи/live Workspace содержимое не обнаружены. Проверка ограничена отобранными источниками, а не гарантией универсального secret detector. Фактическая область неизменности и результаты content scan приведены в `scope-check.json`.

Автоматическая проверка запретила удаление созданного собственного `__pycache__` (`blocked by policy`). Кэш оставлен, не является evidence и явно исключён из manifest/publication scope. Это не блокирует текстовый handoff.

Ротация карточки двухфазная: сначала сохранены постановка/результат и прежняя история, затем освобождён БЛОК 1. При второй atomic replacement наблюдался отдельный transient WinError 5. Исходная phase1 карточка и staged final были сверены; один ограниченный повтор успешно завершил phase2. Этот эпизод сохранён в `rotation.json`, не используется как воспроизведение production F1/F3. Prefix, полная постановка и все прежние БЛОКИ 2–3 проверены на byte-exact сохранность.

## 8. Ограничения и NEXT

Текстовый доказательственный разрыв для **имеющихся** записей устранён локально. Исторические пробелы, внешние Windows readers/антивирус, сторонние writers, power loss и общая STRICT authority этим экспортом не закрыты. Исторический handle owner не установлен. Нет нового GitHub Actions run на final R-004 source; независимый runtime/platform gate на текущей ревизии остаётся необходимым по risk assessment WEB_08. Настоящая TASK его не запускала и не разрешает rollout.

Пользователь публикует перечисленные manifest файлы штатным способом. WEB_08 читает тексты, проверяет source pins/RAW/negative controls и выносит **раздельные F1/F2/F3 verdicts**. Для независимого Windows execution выбрать точный актуальный SHA, suites и допустимую CI-задачу отдельно; старый green rerun не считать новой ревизией. Ни `DONE / VERIFIED`, ни STRICT VERIFIED исполнителем не присвоены.

## 9. SHARED DOC DELTA — WEB_08

- `34`, общий `000`, `05`, `06`, `25`, `36.2`: после публикации и независимой проверки адресно добавить ссылку на R-005, источник/ограничения и отдельные решения F1/F2/F3. Сейчас только RESULT READY / локальный экспорт, не изменение общего CURRENT агентом.
- `23`/`24`/`01`: NO CHANGE по механизму; runtime/architecture/rollout не менялись. Обновление статуса только после verifier decision.
- `18`/`36`/`36.1`: NO CHANGE; применён существующий evidence handoff, нового Rule-ID/contract не требуется.
- Own card: полная исходная постановка → БЛОК 2; factual result → БЛОК 3; прежняя история сохранена; БЛОК 1 освобождён после успешной записи. Proof — `rotation.json`.

## 10. Полный адресный индекс выбранных первичных записей

Следующая таблица создана из provenance; exact member/pointer, полный selector, canonical SHA и byte SHA каждого текста доступны также в четырёх машинных индексах выше.

<!-- ROOT_INDEX -->

| ID / RAW file | Archive / attempt / source pointer | Original status | Selector suffix |
|---|---|---|---|
| [E001](records/f1/E001.jsonl) | R004 / `attempts/focused-final` / `/tests/0` | PASS | `test_F1_admission_first_rejects_closeout_without_touching_existing_evidence` |
| [E002](records/f1/E002.jsonl) | R004 / `attempts/focused-final` / `/tests/1` | PASS | `test_F1_completion_first_serializes_RAW_admission_plan_and_new_mutation` |
| [E003](records/f1/E003.jsonl) | R004 / `attempts/focused-final` / `/tests/2` | PASS | `test_F1_native_post_move_status_failure_and_fresh_recovery` |
| [E004](records/f1/E004.jsonl) | R004 / `attempts/focused-final` / `/tests/3` | PASS | `test_F1_native_pre_move_refusal_preserves_nonempty_evidence_and_fresh_retry` |
| [E005](records/f2f3/E005.jsonl) | R003 / `focused-final-2` / `/tests/31` | PASS | `test_execution_racing_the_task_closure_never_writes_into_a_closed_task` |
| [E006](records/f2f3/E006.jsonl) | R003 / `focused-final-2` / `/tests/43` | PASS | `test_writers_racing_a_dying_completion_never_land_in_the_closed_task` |
| [E007](records/f2f3/E007.jsonl) | R003 / `focused-final-2` / `/tests/52` | PASS | `test_F2_cached_acquire_task_read_reproduces_error_but_preserves_PRE` |
| [E008](records/f2f3/E008.jsonl) | R003 / `focused-final-2` / `/tests/53` | PASS | `test_F2_cached_snapshot_read_is_refused_without_physical_effect` |
| [E009](records/f2f3/E009.jsonl) | R003 / `focused-final-2` / `/tests/54` | PASS | `test_F2_completion_lock_timeout_writes_nothing_and_releases_locks` |
| [E010](records/f2f3/E010.jsonl) | R003 / `focused-final-2` / `/tests/55` | PASS | `test_F2_directory_probes_do_not_invent_duplicate_during_real_move` |
| [E011](records/f2f3/E011.jsonl) | R003 / `focused-final-2` / `/tests/56` | PASS | `test_F2_genuine_duplicate_directory_still_fails_closed` |
| [E012](records/f2f3/E012.jsonl) | R003 / `focused-final-2` / `/tests/57` | PASS | `test_F2_invalid_completion_identity_creates_no_lock_files` |
| [E013](records/f2f3/E013.jsonl) | R003 / `focused-final-2` / `/tests/58` | PASS | `test_F2_move_between_destination_and_source_probe_is_resolved` |
| [E014](records/f2f3/E014.jsonl) | R003 / `focused-final-2` / `/tests/59` | PASS | `test_F2_move_cannot_interleave_START_APPLY_DONE_boundary` |
| [E015](records/f2f3/E015.jsonl) | R003 / `focused-final-2` / `/tests/60` | PASS | `test_F2_preflight_lock_failure_refuses_without_apply_and_replay_is_safe` |
| [E016](records/f2f3/E016.jsonl) | R003 / `focused-final-2` / `/tests/61` | PASS | `test_F2_projection_cached_snapshot_error_preserves_checkpoint_and_raw_state` |
| [E017](records/f2f3/E017.jsonl) | R003 / `focused-final-2` / `/tests/62` | PASS | `test_F2_release_event_error_after_DONE_is_replayed_without_second_apply` |
| [E018](records/f2f3/E018.jsonl) | R003 / `focused-final-2` / `/tests/63` | PASS | `test_F3_RAW_reader_is_inside_operations_lock_before_admission` |
| [E019](records/f2f3/E019.jsonl) | R003 / `focused-final-2` / `/tests/64` | PASS | `test_F3_marked_post_move_crash_late_writers_and_fresh_completion` |
| [E020](records/f2f3/E020.jsonl) | R003 / `focused-final-2` / `/tests/65` | PASS | `test_F3_writer_first_refusal_does_not_claim_crash_phase` |
| [E021](records/negative-controls/E021.jsonl) | R003 / `quality-final` / `/tests/0` | PASS | `test_counterfeit_raw_receipt_is_detected` |
| [E022](records/negative-controls/E022.jsonl) | R003 / `quality-final` / `/tests/1` | PASS | `test_missing_native_trigger_is_detected` |
| [E023](records/negative-controls/E023.jsonl) | R003 / `quality-final` / `/tests/2` | PASS | `test_old_start_barrier_oracle_falsely_rejects_legal_sequential_contracts` |
| [E024](records/negative-controls/E024.jsonl) | R003 / `quality-final` / `/tests/3` | PASS | `test_removing_completion_outer_lock_is_detected` |
| [E025](records/negative-controls/E025.jsonl) | R003 / `quality-final` / `/tests/4` | PASS | `test_removing_gap_recheck_reproduces_false_unknown` |
| [E026](records/negative-controls/E026.jsonl) | R003 / `quality-final` / `/tests/5` | PASS | `test_restored_old_lookup_reproduces_phantom_duplicate` |
| [E027](records/negative-controls/E027.jsonl) | R004 / `attempts/quality-byte-prefix` / `/tests/0` | PASS | `test_counterfeit_persisted_receipt_is_detected` |
| [E028](records/negative-controls/E028.jsonl) | R004 / `attempts/quality-byte-prefix` / `/tests/1` | PASS | `test_false_success_after_native_status_failure_is_detected` |
| [E029](records/negative-controls/E029.jsonl) | R004 / `attempts/quality-byte-prefix` / `/tests/2` | PASS | `test_lost_checkpoint_identity_is_detected` |
| [E030](records/negative-controls/E030.jsonl) | R004 / `attempts/quality-byte-prefix` / `/tests/3` | PASS | `test_missing_closeout_operations_lock_is_detected` |
| [E031](records/negative-controls/E031.jsonl) | R004 / `attempts/quality-byte-prefix` / `/tests/4` | PASS | `test_missing_native_pre_move_trigger_is_detected` |
| [E032](records/negative-controls/E032.jsonl) | R004 / `attempts/quality-byte-prefix` / `/tests/5` | PASS | `test_semantically_equal_rewritten_event_prefix_is_detected` |
| [E033](records/historical-red/E033.jsonl) | R003 / `repro-before` / `/tests/0` | ERROR | `test_F2_directory_probes_do_not_invent_duplicate_during_real_move` |
| [E034](records/historical-red/E034.jsonl) | R003 / `repro-before` / `/tests/1` | FAIL | `test_F3_RAW_reader_is_inside_operations_lock_before_admission` |
| [E035](records/historical-red/E035.jsonl) | R003 / `gap-before` / `/tests/0` | ERROR | `test_F2_move_between_destination_and_source_probe_is_resolved` |
| [E036](records/historical-red/E036.jsonl) | R003 / `target-raw-final` / `/tests/0` | ERROR | `test_execution_racing_the_task_closure_never_writes_into_a_closed_task` |
| [E037](records/historical-red/E037.jsonl) | R003 / `focused-final` / `/tests/33` | FAIL | `test_two_executors_on_one_physical_target_never_both_write` |
| [E038](records/historical-red/E038.jsonl) | R003 / `full-final` / `/tests/591` | ERROR | `test_new_chat_and_new_server_process_reopen_same_disk_state` |
| [E039](records/historical-red/E039.jsonl) | R003 / `full-final` / `/tests/592` | ERROR | `test_new_chat_process_reads_same_checkpoint_while_server_stays_alive` |
| [E040](records/historical-red/E040.jsonl) | R003 / `restart-diagnostic` / `/tests/0` | ERROR | `test_new_chat_and_new_server_process_reopen_same_disk_state` |
| [E041](records/historical-red/E041.jsonl) | R003 / `restart-diagnostic` / `/tests/1` | ERROR | `test_new_chat_process_reads_same_checkpoint_while_server_stays_alive` |
| [E042](records/historical-red/E042.jsonl) | R004 / `attempts/F1-first` / `/tests/3` | FAIL | `test_F1_admission_first_rejects_closeout_without_touching_existing_evidence` |
| [E043](records/historical-red/E043.jsonl) | HIST-F3 / `wa4r002-focused` / `/tests/13` | FAIL | `test_writers_racing_a_dying_completion_never_land_in_the_closed_task` |
