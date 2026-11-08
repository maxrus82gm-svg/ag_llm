"""Synthetic import-graph cases run the ACTUAL S2 isolation test; no inspected code executes."""
import ast
import copy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

import test_rt002_s2_budget_policy as s2

s2._ISOLATED = True
ROOT = s2.ROOT
OBSERVATIONS = {}
LEDGER = (ROOT / "ultra_budget_ledger.py").read_text(encoding="utf-8")


def fixture():
    return {**{name: "" for name in s2.POLICY_ENTRYPOINTS}, "web_alarm": "", "ultra_budget_policy": "PURE = True\n",
            "ultra_budget_ledger": LEDGER, "context_storage": "", "run_store": ""}


def cases():
    base = fixture()
    output = {"offline_capsule_without_production_reachability": (base, "PASS"),
              "benign_new_consumer": ({**base, "new_consumer": "import json\nimport context_storage\n"}, "PASS"),
              "benign_builtin_fromlist": ({**base, "server": "__import__('json', fromlist=['dumps'])\n"}, "PASS")}
    additions = {
        "direct_policy": "import ultra_budget_policy\n",
        "from_policy_alias": "from ultra_budget_policy import evaluate_request as decide\n",
        "policy_module_alias": "import ultra_budget_policy as budget\n",
        "transitive_ledger": "import ultra_budget_ledger as ledger\n",
        "from_ledger_alias": "from ultra_budget_ledger import BudgetLedger as B\n",
        "dynamic_import": "__import__('ultra_budget_policy')\n",
        "dynamic_alias": "from importlib import import_module as load\nload('ultra_budget_policy')\n",
        "dynamic_module_alias": "import importlib as il\nloader = il.import_module\nloader('ultra_budget_policy')\n",
        "getattr_import": "import importlib as il\ngetattr(il, 'import_module')('ultra_budget_policy')\n",
        "dict_import": "import builtins as b\nb.__dict__['__import__']('ultra_budget_policy')\n",
        "dynamic_unknown_name": "import importlib\ndef f(name):\n    return importlib.import_module(name)\n",
        "opaque_loader_attribute": "import importlib\ndef f(method, name):\n    return getattr(importlib, method)(name)\n",
        "opaque_loader_attribute_alias": "import importlib\nchoose = getattr\ndef f(method, name):\n    return choose(importlib, method)(name)\n",
        "opaque_loader_namespace": "import importlib\ndef f(method, name):\n    return importlib.__dict__[method](name)\n",
        "loader_container_escape": "from importlib import import_module as load\nLOADERS = [load]\n",
        "loader_escape": "from importlib import import_module as load\ndef f():\n    return load\n",
        "exec_literal": "exec('import ultra_budget_policy')\n",
        "exec_unknown": "def f(code):\n    exec(code)\n",
        "file_loader_name": "def f(loader):\n    return loader('ultra_budget_policy.py')\n",
        "protected_submodule_name": "def f(loader):\n    return loader('ultra_budget_policy.child')\n",
        "spec_parent_import": "from importlib.util import find_spec as locate\nlocate('ultra_budget_policy.child')\n",
        "unknown_spec_query": "from importlib.util import find_spec as locate\ndef f(name):\n    return locate(name)\n",
        "unknown_import_root": "import unreviewed_bridge\n",
        "pinned_metadata_domain_escape": "from web_alarm.model_cards import _adapter_state as probe\ndef f(provider):\n    return probe(provider)\n",
        "pinned_metadata_registry_escape": "from web_alarm.model_cards import BUILTIN_PROVIDERS as providers\n",
        "relative_builtin_import": "__import__('json', level=1)\n",
        "unknown_builtin_fromlist": "def f(items):\n    return __import__('json', fromlist=items)\n",
        "star_builtin_fromlist": "__import__('json', fromlist=['*'])\n",
        "static_star_import": "from json import *\n",
        "file_import_loader": "from importlib.util import spec_from_file_location as locate\ndef f(path):\n    return locate('x', path)\n",
    }
    for name, source in additions.items(): output[name] = ({**base, "server": source}, "RED")
    output.update({
        "new_direct_consumer": ({**base, "new_consumer": "import ultra_budget_policy\n"}, "RED"),
        "transitive_new_bridge": ({**base, "server": "import bridge\n", "bridge": "from ultra_budget_ledger import BudgetLedger\n"}, "RED"),
        "reexported_dynamic_alias": ({**base, "server": "from bridge import load as invoke\ninvoke('ultra_budget_policy')\n",
                                      "bridge": "from importlib import import_module as load\n"}, "RED"),
        "relative_from_import": ({**base, "pkg": "", "pkg.consumer": "from . import bridge\n", "pkg.bridge": "import ultra_budget_policy\n",
                                  "server": "import pkg.consumer\n"}, "RED"),
        "package_initializer": ({**base, "pkg": "import ultra_budget_policy\n", "pkg.child": "", "server": "from pkg import child\n"}, "RED"),
        "changed_offline_capsule": ({**base, "ultra_budget_ledger": "import ultra_budget_policy\n# unrelated implementation\n"}, "RED"),
        "cloned_capsule_new_name": ({**base, "another_ledger": LEDGER}, "RED"),
        "changed_shared_dependency": ({**base, "context_storage": "import ultra_budget_policy\n"}, "RED"),
        "import_cycle_reaches_policy": ({**base, "server": "import a\n", "a": "import b\n", "b": "import a\nimport ultra_budget_policy\n"}, "RED"),
        "local_stdlib_shadow": ({**base, "server": "import json\n", "json": "import ultra_budget_policy\n"}, "RED"),
        "dynamic_relative": ({**base, "pkg": "", "pkg.consumer": "from importlib import import_module as load\nload('.bridge', 'pkg')\n",
                              "pkg.bridge": "import ultra_budget_policy\n"}, "RED"),
        "missing_policy_source": ({k: v for k, v in base.items() if k != "ultra_budget_policy"}, "RED"),
    })
    return output


