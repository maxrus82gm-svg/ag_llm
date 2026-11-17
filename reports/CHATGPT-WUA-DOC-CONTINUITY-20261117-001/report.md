# Factual documentation continuity — CHATGPT-WUA-DOC-CONTINUITY-20261117-001

**USER GO:** 17.11.2026 (прямое поручение в чате ChatGPT; Codex TASK-socket не назначается). **SOURCE:** published main `70870380fc2828087f785357eeb70c0ac343da9f` (#641), GPT ancestor `3d9fdfe3241ee92731be2f61d9fdda4ed1f12991` (#637). **SCOPE:** только документация/корректность адресных итогов. Изменять runtime, Test/Standard, EVM storage/secret, БЛОК 1/1.1, live provider и git main запрещено. HISTORY ID этой прямой ChatGPT задачи не выдавался — не придумывать номер. Полный реестр №05 содержит эту TASK с прямым адресом.

## USER GO и исправления

Пользователь потребовал постоянный реестр **каждой задачи с любым исходом**. Ошибка, PARTIAL, BLOCKED, NOT RUN или отказ — не повод оставить TASK неучтённой. Один TASK ID привязывает результат, решение, текущий статус независимой проверки, FOLLOWUP и ссылку на successor. При исправлении OPEN статус меняется с доказательством, но исходная запись и историческая неудача не стираются. №001 по-прежнему только последние 10 для скорости старта; №05 — **полный реестр TASK, при этом подробности читаются строго адресно**.

Обновлены нормативные №18, №000, №08, DOC-COMMIT-01, DOC-ITERATION-CLOSEOUT-01; устранён процессный запрет фиксировать неуспешные итерации до технического PASS. Техническое VERIFIED и документы разведены — **не утверждаем**, что H40/H41 технически приняты. В №05 зафиксированы все **51** существующих `reports/*/task_record.json` с точными TASK/HISTORY ID и исходом record (HISTORICAL оставлен историческим); добавлена строка прямой документальной задачи и пять самостоятельных FOLLOWUP. Обновлён 10-строчный Codex №001 (H41–H32), события №06, координаторская №40 и прогресс №37.

**№34 был длиннее лимита №18:** 74 051 символ и устаревший CURRENT H39. Прежняя редакция сохранена побайтово в `preservation/34_TACTICAL_CONTEXT_before.md`; его blob SHA `da3596f2a57c13a0714a06ec739afd456a5b91a8` совпадает с исходным blob `main@70870380fc2828087f785357eeb70c0ac343da9f`. Новый №34 содержит текущую цель, H38–H41, точный статус БЛОК 1=WAITING/1.1=H41, наблюдения owner GUI, OPEN/NEXT, без переписывания прежних источников.

## Состояние H38–H41 и GUI — НЕ независимая продуктовая приёмка

H38: реальный транспорт, author OFFLINE; REAL 0. H39: один отдельный разрешённый GigaChat-2 ответ 15.11, первый BOUNDED LIVE PASS; остальные пять inference UNVERIFIED. H40: EVM ↔ LIVE/session/Turn, убраны 12 sends/30m/128-token trial, 24h grant от подключения сохранён, author Python 90/90, JS 122/122, S1 69/69, S2 73/73, network 0; TECH REVIEW PENDING. H41: per-model enabled, picker, internal pins + browser popup + PiP; author Python 53/53, JS 124/124, S1 69/69, **S2 FAIL 72/73** по policy import; Tcl/Tk combined abort; multi-monitor/topmost физически author NOT RUN, network 0. H41 author PARTIAL, independent acceptance NOT VERIFIED.

Owner GUI 17.11: STANDARD Send blocked, EVM «Проверить чат» не отправляет сообщение, два оконных механизма UX не устраивают; желаемый образец ещё не предоставлен. Вопрос Snipping Tool/двух мониторов возможно относится к ОС и не приписывается Web Alarm без доказательств. Искусственные пробные ограничения в STANDARD противоречат USER GO; реальные технические guards, error recovery и ответственность за платные вызовы остаются обязательными. Точная причина активного runtime HOLD неизвестна: не утверждать, что сработал 24h expiry.

## Контроль и не закрытые пункты

- По опубликованным отчётам и исходникам сверены H38–H41, S2 evidence, индексы/слоты, назначение документов по №18. Полный технический independent CI, проверка на Windows, реальный GigaChat API/paid, `task_history.py validate` **НЕ ЗАПУСКАЛИСЬ** этой документальной задачей.
- При последнем author H41 `task_history.py validate` уже красный от старого H36 source drift: `reports/CHATGPT-WEB30-H36-REVIEW-20261115/review.md`. Проблема отдельно OPEN.
- `tools/task_history.py render` сейчас формирует только последние 10 строк в №001/05 и не создаёт автоматически постоянную 51-строчную проекцию полного реестра. Записи сейчас внесены непосредственно в №05. Автоматизацию с тестами поручить отдельной задаче (`FOLLOWUP-WUA-H41-DOC-REGISTRY-AUTO-001`); до её решения координатор обновляет №05 при каждом изменении, не удаляя строки.
- Отсутствующая независимая проверка H40/H41, H41 S2 FAIL, Tcl/Tk abort, user GUI HOLD, 5 GigaChat REAL unverified, PiP/topmost физическое подтверждение — остаются OPEN. Новую Codex TASK не выдавали, БЛОК 1/1.1 не меняли.

**DOC RESULT:** DOCUMENTATION FACTS PREPARED / TECHNICAL ACCEPTANCE UNCHANGED. Всё подлежит одному атомарному коммиту в `GPT`, без обновления `main` и без объявления локального Windows проекта синхронизированным.
