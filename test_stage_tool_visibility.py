from pathlib import Path
import server


def policy(root: Path, *, read=True, write=False, verify=True):
    value=server._normalize_permissions({'allow_read':read,'allow_write':write,'allow_delete':False,
        'allow_verify':verify,'read_scope':'.','write_scope':'.','delete_scope':'.',
        'tool_limit':20,'auto_backup':False})
    return server._prepare_policy_for_workspace(root,value)


def names(root, caps, **kw):
    return {x['name'] for x in server._functions_for_policy(policy(root,**kw),set(caps))}


def test_stage_tool_visibility(tmp_path: Path):
    read=names(tmp_path,['READ'])
    assert 'read_file' in read and 'write_file' not in read and 'verify_file_content' not in read
    verify=names(tmp_path,['VERIFY'])
    assert 'verify_file_content' in verify and 'write_file' not in verify and 'read_file' not in verify
    rw=names(tmp_path,['READ','WRITE'])
    assert {'read_file','write_file'} <= rw
    denied=names(tmp_path,['WRITE'],write=False)
    assert 'write_file' in denied
    assert 'verify_file_content' not in names(tmp_path,['VERIFY'],read=False)
