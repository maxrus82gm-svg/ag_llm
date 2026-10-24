"""Single-use TASK-authorized rotation; never reads pre-existing archive bytes.

Expected original card and archive metadata are pinned in initial_state.json.
Exclusive Windows handles reject competing writers; all old archive data stays
outside the requested access rights. Do not reuse for another TASK.
"""
import ctypes as c
from ctypes import wintypes as w
import hashlib
import json
from pathlib import Path
import sys
sys.dont_write_bytecode = True
OUT = Path(__file__).resolve().parent
REPO = OUT.parents[1]
TASK = 'CODEX-WUA-0-SINGBOX-SOURCE-REVIEW-001'
CARD = REPO / 'Документация/000_Задачи Codex.md'
ARCHIVE = REPO / 'Документация/001_История выполненных задач Codex.md'
K = c.WinDLL('kernel32', use_last_error=True)
K.CreateFileW.argtypes=[w.LPCWSTR,w.DWORD,w.DWORD,c.c_void_p,w.DWORD,w.DWORD,w.HANDLE]
K.CreateFileW.restype=w.HANDLE
K.CloseHandle.argtypes=[w.HANDLE]
K.GetFileSizeEx.argtypes=[w.HANDLE,c.POINTER(c.c_longlong)]
K.ReadFile.argtypes=[w.HANDLE,c.c_void_p,w.DWORD,c.POINTER(w.DWORD),c.c_void_p]
K.WriteFile.argtypes=K.ReadFile.argtypes
K.SetFilePointerEx.argtypes=[w.HANDLE,c.c_longlong,c.POINTER(c.c_longlong),w.DWORD]
K.SetEndOfFile.argtypes=[w.HANDLE]
K.FlushFileBuffers.argtypes=[w.HANDLE]

class Info(c.Structure):
    _fields_=[('attrs',w.DWORD),('created',w.FILETIME),('accessed',w.FILETIME),('written',w.FILETIME),('volume',w.DWORD),('size_high',w.DWORD),('size_low',w.DWORD),('links',w.DWORD),('index_high',w.DWORD),('index_low',w.DWORD)]
K.GetFileInformationByHandle.argtypes=[w.HANDLE,c.POINTER(Info)]

def check(ok,code):
    if not ok:raise RuntimeError(code)
def sha(b):return hashlib.sha256(b).hexdigest()
def open_exclusive(path,access):
    h=K.CreateFileW(str(path),access,0,None,3,0,None)
    check(h!=w.HANDLE(-1).value,'EXCLUSIVE_OPEN_BLOCKED_'+str(c.get_last_error()))
    return h
def info(h):
    i=Info();check(K.GetFileInformationByHandle(h,c.byref(i)),'FILE_METADATA')
    return {'size':(i.size_high<<32)|i.size_low,'mtime_ns':(((i.written.dwHighDateTime<<32)|i.written.dwLowDateTime)-116444736000000000)*100,'inode':(i.index_high<<32)|i.index_low}
def stat(path):
    s=path.stat();return {'size':s.st_size,'mtime_ns':s.st_mtime_ns,'inode':s.st_ino}
def write(h,b):
    count=w.DWORD();check(K.WriteFile(h,b,len(b),c.byref(count),None) and count.value==len(b),'WRITE_INCOMPLETE');check(K.FlushFileBuffers(h),'FLUSH')
def replace_locked(h,b):
    check(K.SetFilePointerEx(h,0,None,0),'CARD_SEEK');write(h,b);check(K.SetEndOfFile(h),'CARD_TRUNCATE');check(K.FlushFileBuffers(h),'CARD_FLUSH')
def read_locked_card(h):
    size=c.c_longlong();check(K.GetFileSizeEx(h,c.byref(size)) and size.value<200000,'CARD_SIZE');check(K.SetFilePointerEx(h,0,None,0),'CARD_SEEK');b=c.create_string_buffer(size.value);n=w.DWORD();check(K.ReadFile(h,b,len(b),c.byref(n),None) and n.value==size.value,'CARD_READ');return b.raw

