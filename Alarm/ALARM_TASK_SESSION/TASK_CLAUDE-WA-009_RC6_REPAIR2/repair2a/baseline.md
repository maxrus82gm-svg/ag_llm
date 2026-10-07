# Baseline — CLAUDE-WA-009 / RC-6 REPAIR #2A (F-A CAS / lifecycle race closure)

Дата: 2026-10-07. Исполнитель: Claude Opus 5.5. Продолжение Repair #2 (та же TASK).

## Git

- local HEAD: `e551b919628bb0e1232d631f8d2637d9f6fa895c` (commit 161)
- GitHub main: `e551b919628bb0e1232d631f8d2637d9f6fa895c	refs/heads/main`
- **Repair #2 НЕ закоммичен**: база #2A = HEAD 161 + незакоммиченное рабочее дерево Repair #2.
- dirty tree на старте:
```text
M .obsidian/workspace.json
 M web_alarm/projection.py
 M web_alarm/recovery_coordinator.py
 M web_alarm/rollback_service.py
 M web_alarm/target_claim_store.py
 M "Документация/000_Задачи Claude.md"
?? Alarm/ALARM_TASK_SESSION/TASK_CLAUDE-WA-009_RC6_REPAIR2/
?? test_web_alarm_recovery_coordinator_repair2.py
```

## Рабочее дерево Repair #2 на старте #2A (SHA-256)

- `web_alarm/projection.py` — `8e5cf155a215201a1ef3c7bbc5fcdfd924e4cbdba2d99c7dab2f66274ff99c07`
- `web_alarm/recovery_coordinator.py` — `b6773a0a6d2950ddb18a39d52e6bffa4105931656f7620052612aaded822ff47`
- `web_alarm/rollback_service.py` — `c44461effc1e98d6510f2ca3228ed568263ffcf348c564deac711140fbd9a872`
- `web_alarm/target_claim_store.py` — `d069fc00ebfa246f18af4afcd9244f935fae281edd73f4f03149d9742d6db185`
- `test_web_alarm_recovery_coordinator_repair2.py` — `435602533bee3ad5da7e70257d54cd577e8569f461fac8cd235e68d1eeeb9c0e`

## Safety copies #2A (`safety_copies/`)

- `web_alarm/task_store.py` — `c17a42d66ec43392c97adfb4aaa15b10fbbaed4c06a48ed13093ee117c62b208`
- `web_alarm/state_machine.py` — `3c8190daed3779206b93394f8716bcfaf7fe824749306798f6e71606dbf0b5c5`
- `web_alarm/manifest_store.py` — `4df1392caf1a2f6e38a496b88d212a73a888fa31995de1a0eb9e75095652cd67`
- `web_alarm/recovery_coordinator.py` — `b6773a0a6d2950ddb18a39d52e6bffa4105931656f7620052612aaded822ff47`
- `web_alarm/server.py` — `6e4267ed14f83cba2310cc6f118dca01b9d4cb2cf278a3964fa726e7a824f6f4`
- `Документация/000_Задачи Claude.md` — `385a70115b31c7f9310cacfb8b1f534ab8b77ebc0af6f5b3bec205053807958f`

