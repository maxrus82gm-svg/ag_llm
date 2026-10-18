# Gate F — future deployment and rollback contract

**План, не выполненные команды.** Сейчас отсутствуют VM GUID, backend/version и
resource root будущей VM; точные вызовы мутаций нельзя безопасно подставить и
выполнить. Ничего устанавливать/создавать в этой TASK не разрешено.

## Ownership до первой будущей мутации

Утвердить ledger: `task_id`, уникальный `owner_nonce`, фактический VM GUID,
host/backend build, absolute local root, VM config path, каждый VHDX/parent,
checkpoint ID/parent, media/output paths, observer process generation, resource
creation result и исходное состояние. Root новый и exclusive; resolved paths
не должны быть drive root, repo, Windows, profile, чужой VM или junction/UNC.
Никаких global NAT/switch/firewall/DNS/proxy/feature объектов в ownership этой
VM-задачи. Поэтому их rollback также не нужен и не допускается.

Предпочтителен уже подготовленный lab host. Если его нет, STOP перед системной
установкой. Включение Hyper-V/драйверов или reboot текущей Windows требует
другого task scope и собственного baseline/rollback/USER GO; удалить VM не
означает откатить включение гипервизора. Нельзя обещать “ничего не изменится”
для установки, которую здесь не исследовали и не разрешили.

## Деплой будущей owned VM по фазам

1. Проверить source/media/dependencies, ownership ledger, read-only inventory и
   факт отсутствия конфликтующих VM/disk paths. Сохранить подписанное/хешированное
   ожидание до создания. Только после отдельного provisioning GO.
2. Создать VM stopped без NIC/host channels. Записать **вернувшийся GUID**, не
   находить VM по одному display name. После каждой отдельной creation step
   сохранять result/ID; при ошибке не повторять неизвестно завершившуюся мутацию.
3. Stage trusted offline input; проверить I01–I12 до boot для network/device
   части и до native для всего контракта. Любое unknown → stopped/quarantine.
4. Сделать clean offline checkpoint и независимое readback. Второй, отдельный
   USER GO нужен на native run; scope и runtime budget привязаны к config digest.

## Остановка и возврат

1. Отозвать новые запуски/auto-resume. На drift/неисправность observer немедленно
   прекратить owned subject; если guest control не доверен — host pause/power-off
   **по ledger VM GUID**. Не завершать host V2Ray, чужие VM или общий hypervisor.
2. Сохранить доступное sanitized evidence и loss counters; отсутствие final
   receipt не маскировать. Убедиться с host side, что именно эта VM Off. Если
   host не подтверждает остановку, BLOCKED/QUARANTINE, никакого disk export,
   повторного запуска или удаления предполагаемых файлов. Не перезапускать
   hypervisor service и рабочую Windows как “очистку”.
3. Проверить owner markers/IDs, media attachments и backing dependencies перед
   offline read-only export. Никакого подключения output как live guest→host
   bridge. Секретные/неочищенные output не публиковать; исходный инцидент хранить
   по отдельно утверждённому приватному scope, если он возникнет.
4. Для следующего case: при Off вернуть **точный ledger checkpoint ID** / его
   known-clean disk chain; сверить конфигурацию и hashes после восстановления,
   отсутствие NIC/integrations/credentials, запустить новый preflight. При
   невозможности восстановить закрыть VM до investigation; не откатывать чужой
   baseline и не переустанавливать host.
5. Для окончательного disposal: сначала Off и проверка, что VM GUID/config,
   каждый snapshot/disk и resolved path принадлежат ledger, нет внешних
   referencing/backing consumers. Unregister только этот VM object; затем
   удалять только явно перечисленные owner resources в dependency-safe порядке
   по проверенным offline-документам данного backend. Никакого wildcard,
   рекурсивного поиска по имени, удаления общего root или reset firewall.
   Перед рекурсивным удалением повторно проверить абсолютные resolved paths.
6. Readback после cleanup: конкретный VM GUID отсутствует; owner handles/worker
   процессы исчезли; перечисленные resources отсутствуют либо retained и
   причина записана. Сверить хеши защищённых host inputs. Не трогать глобальные
   working-network настройки для достижения зелёного cleanup.

## Частичные отказы

| Сбой | Действие |
|---|---|
| Создание вернуло ошибку без ID | Никакого слепого retry/delete; readback точного owner manifest/path, reconciliation, unknown resource → BLOCKED |
| Hypervisor/control failure | Запрет дальнейших запусков; сохранить последнее host evidence; VM/resources quarantine. Если нельзя гарантировать Off — containment NOT VERIFIED; эскалация оператору лаборатории |
| Checkpoint/chain mismatch | Не восстанавливать “ближайший” snapshot; оставить Off, сохранить chain map, запросить новый доверенный baseline |
| Удаление/lock/access denied | Не повышать права и не force-unlock чужим процессом; остаток пометить retained/quarantine с exact ID/path; дальнейшая очистка отдельно согласуется |
| Evidence export не удался | VM Off, output retained, независимая приёмка BLOCKED; не включать сеть/clipboard ради экспорта |

## Точная отмена изменений этой TASK

Текущий host runtime не менялся. Изменены только новый report folder и own card.
`card_before.md` — единственная адресная резервная копия карточки до изменения;
`card_rotation.json` фиксирует before/staged/final hashes. Если нужно отменить
**только** карточку, сначала прочитать её текущие bytes и требовать совпадения
с recorded final SHA; при совпадении заменить точными bytes backup, затем
проверить before SHA. При любом позднем изменении — STOP/reconciliation, не
перезаписывать новую постановку/историю. Это описание отката, не автоматический
rollback. Report folder сохраняет evidence и не удаляется при откате карточки.
