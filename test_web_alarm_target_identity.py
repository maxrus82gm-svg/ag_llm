import os
import tempfile
import unittest
from pathlib import Path

from web_alarm.target_identity import (
    TargetIdentityError,
    canonical_target,
    target_key,
)

WINDOWS = os.name == "nt"


def _make_junction(link: Path, target: Path) -> None:
    import _winapi

    _winapi.CreateJunction(str(target), str(link))


class CanonicalTargetTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.base = Path(self.tempdir.name)
        self.root = self.base / "project"
        (self.root / "Sub").mkdir(parents=True)
        self.file = self.root / "Sub" / "Marker.txt"
        self.file.write_bytes(b"marker")

    def tearDown(self):
        self.tempdir.cleanup()

    def test_relative_posix_display_and_stable_key(self):
        target = canonical_target(self.root, "Sub/Marker.txt")

        self.assertEqual(target.relative, "Sub/Marker.txt")
        self.assertEqual(target.path, self.file.resolve())
        self.assertEqual(target.key, target_key("Sub/Marker.txt"))

    @unittest.skipUnless(WINDOWS, "case-insensitive identity is a Windows property")
    def test_case_and_separator_spellings_share_identity(self):
        spellings = [
            "Sub/Marker.txt",
            "sub\\marker.TXT",
            "SUB/./MARKER.txt",
            "other/../Sub/Marker.txt",
            str(self.file),
        ]
        targets = [canonical_target(self.root, item) for item in spellings]

        self.assertEqual({item.key for item in targets}, {"sub/marker.txt"})
        # existing components keep their on-disk spelling for display
        self.assertEqual({item.relative for item in targets}, {"Sub/Marker.txt"})

    def test_absent_target_is_allowed_and_keeps_typed_final_name(self):
        target = canonical_target(self.root, "Sub/New.txt")

        self.assertEqual(target.relative, "Sub/New.txt")
        self.assertFalse(target.path.exists())

    def test_escape_and_root_targets_fail_closed(self):
        outside = self.base / "outside.txt"
        outside.write_bytes(b"x")
        for raw in ("../outside.txt", str(outside), ".", "Sub/.."):
            with self.subTest(raw=raw):
                with self.assertRaises(TargetIdentityError):
                    canonical_target(self.root, raw)

    def test_windows_aliasing_forms_fail_closed(self):
        for raw in (
            "Sub/Marker.txt:stream",
            "Sub/Marker.txt::$DATA",
            "Sub/Marker.txt.",
            "Sub./Marker.txt",
            "Sub /Marker.txt",
            "NUL",
            "Sub/con.txt",
            "lpt1.log",
            "Sub/a?b.txt",
            "Sub/a\x01b.txt",
        ):
            with self.subTest(raw=raw):
                with self.assertRaises(TargetIdentityError):
                    canonical_target(self.root, raw)

    @unittest.skipUnless(WINDOWS, "drive-relative paths exist only on Windows")
    def test_drive_relative_target_fails_closed(self):
        with self.assertRaises(TargetIdentityError):
            canonical_target(self.root, "C:marker.txt")

    def test_directory_target_fails_closed(self):
        with self.assertRaises(TargetIdentityError):
            canonical_target(self.root, "Sub")

    def test_unavailable_workspace_root_fails_closed(self):
        with self.assertRaises(TargetIdentityError):
            canonical_target(self.base / "missing", "a.txt")

    def test_symlink_target_fails_closed(self):
        link = self.root / "link.txt"
        try:
            os.symlink(self.file, link)
        except (OSError, NotImplementedError):
            self.skipTest("symlink creation is not permitted here")
        with self.assertRaises(TargetIdentityError):
            canonical_target(self.root, "link.txt")

    @unittest.skipUnless(WINDOWS, "junctions are Windows reparse points")
    def test_parent_junction_inside_workspace_resolves_to_physical_identity(self):
        _make_junction(self.root / "alias", self.root / "Sub")

        via_alias = canonical_target(self.root, "alias/Marker.txt")
        direct = canonical_target(self.root, "Sub/Marker.txt")

        self.assertEqual(via_alias.key, direct.key)
        self.assertEqual(via_alias.relative, "Sub/Marker.txt")

    @unittest.skipUnless(WINDOWS, "junctions are Windows reparse points")
    def test_parent_junction_escaping_workspace_fails_closed(self):
        outside = self.base / "outside_dir"
        outside.mkdir()
        (outside / "secret.txt").write_bytes(b"x")
        _make_junction(self.root / "escape", outside)

        with self.assertRaises(TargetIdentityError):
            canonical_target(self.root, "escape/secret.txt")

    @unittest.skipUnless(WINDOWS, "junctions are Windows reparse points")
    def test_junction_as_target_itself_fails_closed(self):
        _make_junction(self.root / "dir_alias", self.root / "Sub")

        with self.assertRaises(TargetIdentityError):
            canonical_target(self.root, "dir_alias")

    @unittest.skipUnless(WINDOWS, "manifest stores native Windows separators")
    def test_key_matches_manifest_native_relative_spelling(self):
        self.assertEqual(target_key("Sub\\Marker.txt"), target_key("sub/marker.TXT"))


if __name__ == "__main__":
    unittest.main()
