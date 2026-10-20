# Ограничения выпуска 0.1.0-offline

1. **Это законченные Discovery/Plan/Contracts/Tests и заблокированные
   Install/Uninstall scaffolds по §6.3/§12 TASK, а не действующий защищённый
   installer.** Нет реальных provisioning calls. C# source задаёт границу
   компонента, все операции бросают NotSupportedException; он не собирался и
   не загружался. Для полноценного backend нужны reviewed Fwpm/account/LSA/ACL/
   startup/readback APIs, защищённый ledger и отдельный USER GO.
2. **55/55 — покрытие конечного versioned contract**, не «все возможные сведения
   Windows» и не 100% обнаружение/безопасность. На текущей машине 14 metadata
   VERIFIED, из них admin_token=false — корректно обнаруженный отрицательный
   факт; 42 requirement rows блокируют установку. Неизвестное не считается safe.
3. Нет verified SID/WFP matching, loopback/bind identity, arbitration/third-party
   filters, BFE/boot/old-flow behavior, DNS/служб-посредников, effective ACL для
   ещё не созданных SID, observer, host binding, authenticated remote route.
   Даже операторский JSON «VERIFIED» не включает отсутствующий backend.
4. Windows 10 Pro x64 — единственная реально обследованная ОС. Windows 11,
   missing binaries, GPO/MDM/conflicts и другие случаи покрыты synthetic fixtures,
   не физическими компьютерами. ARM64/x86/неизвестные build/SKU — не certified.
   Collector требует 64-bit PowerShell; на 32-bit останавливается до provider
   queries, не выдаёт WOW64 process architecture за установленную OS architecture.
5. Runtime финального выпуска проверен на PowerShell 7.6.5. Финальные 8 PS source
   files разобраны parser Windows PowerShell 5.1 без ошибок; это **не runtime PASS**.
   Его текущая execution policy Restricted не обходилась для финального прогона.
   Ранний прототип дал 47/47 на 5.1 с явно переданным process-only Bypass; это
   отдельный ограниченный результат, не приёмка финального кода и не рекомендуемый
   способ запуска. Постоянные policy stores не изменялись. Флаг больше не
   применялся; в toolkit нет автоматического bypass/unblock/elevation.
6. Новая Windows со stock 5.1/Restricted не обязана запускать неподписанные
   development scripts. Нужна уже разрешённая среда исполнения; signing сам по
   себе не отменяет Restricted/GPO. Любое изменение политики — отдельно у
   пользователя/администратора, не этим toolkit. Python нужен лишь для authoring/
   handoff helpers этой TASK, не для переносимой папки toolkit.
7. Metadata file version не всегда доступна (у найденного брокера отсутствует),
   не равна `--version` или source→EXE attestation. Exact official runtime source
   archive/STDIO paths/resources/cwd/remote endpoint нельзя угадывать. Они требуют
   разрешённого offline operator input. Реальные secret configs не анализировались.
8. PATH search ограничен 256 локальными проверенными entries, без дискового
   рекурсивного поиска; добавлен exact-name process ExecutablePath без CommandLine.
   Renamed/несколько candidates → ввод оператора/CONFLICT. Недоступное поле
   не означает доказанного отсутствия компонента на всём компьютере.
9. Порт — лишь свободный snapshot candidate, не bind/reservation, не проверка
   Windows excluded ranges и не защита от захвата. Никаких socket/health probes.
   File/path проверки не являются kernel-level TOCTOU boundary при враждебной
   подмене локального filesystem. Предполагаются доверенные ОС/providers и
   выбранные локальные пути; T2 malicious-host protection не обещается.
10. GPO/MDM key presence и security-product counts не определяют effective
    WFP graph; нет domain refresh/удалённого опроса. Proxy env/config secret
    values намеренно не читаются. Кausal DNS/WinHTTP/BITS/COM/crypto work остаётся
    обязательным незакрытым proof, а не условно допустимой утечкой.
11. Public plan редактирует private paths/remote addresses в role refs. Exact
    параметры оператор проверяет отдельно локально через `-LocalPreview`;
    его вывод не публикуется. Hash связывает содержимое, но не подписывает
    approval, не удостоверяет компьютер и не заменяет свежий privileged readback.
12. Rollback сейчас — работающий валидатор/планировщик, не удаление ресурсов.
    Заявления ledger `created_by_kit`/`reported_zero` недоверенные до отдельной
    проверки реального ownership/отсутствия SID work/flows. Поэтому всегда
    ROLLBACK BLOCKED и keep_deny=true. Исторические reference PASS не native proof.
13. Ничего не устанавливалось в обычный ChatGPT; UI остаётся вне будущих C/B
    правил. Рабочий V2Ray, production и launcher hold не изменялись. Native/
    remote route/ordinary Chat receipt остаются NOT VERIFIED.
