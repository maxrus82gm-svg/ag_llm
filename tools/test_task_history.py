"""Synthetic history preservation, addressed reads, identity and failure boundaries."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools import task_history as h
from tools.test_task_slot_rotate import Workspace, make_card, run, TASK, DATE, tsr


class History(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='task_history_tests_')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root/'reports').mkdir()
        (self.root/'input.md').write_text('Поручение\nRESULT\n',encoding='utf-8')

    def add(self, task='CODEX-TEST-001'):
        return h.register(self.root,task,'codex','Проверка восстановления','2026-11-04',
                          {'assignment':h.source_ref(self.root,'input.md')})

    def cli(self,*args):
        stdout,stderr=io.StringIO(),io.StringIO()
        with contextlib.redirect_stdout(stdout),contextlib.redirect_stderr(stderr):
            code=h.main(['--repo',str(self.root),*args])
        return code,stdout.getvalue(),stderr.getvalue()

    def test_stable_number_on_repeat_and_increment_for_new_task(self):
        a=self.add();b=self.add();c=self.add('CODEX-TEST-002')
        self.assertEqual(a,b)
        self.assertEqual(a['history_id'],'H-CODEX-000001')
        self.assertEqual(c['history_id'],'H-CODEX-000002')
        self.assertEqual(h.load_record(self.root,a['history_id'])['id'],a['id'])

    def test_revision_keeps_identity_previous_and_does_not_forge_review(self):
        old=self.add()
        (self.root/'new.md').write_text('Новая сдача',encoding='utf-8')
        new=h.register(self.root,old['id'],'codex','Новая сдача','2026-11-05',{'assignment':h.source_ref(self.root,'new.md')})
        self.assertEqual(old['history_id'],new['history_id'])
        self.assertEqual(new['previous'][0]['sources'],old['sources'])
        self.assertEqual(new['review'],'NOT VERIFIED')

    def test_budget_failure_missing_id_and_modified_source_never_dump_text(self):
        self.add()
        for args in [('--max-tokens','1','read','--id','CODEX-TEST-001','--part','assignment'),
                     ('read','--id','CODEX-MISSING-001')]:
            code,out,err=self.cli(*args)
            self.assertEqual(code,2);self.assertEqual(out,'');self.assertNotIn('RESULT',err)
        (self.root/'input.md').write_text('TAMPERED_SECRET',encoding='utf-8')
        code,out,err=self.cli('read','--id','CODEX-TEST-001','--part','assignment')
        self.assertEqual(code,2);self.assertEqual(out,'');self.assertNotIn('TAMPERED_SECRET',err)

    def test_list_does_not_read_or_print_bodies_and_range_is_explicit(self):
        self.add()
        code,out,err=self.cli('read','--id','H-CODEX-000001','--part','assignment','--start-line','2','--lines','1')
        self.assertEqual(code,0);self.assertIn('2-2/2',out);self.assertIn('RESULT',out);self.assertNotIn('Поручение',out)
        (self.root/'input.md').unlink()
        code,out,err=self.cli('list','--agent','codex','--last','5')
        self.assertEqual(code,0);self.assertNotIn('RESULT',out)

    def test_traversal_and_duplicate_alias_refused(self):
        for path in ('../input.md',str(self.root/'input.md')):
            with self.assertRaises(ValueError):h.source_ref(self.root,path)
        a=self.add();b=self.add('CODEX-TEST-002');b['history_id']=a['history_id'];h.save_record(self.root,b)
        with self.assertRaises(ValueError):h.load_record(self.root,a['history_id'])
        with self.assertRaises(ValueError):self.add('CODEX-TEST-003')

    def test_lock_refuses_second_writer_and_failed_save_allocates_no_record(self):
        with h.locked(self.root):
            with self.assertRaises(ValueError):self.add()
        with patch.object(h,'atomic',side_effect=OSError('disk full')):
            with self.assertRaises(OSError):self.add()
        self.assertFalse(h.record_path(self.root,'CODEX-TEST-001').exists())
        self.assertEqual(self.add()['history_id'],'H-CODEX-000001')

    def test_removed_record_does_not_recycle_its_number(self):
        self.add()
        h.record_path(self.root,'CODEX-TEST-001').unlink()
        self.assertEqual(self.add('CODEX-TEST-002')['history_id'],'H-CODEX-000002')

    def test_corrupt_range_is_refused_without_output(self):
        value=self.add();value['sources']['assignment'].update(first_line=-1,last_line=200)
        h.save_record(self.root,value)
        code,out,err=self.cli('read','--id',value['id'],'--part','assignment')
        self.assertEqual(code,2);self.assertEqual(out,'')

    def test_render_retains_all_open_questions_and_only_ten_recent_rows(self):
        docs=self.root/'Документация';docs.mkdir()
        for name in [*h.CARDS.values(),'05_Реестр задач.md']:
            (docs/name).write_text('OPEN_OLD_DO_NOT_DROP\n'+h.BEGIN+'\n'+h.END+'\nTAIL_KEEP\n',encoding='utf-8')
        for i in range(12):self.add(f'CODEX-TEST-{i:03d}')
        self.assertEqual(self.cli('render','--apply')[0],0)
        body=(docs/h.CARDS['codex']).read_text(encoding='utf-8')
        self.assertEqual(body.count('| `H-CODEX-'),10)
        self.assertIn('H-CODEX-000012',body);self.assertNotIn('H-CODEX-000001`',body)
        self.assertIn('OPEN_OLD_DO_NOT_DROP',(docs/'05_Реестр задач.md').read_text(encoding='utf-8'))
        before={p:p.read_bytes() for p in docs.iterdir()}
        self.assertEqual(self.cli('render','--apply')[0],0)
        self.assertEqual(before,{p:p.read_bytes() for p in docs.iterdir()})

    def test_review_repeat_and_submission_repeat_preserve_verdict(self):
        self.add()
        args=('review','--id','H-CODEX-000001','--verdict','PARTIAL','--evidence','input.md','--scope','synthetic only','--apply')
        self.assertEqual(self.cli(*args)[0],0)
        before=h.record_path(self.root,'CODEX-TEST-001').read_bytes()
        self.assertEqual(self.cli(*args)[0],0)
        self.assertEqual(before,h.record_path(self.root,'CODEX-TEST-001').read_bytes())
        self.add()
        self.assertEqual(before,h.record_path(self.root,'CODEX-TEST-001').read_bytes())

    def test_finish_saves_number_in_slot_and_reuses_it(self):
        ws=Workspace(self.root/'slot');ws.card(make_card());ws.package()
        args=('finish','--card',ws.card_path,'--task-id',TASK,'--no-chat-amendment','--date',DATE,'--headless','--apply')
        code,result=run(*args)
        self.assertEqual(code,0,result)
        history_id=result['history']['history_id']
        self.assertIn(history_id.encode(),ws.card_path.read_bytes())
        before=ws.card_path.read_bytes()
        code,result=run(*args)
        self.assertEqual(code,0,result);self.assertEqual(history_id,result['history']['history_id'])
        self.assertEqual(before,ws.card_path.read_bytes())

    def test_history_failure_keeps_active_task_and_snapshot(self):
        ws=Workspace(self.root/'slot');ws.card(make_card());ws.package();before=ws.card_path.read_bytes()
        with patch.object(tsr.task_history,'register_submission',side_effect=ValueError('disk failure')):
            code,result=run('finish','--card',ws.card_path,'--task-id',TASK,'--no-chat-amendment','--date',DATE,'--headless','--apply')
        self.assertEqual(code,3);self.assertEqual(before,ws.card_path.read_bytes())
        self.assertTrue((ws.root/'reports'/TASK/'handoff_task.md').exists())
        self.assertIn('HISTORY_SAVE_FAILED',str(result))

    def test_finish_rejects_a_spoofed_history_number(self):
        ws=Workspace(self.root/'slot');ws.card(make_card());ws.package()
        args=('finish','--card',ws.card_path,'--task-id',TASK,'--no-chat-amendment','--date',DATE,'--headless','--apply')
        code,result=run(*args);self.assertEqual(code,0,result)
        hid=result['history']['history_id']
        forged=ws.card_path.read_bytes().replace(hid.encode(),b'H-TEST-999999')
        ws.card_path.write_bytes(forged)
        code,result=run(*args)
        self.assertEqual(code,3);self.assertIn('HISTORY_ID_MISMATCH',str(result))
        self.assertEqual(forged,ws.card_path.read_bytes())

    def test_assign_cannot_reuse_id_from_older_registered_task(self):
        from tools.test_task_slot_rotate import task_text,WAITING_LITERAL
        ws=Workspace(self.root/'slot');ws.card(make_card());ws.package()
        code,result=run('finish','--card',ws.card_path,'--task-id',TASK,'--no-chat-amendment','--date',DATE,'--headless','--apply')
        self.assertEqual(code,0,result)
        ws.card(make_card(b1=WAITING_LITERAL+'\n'))
        source=ws.root/'again.md';source.write_text(task_text(),encoding='utf-8')
        before=ws.card_path.read_bytes()
        code,result=run('assign','--card',ws.card_path,'--task-file',source,'--expected-card-sha256',h.digest(before),'--headless','--apply')
        self.assertEqual(code,3);self.assertIn('TASK_ID_ALREADY_IN_HISTORY',str(result))
        self.assertEqual(before,ws.card_path.read_bytes())


if __name__=='__main__':unittest.main()
