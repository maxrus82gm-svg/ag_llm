# Context — CLAUDE-WA-014 / RC-6 accepted ABORT before ACTIVE

- Состояние: **RESULT READY / AWAITING INDEPENDENT VERIFICATION**.
- Gate A — CONFIRMED на коде 166 через HTTP API: ABORT принят при READY → ACTIVE 200 (гейт F-C уже отказывал) → RC-6 и прямой RC-4 восстанавливали файлы; тот же класс — ROLLBACK до ACTIVE.
- Gate B — `microtask_gate.activation_refusal` + `ServerStateMachine._admit_active` (решение и CAS под TASK-lock); ручная граница #4A для ROLLBACK без «активируй».
- Проверки: 580 OK, skip 1 ×2; WA-014 11/11 (на 166 падают 9 из 11); фокусно 425/425; стресс 29/29; adversarial 54 раунда — 0 нарушений; живое storage не изменилось.
- Карточка: ротация выполнена (БЛОК 2 / 3 — WA-014 сверху; БЛОК 1 — ожидание).
- Следующий шаг: commit / push пользователем → независимая проверка ChatGPT.
