# Disposable Windows VM — архитектура

**OFFLINE VM DESIGN PARTIAL.** Backend/version/media/source и реализация
независимого observer пока не предоставлены. Это воспроизводимая схема и
порядок подготовки, не готовый VM image или действующая защита.

```text
Trusted lab hypervisor host (existing user network unchanged)
   VM GUID / owned local disks / exact config digest
   no virtual NIC / switch attachment / passthrough / host relay
   basic console only, no clipboard/drive/serial/guest-agent data bridge
   |
   +-- disposable Windows guest, fresh offline baseline
         observer + process-tree census (running before subject)
         native tunnel-client.exe (exact hash, no real credentials)
           -> owned 127.0.0.1 HTTP CONNECT fixture
           -> owned 127.0.0.1 SOCKS5 fixture / fake origin
         all fixtures inside guest, bounded ports and lifetime
```

Граница защищает весь гостевой runtime, включая spawn/children/helpers, а не
только известный EXE. Доверенными остаются host/hypervisor/firmware, оператор
и наблюдатели. VM escape, злонамеренный hypervisor admin, физический/covert
канал не исключаются одним VM config; это явные предпосылки threat model.

## Подготовка в будущей отдельной TASK

1. Сначала получить exact source и offline build/runtime/observer dependencies,
   доверенный hypervisor version и лицензированный Windows ISO/base image.
   Manifest каждого asset: bytes, SHA-256, origin/проверявший, license, dependency
   closure, запрет package auto-update/download. Никаких реальных host secrets.
2. До создания — утвердить owner ID, VM GUID, новый локальный resource root,
   capacity/quota и ledger ресурсов. GUID должен вернуться из фактического
   создания; placeholder не является evidence. Использовать локальные пути без
   UNC/cloud mount/reparse/общих writable backing disks. Проверить base disk
   chain и отсутствие родителя вне утверждённого owner manifest.
3. Подготовить VM **до первого boot** с нулём NIC objects; без switch attachment,
   NAT/bridge/host-only, SR-IOV/discrete-device assignment, USB/GPU/passthrough,
   serial/named pipe/shared socket, guest relay/PowerShell Direct. Отключить
   guest integration/data services в её конфигурации; basic console, без
   enhanced session/RDP clipboard/drive/device redirection. Не менять глобальные
   настройки рабочего host ради одной VM. Нельзя сначала скачать что-то внутри
   VM, а затем объявить её доверенной offline-базой.
4. Stage inputs только через локальный read-only ISO/диск offline. Никаких
   shared folders/host proxy/live V2Ray. После копирования внутрь guest удалить
   ненужные media attachments при выключенной VM. Не держать guest disk
   смонтированным host и guest одновременно. Образы с auto-login чужой учётной
   записи, реальными keys/credentials/history не использовать.
5. Установить guest offline без account/network bypass tricks, при возможности
   поддержанного media/setup. Если конкретный setup требует внешней сети или
   неподтверждённого обхода — BLOCKED; выбрать другой разрешённый image.
   Клиент ещё не запускать. Собрать device/route/DNS/proxy/process inventory;
   отсутствие default route само по себе не достаточно.
6. Выключить VM; сохранить clean pre-native checkpoint + owned disk chain,
   config digest и hashes staged assets; освидетельствовать снаружи. Не обещать
   checkpoint integrity по одному его имени: после возврата заново проверять
   config/content. Checkpoint с памятью/сетью/ключами от другой задачи не подходит.
7. Независимый verifier сверяет контракт и разрешённые версии/состояния;
   отдельный USER GO требуется на ограниченный native запуск. В данной TASK
   ни подготовка VM, ни наблюдатели, ни клиенты не запускались.

## Наблюдение и стоп

Два независимых слоя: host/hypervisor удостоверяет отсутствие device/backend
путей и изменения config; guest observer собирает process create/exit, sockets,
DNS/IPv6/UDP и fixture transcripts. Guest TCP table или отсутствие host packets
в одиночку недостаточны. Неожиданный child, VM config change, event loss,
перезапуск observer, новый NIC/integration/device, неизвестный endpoint,
истечение gate/time budget — немедленный STOP, пауза/выключение **только owned VM**
с host side, сохранение evidence, никакого автоматического reconnect/resume.
При недоступном host control не запускать и не возобновлять subject; дальнейшее
физическое containment относится к отдельной утверждённой лаборатории.

Первый gate исключает Cloudflared. Его отсутствие должно быть доказано
source/config и process oracle; “не ожидали ребёнка” не равно запрету spawn.
Любой обязательный child требует нового exact hash/argv/owner и отдельного
включения в заранее одобренную матрицу. Не копировать cloudflared.exe в VM
на всякий случай и не запускать существующий launcher с hold.

Экспортировать только очищенные JSON/text после завершения и **power-off**:
через отдельно утверждённый owned output disk, подключаемый к доверенной
среде строго read-only, без autorun/исполнения guest-кода. Этот обмен не должен
существовать как live bridge при запуске subject. Evidence фиксирует все
attach/detach операции; очистка и секреты проверяются до публикации.
