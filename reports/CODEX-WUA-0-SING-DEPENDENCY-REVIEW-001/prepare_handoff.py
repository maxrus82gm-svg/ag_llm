"""One-shot offline evidence packaging. No fetch, subprocess, Go or native runtime.

This script records a BLOCKED handoff, not a dependency source-test result.
Existing project/source inputs are read-only; outputs are confined to this folder.
"""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
TASK = ROOT.name
PREV = REPO / 'reports/CODEX-WUA-0-SINGBOX-SOURCE-REVIEW-001'
AM = PREV / 'amendment_01'
SOURCE = Path('M:/WUA_SOURCE_REVIEW/sing-box/v1.13.4/source/sing-box-1.13.4')
VERSION = 'v0.8.3-0.20260315153529-ed51f65fbfde'
MODULE = 'github.com/sagernet/sing'
SUM = 'h1:RNQzlpnsXIuu1HGts/fIzJ1PR7RhrzaNlU52MDyiX1c='
NOW = datetime.now(timezone.utc).isoformat()
DOC = REPO / 'Документация'
CARD = DOC / '000_Задачи Codex.md'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def label(path):
    try:
        return path.relative_to(REPO).as_posix()
    except ValueError:
        return path.as_posix()


def save(name, value):
    path = ROOT / name
    assert path.resolve().is_relative_to(ROOT)
    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(value, ensure_ascii=False, indent=2) + '\n' if not isinstance(value, str) else value
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(content)


def record(path):
    data = path.read_bytes()
    return {'path': label(path), 'bytes': len(data), 'sha256': sha(data)}


