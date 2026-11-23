"""Fault injection for the evidence-only matrix checker, never touches actual logs."""
from pathlib import Path
import hashlib
import shutil
import sys
import tempfile
import unittest
import matrix_audit as audit

HERE=Path(__file__).resolve().parent
WUA=HERE.parents[1]
COLIBRI=Path(sys.argv[1]).resolve()
VAULT=Path(sys.argv[2]).resolve()
PRODUCER_LOG=Path(sys.argv[3]).resolve()

class Negatives(unittest.TestCase):
    def test_exact_source_pins_and_all_log_checksums(self):
        state=audit.run(WUA,COLIBRI,PRODUCER_LOG,VAULT)
        self.assertEqual(state["verified_contract_blobs"],10)
        self.assertEqual(state["archived_WUA_raw_logs_sha256_verified"],12)
        self.assertEqual(len(state["matrix"]),13)
        self.assertEqual(state["statuses"],{"OFFLINE_PASS_SCOPED":8,"PARTIAL":3,"NOT_RUN":2})
        self.assertEqual(state["overall"],"PARTIAL_OFFLINE_NOT_ACCEPTED")

    def test_corrupt_producer_log_refused(self):
        with tempfile.TemporaryDirectory(prefix="wua665-proof-negative-") as name:
            p=Path(name)/"producer.txt"
            data=(PRODUCER_LOG).read_text(encoding="utf8")
            p.write_text(data.replace("Ran 22 tests","Ran 21 tests"),encoding="utf8")
            with self.assertRaisesRegex(ValueError,"producer"):
                audit.run(WUA,COLIBRI,p,VAULT)
        self.assertEqual((PRODUCER_LOG).read_text(encoding="utf8"),data)

    def test_tampered_archived_log_refused_without_altering_source(self):
        with tempfile.TemporaryDirectory(prefix="wua665-vault-negative-") as name:
            d=Path(name)
            files=list(VAULT.glob("*.txt"))
            self.assertEqual(len(files),12)
            for file in files:shutil.copyfile(file,d/file.name)
            target=d/"append_hard_kill.txt"
            target.write_bytes(target.read_bytes()+b"tamper")
            with self.assertRaisesRegex(ValueError,"integrity mismatch"):
                audit.run(WUA,COLIBRI,PRODUCER_LOG,d)
        expected=next(v for v in
          __import__('json').loads(__import__('subprocess').check_output(
            ["git","-C",str(WUA),"show",audit.BASE+":"+audit.REPORT]
          ))['log_manifest'] if v["name"]=="append_hard_kill.txt")
        self.assertEqual(hashlib.sha256((VAULT/expected["name"]).read_bytes()).hexdigest(),
                         expected["sha256"])

    def test_contract_matrix_blob_drift_refused(self):
        old=audit.MATRIX_BLOB
        try:
            audit.MATRIX_BLOB="0"*40
            with self.assertRaisesRegex(ValueError,"matrix source drift"):
                audit.run(WUA,COLIBRI,PRODUCER_LOG,VAULT)
        finally:
            audit.MATRIX_BLOB=old

if __name__=="__main__":
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(Negatives)
    sys.exit(not unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful())
