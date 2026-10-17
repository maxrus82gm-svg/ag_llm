"""Parser robustness tests; these are NOT native proxy/fail-closed tests."""
import unittest
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location('audited_static_parser', Path(__file__).with_name('static_audit.py'))
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)
build_info, go_string, pe_header, uvarint = audit.build_info, audit.go_string, audit.pe_header, audit.uvarint


class StaticParserTests(unittest.TestCase):
    def test_go_inline_frame_independent_fixture(self):
        version = b'go.fixture'
        module = b'x' * 16 + b'path\tfixture/main\nmod\tfixture\t(devel)\t\n' + b'y' * 16
        data = (b'\xff Go buildinf:' + bytes([8, 2]) + bytes(16) +
                bytes([len(version)]) + version + bytes([len(module)]) + module)
        result = build_info(data)
        self.assertEqual(result['go_version'], 'go.fixture')
        self.assertEqual(result['records'][0], ['path', 'fixture/main'])
        self.assertFalse(result['vcs_settings_present'])

    def test_truncated_string_rejected(self):
        with self.assertRaisesRegex(ValueError, 'truncated Go string'):
            go_string(bytes([12]) + b'ab', 0)

    def test_unterminated_varint_rejected(self):
        with self.assertRaisesRegex(ValueError, 'truncated uvarint'):
            uvarint(b'\x80', 0)

    def test_overflow_varint_rejected(self):
        with self.assertRaisesRegex(ValueError, 'overflow uvarint'):
            uvarint(b'\xff' * 10, 0)

    def test_corrupt_pe_offset_rejected(self):
        data = bytearray(64)
        data[:2] = b'MZ'
        data[60:64] = b'\xff' * 4
        with self.assertRaisesRegex(ValueError, 'invalid PE signature'):
            pe_header(bytes(data))


if __name__ == '__main__':
    unittest.main(verbosity=2)
