"""Read-only registry extraction: isolation, ambiguity and bounded output."""
import contextlib
import io
from pathlib import Path
import tempfile
import unittest

from tools.read_task_record import main, read_record


def block(record_id, body):
    return f"<!-- TASK-RECORD {record_id} BEGIN -->\n{body}\n<!-- TASK-RECORD {record_id} END -->\n"


class ReadTaskRecordTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="task_record_reader_")
        self.addCleanup(temporary.cleanup)
        self.path = Path(temporary.name) / "registry.md"

    def write(self, value):
        self.path.write_text(value, encoding="utf-8")

    def test_exact_record_and_lines_exclude_surrounding_tasks(self):
        self.write("Header\n" + block("BP-0001", "Первая задача") + block("BP-0002", "UNRELATED_TASK"))
        result = read_record(self.path, "BP-0001")
        self.assertEqual((result.start_line, result.end_line), (2, 4))
        self.assertEqual(result.text, block("BP-0001", "Первая задача"))
        self.assertNotIn("UNRELATED_TASK", result.text)

    def test_missing_id_does_not_print_full_registry(self):
        self.write(block("BP-0001", "DO_NOT_PRINT"))
        output, error = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(error):
            code = main(["--registry", str(self.path), "--id", "BP-0099"])
        self.assertEqual(code, 2)
        self.assertEqual(output.getvalue(), "")
        self.assertNotIn("DO_NOT_PRINT", error.getvalue())

    def test_windows_newlines_and_utf8_bom_preserve_content_and_source(self):
        raw = b"\xef\xbb\xbf" + block("BP-0001", "Точная задача").replace("\n", "\r\n").encode("utf-8")
        self.path.write_bytes(raw)
        result = read_record(self.path, "BP-0001")
        self.assertEqual(result.text, block("BP-0001", "Точная задача"))
        self.assertEqual((result.start_line, result.end_line), (1, 3))
        self.assertEqual(self.path.read_bytes(), raw)

    def test_duplicate_even_after_requested_record_is_refused(self):
        self.write(block("BP-0001", "first") + block("BP-0001", "duplicate"))
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            read_record(self.path, "BP-0001")

    def test_malformed_nested_missing_and_mismatched_boundaries(self):
        cases = [
            "<!-- TASK-RECORD BP-0001 BEGIN -->\nmissing end\n",
            "<!-- TASK-RECORD BP-0001 BEGIN -->\n<!-- TASK-RECORD BP-0002 END -->\n",
            "<!-- TASK-RECORD BP-0001 BEGIN -->\n" + block("BP-0002", "nested"),
            "<!-- TASK-RECORD BP-0001 BEG -->\n",
        ]
        for value in cases:
            with self.subTest(value=value):
                self.write(value)
                with self.assertRaises(ValueError): read_record(self.path, "BP-0001")

    def test_output_budget_never_silently_truncates(self):
        self.write(block("BP-0001", "x" * 200))
        with self.assertRaisesRegex(ValueError, "exceeds"):
            read_record(self.path, "BP-0001", 100)
        self.assertEqual(read_record(self.path, "BP-0001", 1000).text, block("BP-0001", "x" * 200))

    def test_invalid_id_is_rejected_before_opening_any_file(self):
        for record_id in ("BP-0001|BP-0002", "", "BP-0001\n"):
            with self.subTest(record_id=record_id):
                with self.assertRaisesRegex(ValueError, "Invalid record ID"):
                    read_record(self.path, record_id)


if __name__ == "__main__":
    unittest.main()