def main():
    state=json.loads((OUT/'evidence/initial_state.json').read_text(encoding='utf-8'))
    facts=json.loads((OUT/'test_results.json').read_text(encoding='utf-8'))
    suite=facts['existing_pure_validator_regression']
    check(facts['status']=='BLOCKED / SOURCE_BUNDLE_REQUIRED','BLOCKED_REPORT_REQUIRED')
    check(suite['collected']==suite['passed']==19 and suite['failed']==suite['errors']==suite['skipped']==0,'FINAL_RESULT_REQUIRED')
    check(suite['source_pins_current'] and facts['source_specific_tests']['collected']==facts['source_route_mutations']['executed']==0,'REGRESSION_REQUIRED')
    check(not (OUT/'source/sing-box-v1.13.4.tar.gz').exists(),'SOURCE_INPUT_NOW_AVAILABLE_REASSESS_BLOCKER')
    check(facts['can_apply'] is False and facts['can_start_tunnel'] is False,'ACTIVATION_MUST_REMAIN_BLOCKED')
    check((OUT/'report.md').is_file() and (OUT/'manifest.json').is_file(),'REPORT_MANIFEST_REQUIRED')
    receipt={'task':TASK,'status':'CARD ROTATION BLOCKED','archive_old_bytes_read':0,'archive_previous_bytes_written':0,'method':'exclusive append-only archive handle; bounded readback at new offset; exclusive card write with in-memory rollback'}
    hcard=None;harchive=None
    try:
        check(stat(ARCHIVE)==state['archive_metadata_only'],'ARCHIVE_METADATA_DRIFT')
        hcard=open_exclusive(CARD,0xc0000000)
        original=read_locked_card(hcard);check(sha(original)==state['card_sha256'],'CARD_DRIFT')
        marker=lambda n:('# БЛОК '+str(n)+' —').encode('utf-8')
        pos={n:original.index(marker(n)) for n in range(1,5)}
        block4=original[pos[4]:];check(sha(block4)==state['block4_sha256'],'BLOCK4_DRIFT')
        old2=original[pos[2]:pos[3]].decode('utf-8');old3=original[pos[3]:pos[4]].decode('utf-8')
        rows2=[s for s in old2.splitlines() if s.startswith('- **')];rows3=[s for s in old3.splitlines() if s.startswith('- **')]
        check(len(rows2)==len(rows3)==5,'CARD_WINDOW_SHAPE')
        factual=('BLOCKED / SOURCE_BUNDLE_REQUIRED; LOCAL ONLY; AWAITING WEB_11 REVIEW OF BLOCKER REPORT. '
                 '19/19 existing pure broker validator regression; source-specific tests and route mutations 0 NOT RUN. '
                 'Official sing-box v1.13.4 tag -> d09182614c7778c1e0f51d990635c5d4249c437e confirmed by coordinator statement, not rechecked via Git by Codex. No local archive/path/chain-of-custody supplied; no sing-box source bytes read. '
                 'HTTP CONNECT/strict route source UNVERIFIED; hidden egress review BLOCKED; engine selection pending user; real B egress/WFP/ordinary Chat NOT VERIFIED; hosted tunnel HOLD; can_apply=false; can_start_tunnel=false. '
                 'DOC IMPACT: shared documentation delta handed to coordinator; common docs unchanged.')
        assignment_bytes=(OUT/'assignment.md').read_bytes()
        check(assignment_bytes==original[pos[1]:pos[2]],'ASSIGNMENT_CAPTURE_DRIFT')
        assignment=assignment_bytes.decode('utf-8')
        record=('\r\n\r\n---\r\n\r\n# 2026-10-24 — '+TASK+'\r\n\r\n'
                '**Initial status:** assigned source-only TASK; prior engine snapshot PARTIAL / BOUNDED STATIC-SNAPSHOT ACCEPTED per coordinator B1; local source bundle absent; native F2 and hosted tunnel remain BLOCKED/HOLD.\r\n\r\n'
                '**Полная исходная постановка (immutable assignment snapshot):**\r\n\r\n'+assignment+
                '\r\n\r\n**AMENDMENT:** no separate amendments received for this TASK.\r\n\r\n'
                '**Factual result:** '+factual+'\r\n\r\n'
                '**Report:** `reports/'+TASK+'/report.md`; **manifest:** `reports/'+TASK+'/manifest.json`; '
                '**checks:** `reports/'+TASK+'/test_results.json`; exact regression selectors/result locator included; next_user_decision.md requests one official local source archive v1.13.4 with package SHA256/transfer provenance, without engine switch.\r\n'
                '**Independent acceptance:** NOT VERIFIED; БЛОК 4 unchanged; next review WEB_11.\r\n').encode('utf-8')
        harchive=open_exclusive(ARCHIVE,0x84) # FILE_APPEND_DATA + FILE_READ_ATTRIBUTES; NO FILE_READ_DATA
        check(info(harchive)==state['archive_metadata_only'],'ARCHIVE_HANDLE_DRIFT')
        write(harchive,record);newmeta=info(harchive);check(newmeta['size']==state['archive_metadata_only']['size']+len(record),'ARCHIVE_APPEND_SIZE')
        K.CloseHandle(harchive);harchive=None
        offset=state['archive_metadata_only']['size']
        harchive=open_exclusive(ARCHIVE,0x81) # read-data + attributes; held until card save, no archive write rights
        check(info(harchive)==newmeta,'ARCHIVE_REOPEN_DRIFT')
        check(K.SetFilePointerEx(harchive,offset,None,0),'NEW_ENTRY_SEEK')
        buffer=c.create_string_buffer(len(record));count=w.DWORD()
        check(K.ReadFile(harchive,buffer,len(buffer),c.byref(count),None) and count.value==len(record),'NEW_ENTRY_READ')
        added=buffer.raw # exactly the permitted new byte range
        check(added==record and info(harchive)==newmeta,'ARCHIVE_READBACK_OR_PARALLEL_CHANGE')
        receipt.update(archive_offset=offset,archive_appended_bytes=len(record),archive_appended_sha256=sha(added),archive_new_metadata=newmeta,archive_new_entry_readback=True)
        check(read_locked_card(hcard)==original,'CARD_LOCKED_DRIFT')
        check(info(harchive)==newmeta,'ARCHIVE_PARALLEL_WRITER')
        newline='\r\n' if b'\r\n' in original else '\n'
        b1='# БЛОК 1 — ТЕКУЩАЯ ЗАДАЧА\n\nОЖИДАНИЕ НОВОЙ ЗАДАЧИ\n\n---\n\n'
        b2='# БЛОК 2 — ПЯТЬ ПОСЛЕДНИХ ЗАДАЧ (КОМПАКТНО)\n\nСкользящее окно до 5 выполненных TASK; полный архив — [[001_История выполненных задач Codex]]. Независимый статус не выдумывать.\n\n'
        b2+='\n'.join(['- **2026-10-24 / '+TASK+'** — source-only review не начат: локальный source archive/path не предоставлен. Статус: BLOCKED / SOURCE_BUNDLE_REQUIRED; blocker report ready; independent NOT VERIFIED.']+rows2[:4])+'\n\n---\n\n'
        b3='# БЛОК 3 — КРАТКИЕ ФАКТИЧЕСКИЕ ИТОГИ\n\n'
        b3+='\n'.join(['- **'+TASK+'** — BLOCKED / SOURCE_BUNDLE_REQUIRED: официальный v1.13.4→d091826… подтверждён WEB_11 по B1, но local source bytes не предоставлены. 19/19 pure validator regression; source tests/mutations0 NOT RUN. Engine/Windows/network unchanged; tunnel HOLD. Полный отчёт: `reports/'+TASK+'/report.md`; полная TASK/factual result — новая append-only запись 001 (locator в evidence/card_rotation.json).']+rows3[:4])+'\n\n---\n\n'
        result=original[:pos[1]]+(b1+b2+b3).replace('\n',newline).encode('utf-8')+block4
        check(result[result.index(marker(4)):]==block4,'BLOCK4_BUILD')
        try:
            replace_locked(hcard,result)
            check(read_locked_card(hcard)==result,'CARD_READBACK')
        except BaseException:
            replace_locked(hcard,original);check(read_locked_card(hcard)==original,'CARD_ROLLBACK_FAILED');raise
        receipt.update(status='CARD ROTATION VERIFIED',card_before_sha256=sha(original),card_after_sha256=sha(result),block4_before_sha256=sha(block4),block4_after_sha256=sha(result[result.index(marker(4)):]),block1='ОЖИДАНИЕ НОВОЙ ЗАДАЧИ',block2_rows=5,block3_rows=5,evicted_card_summaries={'block2':rows2[4:],'block3':rows3[4:]})
    except BaseException as exc:
        receipt['reason']=str(exc)
        raise
    finally:
        if harchive is not None:K.CloseHandle(harchive)
        if hcard is not None:K.CloseHandle(hcard)
        (OUT/'evidence/card_rotation.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'status':receipt['status'],'archive_appended_bytes':receipt['archive_appended_bytes'],'archive_old_bytes_read':0,'block4_unchanged':receipt['block4_before_sha256']==receipt['block4_after_sha256']},ensure_ascii=False))

if __name__=='__main__':main()
