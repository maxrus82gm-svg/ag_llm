# Integration plan — current installer remains blocked

1. WEB_11 независимо сверяет manifest/source/build/test evidence этого пакета и
   предыдущего toolkit. Публикует пользователь; агент Git/GitHub не использует.
2. Сохранить текущие `BackendImplemented=false`, `CanApply=false`, Install/Uninstall
   BLOCKED. **Не подменять** `UnavailableWfpBackend.cs` или DLL в опубликованном kit.
   Не добавлять JSON proof/Force/registry/env flag для снятия блокировки.
3. В следующей утверждённой TASK сделать отдельный lab-only executable adapter:
   new local identities/token/SID proof, trusted host/owner lineage, exact approved
   plan + freshness, private authenticated ledger, least privilege controller/
   object ACLs, full effective graph readback, lifecycle/startup/receiver guards.
   Native stage preview не решает эти обязанности. Нужны source changes и review,
   не простое включение скрытого option.
4. Native stage использует persistent provider/sublayer/filters, exact per-plan
   deterministic keys, transaction begin/add/commit, exact readback. При одном
   совпавшем/чужом объекте stop без overwrite; full existing-match требует trusted
   lineage и generation reconciliation. Новый plan с другим request digest может
   создать другие keys: требуется закрытый single-generation ownership catalog,
   чтобы не накапливать policies одного owner. Этого catalog сейчас нет.
5. Перед выдачей реального capability пройти `lab_gate.md`. File hashes/static
   predicates/SDK declarations не заменяют независимые OS/runtime результаты.
6. Rollback adapter отдельный: trusted ownership + quiescence, keep-deny on unknown,
   exact target deletion, no enumeration-wide purge, no dynamic-session protection
   disappearing on controller exit. Пока delete не реализован и не проверен.
7. Только после нового независимого PASS и нового USER GO изменять установщик
   отдельным согласованным release. Сначала disabled provisioning и post-install
   review; activation/native/network — отдельный этап. UI/primary account outside
   C/B scope; при поломке строгого profile показывать BLOCKED, не другой profile.

Минимальный следующий шаг — source/evidence review WEB_11. Никакой работающей
сети/Windows/V2Ray или MCP активации для этого review не требуется.
