"""Local scoped evidence capture, no Git and no host changes."""
import datetime, hashlib, json
from pathlib import Path

TASK = Path(__file__).resolve().parent
ROOT = TASK.parents[1]
DOC = ROOT / 'Документация'

def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')

if __name__ == '__main__':
    evidence = TASK/'evidence'
    evidence.mkdir(exist_ok=True)
    card = DOC/'000_Задачи Codex.md'
    text = card.read_text(encoding='utf-8-sig')
    snapshot = text.split('# БЛОК 1 — ТЕКУЩАЯ ЗАДАЧА',1)[1].split('# БЛОК 2 —',1)[0]
    (evidence/'task_snapshot.md').write_text('# БЛОК 1 — ТЕКУЩАЯ ЗАДАЧА'+snapshot,encoding='utf-8')
    dump(evidence/'sync_gate.json', {'classification':'USER_DECLARED','question':'Local copy synchronized with approved main for current TASK?', 'answer':'Да, локальная копия синхронизирована','independent_git_revision_check':False,'git_operations':0,'recorded_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()})
    docs = ['000_Задачи Codex.md','08_Старт.md','18_Регламент сопровождения документации.md','19_Архитектура внешних AI-интеграций - Codex CLI и ChatGPT MCP.md','34_TACTICAL_CONTEXT.md','36.1_Обязательный регламент тестирования для LLM.md','36.2_Профиль тестирования Web Alarm Workspace.md']
    package = ROOT/'integrations/wua_chatgpt_mcp'
    paths = [DOC/n for n in docs] + [package/n for n in ['broker.py','security_contract.py','common.py','broker_fixture.py','route_simulation.py','configs/broker.v1.schema.json','npfs/Shared.cs','npfs/Gateway.cs','npfs/Relay.cs','npfs/gateway_worker.py','tests/admission_suite.py','tests/broker_suite.py']]
    paths += [ROOT/'reports/CODEX-WUA-0-STRICT-ADMISSION-CONTRACT-001'/n for n in ['report.md','admission_matrix.md','manifest.json']]
    paths += [ROOT/'reports/CODEX-WUA-0-WFP-OFFLINE-BACKEND-001'/n for n in ['contracts/backend-contract.json','source/Core.cs']]
    dump(evidence/'protected_inputs_before.json', {'files':[{'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in paths], 'scope':'Addressed inputs only; not a workspace-wide filesystem monitor.'})
