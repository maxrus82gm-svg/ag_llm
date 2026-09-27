import subprocess
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent


def git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


class GitRuntimeIgnoreTests(unittest.TestCase):
    def test_runtime_paths_are_declared_in_gitignore(self) -> None:
        gitignore = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
        self.assertIn(".ultra/audit/", gitignore)
        self.assertIn(".ultra/chats/", gitignore)

    def test_runtime_probe_paths_are_ignored(self) -> None:
        for path in (
            ".ultra/audit/__git_ignore_probe__.json",
            ".ultra/chats/__git_ignore_probe__.json",
        ):
            result = git("check-ignore", "-q", path)
            self.assertEqual(
                result.returncode,
                0,
                msg=f"{path} is not ignored by Git",
            )

    def test_no_runtime_files_are_tracked(self) -> None:
        result = git("ls-files", ".ultra/audit", ".ultra/chats")
        self.assertEqual(result.returncode, 0, msg=result.stderr)

        tracked = [
            line.strip()
            for line in result.stdout.splitlines()
            if line.strip()
        ]

        self.assertEqual(
            tracked,
            [],
            msg="Runtime files are still tracked:\n" + "\n".join(tracked),
        )


if __name__ == "__main__":
    unittest.main()
