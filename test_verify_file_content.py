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
    for result in (
        call(tmp_path,'a.txt','exists',''),
        call(tmp_path,'missing.txt','absent',''),
        call(tmp_path,'a.txt','equals','hello\nмир'),
        call(tmp_path,'a.txt','contains','мир'),
    ):
        assert result['ok'] is True
        assert result['passed'] is True
        assert result['matched'] is True
        assert result['check'] == 'verify_file_content'
    for result in (
        call(tmp_path,'a.txt','equals','wrong'),
        call(tmp_path,'a.txt','contains','нет'),
    ):
        assert result['ok'] is False
        assert result['passed'] is False
        assert result['matched'] is False
    digest=hashlib.sha256('hello\nмир'.encode()).hexdigest()
    matched=call(tmp_path,'a.txt','sha256',digest)
    mismatch=call(tmp_path,'a.txt','sha256','0'*64)
    assert (matched['ok'], matched['passed'], matched['matched']) == (True, True, True)
    assert (mismatch['ok'], mismatch['passed'], mismatch['matched']) == (False, False, False)
    assert call(tmp_path,'a.txt','equals','hello\nмир')['expected_sha256'] == digest
    assert call(tmp_path,'a.txt','contains','мир')['expected_chars'] == 3
    assert matched['expected_sha256'] == digest
    assert f.read_bytes()==before


def test_verify_validation_and_scope(tmp_path: Path):
    (tmp_path/'bad.bin').write_bytes(b'abc')
    with pytest.raises(ValueError): call(tmp_path,'x.txt','sha256','BAD')
    with pytest.raises(ValueError): call(tmp_path,'bad.bin','exists','')
    with pytest.raises(PermissionError): call(tmp_path,'x.txt','exists','',policy(tmp_path,verify=False))
    outside=tmp_path.parent/'outside.txt'; outside.write_text('x',encoding='utf-8')
    with pytest.raises((PermissionError, ValueError)): call(tmp_path,'../outside.txt','exists','')


