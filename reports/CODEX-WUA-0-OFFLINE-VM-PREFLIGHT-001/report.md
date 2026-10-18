# CODEX-WUA-0-OFFLINE-VM-PREFLIGHT-001 — factual report

Codex 007 · 2026-10-18 (Asia/Yekaterinburg) · для независимой проверки WEB_10.

**PARTIAL / RESULT READY / AWAITING INDEPENDENT VERIFICATION.**
Разрешённая offline-подготовка завершена; deployment/native gates заблокированы.
**LOCAL ONLY / PUBLICATION NOT VERIFIED.** Git/GitHub не использовались.

```text
OFFICIAL SOURCE PACK BLOCKED
LOCAL SOURCE AUDIT PARTIAL
VM PLATFORM INVENTORY PARTIAL
OFFLINE VM DESIGN PARTIAL
ISOLATION PREFLIGHT CONTRACT PARTIAL
OS/HYPERVISOR ISOLATION NOT VERIFIED
NATIVE CLIENT EXECUTION NOT STARTED
NATIVE CLIENT FAIL-CLOSED NOT VERIFIED
V2RAY REMOTE ROUTE NOT VERIFIED
HOSTED TUNNEL NOT STARTED
ORDINARY CHAT E2E NOT VERIFIED
```

## A. Подтверждённые результаты

1. Прочитаны утверждённый B1, маршрут 08→000→34→18→01, профиль 19/23/36/36.1/
   36.2/37, адресные 05/06 и предыдущие AM05–AM07/native-egress материалы.
   17 текущих rule sources совпали по hash с прошлым чтением; `rules_read.json`
   сохраняет selectors/hashes. Независимые findings WEB_10 прочитаны в 19/34:
   прежние 22/22 приняты как reference evidence с открытыми рисками, не OS proof.
   Git source pin `795e1fddf6741169f006caf8ba9430e4d22fca0f` — сообщение
   координатора из задания, не самостоятельно проверенный HEAD.
2. `local_file_inventory.json`: bounded search 8 roots не обнаружил точный
   runtime source archive, VM configs или Windows ISO/WIM/ESD. Глубины, 68
   отсечённых подкаталогов reports и exclusions сохранены. Это не whole-disk
   census. Exact source pack: 239841 B, SHA-256
   `88953678325ffe650cc562bbd0b147e7e8e984b0527aa8b1647b02d6660ce9e0`.
   Архив не скачивался; процедура безопасной передачи и точные audit selectors
   описаны в `source_pack_preflight.md`.
3. Fresh EXE hash:
   `4226bb74a72388147882881f29f79801b95e285d731a138071812e3aa6766571`,
   22,591,488 B. Равен EXE в cached Windows ZIP. ZIP SHA-256
   `edef7241b0c647fcb30f1a80ff376b6b25c51927960f257a3f01e21b17c2aba6`
   совпадает с cached release metadata и SHA256SUMS. `provenance.json` отделяет
   эту identity chain от неподтверждённого source→binary/build attestation.
   Native EXE не запускался даже для version/help. Полный новый Go audit не
   выполнен; 88 file path hints и findings WEB_10 — указатели на следующий audit.
4. `host_inventory.json`: Windows 10 Pro x64 10.0.19045; i5-12400F, firmware
   virtualization/VM monitor/SLAT=true; HypervisorPresent=false, RAM
   34,175,574,016 B. 12 выбранных optional features имеют InstallState=2;
   текстовая mapping в CIM не предоставлена. В 3 стандартных uninstall roots,
   filtered services/drivers, Hyper-V module metadata и 7 standard binary paths
   подходящей платформы не найдено; 8 PATH lookups также пусты. Ошибок saved
   queries/search — 0. Не утверждается отсутствие portable VM вне read_scope.
5. Сравнены полные Hyper-V/VirtualBox/VMware/QEMU VM, Sandbox и WSL/container.
   Предпочтён условный Hyper-V Gen2 backend **на уже подготовленном lab host**:
   zero NIC objects, никаких host relay/integration/data bridges во время subject,
   все fixtures внутри guest loopback. Точная версия backend/media/dependencies,
   native argv и attempt observer пока отсутствуют: дизайн PARTIAL.
6. Составлены I01–I12 isolation contract, 16 будущих native case contracts,
   staged/offline input и power-off output procedure, отдельные provisioning/
   execution USER gates, rollback по exact owned GUID/path/chain и manual
   adversarial review. Не выданы за работающую изоляцию.

## B. Проверки и пределы

`checks.json` — отдельная evidence matrix, не unit suite. Финальный счёт
записывает `bundle_validation.json`; native plan содержит **16 NOT RUN** cases.
Новых runtime/security unit tests — 0. Старые reference suites 19/19, 5/5,
36/36, 22/22 повторно не запускались. Actual native executions, VM creation/
start/config changes, сетевые probes/downloads и Windows/network mutations — **0**.