def actual_oracle(sources):
    s2._OBSERVATIONS.pop("policy_import_isolation", None)
    result = unittest.TestResult()
    with patch.object(s2, "policy_isolation_sources", return_value=(sources, {"web_alarm", "pkg"} & sources.keys())):
        unittest.TestSuite([s2.IsolationTests("test_no_production_module_imports_the_policy_yet")]).run(result)
    assert result.testsRun == 1 and not result.errors and not result.skipped, (result.testsRun, result.errors, result.skipped)
    return {"actual": "RED" if result.failures else "PASS", "tests_run": result.testsRun,
            "failures": [text for _, text in result.failures], "audit": copy.deepcopy(s2._OBSERVATIONS["policy_import_isolation"])}


class ImportIsolationQualityTests(unittest.TestCase):
    def collected_case(self, label, child_source, expected):
        base = SANDBOX / label
        sources = {**fixture(), "server": "__import__('pkg', fromlist=['child'])\n", "pkg": "", "pkg.child": child_source}
        packages = {"web_alarm", "pkg"}
        for name, source in sources.items():
            path = base.joinpath(*name.split("."))
            path = path / "__init__.py" if name in packages else path.with_suffix(".py")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(source, encoding="utf-8")
        initial = [*base.glob("*.py"), *(base / "web_alarm").glob("*.py")]
        with patch.object(s2, "ROOT", base), patch.object(s2.s1, "_production_modules", return_value=initial):
            collected, found_packages = s2.policy_isolation_sources()
        self.assertIn("pkg.child", collected, "fromlist must expand beyond the initial S1 census")
        result = actual_oracle(collected)
        OBSERVATIONS[label] = {"expected": expected, "collected_nested_child": True, **result}
        self.assertEqual(result["actual"], expected)
        if expected == "RED": self.assertTrue(result["audit"]["policy_paths"])

    def test_collector_fromlist_nested_policy(self):
        self.collected_case("collector_fromlist_nested_policy", "import ultra_budget_policy\n", "RED")

    def test_collector_fromlist_benign_child(self):
        self.collected_case("collector_fromlist_benign_child", "import json\n", "PASS")

    def check_case(self, name):
        sources, expected = cases()[name]
        before = copy.deepcopy(sources)
        result = actual_oracle(sources)
        OBSERVATIONS[name] = {"expected": expected, **result}
        self.assertEqual(result["actual"], expected, name)
        if name in {"direct_policy", "from_policy_alias", "policy_module_alias", "transitive_ledger", "from_ledger_alias",
                    "dynamic_import", "dynamic_alias", "dynamic_module_alias", "getattr_import", "dict_import",
                    "exec_literal", "spec_parent_import", "new_direct_consumer", "transitive_new_bridge",
                    "reexported_dynamic_alias", "relative_from_import", "package_initializer", "changed_shared_dependency",
                    "import_cycle_reaches_policy", "local_stdlib_shadow", "dynamic_relative", "cloned_capsule_new_name"}:
            self.assertTrue(result["audit"]["policy_paths"], "RED must include an actual resolved policy path: " + name)
        self.assertEqual(sources, before)


for name in cases():
    setattr(ImportIsolationQualityTests, "test_" + name, lambda self, name=name: self.check_case(name))


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "weaken_disable":
        original = s2.policy_import_audit
        def unchecked(*args, **kwargs):
            result = original(*args, **kwargs); result["issues"] = []; return result
        s2.policy_import_audit = unchecked
    elif mode == "weaken_transitive":
        original = s2._import_events
        def omitted(module, *args, **kwargs):
            events, issues, observed = original(module, *args, **kwargs)
            return ([e for e in events if e[0] != "ultra_budget_ledger"] if module != "ultra_budget_ledger" else events), issues, observed
        s2._import_events = omitted
    elif mode == "weaken_capsule_hash":
        s2._sha256 = lambda _: s2.OFFLINE_POLICY_CAPSULES["ultra_budget_ledger"]
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]))
    import test_rt002_s1_routes as s1
    print(json.dumps({"mode": mode, "counts": {"run": result.testsRun, "fail": len(result.failures), "error": len(result.errors),
        "skip": len(result.skipped)}, "isolation_violations": s1._GUARD_VIOLATIONS, "observations": OBSERVATIONS}, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result.wasSuccessful() and not s1._GUARD_VIOLATIONS else 1)
