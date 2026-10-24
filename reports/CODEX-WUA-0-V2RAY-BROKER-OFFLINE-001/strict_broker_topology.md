# Топология STRICT_V2RAY_BROKER

## Будущая система — требования, не установленное состояние

```text
C: wua-client (непривилегированный SID)
  official tunnel-client ──TCP4──> 127.0.0.1:P
      └─ STDIO → существующий C relay ──local authenticated NPFS──> U gateway

B: wua-broker (другой непривилегированный SID)
  один reviewed V2Ray engine process
    HTTP CONNECT listener 127.0.0.1:P
    этот же PID + effective B token ──TCP4──> один literal upstream R:Q

U: server-owned gateway → read-only server authority → Web Alarm
```

Внешние CONNECT destinations передаются внутри **аутентифицированного зашифрованного remote proxy protocol**; R:Q — transport next hop, не произвольный конечный адрес, сообщённый C. Protocol/peer pin/credential delivery пока не выбраны и не доказаны. Шаблон не содержит remote credentials. Обычный plaintext forward proxy или прямой dial CONNECT host не удовлетворяют целевой конструкции.

Только C→P и B→R:Q могут быть сетевыми edges этой цепочки. Никаких C→remote, B→пользовательский SOCKS, B→второй proxy, B→resolver или companion с внешним сокетом. U authority и NPFS не дают C/B права менять задачи/разрешения/команды. Сам по себе allow на loopback P не аутентифицирует listener; нужен held process identity/image/token и свежая authority handshake.

P/R/Q/SID, owner UUID, generation — параметры будущего target discovery. В synthetic example SID1001/1002/1003, P32123 и R192.0.2.17:443 — тестовые данные, не настройки хоста. Валидатор переиспользует прежние C/B/UI SID domains, child roles/hashes и STDIO/NPFS topology checks.

## Реально выполненная модель

```text
test parent PID (current user), C-model client + независимый receiver/observer
  CONNECT → собственный 127.0.0.1:P, allocated by bind(0)
      Python worker PID (current user), B-model
         единственный connect → собственный 127.0.0.1:T
             receiver в parent PID
```

Worker PID совпадает с владельцем listener и outgoing socket по read-only Windows TCP table. Receiver проверяет UUID/phase/session и отдаёт synthetic route nonce. Ни T, ни `.invalid` payload names не являются внешними endpoints; DNS не вызывается. В положительном тесте один CONNECT и один worker connect; forwarding работает в том же процессе без SOCKS/helper.

Все процессы используют текущую пользовательскую identity. **B-model не является wua-broker**. Настоящего remote R:Q, шифрованного proxy protocol, Windows token separation и V2Ray здесь нет. Разделение parent/worker/receiver нужно для наблюдаемого socket ownership и mutation controls, а не имитации OS enforcement.

Lifecycle contract: startup DISABLED; observer/policy loss → stop owned chain, no auto resume; restart → fresh instance/generation/attestation; pre-existing flows требуют лабораторного доказательства. Fixture practically enforces one-use directory claim, fresh UUID, bounded frame/relay lifetime и завершение собственного процесса. Управление настоящим V2Ray или службами отсутствует.