if __name__ == '__main__':
    assert TASK == 'CODEX-WUA-0-SING-DEPENDENCY-REVIEW-001'
    if (ROOT / 'manifest.json').exists():
        raise SystemExit('Existing handoff retained; do not overwrite evidence or rerun blindly.')
    docs = [CARD, DOC / '08_Старт.md', DOC / '34_TACTICAL_CONTEXT.md',
            DOC / '19_Архитектура внешних AI-интеграций - Codex CLI и ChatGPT MCP.md',
            DOC / '01_Архитектура и текущее состояние.md',
            DOC / '18_Регламент сопровождения документации.md',
            DOC / '36_Единая архитектура тестирования.md',
            DOC / '36.1_Обязательный регламент тестирования для LLM.md',
            DOC / '36.2_Профиль тестирования Web Alarm Workspace.md']
    old_files = [PREV / 'report.md', AM / 'USER_GO.md',
                 AM / 'evidence/download_receipt.json', AM / 'evidence/source_tree_manifest.json',
                 AM / 'evidence/dependency_gap.json', AM / 'evidence/source_locations.json']
    code_files = [REPO / 'integrations/wua_chatgpt_mcp/singbox_source_review.py',
                  REPO / 'integrations/wua_chatgpt_mcp/tests/singbox_source_review_suite.py']
    source_names = ['go.mod', 'go.sum', 'protocol/http/inbound.go', 'option/options.go',
                    'cmd/sing-box/cmd_run.go', 'common/uot/router.go']
    protected = docs + old_files + code_files + [REPO / '.gitignore'] + [SOURCE / n for n in source_names]
    before = [record(p) for p in protected]
    save('evidence/protected_inputs_before.json', {'captured_at': NOW, 'files': before,
         'scope_limit': 'Selected files only; no .git or personal 001 read. No whole-host attestation.'})
    card = CARD.read_text(encoding='utf-8')
    task_text = card.split('# БЛОК 1 — ТЕКУЩАЯ ЗАДАЧА\n', 1)[1].split('# БЛОК 2 —', 1)[0]
    save('evidence/task_snapshot.md', task_text)
    launch = ('Уважаемый агент 007 (Codex)!\n'
              'Приступайте к задаче `CODEX-WUA-0-SING-DEPENDENCY-REVIEW-001` согласно утверждённому БЛОКУ 1 вашей персональной карточки.\n'
              'Сначала проверьте наличие отдельного USER GO на один source-only download. Если оно отсутствует — не выполняйте загрузку, зафиксируйте `DOWNLOAD_GO_REQUIRED`.\n'
              'Сохраняйте полный factual report, manifest и sanitized evidence. Не меняйте Windows, прокси, WFP, работающий sing-box, персональную карточку и Git/GitHub.\n'
              'Цель — завершить проверку HTTP CONNECT/auth/JSON по точной зависимости, сохранив все строгие security gates.\n')
    save('evidence/user_launch.txt', launch)
    save('evidence/authorization.json', {
        'task': TASK, 'status': 'DOWNLOAD_GO_REQUIRED',
        'separate_dependency_download_go_received': False,
        'basis': 'Direct user launch + B1 section 2 + prior exact USER_GO + prior receipt + current 34 handoff.',
        'search_limit': 'Available conversation and addressed task/authorization documents; not a global search of all user messages/files.',
        'prior_permission_scope': 'One sing-box v1.13.4 source ZIP only; consumed in prior TASK.',
        'prior_permission_ref': label(AM / 'USER_GO.md'),
        'prior_receipt_ref': label(AM / 'evidence/download_receipt.json'),
        'dependency_download_attempts': 0, 'network_probes': 0,
        'next_user_go_file_is': 'PROPOSAL ONLY / NOT AUTHORIZATION',
        'observation_limit': 'Agent action inventory, not system-wide network capture.'})
    rules = ['DOC-GIT-01@1', 'DOC-PARALLEL-01@1', 'DOC-LOCAL-REPORT-HANDOFF-01@1',
             'DOC-TASK-CLOSEOUT-OWNER-01@1', 'DOC-TEST-LIFECYCLE-01@1',
             'DOC-VERIFIER-BLOCK4-01@2', 'DOC-TASK-READ-SCOPE-01@1',
             'DOC-HISTORY-ACCESS-01@1', 'DOC-TASK-BLOCK1-01@1',
             'TEST-COLLAB-01@2', 'TEST-ENG-01@1', 'TEST-COV-01@1',
             'TEST-EXEC-01@1', 'TEST-QA-01@1', 'TEST-EVID-01@1', 'TEST-SCOPE-01@1']
    save('evidence/read_set.json', {'task': TASK, 'captured_at': NOW, 'rule_set_ref': rules,
         'files': before,
         'reading_scope': {'card': 'Rules + B1 + B4; no 001 archive',
          '08': 'Current start/roles/tests', '34': 'WEB_11 NEXT MCP CHAT and sing-box source review',
          '19': '7.1/7.2/7.4/7.6', '01': 'External AI integration and project limits',
          '18': 'Addressed definitions and applicable dependencies; no whole-document historical review',
          '36': 'Test areas/evidence/safety', '36.1': 'Applicable TEST rules',
          '36.2': 'Invariant matrix/isolated test scope', 'previous_task': 'Report, exact old GO, receipt, dependency gap, source locators/tree manifest'}})
    mod = (SOURCE / 'go.mod').read_text(encoding='utf-8')
    sums = (SOURCE / 'go.sum').read_text(encoding='utf-8')
    assert MODULE + ' ' + VERSION in mod
    assert MODULE + ' ' + VERSION + ' ' + SUM in sums
    old_tree = json.loads((AM / 'evidence/source_tree_manifest.json').read_text(encoding='utf-8'))
    old_pins = {p['path'].split('/', 1)[1]: p['sha256'] for p in old_tree['files']}
    comparisons = []
    for name in source_names:
        current = sha((SOURCE / name).read_bytes())
        assert current == old_pins[name], name
        comparisons.append({'path': name, 'sha256': current, 'matches_previous_tree_manifest': True})
    anchors = [
        ('go.mod', 'require', MODULE + ' ' + VERSION),
        ('go.sum', 'checksum', MODULE + ' ' + VERSION + ' ' + SUM),
        ('protocol/http/inbound.go', 'NewInbound', 'authenticator: auth.NewAuthenticator(options.Users)'),
        ('protocol/http/inbound.go', 'NewInbound', 'router:        uot.NewRouter(router, logger)'),
        ('protocol/http/inbound.go', 'Inbound.NewConnectionEx', 'err := http.HandleConnectionEx('),
        ('protocol/http/inbound.go', 'Inbound.newUserConnection', 'func (h *Inbound) newUserConnection('),
        ('protocol/http/inbound.go', 'Inbound.streamUserPacketConnection', 'func (h *Inbound) streamUserPacketConnection('),
        ('option/options.go', 'Options.UnmarshalJSONContext', 'decoder := json.NewDecoderContext('),
        ('option/options.go', 'Options.UnmarshalJSONContext', 'decoder.DisallowUnknownFields()'),
        ('cmd/sing-box/cmd_run.go', 'readConfigAndMerge', 'mergedMessage, err = badjson.MergeJSON(')]
    locators = []
    for name, function, needle in anchors:
        lines = (SOURCE / name).read_text(encoding='utf-8').splitlines()
        found = [(i + 1, line.strip()) for i, line in enumerate(lines) if needle in line]
        assert len(found) == 1, (name, needle)
        line, text = found[0]
        locators.append({'path': name, 'function': function, 'line': line, 'excerpt': text,
                         'file_sha256': old_pins[name]})
    vendor = SOURCE / 'vendor/github.com/sagernet/sing'
    source_top = sorted(p.name for p in Path('M:/WUA_SOURCE_REVIEW').iterdir() if p.is_dir())
    save('evidence/source_boundary.json', {'module_pin': MODULE + '@' + VERSION,
         'expected_zip_h1': SUM, 'source_root': SOURCE.as_posix(),
         'source_hash_comparisons': comparisons, 'locators': locators,
         'vendor_sing_directory_exists': vendor.exists(), 'known_source_root_top_directories': source_top,
         'exact_dependency_bundle_provided': False,
         'limit': 'Six parent-source hashes checked; no new sing archive/auth/parser/JSON bodies reviewed. No global cache search.'})
    save('source_provenance.json', {'task': TASK, 'captured_at': NOW,
         'module': MODULE, 'version': VERSION, 'expected_module_zip_h1': SUM,
         'expected_go_mod_h1': 'h1:ARkL0gM13/Iv5VCZmci/NuoOlePoIsW0m7BWfln/Hak=',
         'pin_origin': {'go_mod': 'go.mod:36', 'go_sum_zip': 'go.sum:239', 'go_sum_mod': 'go.sum:240'},
         'proposed_url': 'https://proxy.golang.org/' + MODULE + '/@v/' + VERSION + '.zip',
         'url_status': 'From approved B1; not contacted or independently checked online in this TASK',
         'download_status': 'NOT ATTEMPTED / DOWNLOAD_GO_REQUIRED',
         'archive_path': None, 'received_at': None, 'bytes': None, 'zip_sha256': None,
         'redirect_chain': None, 'actual_route': None, 'proxy_currently_verified': False,
         'archive_structure_crc_paths_case_links': 'NOT RUN / ARCHIVE NOT ACQUIRED',
         'module_zip_h1_computation': 'NOT RUN / ARCHIVE NOT ACQUIRED',
         'h1_verified': False, 'source_revision_verified': False,
         'parent_singbox_revision': 'd09182614c7778c1e0f51d990635c5d4249c437e',
         'parent_source_status': 'Previous independent bounded acceptance preserved; six local files compared, not a new acceptance',
         'external_source_tree_created': False, 'dependencies_installed': False})
    graph = ['# Source call graph — граница известного и отсутствующего\n',
             '**BLOCKED / DOWNLOAD_GO_REQUIRED.** Это карта делегирования в сохранённом sing-box, не реализация sing и не доказательство runtime.\n',
             '## Точные локальные locators\n', '| Файл | Функция | Строка | Наблюдаемый вызов |', '| --- | --- | --- | --- |']
    graph += [f"| `{x['path']}` | `{x['function']}` | {x['line']} | `{x['excerpt']}` |" for x in locators]
    graph += ['\nSHA файлов и exact source root — `evidence/source_boundary.json`. Все шесть соответствуют прежнему tree manifest; это не новый приёмочный verdict.\n',
              '## Не замкнутые ветви\n',
              'HTTP TCP/TLS inbound → внешний sing `http.HandleConnectionEx` (CONNECT parsing/auth UNKNOWN) → `adapter.NewUpstreamHandlerEx` callbacks → newUserConnection → uot router → sing-box route. Packet callback существует отдельно. Auth factory передаётся handler; enforcement до dial пока не установлен.\n',
              'JSON: sing-box `Options.UnmarshalJSONContext` → внешний sing JSON decoder (unknown/null/types/duplicate keys semantics UNKNOWN) → `checkOptions`. CLI `readConfigAndMerge` → внешний `badjson.MergeJSON` → options. Внутренние тела sing отсутствуют в разрешённом материале.\n',
              'После exact module archive/h1 нужно раскрыть методы, authority/port/IPv4/IPv6, early EOF, malformed input, auth reject-before-dial, alternative handlers, nested JSON/defaults/merge/reload и transitives. Go стандартная библиотека и прочие dependencies не считаются автоматически закрытыми.\n']
    save('source_callgraph.md', '\n'.join(graph))
    save('strict_route_gap_matrix.md', '''# Strict route gap matrix

TASK: CODEX-WUA-0-SING-DEPENDENCY-REVIEW-001 / BLOCKED / DOWNLOAD_GO_REQUIRED.
Статусы относятся к доказательствам, а не к применённой системной политике.

| Gate | Сохранённое основание | Чего не хватает / требование | Статус |
| --- | --- | --- | --- |
| Exact dependency | go.mod/go.sum pin, шесть parent file hashes | Отдельный download GO, origin/ZIP h1 | BLOCKED |
| HTTP CONNECT | Parent передаёт поток в sing handler | Authority/port/IPv6/malformed/methods/EOF и порядок dial | BLOCKED |
| Authentication | Parent создаёт и передаёт authenticator | Реальное reject-before-upstream, empty/wrong credentials, alternate handlers | BLOCKED |
| JSON/options | Parent вызывает DisallowUnknownFields и MergeJSON | Вложенные decoder/default/null/types/duplicate keys/merge/reload | BLOCKED |
| Default deny | Ранее принято: native default может быть DIRECT | Explicit final + deny unmatched/incomplete config; unknown defaults отвергать | CONDITIONAL / FULL POLICY UNVERIFIED |
| No fallback | Ранее просмотрен ограниченный normal dial failure path | Все protocol/group/detour/resolver/failover branches | UNVERIFIED |
| TCP-only logical traffic | Ранее принят UoT packet path | Отсечь packet/UDP/UoT отдельно от запрета UDP sockets | CONDITIONAL / ENFORCEMENT UNVERIFIED |
| DNS/IPv6 | Ранее выявлены local DNS/resolver paths | Исключить неутверждённые пути и все дополнительные socket families | UNVERIFIED |
| Background egress | Ранее выявлены conditional health/rules/NTP/etc | Exact disabled subset и полный closure; источник не равен active config | UNVERIFIED |
| One B-owned socket | Архитектурный целевой контракт | Фактический token/process/socket owner, SID и WFP containment | BLOCKED / NOT VERIFIED |
| Proxy route получения | Предыдущий localhost:10808 receipt | Текущая разрешённость и актуальность; сейчас не проверять сеть без GO | BLOCKED |
| Real fail-closed | Ни source, ни pure model не доказывают OS | Изолированная lab + отдельный GO + negative controls | NOT VERIFIED |
| Engine selection | engine.family=V2Ray сохранён | Отдельное решение пользователя после closure | PENDING USER |
| Hosted / ordinary Chat | Старые gates сохранены | Отдельные разрешения и реальные tool calls/receipt | HOLD / NOT VERIFIED |

Никаких изменений policy или ослабления gate. При последующем обнаружении дополнительных dependencies — адресный blocker без auto-fetch. Негативные сценарии текущей TASK NOT RUN, прежний 30/30 не переносится как их результат.
''')
    after = [record(p) for p in protected]
    assert before == after, 'Protected input changed during packaging'
    save('checks.json', {'task': TASK, 'status': 'BLOCKED / DOWNLOAD_GO_REQUIRED',
         'kind': 'Documentation/evidence checks, not source semantic or native tests',
         'command': '.\\.venv\\Scripts\\python.exe -B reports/CODEX-WUA-0-SING-DEPENDENCY-REVIEW-001/prepare_handoff.py',
         'check_completed_at': datetime.now(timezone.utc).isoformat(),
         'source_tests': {'collected': 0, 'pass': 0, 'fail': 0, 'error': 0, 'skip': 0,
                          'status': 'NOT RUN / BLOCKED', 'exit_code': None},
         'native_go_engine_network_tests': 'NOT RUN / FORBIDDEN',
         'planned_source_controls_not_run': ['source pin drift', 'module ZIP h1 mismatch', 'auth guard omission',
                                            'parser/route mutation', 'DIRECT admission', 'unknown default'],
         'go_mod_and_zip_go_sum_pin': 'MATCH', 'source_hashes_matched': len(comparisons),
         'source_hashes_compared': len(comparisons), 'locators_found': len(locators),
         'protected_inputs_unchanged': before == after, 'protected_input_count': len(before),
         'all_outputs_confined_to_task': True, 'personal_001_read_or_write': False,
         'agent_action_inventory': {'network_requests': 0, 'downloads': 0, 'git_operations': 0,
             'system_configuration_writes': 0, 'integration_source_writes': 0, 'test_file_writes': 0},
         'publication_ignore_check': 'Root .gitignore manually reviewed; reports/.gitignore absent. No Git/global-excludes claim.',
         'manifest_readback': 'Required after script exit; separate read-only command in final tool evidence.',
         'independent_review': 'PENDING'})
    files = sorted(p for p in ROOT.rglob('*') if p.is_file())
    assert all(p.suffix not in {'.pyc', '.zip', '.exe'} for p in files)
    save('manifest.json', {'task': TASK, 'status': 'BLOCKED / DOWNLOAD_GO_REQUIRED',
         'created_at': datetime.now(timezone.utc).isoformat(),
         'publication': 'LOCAL ONLY / NOT SYNCED', 'independent_verification': 'PENDING',
         'task_snapshot': 'evidence/task_snapshot.md', 'amendments_for_this_task': [],
         'scope': 'New TASK folder only; all referenced pre-existing inputs read-only',
         'path_base': 'manifest directory', 'excludes': ['manifest.json (self hash)'],
         'files': [{'path': p.relative_to(ROOT).as_posix(), 'bytes': p.stat().st_size,
                    'sha256': sha(p.read_bytes())} for p in files]})
    print(json.dumps({'status': 'BLOCKED / DOWNLOAD_GO_REQUIRED', 'manifest_entries': len(files),
                      'source_hash_matches': len(comparisons), 'protected_unchanged': len(before),
                      'source_tests_run': 0, 'network_calls': 0, 'output': label(ROOT)}, ensure_ascii=False))
