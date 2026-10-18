"""Bounded filename-only local source/media/VM search; never follow reparse points."""
from pathlib import Path
import os
import stat
import json
import hashlib
import shutil
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
SOURCE_NAME = 'tunnel-client-runtime-source-v0.0.16.tar.gz'
EXPECTED = '88953678325ffe650cc562bbd0b147e7e8e984b0527aa8b1647b02d6660ce9e0'
SKIP = {'.git', 'node_modules', '.venv', 'venv', 'site-packages', '__pycache__', '.cache'}

def sha_file(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()

def main():
    roots=[(ROOT/'reports',12),(Path(r'C:\Users\REX\Downloads'),5),
           (Path(r'C:\Users\REX\.codex\attachments'),5),
           (Path(r'C:\Users\REX\VirtualBox VMs'),5),
           (Path(r'C:\Users\REX\Documents\Virtual Machines'),5),
           (Path(r'C:\Users\Public\Documents\Hyper-V'),5),
           (Path(r'C:\ProgramData\Microsoft\Windows\Hyper-V'),3),
           (Path(r'C:\Users\REX\.VirtualBox'),2)]
    found=[];coverage=[]
    for base,depth in roots:
        item={'root':str(base),'max_depth':depth,'exists':base.exists(),'visited_dirs':0,'visited_files':0,'errors':[],'depth_pruned':0,'reparse_or_offline_skipped':0}
        def err(e):item['errors'].append({'path':str(e.filename),'errno':e.errno,'winerror':getattr(e,'winerror',None)})
        if base.exists():
            for current,dirs,files in os.walk(base,followlinks=False,onerror=err):
                cur=Path(current);item['visited_dirs']+=1
                keep=[]
                for name in dirs:
                    p=cur/name
                    if name.lower() in SKIP:continue
                    try:attrs=getattr(p.lstat(),'st_file_attributes',0)
                    except OSError as e:err(e);continue
                    if attrs & (0x400|0x1000):item['reparse_or_offline_skipped']+=1;continue
                    if len(p.relative_to(base).parts)>depth:item['depth_pruned']+=1;continue
                    keep.append(name)
                dirs[:]=keep
                for name in files:
                    item['visited_files']+=1;p=cur/name;lower=name.lower()
                    kind=('official_source' if name==SOURCE_NAME else 'source_candidate' if ('tunnel-client' in lower and lower.endswith(('.tar.gz','.zip','.tgz'))) else 'windows_media_candidate' if lower.endswith(('.iso','.wim','.esd')) else 'vm_config' if lower.endswith(('.vmx','.vbox','.vmcx','.wsb')) or name=='VirtualBox.xml' else None)
                    if kind is None:continue
                    try:
                        st=p.lstat();attrs=getattr(st,'st_file_attributes',0)
                        if attrs&(0x400|0x1000):item['reparse_or_offline_skipped']+=1;continue
                        entry={'path':str(p),'kind':kind,'bytes':st.st_size}
                        if kind in ('official_source','source_candidate'):
                            entry['sha256']=sha_file(p)
                            entry['expected_source_match']=name==SOURCE_NAME and st.st_size==239841 and entry['sha256']==EXPECTED
                        found.append(entry)
                    except OSError as e:err(e)
        coverage.append(item)
    exe=ROOT/'reports/CODEX-WUA-0-DESKTOP-MCP-E2E-001/secure_tunnel_preparation/tools/tunnel-client.exe'
    data={'task_id':OUT.name,'created_utc':datetime.now(timezone.utc).isoformat(),'roots':coverage,'found':found,
          'source_pack_matches':[x for x in found if x.get('expected_source_match')],
          'executable':{'path':str(exe),'exists':exe.exists(),'bytes':exe.stat().st_size if exe.exists() else None,'sha256':sha_file(exe) if exe.exists() else None,'executed':False},
          'path_lookup_only':{x:shutil.which(x) for x in ['VBoxManage','vmrun','vmware','qemu-system-x86_64','WindowsSandbox','hcsdiag','docker','podman']},
          'limitations':['No whole-disk search','Filename candidates are not trusted Windows media','No VM state change or product launch','Absent PATH entry alone does not prove product absent']}
    with (OUT/'local_file_inventory.json').open('x',encoding='utf-8') as f:json.dump(data,f,ensure_ascii=False,indent=2);f.write('\n')
    print(json.dumps(data,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
