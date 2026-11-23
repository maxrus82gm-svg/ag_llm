"""#666 source-only S1/S2/D8 negative controls: no real network or Manager."""
from __future__ import annotations
import ast
from pathlib import Path
import unittest
import test_rt002_s1_routes as s1
import test_rt002_s2_budget_policy as s2

ROOT = Path(__file__).resolve().parent

class GateReview(unittest.TestCase):
    def test_history_adapter_model_catalog_is_pure(self):
        path=ROOT/"web_alarm/test_model_selector.py"
        tree=ast.parse(path.read_text(encoding="utf8"))
        imports=sorted(n.module for n in ast.walk(tree) if isinstance(n,ast.ImportFrom))
        self.assertEqual(imports,["__future__","model_registry"])
        from web_alarm.test_model_selector import allowed_test_model_ids
        from model_registry import MODEL_REGISTRY
        self.assertEqual(allowed_test_model_ids(),[
            x.model_id for x in MODEL_REGISTRY.values()
            if x.enabled and x.provider=="gigachat" and not x.is_local])

    def test_s1_network_sources_remain_pinned(self):
        for f in ("web_alarm/launcher.py","web_alarm/model_cards.py"):
            observed=s1.analyze_module(Path(f).name,(ROOT/f).read_text(encoding="utf8"))
            self.assertEqual(observed["reconciliation_issues"],[])
            self.assertEqual(observed["unexplained"],[])
        src="import httpx\nasync def extra():\n return httpx.post('https://api.giga.chat/v1/chat/completions')\n"
        scanned=s1.scan_send_sites("synthetic.py",src)
        self.assertEqual(scanned[0]["traffic"],"UNKNOWN")
        self.assertNotIn(("synthetic.py","extra","httpx.post","UNKNOWN"),s1.EXPECTED_PRODUCTION_SITES)

    def test_s1_exact_httpx_importer_inventory(self):
        found=set()
        for path in s1._production_modules():
            if path.name in s1.NON_PRODUCTION_MODULES:continue
            for n in ast.walk(ast.parse(path.read_text(encoding="utf8"))):
                if isinstance(n,ast.Import) and any(a.name.split(".")[0]=="httpx" for a in n.names):
                    found.add(path.name)
                if isinstance(n,ast.ImportFrom) and (n.module or "").split(".")[0]=="httpx":
                    found.add(path.name)
        self.assertEqual(found,{
            "server.py","planner_runtime.py","verifier_runtime.py",
            "compressor_runtime.py","gigachat_transport.py",
            "ordinary_gigachat_transport.py","gigachat_admission.py",
            "gigachat_runtime.py","colibri_bridge_transport.py"})

    def test_s2_real_unreviewed_policy_import_fails(self):
        sources,packages=s2.policy_isolation_sources()
        current=s2.policy_import_audit(sources,packages=packages,required_entrypoints=s2.POLICY_ENTRYPOINTS)
        self.assertEqual(current["issues"],[])
        altered=dict(sources)
        altered["web_alarm.ordinary_provider"]+="\nfrom ultra_budget_policy import evaluate_request\n"
        result=s2.policy_import_audit(altered,packages=packages,required_entrypoints=s2.POLICY_ENTRYPOINTS)
        self.assertTrue(any("OFFLINE_ADMISSION_GATE_CHANGED" in issue[2] for issue in result["issues"]))

    def test_s2_unlisted_external_import_is_rejected(self):
        sources,packages=s2.policy_isolation_sources()
        altered=dict(sources)
        altered["web_alarm.ordinary_provider"]+="\nimport unsafe_external666\n"
        issues=s2.policy_import_audit(altered,packages=packages,required_entrypoints=s2.POLICY_ENTRYPOINTS)["issues"]
        self.assertTrue(any("UNKNOWN_IMPORT_ROOT:unsafe_external666" in x[2] for x in issues))

if __name__=="__main__":
    unittest.main()
