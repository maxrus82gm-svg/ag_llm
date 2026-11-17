"""Offline Windows tests for STANDARD GigaChat environment inheritance.

No real secrets or provider network calls are used.
"""
import io
import os
import unittest
from unittest.mock import patch

from web_alarm import launcher


@unittest.skipUnless(os.name == "nt", "Windows user Environment registry only")
class StandardCredentialEnvironmentTests(unittest.TestCase):
    def test_user_registry_values_are_used_only_when_process_variables_absent(self):
        import winreg
        def fake_value(_key, name):
            return ({"GIGACHAT_CREDENTIALS": "fixture-credential",
                     "GIGACHAT_SCOPE": "GIGACHAT_API_PERS"}[name], winreg.REG_SZ)
        with patch.dict(os.environ, {}, clear=True), \
                patch("winreg.OpenKey") as opened, \
                patch("winreg.QueryValueEx", side_effect=fake_value):
            launcher._refresh_standard_gigachat_environment()
            self.assertEqual(os.environ["GIGACHAT_CREDENTIALS"], "fixture-credential")
            self.assertEqual(os.environ["GIGACHAT_SCOPE"], "GIGACHAT_API_PERS")
            opened.assert_called_once_with(winreg.HKEY_CURRENT_USER, "Environment")

    def test_explicit_process_variables_are_not_overwritten(self):
        import winreg
        with patch.dict(os.environ, {"GIGACHAT_CREDENTIALS": "explicit", "GIGACHAT_SCOPE": "OTHER"}, clear=True), \
                patch("winreg.OpenKey") as opened, \
                patch("winreg.QueryValueEx", return_value=("registry", winreg.REG_SZ)) as query:
            launcher._refresh_standard_gigachat_environment()
            self.assertEqual(os.environ["GIGACHAT_CREDENTIALS"], "explicit")
            self.assertEqual(os.environ["GIGACHAT_SCOPE"], "OTHER")
            query.assert_not_called()

    def test_registry_unavailable_does_not_create_credentials(self):
        with patch.dict(os.environ, {}, clear=True), \
                patch("winreg.OpenKey", side_effect=OSError("missing")):
            launcher._refresh_standard_gigachat_environment()
            self.assertNotIn("GIGACHAT_CREDENTIALS", os.environ)

    def test_standard_only_skips_offline_self_test(self):
        with patch.object(launcher, "_refresh_standard_gigachat_environment") as refresh, \
                patch.object(launcher, "run_web_alarm", return_value=0) as run:
            self.assertEqual(launcher.main(["--standard", "--no-browser"], io.StringIO()), 0)
            refresh.assert_called_once_with()
            refresh.reset_mock()
            self.assertEqual(launcher.main(["--standard", "--self-test", "temp.json"], io.StringIO()), 0)
            refresh.assert_not_called()
            self.assertTrue(run.called)


if __name__ == "__main__":
    unittest.main()
