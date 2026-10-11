"""Isolated integration test for the WA4-O Windows double-click launcher."""
import subprocess
import sys
import unittest
from pathlib import Path


class DemoLauncherTests(unittest.TestCase):
    def test_launcher_starts_local_fixture_and_serves_ui_without_browser(self):
        repo = Path(__file__).resolve().parent
        result = subprocess.run(
            [sys.executable, "-B", "wa4o_ui_launcher.py", "--self-test"],
            cwd=repo, capture_output=True, text=True, encoding="utf-8",
            timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stdout + "\n" + result.stderr)
        self.assertIn("WA4-O launcher self-test PASS", result.stdout)


if __name__ == "__main__":
    unittest.main()