`inputs_before.json` фиксирует fresh baseline **151** protected file, включая
артефакты AM05–AM07 и native-egress, профильные документы, config и launcher. Own card
— единственное разрешённое исключение. `integrity.json` содержит конечную сверку
150 остальных файлов и авторизованное изменение карточки. Hash census не является
универсальным OS/network audit и не покрывает неизвестные файлы всей машины.
Final `manifest.json` перечисляет bytes/SHA-256 каждого package file, кроме себя;
`bundle_validation.json` и `seal_bundle.py` позволяют проверить полноту комплекта.

## C. Карточка и DOC IMPACT

Прямое USER GO сохранено целиком в `user_go_card_rotation.md`; оно разрешает
адресную запись own card сверх report-only scope. `card_before.md` — точная
резервная копия исходной карточки; `assignment.md` — полный frozen B1.
После сохранения этого отчёта выполняется проверяемая ротация: новая B2 содержит
всю постановку и USER GO, B3 — factual result, прежняя история сохраняется
дословно, B1 очищается только после staged readback B2/B3. Фактический результат
операции фиксируется в `card_rotation.json` и финальном дополнении ниже.

Минимальная правка правила относится только к исполненному объёму TASK с готовым
отчётом (включая PARTIAL/BLOCKED), не объявляет external gate закрытым. Общий
документ 18 не изменён: его базовый rotation порядок согласован, прежняя scope
неоднозначность и точное предложение WEB_10 — в `shared_doc_delta.md`.
Другие документы, Claude/LLM12/Web Alarm, Git и MCP connections не редактировались.

## D. Незакрытые условия и следующий USER GO

Минимум сейчас — пользовательская передача **точного source archive** в
`reports/CODEX-WUA-0-OFFLINE-VM-PREFLIGHT-001/source_input/`, без credentials,
и указание доступного уже подготовленного offline Windows lab host/VM/media.
Это не просьба включать Hyper-V или менять сеть текущей машины.

Предлагаемый **следующий отдельный scope**, пока не запущен: exact-source offline
audit + проверка trusted hypervisor/version/media/dependency package; затем
адресное разрешение подготовить owned stopped VM без NIC и провести independent
isolation preflight **без native subject**. В GO закрепить resource root/owner/
GUID acquisition, no host networking change и rollback. Только после I01–I12,
независимого review и нового USER GO на exact snapshot/argv/cases допустим
ограниченный native run. Если готового lab host нет, сначала отдельное решение
пользователя по платформе; automatic installation не предлагается как разрешённая.

V2Ray remote route и ordinary ChatGPT E2E — ещё более поздние отдельные gates.
Обычный ChatGPT по-прежнему должен реально вызвать ping, list_capabilities,
read_synthetic_context с разрешённой задачей и с other_task, а независимый
verifier — сверить серверный receipt. Эта TASK таких вызовов не выполняла.

Полный комплект сохранён внутри `reports/CODEX-WUA-0-OFFLINE-VM-PREFLIGHT-001/`.
Публикацию и передачу WEB_10 выполняет пользователь; агент ничего не отправлял
в другой чат и не объявлял независимую приёмку.

## E. Финальная сверка и ротация

**CARD ROTATION VERIFIED (local).** Новые БЛОКИ 2–3 сохранены и перечитаны
перед очисткой БЛОКА 1. Полная исходная постановка и USER GO сохранены;
405,816 B прежней истории сохранены дословно. БЛОК 1 теперь содержит
`ОЖИДАНИЕ НОВОЙ ЗАДАЧИ`. Одно правило собственной карточки уточнено.
До изменения SHA-256 карточки:
`fd1668b84b41aaabcc1e790db158b95280d2eec5b444d578ac54ed83af2baf0b`;
после:
`6df2f7e5f968840ccc71ee3dddec30bb7c0f031ffc9e7e2e630a627248f5e71f`.
Откат только при совпадении текущего hash с recorded final, из card_before.md;
при поздних изменениях — reconciliation. История не удалялась.

Итог checks: **25 строк — 14 PASS / 6 BLOCKED / 5 NOT RUN**. Это evidence rows,
не 14 native tests. Native plan — **16/16 NOT RUN**, фактических запусков 0.
**150/150** защищённых файлов вне own card сохранили исходные hashes;
151-й файл — только разрешённая карточка. Final manifest/validator подтверждают
целостность package, но не OS/hypervisor/client behavior и не independent PASS.
Root `.gitignore` прочитан как обычный файл; среди его правил и двух проверенных
вложенных путей нет исключения новой report folder. Git/global excludes не
опрашивались; публикация пользователем ещё не проверена.
