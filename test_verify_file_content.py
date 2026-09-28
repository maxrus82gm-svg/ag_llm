import hashlib
from pathlib import Path
import pytest
import server


def policy(root: Path, *, read=True, verify=True):
    value=server._normalize_permissions({'allow_read':read,'allow_write':False,'allow_delete':False,
      'allow_verify':verify,'read_scope':'.','write_scope':'.','delete_scope':'.','tool_limit':20,'auto_backup':False})
    return server._prepare_policy_for_workspace(root,value)


def call(root,path,kind,value,p=None):
    return server._agent_verify_file_content(root,path,kind,value,p or policy(root))


def test_verify_file_content_all_kinds_and_read_only(tmp_path: Path):
    f=tmp_path/'a.txt'; f.write_bytes('hello\nмир'.encode('utf-8')); before=f.read_bytes()
    assert call(tmp_path,'a.txt','exists','')['passed']
    assert call(tmp_path,'missing.txt','absent','')['passed']
    assert call(tmp_path,'a.txt','equals','hello\nмир')['passed']
    assert not call(tmp_path,'a.txt','equals','wrong')['passed']
    assert call(tmp_path,'a.txt','contains','мир')['passed']
    assert not call(tmp_path,'a.txt','contains','нет')['passed']
    digest=hashlib.sha256('hello\nмир'.encode()).hexdigest()
    assert call(tmp_path,'a.txt','sha256',digest)['passed']
    assert not call(tmp_path,'a.txt','sha256','0'*64)['passed']
    assert f.read_bytes()==before


def test_verify_validation_and_scope(tmp_path: Path):
    (tmp_path/'bad.bin').write_bytes(b'abc')
    with pytest.raises(ValueError): call(tmp_path,'x.txt','sha256','BAD')
    with pytest.raises(ValueError): call(tmp_path,'bad.bin','exists','')
    with pytest.raises(PermissionError): call(tmp_path,'x.txt','exists','',policy(tmp_path,verify=False))
    outside=tmp_path.parent/'outside.txt'; outside.write_text('x',encoding='utf-8')
    with pytest.raises((PermissionError, ValueError)): call(tmp_path,'../outside.txt','exists','')


