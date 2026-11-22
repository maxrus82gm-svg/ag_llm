import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import shared_integration_plan as p

def fixture():
    rows = ""
    for actor in p.ACTORS:
        rows += f"<!-- {actor}:BEGIN -->\n| WUA-COLIBRI-BRIDGE-001/P0 | P0 | PLANNED | TBD | dep | criterion | — | next |\n<!-- {actor}:END -->\n"
    return rows.encode("utf-8")

class PlanTests(unittest.TestCase):
    def test_edit_own_section(self):
        old=fixture()
        new=p.update(old,"WUA","P0",{"status":"IN_PROGRESS","task":"LOCAL-1"})
        a,b=p.sections(old.decode(),"COLIBRI")
        c,e=p.sections(new.decode(),"COLIBRI")
        self.assertEqual(old.decode()[a:b],new.decode()[c:e])
        self.assertIn(b"LOCAL-1",new)
    def test_invalid_fields(self):
        for changes in ({"criterion":"different"},{"status":"FAKE"},{"next":"a|b"},{"next":"x\n<!-- COLIBRI:BEGIN -->"},{"status":"ACCEPTED"}):
            with self.subTest(changes=changes),self.assertRaises(ValueError):
                p.update(fixture(),"WUA","P0",changes)
    def test_archive_requires_both(self):
        with self.assertRaises(ValueError):
            p.archive_stage(fixture(),b"# Archive\n","P0")
    def test_archive_retry_and_preserve(self):
        data=fixture()
        for actor in p.ACTORS:
            data=p.update(data,actor,"P0",{"status":"ACCEPTED","evidence":"owner+"+actor})
        new,hist=p.archive_stage(data,b"# Archive\n","P0")
        self.assertNotIn(b"| WUA-COLIBRI-BRIDGE-001/P0 |",new)
        self.assertIn(b"owner+WUA",hist)
        self.assertIn(b"owner+COLIBRI",hist)
        self.assertEqual((new,hist),p.archive_stage(data,hist,"P0"))
        with self.assertRaises(ValueError):
            p.archive_stage(data,hist.replace(b"owner+WUA",b"changed"),"P0")
    @unittest.skipUnless(os.name=="nt","Windows lock")
    def test_cross_process_lock(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            (root/".git").mkdir()
            code="import sys;from pathlib import Path;from shared_integration_plan import locked\nwith locked(Path(sys.argv[1]),timeout=.25): print('LOCK_ACQUIRED')"
            env={**os.environ,"PYTHONPATH":str(Path(p.__file__).parent),"PYTHONUTF8":"1"}
            with p.locked(root):
                child=subprocess.run([sys.executable,"-c",code,t],capture_output=True,text=True,env=env,timeout=5)
                self.assertNotEqual(child.returncode,0)
                self.assertIn("PLAN_BUSY",child.stderr)
            child=subprocess.run([sys.executable,"-c",code,t],capture_output=True,text=True,env=env,timeout=5)
            self.assertEqual(child.returncode,0,child.stderr)
            self.assertIn("LOCK_ACQUIRED",child.stdout)
    @unittest.skipUnless(os.name=="nt","Windows lock")
    def test_cli_stale_and_cross_actor(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);(root/".git").mkdir();(root/"tools").mkdir();(root/"Документация").mkdir()
            helper=root/"tools"/"shared_integration_plan.py"
            shutil.copyfile(p.__file__,helper)
            plan=root/"Документация"/p.PLAN
            plan.write_bytes(fixture())
            (root/"Документация"/p.ARCHIVE).write_bytes(b"# Archive\n")
            def cli(*args):
                return subprocess.run([sys.executable,str(helper),*args],capture_output=True,text=True,encoding="utf-8",timeout=20)
            read=cli("read")
            self.assertEqual(read.returncode,0,read.stderr)
            old=p.sha(plan.read_bytes())
            self.assertIn(old,read.stdout)
            first=cli("update","--actor","WUA","--stage","P0","--expect",old,"--status","IN_PROGRESS")
            self.assertEqual(first.returncode,0,first.stderr)
            now=plan.read_bytes()
            stale=cli("update","--actor","COLIBRI","--stage","P0","--expect",old,"--status","IN_PROGRESS")
            self.assertNotEqual(stale.returncode,0)
            self.assertIn("STALE_PLAN",stale.stderr)
            self.assertEqual(now,plan.read_bytes())
            second=cli("update","--actor","COLIBRI","--stage","P0","--expect",p.sha(now),"--status","IN_PROGRESS")
            self.assertEqual(second.returncode,0,second.stderr)
            self.assertEqual(plan.read_bytes().count(b"IN_PROGRESS"),2)
            denied=cli("archive","--actor","COLIBRI","--stage","P0","--expect",p.sha(plan.read_bytes()))
            self.assertNotEqual(denied.returncode,0)
    def test_atomic(self):
        with tempfile.TemporaryDirectory() as t:
            f=Path(t)/"plan"
            p.atomic(f,b"new")
            self.assertEqual(f.read_bytes(),b"new")
            p.atomic(f,b"next")
            self.assertEqual(f.read_bytes(),b"next")
            self.assertEqual(list(Path(t).iterdir()),[f])

if __name__=="__main__":
    unittest.main()
