# Fixture scope

`unprovisioned.json` — реальный текущий сценарий: одобренная VM не предоставлена, I01–I12 BLOCKED. Host inventory — отдельный contextual read-only snapshot, не подставной host attestation.

Сохранённый полный positive fixture и public test-only trust: `../evidence/attempt08/tests/`. Его expected PASS проверяется handwritten тестом; положительные ожидания не генерируются из production validator. Тестовый root и keys никогда не принимаются real mode. Synthetic GUID/owner/image hashes/time/endpoints не относятся к настоящей VM или профилям пользователя. Ни один fixture endpoint не открывался.

Каждая negative/mutation проверка получает адресно изменённый fixture; точные имена и результаты — `../evidence/attempt08/tests/results.json`, final mutants — `mutant_nic03`, `mutant_trust03`. Negative facts переподписываются synthetic ключами, чтобы проверять семантику, а не только повреждённую подпись. Для подписи отдельные ephemeral private keys остаются только в памяти процесса. Сохраняются публичные ключи и подписи.
