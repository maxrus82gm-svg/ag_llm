# План native испытаний — NOT RUN

18 семейств сценариев, не 18 выполненных probes. Варианты внутри семейства требуют отдельного future exact collection. Все сетевые/NPFS/process probes здесь запрещены.

Перед будущим прогоном: новый scoped USER GO, доказанное независимое outer containment, approved dummy endpoints/source/roles, trusted observers, monotonic complete window и свежие nonce. Observers и positive controls не должны менять policy проверяемого процесса. Incomplete observer, unsupported protocol, timeout или отсутствие receiver не PASS.

Native receipt format/подпись/доверенная выдача ещё не реализованы. offline_oracles.py проверяет лишь согласованность синтетических утверждений для DENY, B egress ALLOW, QUIESCENCE; не аутентифицирует evidence и не покрывает отдельно NPFS/auth/boot/config семантику. Эти семейства требуют специальных native observers. N16 не передаётся B-egress oracle.

Данные: native_plan.json; no runnable native test/setup scripts. Остановка и rollback: rollback_plan.md. Upstream auth leakage SECURITY BLOCKER остаётся даже для dummy-native плана до отдельного review.

## N01 — C direct IPv4 TCP

**Статус:** BLOCKED / NOT RUN.

**Наблюдение:** Trusted observer удерживает C process/token/image handle; independent WFP decision + scoped owned receiver с run nonce.

**Ожидание:** Попытка действительно инициирована C; коррелируемый deny выбранной boundary; ноль nonce receipts.

**Отрицательный контроль:** В заведомо изолированной lab разрешённый контроль observer/receiver и намеренно отсутствующий lab deny должны выявить неверный oracle; bypass разрешён только при доказанном outer containment.

**Ложный PASS:** Timeout, неверный target, не запущенный процесс или недоступный receiver выглядят как block.

**Подготовка/откат:** Заранее согласованные disposable endpoints; после пробы quiesce C, keep-deny, без реального DIRECT из рабочей Windows.

## N02 — B exact physical upstream

**Статус:** BLOCKED / NOT RUN.

**Наблюдение:** Independent socket→held process→primary B token/image observer и remote controlled upstream receipt; logical CONNECT receipt отдельно.

**Ожидание:** Один approved R:Q TCP socket реально принадлежит B engine; nonce/payload у owned upstream, без UI delegation.

**Отрицательный контроль:** B-wrapper с U-owned engine и CONNECT200 без downstream receipt должны провалить owner/route oracle.

**Ложный PASS:** CONNECT200, PID reuse, sampled socket table или TLS session cache ошибочно принимаются за B egress.

**Подготовка/откат:** Только lab-approved engine/source и dummy auth после secret safety review; никакого real tunnel; остановить owned tree, закрыть flows.

## N03 — B wrong address/port/alternate proxy

**Статус:** BLOCKED / NOT RUN.

**Наблюдение:** B initiation/token evidence + effective tuple policy observer + controlled forbidden receivers.

**Ожидание:** Каждый wrong-IP/wrong-port/secondary proxy tuple отклонён; нет receipts или альтернативного socket owner.

**Отрицательный контроль:** Внутри outer-contained lab intentional wrong-tuple filter mutant должен быть обнаружен downstream observer.

**Ложный PASS:** Receiver down, неверный IP family или движок сам отказал до системного фильтра.

**Подготовка/откат:** Тестовый бинарник/набор tuple утверждены отдельно; scoped receipts; quiesce до cleanup.

## N04 — Upstream loss/retries/redirect/env

**Статус:** BLOCKED / NOT RUN.

**Наблюдение:** Owned upstream fault controller, monotonic attempt log, independent all C/B scoped flow observer и effective policy.

**Ожидание:** После отказа/timeout/reset/redirect/NO_PROXY/env попытки остаются только approved edge; нет DIRECT/DNS/secondary route.

**Отрицательный контроль:** Изолированный fallback mutant с controlled alternate receiver должен дать FAIL даже при исходном CONNECT error.

**Ложный PASS:** Короткое окно скрывает delayed retry, DNS/health dial или reconnect после восстановления.

**Подготовка/откат:** Fault injection только lab endpoint; bounded retries+grace window из source review; keep-deny при восстановлении.

## N05 — IPv6 / mapped / transition

**Статус:** BLOCKED / NOT RUN.

**Наблюдение:** Initiator token + address-family/tuple observer, V4/V6 classification evidence и owned dual-stack receivers.

**Ожидание:** C/B ::1, IPv6 external, IPv4-mapped и доступные transition paths не создают неутверждённый egress.

**Отрицательный контроль:** Изолированный V6 deny omission mutant выявляется; positive observer control на отдельной lab role.

**Ложный PASS:** IPv6 disabled или отсутствует route: NOT TESTABLE, а не подтверждённый WFP deny.

