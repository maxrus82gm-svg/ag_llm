"""Offline factual packaging only. Does not fetch, execute Go or close cards."""
from pathlib import Path
import ast, datetime, hashlib, json, sys

AM=Path(__file__).resolve().parent;TASK=AM.parent;REPO=TASK.parents[1]
PKG=REPO/'integrations/wua_chatgpt_mcp'
sys.path.insert(0,str(PKG))
import singbox_source_review as review

def guard(event,args):
    if event.startswith('socket.') or event in ('subprocess.Popen','os.system','os.posix_spawn'):
        raise PermissionError('OFFLINE_PACKAGING_ONLY')
sys.addaudithook(guard)

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def put(path,value):
    assert path.resolve().is_relative_to(TASK)
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def text(path,value):
    assert path.resolve().is_relative_to(TASK)
    path.write_text(value,encoding='utf-8')
def local(p):return p.relative_to(REPO).as_posix()

def main():
    initial=TASK/'initial_blocked';old=json.loads((initial/'manifest.json').read_bytes())
    assert digest(initial/'manifest.json')=='bd4d417d93c71faa5bf5fdbafd429129033b798eb69675589922307d989d9cc8'
    for row in old['files']:
        p=initial/row['path'];assert p.stat().st_size==row['bytes'] and digest(p)==row['sha256']
    prior=json.loads((initial/'evidence/protected_inputs_before.json').read_bytes())['files']
    authorized={'integrations/wua_chatgpt_mcp/singbox_source_review.py','integrations/wua_chatgpt_mcp/tests/singbox_source_review_suite.py'}
    preserved=[];changed=[]
    for row in prior:
        p=Path(row['path']);p=p if p.is_absolute() else REPO/p
        current=digest(p)
        if row['path'] in authorized:
            changed.append({'path':row['path'],'before_sha256':row['sha256'],'after_sha256':current})
            continue
        assert current==row['sha256'],row['path'];preserved.append(row['path'])
    baseline=json.loads((AM/'evidence/baseline_run.json').read_bytes())
    baseline_path=TASK/baseline['run']
    baseline_pins=json.loads((baseline_path/'local_source_pins.json').read_bytes())
    for name,pin in baseline_pins.items():
        if name not in authorized:
            assert digest(REPO/name)==pin
            if name not in preserved:preserved.append(name)
    module=json.loads((AM/'evidence/module_integrity.json').read_bytes())
    sing=Path(module['source_root']);archive=sing.parent/'sing-module-source.zip'
    fresh=review.module_zip_identity(archive)
    assert fresh['h1']==module['h1'] and fresh['files']==module['files']
    for row in module['files']:assert digest(sing/row['path'])==row['sha256']
    prior_am=REPO/'reports/CODEX-WUA-0-SINGBOX-SOURCE-REVIEW-001/amendment_01'
    parent=json.loads((prior_am/'evidence/source_tree_manifest.json').read_bytes())
    box=Path(parent['source_root'])
    for row in parent['files']:assert digest(box/row['path'].split('/',1)[1])==row['sha256']
    assert digest(Path(parent['archive_path']))==parent['archive_sha256']
    final_run=AM/'runs/source-20261025-014112-a2f64d92'
    results=json.loads((final_run/'result.json').read_bytes())
    assert results['collected']==results['passed']==51
    assert results['failed']==results['errors']==results['skipped']==results['exit_code']==0
    for name,pin in json.loads((final_run/'local_source_pins.json').read_bytes()).items():assert digest(REPO/name)==pin
    for name,pin in json.loads((final_run/'upstream_source_pins.json').read_bytes()).items():assert digest(box/name)==pin
    for name,pin in json.loads((final_run/'dependency_source_pins.json').read_bytes()).items():assert digest(sing/name)==pin
    for name in authorized:ast.parse((REPO/name).read_bytes())
    summary=json.loads((final_run/'dependency_review.json').read_bytes())
    locators=[dict(row,snapshot='sing') for row in summary['locators']]
    parent_names={'go.mod','go.sum',*(v[0] for v in review.LOCI.values())}
    parent_review=review.inspect({n:(box/n).read_bytes() for n in parent_names})
    locators.extend(dict(row,snapshot='sing-box') for row in parent_review['locators'])
    extras=[('sing','common/exceptions/error.go','New','return errors.New(F.ToString(message...))','error_new'),
      ('sing','common/json/internal/contextjson/decode.go','decodeState.literalStore','d.saveError(&UnmarshalTypeError{Value: "bool"','json_type_error'),
      ('sing','common/json/comment.go','NewCommentFilter','func NewCommentFilter(reader io.Reader) io.Reader {','comment_filter'),
      ('sing','common/buf/buffer_windows.go','Buffer.Iovec','import "golang.org/x/sys/windows"','platform_dependency'),
      ('sing-box','protocol/http/inbound.go','Inbound.NewConnectionEx','h.logger.ErrorContext(ctx, E.Cause(err, "process connection from ", metadata.Source))','parent_error_log'),
      ('sing-box','option/inbound.go','Inbound.UnmarshalJSONContext','err = badjson.UnmarshallExcludedContext(ctx, content, (*_Inbound)(h), options)','parent_nested'),
      ('sing-box','cmd/sing-box/cmd_run.go','readConfigAndMerge','mergedMessage, err = badjson.MergeJSON(','parent_merge'),
      ('sing-box','cmd/sing-box/cmd_run.go','run','if osSignal == syscall.SIGHUP {','parent_reload'),
      ('sing-box','adapter/upstream.go','myUpstreamHandlerWrapperEx.NewConnectionEx','w.connectionHandler(ctx, conn, myMetadata, onClose)','parent_callback')]
    for snapshot,name,function,anchor,key in extras:
        p=(sing if snapshot=='sing' else box)/name;content=p.read_text(encoding='utf-8');assert anchor in content
        locators.append({'id':key,'snapshot':snapshot,'path':name,'function':function,'line':content[:content.index(anchor)].count('\n')+1,'anchor':anchor,'file_sha256':digest(p)})
    put(AM/'evidence/source_locators.json',{'task':TASK.name,'source_roots':{'sing':sing.as_posix(),'sing-box':box.as_posix()},'locators':locators,'limit':'Exact source anchors, not a Go AST/semantic/native proof'})
    lines=['# Source call graph — bounded dependency review\n','Exact source roots/hashes: amendment_01/evidence/source_locators.json. Module ZIP h1 is verified; native execution is NOT RUN.\n',
      'HTTP: sing-box Inbound.NewConnectionEx → sing ReadRequest (linkname Go net/http.readRequest; stdlib gap) → enabled auth Verify/407 → SourceAddress → CONNECT/Upgrade/plain HTTP → upstream callback → parent newUserConnection → UoT router → sing-box route/dial. CONNECT 200 precedes callback; nil authenticator skips verification. Plain HTTP uses injected pipe/callback, not the separate http.Client nil-dialer default.\n',
      'JSON: CLI readConfigAt → UnmarshalExtendedContext(CommentFilter) → context Decoder.Decode → parent Options.UnmarshalJSONContext → DisallowUnknownFields/decode/checkOptions. Nested inbound registry → badjson.UnmarshallExcludedContext → context unknown-field decoder. Multi-file path sort → MergeJSON → recursive object/append merge → Options decode. Reload can recreate service; protected admission is not implemented by these source calls.\n',
      '| Snapshot / file | Function | Line | ID / anchor |','| --- | --- | --- | --- |']
    lines += [f"| {v['snapshot']}/{v['path']} | {v['function']} | {v['line']} | {v['id']}: `{v['anchor'].replace('|','&#124;')}` |" for v in locators]
    lines += ['\nBLOCKED: exact Go stdlib parser/URL/TLS/net and runtime/platform x/sys closure. No source→binary, SID/WFP, owner/traffic or ordinary Chat proof. No automatic additional downloads.\n']
    text(TASK/'source_callgraph.md','\n'.join(lines))
    text(TASK/'strict_route_gap_matrix.md','''# Strict route gap matrix — USER GO amendment 01

| Gate | Реальное source/evidence | Условие / открытый риск | Статус |
| --- | --- | --- | --- |
| Exact sing module | Version, raw ZIP SHA, Go h1, 322 hashes | Не binary reproducibility/полный upstream revision | SOURCE CONFIRMED (content pin) |
| Enabled auth before callbacks | Verify/407 до CONNECT/Upgrade/HTTP | Empty users даёт nil и no auth | SOURCE CONFIRMED / strict config CONDITIONAL |
| Secret-safe auth failure | Error включает password/header; parent logger | Нужна remediation/доказанная redaction до эксплуатации | BLOCKED for strict acceptance |
| Basic interoperability | URL-safe decode/error ignored vs client standard encode | Нет Go native oracle malformed/+slash inputs | SOURCE CONFIRMED / behavior TEST GAP |
| CONNECT success | 200 до route callback | Не считать его downstream/route/owner proof | SOURCE CONFIRMED |
| CONNECT-only admission | Есть plain HTTP/Upgrade | Отдельный строгий method/destination allowlist | NOT IMPLEMENTED / CONDITIONAL |
| Authority and port | Atoi ignored, uint16 cast/defaults | Exact Go parser grammar/range validation не закрыты | BLOCKED for full parser claim |
| Source identity | XFF source override | Не использовать forwarded IP как SID/authority | SOURCE CONFIRMED / OS UNVERIFIED |
| Default deny | Прежний accepted DIRECT default | Empty/missing/unmatched config должен отдельно отвергаться | SOURCE CONFIRMED unsafe capability / strict UNVERIFIED |
| No secondary/direct fallback | Normal injected callback есть; отдельный client nil→SystemDialer | Все callers/groups/resolvers исключить/доказать | UNVERIFIED |
| TCP-only logical operations | UoT packet routing существует | Отсечь UDP/UoT и magic destination, не только UDP socket | CONDITIONAL / enforcement UNVERIFIED |
| DNS/IPv6/background | Прежние optional DNS/health/rules/NTP paths | Exact permitted subset и полный closure | UNVERIFIED |
| JSON strictness | Unknown struct error есть; duplicates/null/default/merge permissive | Canonical single protected config, reject ambiguity before engine | CONDITIONAL / admission NOT IMPLEMENTED |
| Merge/reload protection | Multi-file sort/merge и recreate capability | Защитить inputs/CLI; Windows runtime не тестирован | UNVERIFIED |
| Stdlib/platform | Go linkname, x/sys Windows imports | Exact additional source input + отдельный GO при необходимости | BLOCKED |
| Existing proxy path for one fetch | Metadata + one audited loopback connect + TLS200 | Не remote V2Ray/B owner proof | BOUNDED OBSERVATION |
| C/B owner/WFP/fail-closed | Source не устанавливает OS guarantees | Lab isolation + отдельный USER GO + negative controls | NOT VERIFIED / BLOCKED |
| Engine selection | engine.family=V2Ray не менялся | Пользователь после независимого bounded review | PENDING USER |
| Hosted/ordinary Chat | can_apply=false, can_start_tunnel=false | Separate permissions and actual calls/receipt | HOLD / NOT VERIFIED |

51/51 Python source/intent controls не являются Go execution или native enforcement. Никакая policy не применялась. Показанные capabilities не доказывают их включение в рабочем profile.
''')
    download=json.loads((AM/'evidence/download_receipt.json').read_bytes())
    put(TASK/'source_provenance.json',{'task':TASK.name,'amendment':1,'user_go':local(AM/'USER_GO.md'),
        'module':module['module'],'version':module['version'],'url':download['url'],'received_at':download['received_at'],
        'archive_path':download['archive_path'],'source_root':sing.as_posix(),'bytes':download['bytes'],
        'raw_zip_sha256':download['sha256'],'expected_h1':review.SING_SUM,'computed_h1':fresh['h1'],
        'h1_verified':True,'archive_checks':'CRC/prefix/paths/collisions/links/resource bounds/source-only subset before extraction',
        'source_files':322,'uncompressed_bytes':756376,'download_attempts':1,'redirects':0,'actual_client_socket':download['connect_events'],
        'proxy_route_limit':'Existing loopback CONNECT path, not remote V2Ray/B-owned egress proof',
        'new_sumdb_lookup':False,'detached_signature_verified':False,'full_dependency_revision_verified':False,
        'source_binary_correspondence_verified':False,'complete_transitive_closure':False,'additional_downloads':0,
        'native_go_engine_network_tests':'NOT RUN','old_blocked_provenance':local(initial/'source_provenance.json')})
    put(TASK/'evidence/authorization.json',{'task':TASK.name,'separate_user_go_received':True,'scope':'One exact source-only sing ZIP via existing approved HTTP CONNECT only',
        'permission_file':local(AM/'USER_GO.md'),'permission_sha256':digest(AM/'USER_GO.md'),'consumed':True,
        'download_attempts':1,'additional_downloads_allowed':False,'native_go_network_tests_allowed':False,
        'old_blocked_phase':local(initial/'evidence/authorization.json'),'reviewer':'WEB_12'})
    put(TASK/'evidence/source_boundary.json',{'parent_source':box.as_posix(),'dependency_source':sing.as_posix(),
        'module_h1':fresh['h1'],'source_locators':local(AM/'evidence/source_locators.json'),
        'remaining_source_gaps':['Exact Go stdlib net/http.readRequest/net/url/TLS/net/base64','golang.org/x/sys v0.21.0 platform code'],
        'old_boundary':local(initial/'evidence/source_boundary.json')})
    reads=json.loads((initial/'evidence/read_set.json').read_bytes())
    reads['phase']='Initial addressed rules preserved; amendment reviewed exact sing source and user GO'
    reads['current_changed_source_pins']=changed;reads['amendment_source_locator_ref']=local(AM/'evidence/source_locators.json')
    put(TASK/'evidence/read_set.json',reads)
    attempts=[]
    for run in sorted((AM/'runs').iterdir()):
        if (run/'result.json').is_file():
            r=json.loads((run/'result.json').read_bytes())
            attempts.append({'path':local(run),'collected':r['collected'],'pass':r['passed'],'fail':r['failed'],'error':r['errors'],'skip':r['skipped'],'exit_code':r.get('exit_code',baseline['exit_code'])})
    put(AM/'evidence/test_quality_review.json',{'first_red_preserved':'source-20261025-013946-682a46e7','classification':'TEST FIXTURE / ZIP NAME REPRESENTATION',
        'observed':'ZipInfo writer normalized backslash on Windows; expected PATH code not reached, h1 rejected altered archive',
        'correction':'Inject raw local+central names, assert orig_filename trigger; reject normalization/NUL',
        'oracle_weakened':False,'later_engineering_hardening':'One capped byte snapshot for raw SHA/ZIP; oversize control added',
        'semantic_tests_not_run':['Go HTTP parser/EOF/malformed authority','Go Basic codec/auth interoperability','Go JSON duplicate/null/trailing/merge execution','Native Windows/WFP/B-owned sockets/remote route'],
        'go_text_mutation_is':'Lexical copied-source control only; not native Go execution'})
    put(AM/'evidence/final_integrity.json',{'task':TASK.name,'checked_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'initial_package_files_preserved':15,'initial_manifest_sha256':digest(initial/'manifest.json'),
        'read_only_selected_inputs_unchanged':len(preserved),'read_only_input_paths':preserved,
        'authorized_modified_source_tests':changed,'parent_source_files_unchanged':len(parent['files']),
        'parent_zip_sha_matches':True,'sing_source_files_unchanged':len(module['files']),
        'sing_h1_recomputed_with_final_validator':fresh['h1'],'final_test_source_pins_match':True,
        'card_all_blocks_unchanged':True,'personal_001_read_or_write':False,
        'limit':'Selected inputs + complete two supplied source trees; not whole workspace/OS/global isolation attestation'})
    put(TASK/'checks.json',{'task':TASK.name,'amendment':1,'status':'PARTIAL / AWAITING INDEPENDENT VERIFICATION WEB_12',
        'command':'.\\.venv\\Scripts\\python.exe -B integrations/wua_chatgpt_mcp/tests/singbox_source_review_suite.py --dependency',
        'attempts':attempts,'final':{'collected':51,'pass':51,'fail':0,'error':0,'skip':0,'exit_code':0},
        'components':{'existing_source':11,'existing_pure_contract':19,'new_archive_dependency':21},
        'network_downloads':1,'network_tests':0,'go_native_build_install_runs':0,'runtime_activation':False,
        'offline_socket_subprocess_guard':True,'independent_verification':'PENDING WEB_12',
        'test_gap_ref':local(AM/'evidence/test_quality_review.json'),'integrity_ref':local(AM/'evidence/final_integrity.json'),
        'packaging_note':'One apply_patch replace attempt was rejected for duplicate file operations; no mutation; new amendment report then copied to canonical root.',
        'publication':'LOCAL ONLY / NOT SYNCED','git_used':False})
    text(TASK/'report.md','> Полная копия amendment_01/report.md. Относительные пути в тексте относятся к amendment_01; source_callgraph.md и strict_route_gap_matrix.md находятся в корне TASK.\n\n'+(AM/'report.md').read_text(encoding='utf-8'))
    text(TASK/'NEXT_USER_GO.txt','USER GO received and consumed by one exact sing module ZIP. Do not repeat download.\nNEXT: independent WEB_12 review. Exact Go stdlib/x/sys inputs and any remediation/native action need separate scope/GO.\nOld proposal: initial_blocked/NEXT_USER_GO.txt. Current permission: amendment_01/USER_GO.md.\n')
    text(TASK/'DOC_IMPACT.md','''# DOC IMPACT / SHARED DOC DELTA — WEB_12

No shared documentation/card/001 edits by Codex. Task remains assigned in B1.

- №19 §7.6: exact sing ZIP/h1 and bounded HTTP/auth/JSON findings. Empty-users auth bypass-by-design, secret-in-error, codec mismatch, 200-before-route, HTTP/Upgrade alternatives, JSON duplicate/null/merge ambiguity; native guarantees remain unverified. Preserve prior WEB_11 acceptance.
- №34 current/NEXT: separate GO received/consumed, one download, final51, WEB_12 pending, stdlib/x/sys and logging/strict-admission/OS gates open. Do not automatically switch engine or authorize fetch/native.
- №06: factual amendment; baseline30, first RED49/50, intermediate50/50, final51/51 separately; Go/native/network tests NOT RUN. Initial BLOCKED package preserved. Independent verdict only after verifier's review.
- Card/001 closeout: coordinator workflow after publication/review or user terminal PARTIAL decision; executor makes no rotation.

LOCAL ONLY / NOT SYNCED. Root .gitignore has no matching new-task exclusion; reports/.gitignore absent. Git/global excludes not queried. User checks exact publication set. Third-party ZIP/tree remain outside repo; receipt/hashes/locators and data-only text mutants are included. Existing suite path reused, no duplicate root-level suite/framework.
''')
    entries=[]
    for p in sorted(TASK.rglob('*')):
        if not p.is_file() or p==TASK/'manifest.json':continue
        assert not p.is_symlink() and p.suffix.lower() not in ('.zip','.exe','.pyc'),local(p)
        entries.append({'path':local(p),'bytes':p.stat().st_size,'sha256':digest(p)})
    for name in sorted(authorized):
        p=REPO/name;entries.append({'path':name,'bytes':p.stat().st_size,'sha256':digest(p)})
    put(TASK/'manifest.json',{'task':TASK.name,'amendments':['USER GO source-only download; reviewer WEB_12'],
        'status':'PARTIAL / BOUNDED DEPENDENCY SOURCE REVIEW','publication':'LOCAL ONLY / NOT SYNCED',
        'independent_verification':'PENDING WEB_12','created_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'path_base':'repository root M:/GitHub/ag_llm','excludes':['reports/'+TASK.name+'/manifest.json (self hash)'],
        'task_snapshot':local(TASK/'evidence/task_snapshot.md'),'user_go':local(AM/'USER_GO.md'),
        'files':entries,'external_archives_trees':'Not in publication package; see source_provenance.json/module_integrity.json',
        'can_apply':False,'can_start_tunnel':False})
    print(json.dumps({'status':'PARTIAL','final_tests':51,'manifest_entries':len(entries),'locators':len(locators),
                      'read_only_selected_unchanged':len(preserved),'parent_source_unchanged':len(parent['files']),
                      'sing_source_unchanged':len(module['files']),'initial_package_preserved':15}))

if __name__=='__main__':main()
