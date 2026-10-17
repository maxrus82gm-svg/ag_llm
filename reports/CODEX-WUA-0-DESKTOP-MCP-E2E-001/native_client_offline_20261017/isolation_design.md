# Native containment gate — BLOCKED

Требование AM06: до первого исполнения настоящего клиента исключить внешний
выход. В этом этапе EXE не запускался даже с `--help`/`--version`: использован
сохранённый вывод и непосредственное чтение байтов. Child native transport tests: 0.

## Что установлено в текущей Windows

`environment_inventory.json`: Windows 10.0.19045.0. В PATH не найдены Go,
Docker/Podman, WindowsSandbox, hcsdiag, Get-VM/Get-Container. Штатного
WindowsSandbox.exe нет; `wsl --status` возвращает 50. Пять optional features имеют
сырое InstallState=2. Этот ограниченный inventory не доказывает отсутствие всех
возможных средств на компьютере, но готовую применимую изоляцию не предоставляет.
VM/container не запускались, features не включались. Текущих tunnel-client/
cloudflared процессов при снимке не найдено; чужие процессы не завершались.

## Почему недостаточно уже доступных средств

- Loopback-флаги — настройка приложения. Они не запрещают другой dial, resolver,
  background health checker, redirect, дополнительный transport или child process.
- Python audit hook действует на Python API своего процесса. Go WinSock и дочерние
  процессы через него не проходят. AM05 stand не является containment native EXE.
- Proxy environment/явный proxy — маршрут отдельных HTTP клиентов, не граница ОС.
  Само наличие SOCKS5 listener или V2Ray не запрещает прямой выход приложения.
- TCP snapshot/лог proxy не ловит все кратковременные TCP/UDP/DNS попытки и не
  устанавливает невозможность внешнего выхода.
- Ограничение времени/числа процессов Job Object само по себе не предъявлено как
  доказанный network deny. Здесь не создавались новые security tokens, AppContainer
  profiles, loopback exemptions, firewall rules или hook/injection обходы.
- Linux-контейнер с другим бинарником или Wine не является эквивалентным тестом
  установленного Windows amd64 EXE. Результаты другой платформы нужно отделять.

## Минимальный проект допустимой будущей границы

Предпочтительный вариант для **этого же Windows EXE** — предоставленная заранее
disposable Windows VM/sandbox с принудительно отключённой внешней сетевой связью.
Это проект требований, не установленная/проверенная здесь технология и не разрешение
включить компоненты ОС. Создание/активация такой среды требует отдельного scope.
Изоляция должна сохранять внутри гостя TCP loopback для origin/proxy fixtures.

До старта EXE reviewer должен проверить:

1. Есть независимо проверяемая конфигурация гипервизора/границы, запрещающая весь
   non-loopback IPv4/IPv6, UDP/DNS и сетевые пути дочерних процессов. Нет NAT/bridge,
   host proxy, forwarding, виртуального сетевого канала с выходом наружу. Отсутствие
   маршрута в выводе утилиты без enforceable boundary недостаточно.
2. Переданы только bytes проверенного EXE и offline fixtures; hashes сверены внутри.
   Нет live credentials, OpenAI API key, профилей пользователя, Cloudflared companion,
   сокетов/агентов хоста, production mounts. Нужные зависимости доставлены offline.
3. Все фиктивные origin, proxy и control-plane endpoints созданы внутри изоляции;
   bind только 127.0.0.1 (и отдельно ::1 при необходимости). Нельзя использовать
   loopback bridge к рабочему V2Ray: он был бы разрешённым местным gateway в интернет.
4. Enforced boundary проверена до native runtime и отдельно от логики клиента.
   Контроль должен охватить IPv4/IPv6/DNS и descendants. Даже предположительно
   заблокированные реальные внешние адреса/OpenAI не используются в этом TASK.
5. Native observer различает попытку direct dial и успешный proxy forward внутри
   гостя. Защита среды не должна маскировать продуктовый fallback как fail-closed:
   если клиент пытается direct, product gate FAIL, даже когда ОС блокирует пакет.
6. Проверены deny-on-boundary-failure, bounded timeout, kill/reap **собственных**
   процессов и отсутствие cleanup вне disposable root. Уничтожение среды не должно
   менять host firewall/V2Ray/DNS/права. Рабочие процессы не перезапускаются.

Только после отдельной проверки этих пунктов имеет смысл реализовать native driver
и сценарии `native_test_plan.json`. В текущем `native_test_gate.py` исполнителя
процессов нет вообще; файл только фиксирует BLOCKED, exit=3. Он намеренно не
принимает самодельный JSON-флаг «изоляция подтверждена» как разрешение запуска.

## Условия снятия BLOCKED

Два независимых пробела: (1) соответствующие исходники/provenance и законченный
source review; (2) разрешённая, доказанная native containment boundary. Один source
audit без enforced границы не заменяет требование пользователя. Пока оба пункта
не выполнены, исходящие native fault tests не запускаются. Это не утверждение
об их принципиальной невозможности.
