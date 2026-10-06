from pathlib import Path
root=Path(r'M:\GitHub\ag_llm')
task=(root/'Alarm'/'ALARM_TASK_SESSION'/'TASK_CHATGPT-WA-008_RC6'/'task.md').read_text(encoding='utf-8')

p=root/'Документация'/'000_Задачи ChatGPT.md'
txt=p.read_text(encoding='utf-8')
s=txt.index('# БЛОК 1 — ТЕКУЩАЯ ЗАДАЧА')
e=txt.index('# БЛОК 2 — ПОСЛЕДНЯЯ ВЫПОЛНЕННАЯ ЗАДАЧА',s)
block='# БЛОК 1 — ТЕКУЩАЯ ЗАДАЧА\n---\n\nСтатус: ACTIVE / IN PROGRESS\nTASK: CHATGPT-WA-008 / RC-6\n\n'+task+'\n\n---\n'
p.write_text(txt[:s]+block+txt[e:],encoding='utf-8',newline='')

p=root/'Документация'/'000_Задачи для агента.md'
txt=p.read_text(encoding='utf-8')
s=txt.index('# БЛОК 1 — ТЕКУЩАЯ ЗАДАЧА')
e=txt.index('# БЛОК 2 — ПОСЛЕДНЯЯ ЗАВЕРШЁННАЯ ЗАДАЧА',s)
router='''# БЛОК 1 — ТЕКУЩАЯ ЗАДАЧА\n---\n\n**Статус:** ACTIVE / IN PROGRESS.\n**TASK:** `CHATGPT-WA-008 / RC-6 — Project-level Recovery Closure`.\n**Исполнитель:** ChatGPT / GPT-5.6 Sol (Remote Desktop Commander).\n**Персональная карточка:** [[000_Задачи ChatGPT]], БЛОК 1.\n**Task session:** `Alarm/ALARM_TASK_SESSION/TASK_CHATGPT-WA-008_RC6/`.\n**Baseline:** commit 156 `897d724b74843740ce2b936fcb6671106bb2dee0`.\n\n**Scope decision:** утверждённая Chat-постановка расширяет старый minimal read-only RC-6 до bounded Recovery Coordinator, но не пересекает WA4-E physical execution boundary.\n\n**NEXT SAFE ACTION:** выполнить только RC-6; WA4-E не начинать. Deferred TASK 151C в БЛОКЕ 3 не трогать.\n\n---\n'''
p.write_text(txt[:s]+router+txt[e:],encoding='utf-8',newline='')
print('TASK_CARDS_UPDATED')