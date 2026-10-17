# MANUAL ENGINEERING REVIEW — AMENDMENT 06

Codex 007, самостоятельный review поверх автоматических parser tests.
Это не независимая приёмка WEB_10 и не runtime source audit недоступного кода.

## Изученный порядок операций и доказательства

1. Текущая карточка и нормы 18/36.1 прочитаны. Старые SELF_PUBLISH/WEB_08/ротация
   карточки не применены: AM06 явно задаёт только новый каталог, запрет Git/GitHub,
   frozen БЛОК 1 и отчёт через пользователя WEB_10. 17 адресных Rule-ID/contract
   definitions в `rules_read.json`; source hashes совпадают с AM05. Текущий route
   08→000→34→18→01 и профильные материалы сохраняют разделение WUA/WA4-R/LLM12.
2. Прочитаны AM05 report/manual review/checks и readable WEB_10 summary. Formal
   review в app read_thread представлен только placeholder: его содержимое нельзя
   объявить прочитанным или принятие состоявшимся. Summary подтверждает границу
   reference 19/19 против ещё непроверенного native клиента. Сообщений не отправляли.
3. `static_audit.py`: сначала hash EXE, затем только byte parsing. ZIP не распакован
   на диск, исполняемый файл из ZIP читается в память; проверена единственность
   имени и hash. SHA сравнен и с cached release digest, и с ранее сохранённым
   SHA256SUMS. Это контроль сохранности/происхождения cached комплекта, не новая
   remote authentication. Метаданные/суммы одного origin не независимая attestation.
4. Go inline build-info прочитан без запуска: module framing, version, deps и
   build settings. PE32+/machine и certificate directory проверены с bounds checks.
   pcHeader найден единственным по формату/разумным пределам; извлечены names и
   source paths. Нельзя превратить эти paths в утверждение, что сами Go файлы
   доступны. Исполнения EXE/Go resolver/client transport в этом этапе нет.
5. Два наиболее существенных новых свидетельства — **встроенный** proxy контракт
   ignore-NO_PROXY при explicit route и HTTP(S)-only error literal. Review отделяет
   contract/literal/symbol от branch execution. Не объявлено, что NO_PROXY был
   реально подставлен в native процесс или SOCKS rejection исполнился.
6. Матрица `proxy_path_audit.md` проверена по конкретным names/path entries.
   Рассмотрены default clone, config inheritance, per-binding factory/cache,
   control-plane secret transport, startup/runtime MCP, OAuth origin/redirect,
   Harpoon callouts, proxy health и companion. Ни один пробел не помечен PASS
   только по названию функции. В частности resolveProxyWithFallback ≠ доказанный
   network fallback; proxyhealth.recordDirect ≠ автоматически direct dial.

## Trigger, oracle и edge cases собственных helper tests

Пять unit tests относятся только к byte parser, не к tunnel-client. Независимый
малый Go inline frame проверяет действительное framing/records, malformed string,
незавершённый/overflow varint и PE offset выходят на точные ValueError branches.
Тесты не вычисляют expected из production method и не требуют сети/EXE.
Результат: 5 collected / 5 PASS / 0 FAIL/ERROR/SKIP, exit 0.

Первоначальный inline artifact validator имел ошибочное имя codec utf8-sig и
остановился на чтении UTF-8 текста. Original traceback сохранён отдельно как
HARNESS DEFECT. Исправленный `validate_artifacts.py` использует utf-8-sig,
перепроверяет 70 input hashes, JSON/AST, counts/locators/identity, выполняет
ограниченный secret scan и запечатывает manifest. В нём нет native executor.
Его файловые/regex проверки не заменяют независимого review и не являются DLP
или OS/network attestation. Обновления при повторном запуске только в owned folder.

`native_test_gate.py` просмотрен отдельно от результатов: в нём нет subprocess,
socket, shell, executor, --force или приёма JSON «доказательства». Он только пишет
BLOCKED и возвращает 3. Конфиг не может включить отсутствующий исполнитель.
18 contracts в `native_test_plan.json` — **не собранные/пропущенные native tests**.
Нужные API paths фиктивного control-plane не придуманы по имени команды: native
fixtures/driver ещё не реализованы, зависят от matching source + containment.

## Рассмотренные альтернативы

- Повторить AM05 Python stand: не ответит на вопрос о Go binary; не запускался.
- Повторить старый dev proxy localhost bridge: проверит happy path MCP, не общую
  native изоляцию/fault paths; не запускался и не переименован в fail-closed PASS.
- Задать только loopback flags/child environment: полезно как defense-in-depth,
  но не enforceable граница для всех native/child DNS/transport paths.
- Использовать текущий V2Ray для faults: запрещённая рабочая инфраструктура, кроме
  того loopback proxy может вести наружу. Он вообще не включён в новый стенд.
- Python audit или обычный Job Object: не предъявляют нужный native network deny.
- Создать OS security profile, изменить firewall/TUN/права или включить VM features:
  вне разрешения; не сделано. Инвентаризация нашла только недоступные сейчас
  кандидаты, не невозможность безопасного решения вообще.
- Скачать source release asset самому: запрещён Git/GitHub. Вместо обхода найден
  точный locator/size/digest и составлен адресный запрос координатору.

## Открытые риски и итог review

Без исходников нельзя исключить alternate transport/override/redirect/DNS, а без
принудительной границы даже хороший source review не выполняет требование AM06.
Для сетевого product oracle недостаточно отсутствия origin request: нужен учёт
**попыток** direct dial, в том числе заблокированных самой средой. ОС containment
и product fail-closed — разные проверки. Фиктивные endpoints должны быть внутри
будущего гостя; внешние canaries/OpenAI и реальные ключи не нужны и запрещены.

Корректное решение сейчас — **BLOCKED / native NOT EXECUTED**. Подготовка завершена
в текущем scope, но технологическая цель native fail-closed не достигнута.
Следующий этап требует exact source pack/provenance и отдельно доступной,
разрешённой, проверенной loopback-only среды для **того же Windows EXE**.
Независимая проверка WEB_10 ещё предстоит после пользовательской передачи/публикации.
