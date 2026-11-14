"""H35 import-graph reconciliation keeps unreviewed consumers and mutated gates RED."""
import unittest
import test_rt002_s2_budget_policy as s2

class GateIsolationTests(unittest.TestCase):
    def sources(self):
        return s2.policy_isolation_sources()

    def test_reviewed_admission_is_accepted_but_still_in_graph(self):
        sources,packages=self.sources()
        result=s2.policy_import_audit(sources,packages=packages,required_entrypoints=s2.POLICY_ENTRYPOINTS)
        self.assertEqual(result['issues'],[])
        self.assertIn('ultra_budget_ledger',result['graph']['web_alarm.turn_service'])
        self.assertIn('ultra_budget_policy',result['graph']['web_alarm.ordinary_chat_bridge'])
        self.assertIn('ultra_budget_ledger',result['graph']['web_alarm.ordinary_provider'])

    def test_mutating_each_gate_is_detected(self):
        sources,packages=self.sources()
        for name in s2.OFFLINE_ADMISSION_GATES:
            with self.subTest(gate=name):
                changed={**sources,name:sources[name]+'\nH35_UNREVIEWED_MUTATION = True\n'}
                result=s2.policy_import_audit(changed,packages=packages,required_entrypoints=s2.POLICY_ENTRYPOINTS)
                self.assertTrue(any(issue[0]==name and issue[2]=='OFFLINE_ADMISSION_GATE_CHANGED' for issue in result['issues']))

    def test_unreviewed_direct_and_transitive_policy_consumers_are_rejected(self):
        sources,packages=self.sources()
        for dependency in ('ultra_budget_policy','ultra_budget_ledger'):
            with self.subTest(dependency=dependency):
                changed={**sources,'h35_unknown_helper':'import '+dependency+'\n',
                         'h35_unknown_entry':'import h35_unknown_helper\n'}
                result=s2.policy_import_audit(changed,packages=packages,required_entrypoints=s2.POLICY_ENTRYPOINTS)
                self.assertTrue(any(issue[0]=='h35_unknown_entry' and 'PRODUCTION_REACHES_POLICY' in issue[2] for issue in result['issues']))

    def test_standard_entrypoint_cannot_add_an_unguarded_policy_edge(self):
        sources,packages=self.sources()
        changed={**sources,'server':sources['server']+'\nimport ultra_budget_policy\n'}
        result=s2.policy_import_audit(changed,packages=packages,required_entrypoints=s2.POLICY_ENTRYPOINTS)
        self.assertTrue(any(issue[0]=='server' and 'PRODUCTION_REACHES_POLICY' in issue[2] for issue in result['issues']))

    def test_guard_bootstrap_cannot_load_another_script(self):
        sources,packages=self.sources()
        module='web_alarm.ordinary_test_fixture'
        changed={**sources,module:sources[module].replace('guard/sitecustomize.py','guard/UNREVIEWED.py')}
        self.assertNotEqual(changed[module],sources[module])
        result=s2.policy_import_audit(changed,packages=packages,required_entrypoints=s2.POLICY_ENTRYPOINTS)
        self.assertTrue(any(issue[0]==module and issue[2]=='OPAQUE_IMPORT_LOADER' for issue in result['issues']))