**Подготовка/откат:** Не включать IPv6 на рабочей Windows; поддержка family предварительно согласуется для lab; затем quiesce.

## N06 — DNS and delegated resolver

**Статус:** BLOCKED / NOT RUN.

**Наблюдение:** Scoped C/B attempts + independent resolver/service delegation observer + owned DNS/DoH/DoT receivers.

**Ожидание:** Нет unapproved resolution ни от C/B, ни от делегированного U/SYSTEM service.

**Отрицательный контроль:** Cache-busting nonce и deliberately delegated resolver mutant должны выявить обход SID-only coverage.

**Ложный PASS:** Cache hit/hosts file скрывает сетевой DNS, а наблюдение только C/B пропускает DNS Client service.

**Подготовка/откат:** Синтетические имена и owned DNS только под отдельным network GO; не менять host DNS/V2Ray; dispose lab.

## N07 — UDP/raw/secondary protocols

**Статус:** BLOCKED / NOT RUN.

**Наблюдение:** Actual protocol capability/attempt observer + filter classification + owned protocol receivers.

**Ожидание:** Никакого необъявленного UDP/ICMP/raw/secondary path; неподдерживаемые probes отдельно NOT TESTABLE.

**Отрицательный контроль:** UDP omission mutant в outer-contained lab должен зарегистрироваться receiver, а не остаться зелёным.

**Ложный PASS:** Privilege error при raw socket creation принимается за сетевой фильтр; UDP silence за deny.

**Подготовка/откат:** Не повышать права для текущей TASK; будущий GO задаёт разрешённые протоколы; quiesce/keep-deny.

## N08 — Unauthorized NPFS peer / pipe squatting

**Статус:** BLOCKED / NOT RUN.

**Наблюдение:** Gateway access/peer decision fixed code, kernel pipe peer PID→held token/image handle, independent worker invocation counter.

**Ожидание:** Wrong SID, same-SID wrong image, remote pipe и precreated fake server отвергнуты; SDK не запущен для запроса.

**Отрицательный контроль:** ACL-only или SID-only peer mutant в lab обязан пропустить controlled adversary и вызвать FAIL.

**Ложный PASS:** Gateway не работает/нет pipe; отказ не из-за auth; PID/image race или broad access mask.

**Подготовка/откат:** Disposable exact pipe names и dummy grant; без реальных secrets; закрыть pipe/job/handles и проверить отсутствие child.

## N09 — Config/source tamper and TOCTOU

**Статус:** BLOCKED / NOT RUN.

**Наблюдение:** Trusted controller preimage/pins + file ACL/reparse/replacement observer + actual launcher admission and process count.

**Ожидание:** Модификация после preflight/смена parent/reparse/merge/env/reload => no Resume; никаких network attempts.

**Отрицательный контроль:** Pin-check omission или writable-parent mutant должен дать controlled launch и FAIL oracle.

**Ложный PASS:** Повторное чтение того же caller pin, вместо trusted controller; disk hash не равен mapped executable.

**Подготовка/откат:** Только lab copy, никакого рабочего config; restore owned preimage compare-and-swap, keep admissions frozen.

## N10 — Auth/407/error/log secret boundary

**Статус:** BLOCKED / NOT RUN.

**Наблюдение:** Dummy unique canaries; independent enumeration permitted diagnostic sinks/crash/argv/env channels; auth handler receipt.

**Ожидание:** Missing/empty/wrong auth отклонён; canary secret/header absent in every agreed sink, including upstream error chain.

**Отрицательный контроль:** Canary-leaking logger mutant обязан детектироваться; пустые/несобранные sinks => INCOMPLETE.

**Ложный PASS:** Redaction маскирует исходную утечку, incomplete sinks, real credential ошибочно попал в evidence.

**Подготовка/откат:** Только dummy credentials после source fix/review; реальный upstream secret blocker не снят; sanitized counts, raw canary fixture приватен в lab.

## N11 — Recovery / deny removal / UI preservation

**Статус:** BLOCKED / NOT RUN.

**Наблюдение:** Independent lifecycle+queued-work/flow/handle observer, exact owned filter/ACL readback before/after; agreed U baseline.

**Ожидание:** Deny не удаляется до zero-work, startup frozen; recovery не меняет U proxy и не resurrect C/B.

**Отрицательный контроль:** Forged ledger zero, surviving child/flow и чужой object key должны дать KEEP DENY, не cleanup.

**Ложный PASS:** PID list/ledger заменяет real quiescence; global reset чинит lab ценой ослабления host.

**Подготовка/откат:** Out-of-band recovery и scoped preimages до setup; only exact owned rollback, unknown => keep-deny/escalate.

## N12 — Children / alternate token / delegated helper

**Статус:** BLOCKED / NOT RUN.

**Наблюдение:** Held process ancestry/primary tokens, job handles, independent flow owner and delegated work observation.

