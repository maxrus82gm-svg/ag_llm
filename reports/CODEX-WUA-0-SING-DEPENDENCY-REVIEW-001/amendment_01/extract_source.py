"""Offline checksum/archive checks before extraction; no source execution."""
from pathlib import Path
import datetime, hashlib, json, sys, zipfile

OUT=Path(__file__).resolve().parent
REPO=OUT.parents[2]
sys.path.insert(0,str(REPO/'integrations/wua_chatgpt_mcp'))
import singbox_source_review as review

def guard(event,args):
    if event.startswith('socket.') or event in ('subprocess.Popen','os.system','os.posix_spawn'):
        raise PermissionError('OFFLINE_ONLY')
sys.addaudithook(guard)

def check_path(path):
    for p in (path,*path.parents):
        if p.exists():
            assert not p.is_symlink() and not getattr(p.lstat(),'st_file_attributes',0)&0x400,'REPARSE_PATH'

def main():
    receipt_path=OUT/'evidence/module_integrity.json'
    assert not receipt_path.exists(),'EXISTING_INTEGRITY_RECEIPT'
    download=json.loads((OUT/'evidence/download_receipt.json').read_bytes())
    archive=Path(download['archive_path']);base=archive.parent;source=base/'source'
    receipt={'task':'CODEX-WUA-0-SING-DEPENDENCY-REVIEW-001','status':'BLOCKED','started_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    try:
        assert download['http_status']==200 and not download['redirect_followed']
        assert hashlib.sha256(archive.read_bytes()).hexdigest()==download['sha256'],'DOWNLOAD_FILE_DRIFT'
        identity=review.module_zip_identity(archive)
        receipt.update(identity)
        check_path(base);assert not source.exists(),'NEW_SOURCE_DIRECTORY_REQUIRED'
        # Every name, body CRC, resource bound and expected h1 was checked above.
        source.mkdir()
        prefix=identity['module']+'@'+identity['version']+'/'
        with zipfile.ZipFile(archive) as z:
            for row in identity['files']:
                target=source/row['path']
                assert target.resolve().is_relative_to(source.resolve()),'EXTRACT_SCOPE'
                target.parent.mkdir(parents=True,exist_ok=True);check_path(target.parent)
                body=z.read(prefix+row['path'])
                assert hashlib.sha256(body).hexdigest()==row['sha256']
                with target.open('xb') as stream:stream.write(body)
        assert all(hashlib.sha256((source/f['path']).read_bytes()).hexdigest()==f['sha256'] for f in identity['files'])
        receipt.update(status='MODULE ZIP H1 VERIFIED / SOURCE EXTRACTED',source_root=source.as_posix(),
                       extracted_files_match=True,finished_at=datetime.datetime.now(datetime.timezone.utc).isoformat())
    except BaseException as exc:
        receipt['reason']=str(exc) if isinstance(exc,(AssertionError,RuntimeError)) else type(exc).__name__
    with receipt_path.open('x',encoding='utf-8') as f:json.dump(receipt,f,indent=2)
    print(json.dumps({k:v for k,v in receipt.items() if k!='files'}))
    return 0 if receipt['status'].startswith('MODULE ZIP H1 VERIFIED') else 20

if __name__=='__main__':sys.exit(main())
