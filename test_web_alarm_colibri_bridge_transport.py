"""Independent WUA-side tests, no network or live profile."""
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from web_alarm.colibri_bridge_transport import (
    BridgeFault, Contract, SSEDecoder, OfflineColibriTransport, strict_json, canonical,
    _discover,
)


class DecodeTests(unittest.TestCase):
    def test_split_utf8_multiline_comments_crlf(self):
        text = ': heartbeat\r\nevent: delta\r\nid: 1\r\ndata: {"type":"delta",\r\ndata: "text":"Привет 🌊","sequence":1}\r\n\r\n'
        dec = SSEDecoder()
        events = []
        for b in text.encode("utf-8"):
            events.extend(dec.feed(bytes([b])))
        dec.eof()
        self.assertEqual(events, [("delta", "1", {"type":"delta","text":"Привет 🌊","sequence":1})])

    def test_malformed_and_truncated_refuse(self):
        for raw in (b'event: meta\nevent: delta\nid: 0\ndata: {}\n\n',
                    b'event: delta\nid: 0\ndata: {"a":1,"a":2}\n\n',
                    b'event: delta\nid: 0\ndata: \xff\n\n',
                    b'event: delta\nid: 0\ndata: {}\n'):
            with self.subTest(raw=raw), self.assertRaises(BridgeFault):
                d = SSEDecoder()
                list(d.feed(raw))
                d.eof()

    def test_usage_raw_nullable_and_derived(self):
        c = Contract()
        u = dict(status="partial",source="provider_and_derived_total",prompt_basis="unknown",
                 prompt_tokens=0,completion_tokens=7,total_tokens=7,reasoning_tokens=None,cached_prompt_tokens=None)
        self.assertEqual(c.check("Usage",u),u)
        for bad in ({**u,"total_tokens":8}, {**u,"status":"reported"},
                    {**u,"reasoning_tokens":8}, {**u,"prompt_tokens":True}):
            with self.subTest(bad=bad), self.assertRaises(BridgeFault):
                c.check("Usage",bad)
        raw = {**u,"source":"unavailable","status":"unavailable",**{k:None for k in
            ("prompt_tokens","completion_tokens","total_tokens","reasoning_tokens","cached_prompt_tokens")}}
        self.assertEqual(c.check("Usage",raw),raw)

    def test_discovery_strict_loopback_and_expected_identity(self):
        with TemporaryDirectory() as td:
            p = Path(td).resolve()
            token = p/"bridge-wua.token"
            token.write_text("X"*64,encoding="ascii")
            token.chmod(0o600)
            d = p/"bridge-discovery.json"
            value=dict(bridge_id="a"*32,protocol_version="1.0.0",origin="http://127.0.0.1:12345",
                       credential_ref="bridge-wua.token",launch_identity="b"*32)
            for delta in ({"origin":"http://localhost:12345"},{"origin":"http://127.0.0.1:12345@evil.test"},
                          {"origin":"http://127.0.0.1:65536"},{"bridge_id":"c"*32},
                          {"protocol_version":"2.0.0"},{"credential_ref":"../token"},
                          {"launch_identity":"not-an-id"}):
                d.write_bytes(canonical({**value,**delta}));d.chmod(0o600)
                with self.subTest(delta=delta),self.assertRaises(BridgeFault):
                    _discover(p,"a"*32)
            d.write_bytes(canonical(value))
            self.assertNotIn("X"*64,repr(_discover(p,"a"*32)))
        with self.assertRaises(BridgeFault):
            OfflineColibriTransport(Path(__file__).parent,expected_bridge_id="a"*32)