**Ожидание:** Same-SID children restricted; undeclared image suspended/rejected; token/delegation/handle escape не даёт U egress.

**Отрицательный контроль:** Image-only filter или broker wrapper delegating U engine должен дать FAIL.

**Ложный PASS:** Job kill-on-close ошибочно принят за сетевой sandbox; snapshots пропускают короткоживущий helper.

**Подготовка/откат:** Только disposable binaries и controlled U helper; no SeDebug grant; stop entire owned tree and delegated queues.

## N13 — Loopback exact port / B listener owner

**Статус:** BLOCKED / NOT RUN.

**Наблюдение:** Local listen/accept owner token+image, bind exclusivity, client auth and independent flow policy observer.

**Ожидание:** Wrong port, ::1, fake/rebound U listener и non-B listener не приняты; C exception не расширяется.

**Отрицательный контроль:** Correct tuple but wrong listener owner должен провалить gate даже при CONNECT200.

**Ложный PASS:** Tuple-only ALE check ошибочно приписывает порт B, process reuse и bind race.

**Подготовка/откат:** Только если выбран loopback transport; no рабочие ports; stop client before server cleanup, keep-deny.

## N14 — Crash / reboot / BFE/provider loss

**Статус:** BLOCKED / NOT RUN.

**Наблюдение:** Out-of-band boot/lifecycle observer + effective persistent-policy readback before admission + controlled receiver.

**Ожидание:** C/B не Resume в gap и после policy loss; reboot не превращает отсутствие controller в разрешение.

**Отрицательный контроль:** Startup-before-policy mutant должен дать FAIL; nonpersistent omission в disposable lab обнаруживается.

**Ложный PASS:** PERSISTENT flag принимается за boot-time enforcement; probe начинается после опасного окна.

**Подготовка/откат:** Отдельный GO на reboot/service fault в lab, никогда рабочую BFE; independent outer containment and recovery до fault.

## N15 — Existing flow / inherited socket handle

**Статус:** BLOCKED / NOT RUN.

**Наблюдение:** Trusted handle inheritance inventory, admission ordering, scoped flow lifecycle observer и owned receiver.

**Ожидание:** Нет pre-policy established flow или duplicated foreign socket у C/B; rollback waits for all references.

**Отрицательный контроль:** Intentionally inherited already-connected lab socket должен выявить gap connect-time-only policy.

**Ложный PASS:** Новые connect blocked, но existing socket продолжает data; table sampling теряет ownership handoff.

**Подготовка/откат:** Existing-flow preparation только под separate native GO в containment; close all duplicates, zero-work proof.

## N16 — Cross-SID NPFS authorized positive path

**Статус:** BLOCKED / NOT RUN.

**Наблюдение:** Kernel peer token/SID/image both directions + exact DACL readback + fixed read-only synthetic MCP nonce/receipt.

**Ожидание:** Correct C↔U peer работает с minimal query rights и Identification-only; no SeDebug/admin/C token leakage.

**Отрицательный контроль:** Wrong client/server SID и higher impersonation variant отвергнуты; no grant/token inheritance.

**Ложный PASS:** Same-user fixture выдаётся за cross-user pass; helper получает U rights; отсутствие receiver контроля.

**Подготовка/откат:** Отдельный launcher/ACL scope и dummy grants; MCP receipt read-only synthetic; stop job/pipe before cleanup. Generic egress oracle здесь НЕ применяется.

## N17 — Logical CONNECT target vs physical upstream

**Статус:** BLOCKED / NOT RUN.

**Наблюдение:** Native handler parsed authority/method/auth observer + physical B R:Q owner and owned logical destination receipt.

**Ожидание:** CONNECT other D/port, Upgrade/plain/UoT denied, даже если physical R:Q allowed.

**Отрицательный контроль:** Allow-all CONNECT parser mutant обязан FAIL; metadata JSON и HTTP200 сами по себе недостаточны.

**Ложный PASS:** Только transport socket проверен; логическая DNS/UDP операция зашифрована внутри allowed TCP.

**Подготовка/откат:** Lab dummy protocol endpoints после source compatibility review; no OpenAI/tunnel; quiesce owned processes.

## N18 — Rollback object ownership / concurrency

**Статус:** BLOCKED / NOT RUN.

**Наблюдение:** Trusted preimage + exact provider/filter/ACL/account ownership readback, independent drift and quiescence observer.

**Ожидание:** Concurrent replacement, foreign reference/key, preexisting account => STOP/KEEP DENY; не remove-by-name.

**Отрицательный контроль:** Forged UUID/ledger или account-name-only deleter должен дать FAIL на controlled foreign lab object.

**Ложный PASS:** Successful delete по неверному объекту маскирует damage; snapshot restore затирает чужой change.

**Подготовка/откат:** Только disposable lab owned and controlled decoy objects; no global import/reset; preserve evidence and escalate.

