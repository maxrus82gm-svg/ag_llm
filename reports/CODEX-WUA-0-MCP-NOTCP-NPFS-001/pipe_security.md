# Pipe / token / grant модель

Это текущий пользовательский fixture, не доказанная cross-SID изоляция. Фактические результаты и source pins — `checks.json` и финальный `runs/<attempt>/`.

| Уровень | Реализация / доказательство | Предел |
|---|---|---|
| Namespace | Литеральный `\\.\pipe\` + regex точного имени; Win32 NPFS; `PIPE_REJECT_REMOTE_CLIENTS` | Remote names отклонены до native open; SMB/DNS не используются |
| Ownership | `FILE_FLAG_FIRST_PIPE_INSTANCE`, maxinstances=1, непередаваемый handle | Чужой precreated endpoint нельзя незаметно переиспользовать; второй owned instance отвергается |
| DACL | Protected `D:P(A;;0x00100083;;;<current-user SID>)`; readback реального descriptor через PipeStream.GetAccessControl | Единственный Allow ACE: read-data, write-data, read-attributes, synchronize. Нет Everyone/anonymous, WRITE_DAC/OWNER или FILE_CREATE_PIPE_INSTANCE. Это не шаблон production ACL между разными SID |
| Server → client auth | GetNamedPipeClientProcessId; held OpenProcess handle; primary token SID через OpenProcessToken/WindowsIdentity; image path/SHA; после hello — RunAsClient + эффективный SID и ровно Identification level | PID/имя/MAC отдельно не заменяют SID. RunAsClient заканчивается до запуска SDK/API, авторитет U не исполняет вызовы с токеном клиента |
| Client → server auth | GetNamedPipeServerProcessId, точный ожидаемый PID, удерживаемый process handle, primary token SID и SHA образа; Unicode Windows image API | Это primary token владельца процесса, не заявление о токенах всех его потоков. Image-file pin не является code signing или измерением всего loaded memory/dependency closure |
| Client SQOS | CreateFile с Identification-only SQOS и точными data rights; нет делегирующего impersonation level | Реальные C/U cross-token access rights ещё не испытаны |
| Grant | Новый session UUID + 256-bit in-memory key; HMAC-SHA256 с direction, protocol, session, sequence, length, body; сравнение MAC без раннего выхода | Environment используется только для своего текущего-user fixture. Защищённая доставка/revocation production grant и hostile same-user caller не доказаны |
| Authorization | Одна server-owned fixture/TASK, только ping/capabilities/context/status; существующая schema validation и независимый server read check | Нет production root/Run Store/path/process/model authority |
| Replay/mixing | Раздельные направления/sequence, неизменяемый session, request-ID history и pending correlation; fixture session обязана совпасть с transport config | Новая session требует нового экземпляра; нет reconnect или автоматического расширения scope |
| Limits | JSON: строгий UTF8, duplicates/types/depth/items; 8192 request / 32768 response; 128 wire frames, 96 request IDs/направление, 16 inflight; frame 2500ms, bridge 30s, process watchdog 40s | Idle тоже ограничен; это короткая fixture grant session, не готовый долговечный production service |

До auth отказ не создаёт synthetic API state. Negative cases проверяют MAC, session, peer PID/SID/image, protocol, replay, correlation, oversized/partial frames и чужой TASK. Проверка ожидаемого wrong SID использует настоящее чтение текущего peer token с намеренно несовпадающим ожидаемым SID; **это не запуск под вторым SID**. Новый current-user-only gateway намеренно отказывает конфигурации для другой identity.

Windows handles у relay/server непередаваемые. U child получает только три явных pipe handles; job назначен при suspended launch. Нормальный EOF передаётся authenticated close, затем закрывается stdin SDK и проверяется receipt. Abnormal close/timeout прекращает текущую owned цепочку. Жёсткий watchdog ограничивает даже зависший путь Dispose/IO; при завершении U ОС закрывает job. Это не supervisor чужих процессов и не право останавливать рабочие службы.

Остаточные TCB/gates: доверенные текущий launcher, OS/.NET/Python/SDK, локальные fixed-volume source/config paths; local administrator/same-user tampering не нейтрализованы DACL одного SID. Перед production нужны разные реальные токены, ACL источников/grant, pin полной runtime closure, негативные cross-SID/impersonation/handle-inheritance и race пробы в отдельной лаборатории. Один защищённый pipe не закрывает прочие BITS/COM/NPFS/system-DNS каналы. WFP native enforcement и фактический B egress владелец не проверены.
