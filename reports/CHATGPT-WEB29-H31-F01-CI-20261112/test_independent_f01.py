"""Independent GitHub CI oracles for H31 F-01. No real script execution."""
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from web_alarm import launcher


class F01Independent(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="h31_independent_")
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)

    def config(self, name, script, args=None):
        profile = {"title": "Offline reviewer", "kind": "python_script", "script": script}
        if args is not None:
            profile["args"] = args
        path = self.tmp / "case.json"
        path.write_text(json.dumps({"schema_version": 1, "active": name,
                                    "test_profiles": {name: profile}}), encoding="utf-8")
        return path

    def test_only_exact_approved_pairs_reach_dispatch(self):
        approved = (
            ("ordinary-core-offline", "web_alarm/ordinary_test_fixture.py", []),
            ("stage5-offline", "reports/CODEX-WUA-CHAT-S5-OFFLINE-FULL-CHAT-001/review_fixture.py", ["--web"]),
        )
        for name, script, args in approved:
            with self.subTest(name=name):
                path = self.config(name, script, args)
                with patch.object(launcher, "run_script", return_value=19) as dispatch, \
                        patch.object(launcher, "run_web_alarm") as web:
                    self.assertEqual(launcher.main(["--config", str(path), "--require-test"],
                                                   out=io.StringIO()), 19)
                    dispatch.assert_called_once()
                    self.assertEqual(dispatch.call_args.args[0].script, script)
                    self.assertEqual(dispatch.call_args.args[0].args, tuple(args))
                    web.assert_not_called()

    def test_cross_profile_and_unapproved_scripts_cannot_start(self):
        ordinary = "web_alarm/ordinary_test_fixture.py"
        stage5 = "reports/CODEX-WUA-CHAT-S5-OFFLINE-FULL-CHAT-001/review_fixture.py"
        unapproved = (
            ("ordinary-core-offline", "probe_gigachat_models.py", []),
            ("ordinary-core-offline", ordinary, ["--no-browser"]),
            ("stage5-offline", stage5, []),
            ("stage5-offline", ordinary, []),
            ("ordinary-core-offline", stage5, ["--web"]),
            ("unapproved", ordinary, []),
        )
        for name, script, args in unapproved:
            with self.subTest(name=name, script=script, args=args):
                path = self.config(name, script, args)
                with patch.object(launcher, "run_script") as dispatch, \
                        patch.object(launcher, "run_web_alarm") as web, \
                        patch.object(launcher.subprocess, "call") as call, \
                        patch.object(launcher.subprocess, "Popen") as popen:
                    out = io.StringIO()
                    self.assertEqual(launcher.main(["--config", str(path), "--require-test"],
                                                   out=out), 2)
                    self.assertIn("ЗАПУСК ОСТАНОВЛЕН", out.getvalue())
                    dispatch.assert_not_called()
                    web.assert_not_called()
                    call.assert_not_called()
                    popen.assert_not_called()

    def test_standard_not_silently_selected_by_test_entry(self):
        path = self.tmp / "missing.json"
        with patch.object(launcher, "run_web_alarm") as web, \
                patch.object(launcher, "run_script") as script:
            self.assertEqual(launcher.main(["--config", str(path), "--require-test"],
                                           out=io.StringIO()), 2)
            web.assert_not_called()
            script.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)
