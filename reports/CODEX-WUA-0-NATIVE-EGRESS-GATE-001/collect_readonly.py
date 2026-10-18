"""Read-only inventory/source evidence. No socket/HTTP/Git/native-client calls.

PowerShell is used solely for local CIM, service and command-presence queries.
No security API is invoked; SDK declarations are read as text, not executed.
"""
from pathlib import Path
import datetime
import hashlib
import json
import os
import subprocess
import sys

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
OLD = ROOT / 'reports/CODEX-WUA-0-DESKTOP-MCP-E2E-001'


def save(name, data):
    (OUT / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def fingerprint(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ps(script):
    result = subprocess.run(['powershell.exe', '-NoProfile', '-Command',
                             '[Console]::OutputEncoding=[Text.UTF8Encoding]::new(); ' + script],
                            capture_output=True, encoding='utf-8-sig', errors='replace', timeout=25)
    if result.returncode:
        raise RuntimeError('Read-only inventory failed; private raw output withheld')
    return json.loads(result.stdout or 'null')


def main():
    inventory = ps("$p=@(Get-CimInstance Win32_Process | Where-Object {$_.Name -match '^(v2rayN|sing-box)\\.exe$'} | Select-Object Name,ProcessId,ParentProcessId,ExecutablePath,CommandLine); "
                   "$l=@(Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue | Select-Object LocalAddress,LocalPort,OwningProcess); "
                   "$f=@(Get-CimInstance Win32_OptionalFeature -Filter \"Name='Containers' OR Name='Microsoft-Hyper-V' OR Name='VirtualMachinePlatform' OR Name='Containers-DisposableClientVM' OR Name='Microsoft-Windows-Subsystem-Linux'\" | Select-Object Name,InstallState); "
                   "$c=@('Get-VM','Get-VMNetworkAdapter','docker','podman','WindowsSandbox','hcsdiag','VBoxManage','vmrun') | ForEach-Object { @{name=$_;present=($null -ne (Get-Command $_ -ErrorAction SilentlyContinue))} }; "
                   "@{processes=$p;listeners=$l;features=$f;commands=@($c);bfe=(Get-Service BFE -ErrorAction SilentlyContinue | Select-Object Name,@{n='Status';e={$_.Status.ToString()}})} | ConvertTo-Json -Depth 6")
    processes = []
    for row in inventory['processes']:
        processes.append({'name':row['Name'],'pid':row['ProcessId'],'parent_pid':row['ParentProcessId'],
                          'executable_path_available':bool(row.get('ExecutablePath')),
                          'command_line_available':bool(row.get('CommandLine')),
                          'listeners':[{'address':x['LocalAddress'] if x['LocalAddress'] in ('127.0.0.1','::1') else 'nonloopback-redacted',
                                        'port':x['LocalPort']} for x in inventory['listeners'] if x['OwningProcess']==row['ProcessId']]})
    requested_ports={str(port):[{'address':x['LocalAddress'] if x['LocalAddress'] in ('127.0.0.1','::1') else 'nonloopback-redacted',
                                'owner_pid':x['OwningProcess'],
                                'owner':next((p['Name'] for p in inventory['processes'] if p['ProcessId']==x['OwningProcess']),'other-process-not-inspected')}
                               for x in inventory['listeners'] if x['LocalPort']==port] for port in (10808,10814)}
    save('inventory.sanitized.json', {'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
                                     'processes':processes,'feature_states':inventory['features'],
                                     'requested_port_owners':requested_ports,
                                     'command_presence':inventory['commands'],'bfe_service':inventory['bfe'],
                                     'sandbox_exe_present':Path(r'C:\Windows\System32\WindowsSandbox.exe').is_file(),
                                     'loaded_config_attested':False,'http_mixed_inbound_attested':False,
                                     'process_cmdlines_exported':False,'live_listener_probes':0,
                                     'isolation_verified':False,
                                     'limitation':'Bounded presence/CIM inventory; not exhaustive VM inventory or packet/process containment proof.'})
    sdk = Path(r'C:\Program Files (x86)\Windows Kits\10\Include\10.0.19041.0')
    selectors = {
        'um/fwpmu.h':['FWPM_LAYER_ALE_AUTH_CONNECT_V4','FWPM_LAYER_ALE_AUTH_CONNECT_V6',
                     'FWPM_CONDITION_ALE_APP_ID','FWPM_CONDITION_ALE_PACKAGE_ID','FWPM_CONDITION_ALE_USER_ID',
                     'FWPM_CONDITION_IP_REMOTE_ADDRESS','FWPM_CONDITION_IP_REMOTE_PORT','FWPM_CONDITION_IP_PROTOCOL',
                     'FwpmGetAppIdFromFileName0','FwpmTransactionBegin0','FwpmTransactionCommit0',
                     'FwpmTransactionAbort0','FwpmFilterAdd0','FwpmFilterDeleteByKey0','FwpmNetEventSubscribe0'],
        'shared/fwpmtypes.h':['FWPM_SESSION_FLAG_DYNAMIC','FWPM_FILTER_FLAG_PERSISTENT',
                              'FWPM_FILTER_FLAG_BOOTTIME','FWPM_FILTER_FLAG_PERMIT_IF_CALLOUT_UNREGISTERED',
                              'FWPM_NET_EVENT_TYPE_CLASSIFY_DROP'],
        'shared/fwptypes.h':['FWP_ACTION_BLOCK','FWP_ACTION_PERMIT']}
    evidence = []
    for relative, names in selectors.items():
        path = sdk / relative
        lines = path.read_text(encoding='utf-8-sig').splitlines()
        hits = []
        for name in names:
            matches = [i+1 for i,line in enumerate(lines) if name in line]
            hits.append({'symbol':name,'present':bool(matches),'lines':matches,
                         'kind':'SOURCE VERIFIED: local SDK declaration only, not runtime behavior'})
        evidence.append({'path':str(path),'sha256':fingerprint(path),'selectors':hits})
    stdlib = Path(sys.base_prefix) / 'Lib/subprocess.py'
    lines = stdlib.read_text(encoding='utf-8').splitlines()
    create = next(i+1 for i,line in enumerate(lines) if 'hp, ht, pid, tid = _winapi.CreateProcess(' in line)
    audit = max(i+1 for i,line in enumerate(lines[:create-1]) if 'sys.audit("subprocess.Popen"' in line)
    save('windows_source_evidence.json', {'sdk_version':'10.0.19041.0','sdk_headers':evidence,
                                         'wfp_security_apis_invoked':0,
                                         'session_process_id_warning':'FWPM_SESSION0.processId is engine session metadata; not evidence of a descendant filter condition.',
                                         'semantics_limit':'Header declarations do not prove filter precedence, loopback coverage, descendant inheritance, crash behavior or active installation.',
                                         'subprocess_python_source':{'path':str(stdlib),'sha256':fingerprint(stdlib),
                                             'popen_audit_line':audit,'native_create_process_line':create,
                                             'audit_precedes_create':audit < create}})
    asset = 'tunnel-client-runtime-source-v0.0.16.tar.gz'
    roots = [OLD, Path(r'C:\Users\REX\Downloads'), Path(r'C:\Users\REX\.codex\attachments')]
    hits = []
    for root in roots:
        for parent, dirs, files in os.walk(root, followlinks=False):
            dirs[:] = [d for d in dirs if d.lower() not in ('.git','.venv','venv','node_modules','site-packages','__pycache__') and not Path(parent,d).is_symlink()]
            if asset in files:
                p = Path(parent,asset)
                hits.append({'path':str(p),'sha256':fingerprint(p),'bytes':p.stat().st_size})
    save('source_pack_search.json', {'asset':asset,'expected_sha256':'88953678325ffe650cc562bbd0b147e7e8e984b0527aa8b1647b02d6660ce9e0',
                                    'roots':list(map(str,roots)),'matches':hits,
                                    'status':'SOURCE PACK BLOCKED' if not hits else 'FOUND; VERIFY BEFORE READING',
                                    'external_fetches':0})
    # Re-read current rule definitions and coordinator review, without full card dumps.
    index = json.loads((OLD/'http_socks_adapter_20261018/rules_read.json').read_text(encoding='utf-8'))
    for item in index['rules']:
        p = ROOT/item['source'];raw=p.read_bytes();text=raw.decode('utf-8-sig').splitlines()
        item['current_source_sha256']=hashlib.sha256(raw).hexdigest()
        item['current_definition']='\n'.join(text[item['line_start']-1:item['line_end']])
    index['user_amendment_precedence']='New TASK only reports/CODEX-WUA-0-NATIVE-EGRESS-GATE-001; no native execution or OS mutation; prior AM05-AM07 immutable. Card rotation text prepared in report until write-scope ambiguity resolved.'
    save('rules_read.json',index)
    excerpts=[]
    for name,last in [('34_TACTICAL_CONTEXT.md',9),('19_Архитектура внешних AI-интеграций - Codex CLI и ChatGPT MCP.md',23)]:
        p=ROOT/'Документация'/name;raw=p.read_bytes();excerpts.append({'path':name,'sha256':hashlib.sha256(raw).hexdigest(),
            'line_start':1,'line_end':last,'text':'\n'.join(raw.decode('utf-8-sig').splitlines()[:last]),
            'provenance':'Coordinator statements read locally, not a new agent Git/GitHub check'})
    save('coordinator_findings.json',{'sources':excerpts})
    print(json.dumps({'processes':processes,'source_pack_matches':len(hits),
                      'sdk_declarations':sum(len(x['selectors']) for x in evidence),
                      'popen_audit_before_native_create':audit<create,'native_client_runs':0}))


if __name__=='__main__':main()
