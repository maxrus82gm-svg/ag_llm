"""Additional checks, separate from the sealed 69-method MANIFEST. Mutations stay in memory."""
import ast
import asyncio
from contextlib import ExitStack
from functools import lru_cache
import io
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import test_rt002_s1_routes as s1

# Pure analysis is keyed by both module identity and complete source bytes, never by a mutable path.
s1.analyze_module = lru_cache(maxsize=512)(s1.analyze_module)

ROOT = s1.ROOT
OBSERVATIONS = {}
SOURCES = {p.relative_to(ROOT).as_posix(): p.read_text(encoding="utf-8") for p in s1._production_modules()}


class MemoryModule:
    def __init__(self, name, source):
        self.name, self.source = Path(name).name, source

    def read_text(self, **_):
        return self.source


def oracle(sources):
    """Run the TWO ACTUAL production inventory/endpoint tests against in-memory source."""
    modules = [MemoryModule(k, v) for k, v in sources.items()]
    suite = unittest.TestSuite(s1.StaticRouteInventoryTests(name) for name in (
        "test_production_send_sites_match_inventory_with_multiplicity",
        "test_every_endpoint_constant_read_is_an_inventoried_send_url"))
    result = unittest.TestResult()
    with patch.object(s1, "_production_modules", return_value=modules):
        suite.run(result)
    assert not result.errors, result.errors
    assert result.testsRun == 2 and not result.skipped, (result.testsRun, result.skipped)
    return [{"test": t._testMethodName, "failure": text} for t, text in result.failures]


def changed(module, old, new):
    module = module if module in SOURCES else "web_alarm/" + module
    assert SOURCES[module].count(old) == 1, (module, old)
    return {**SOURCES, module: SOURCES[module].replace(old, new, 1)}


def cases():
    additions = {
        "additional_llm_post": "\nasync def _extra_llm():\n    async with httpx.AsyncClient() as client:\n        return await client.post(CHAT_URL)\n",
        "additional_oauth_post": "\nasync def _extra_oauth():\n    async with httpx.AsyncClient() as client:\n        return await client.post(OAUTH_URL)\n",
        "alias_send": "\nasync def _alias():\n    async with httpx.AsyncClient() as client:\n        sender = client.post\n        return await sender(CHAT_URL)\n",
        "getattr_send": "\nasync def _reflected():\n    async with httpx.AsyncClient() as client:\n        return await getattr(client, 'post')(CHAT_URL)\n",
    }
    output = {key: {**SOURCES, "server.py": SOURCES["server.py"] + value} for key, value in additions.items()}
    output["external_host"] = changed("launcher.py", 'HOST = "127.0.0.1"', 'HOST = "provider.invalid"')
    output["external_health_caller"] = {**SOURCES, "web_alarm/launcher.py": SOURCES["web_alarm/launcher.py"].replace(
        '_get(url + "status")', '_get("https://provider.invalid/status")', 1)}
    output["metadata_becomes_network"] = changed("model_cards.py", 'api_url="https://api.giga.chat/v1/chat/completions"',
        'api_url=__import__("httpx").post("https://api.giga.chat/v1/chat/completions")')
    output["metadata_field_becomes_network"] = {**SOURCES, "web_alarm/model_cards.py": SOURCES["web_alarm/model_cards.py"] +
        '\nasync def _metadata_send(http):\n    return await http.post(BUILTIN_PROVIDERS["gigachat"].api_url)\n'}
    tree = ast.parse(SOURCES["web_alarm/model_cards.py"])
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "ModelCards")
    method = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == "catalog")
    method.body[-1] = ast.parse('return http.post(providers[0]["api_url"])').body[0]
    output["metadata_consumer_indirection"] = {**SOURCES, "web_alarm/model_cards.py": ast.unparse(tree) + "\n"}
    output["duplicate_physical_send"] = changed("ordinary_chat_service.py",
        'return await transport.send(request.payload, timeout_seconds=timeout_seconds)',
        'await transport.send(request.payload, timeout_seconds=timeout_seconds)\n            return await transport.send(request.payload, timeout_seconds=timeout_seconds)')
    output["new_unknown_transport"] = {**SOURCES, "synthetic.py":
        'async def _unknown(transport):\n    return await transport.send({})\n'}
    output["new_unknown_transport_alias"] = {**SOURCES, "synthetic.py":
        'async def _unknown(transport):\n    sender = transport.send\n    return await sender({})\n'}
    output["new_unknown_transport_getattr"] = {**SOURCES, "synthetic.py":
        'async def _unknown(transport):\n    return await getattr(transport, "send")({})\n'}
    output["new_unknown_caller"] = {**SOURCES, "synthetic.py":
        'import ordinary_chat_service as chat\nasync def _unknown(request, transport):\n    return await chat.execute_request(request, transport=transport)\n'}
    output["new_launcher_caller"] = {**SOURCES, "synthetic.py":
        'from web_alarm.launcher import _get as fetch\ndef _unknown():\n    return fetch("https://provider.invalid/")\n'}
    output["new_run_web_alarm_caller"] = {**SOURCES, "synthetic.py":
        'from web_alarm.launcher import run_web_alarm\ndef _unknown(launch, out):\n    return run_web_alarm(launch, out=out, colors=False, port="54321@provider.invalid")\n'}
    output["port_validation_removed"] = changed("launcher.py", 'if not raw.isdigit() or not 1024 <= int(raw) <= 65535:',
        'if False:')
    output["extra_metadata_literal"] = {**SOURCES, "synthetic.py":
        'METADATA = {"api_url": "https://api.giga.chat/v1/chat/completions"}\n'}
    return output


class ReconciliationNegativeTests(unittest.TestCase):
    def test_nominal_and_whitespace_control(self):
        self.assertEqual(oracle(SOURCES), [])
        self.assertEqual(oracle({name: "\n# no semantic change\n" + text for name, text in SOURCES.items()}), [])

    def check_mutation(self, name):
        failures = oracle(cases()[name])
        OBSERVATIONS[name] = failures
        self.assertTrue(failures, name + " escaped the real S1 oracle")


for _name in cases():
    setattr(ReconciliationNegativeTests, "test_" + _name,
            lambda self, name=_name: self.check_mutation(name))


class FakeExecutionTests(unittest.TestCase):
    def test_launcher_port_sources_reject_url_injection(self):
        from web_alarm import launcher as launch
        import os
        for value in ["54321@provider.invalid", "https://provider.invalid", "0", "65536"]:
            with self.subTest(value=value), patch.dict(os.environ, {"WEB_ALARM_PORT": value}), self.assertRaises(launch.LaunchConfigError):
                launch.standard_port()
        for value in [True, "54321@provider.invalid", "54321", 0, 65536]:
            with self.subTest(profile_port=value), self.assertRaises(launch.LaunchConfigError):
                launch._profile("synthetic", {"kind": "web_alarm", "title": "synthetic", "storage": "temp", "port": value})

    def test_launcher_get_and_all_url_callers_without_http(self):
        from web_alarm import launcher as launch
        seen = []
        page = "synthetic UI"
        storage = SANDBOX / "synthetic_storage"

        class Response:
            status = 200

            def __init__(self, request):
                self.request = request

            def __enter__(self): return self
            def __exit__(self, *_): return False

            def read(self):
                return json.dumps({"storage_root": str(storage), "service": "Web Alarm"}).encode() if self.request.full_url.endswith("status") else (
                    b'{"ultra_chat":{"available":true}}' if self.request.full_url.endswith("capability") else page.encode())

        def fake_open(request, **kwargs):
            seen.append({"url": request.full_url, "method": request.get_method(), "timeout": kwargs["timeout"]})
            self.assertEqual(request.get_method(), "GET")
            self.assertEqual(request.get_header("Cache-control"), "no-store")
            return Response(request)

        fake_thread = SimpleNamespace(start=lambda: None, join=lambda _: None, is_alive=lambda: False)
        server = SimpleNamespace(serve_forever=lambda: None, server_port=54321, shutdown=lambda: None, server_close=lambda: None)
        with patch.object(launch.urllib.request, "urlopen", side_effect=fake_open), patch.object(
                launch, "default_storage_root", return_value=storage), patch.object(launch.threading, "Thread", return_value=fake_thread):
            self.assertEqual(launch._already_running("http://127.0.0.1:54321/", page, storage), "same")
            self.assertEqual(launch._already_running("http://127.0.0.1:54321/", page, None), "other")
            self.assertEqual(launch._self_test(server, launch.standard_launch(), "http://127.0.0.1:54321/", page,
                str(storage), SANDBOX / "launcher_self_test.json", io.StringIO()), 0)
        self.assertEqual([s["url"] for s in seen], ["http://127.0.0.1:54321/status", "http://127.0.0.1:54321/",
            "http://127.0.0.1:54321/status", "http://127.0.0.1:54321/", "http://127.0.0.1:54321/ui/ultra-chat/capability"])
        with ExitStack() as stack:
            for name, value in [("_claim_port", SimpleNamespace(release=lambda: None)), ("_port_in_use", False),
                                ("WebAlarmApi", object()), ("create_server", server), ("_self_test", 0),
                                ("default_storage_root", storage), ("set_console_title", None)]:
                stack.enter_context(patch.object(launch, name, return_value=value))
            check = launch._self_test
            self.assertEqual(launch.run_web_alarm(launch.standard_launch(), out=io.StringIO(), colors=False,
                open_browser=False, self_test=SANDBOX / "unused", port=54321), 0)
            self.assertEqual(check.call_args.args[2], "http://127.0.0.1:54321/")
            stack.enter_context(patch.object(launch, "_port_in_use", return_value=True))
            reuse = stack.enter_context(patch.object(launch, "_already_running", return_value="same"))
            self.assertEqual(launch.run_web_alarm(launch.standard_launch(), out=io.StringIO(), colors=False,
                open_browser=False, port=54321), 0)
            self.assertEqual(reuse.call_args.args[0], "http://127.0.0.1:54321/")
        OBSERVATIONS["fake_launcher"] = {"requests": seen, "physical_calls": 0, "all_get_callers": True}

    def test_metadata_default_checker_does_not_send(self):
        from web_alarm import model_cards as cards
        provider = cards.BUILTIN_PROVIDERS["gigachat"]
        self.assertEqual(provider.api_url, "https://api.giga.chat/v1/chat/completions")
        self.assertEqual(provider.oauth_url, "https://ngw.devices.sberbank.ru:9443/api/v2/oauth")
        service = cards.ModelCards(SANDBOX / "cards", object(), tk_state_path=None, environ={})
        self.assertFalse(service.checker.authorized)
        with patch.object(service, "_context", return_value={"registry": object()}), patch.object(
                service, "_spec", return_value=SimpleNamespace(enabled=True)), patch.object(
                service, "_card", return_value={"api": {"reason": "UNCHECKED"}}), patch.object(
                service.checker, "check", side_effect=AssertionError("checker must not run")) as check:
            result = service.run_check("synthetic")
        check.assert_not_called()
        self.assertEqual(result["outcome"], "LIVE_CHECK_NOT_AUTHORIZED")
        self.assertEqual(result["network_calls"], 0)
        OBSERVATIONS["metadata"] = {"default_check": result["outcome"], "network_calls": 0,
                                    "injected_authorized_checker": "potential physical boundary; no live approval"}

    def test_ordinary_transport_is_one_injected_invocation(self):
        import ordinary_chat_service as chat
        prepared = chat.prepare_request(model_id="gigachat_2", context=[], user_text="synthetic",
            context_ref="S1_SYNTHETIC", limits=chat.RequestLimits(4, 1024, 4096, 4096, 8, 1))
        calls = []

        class FakeTransport:
            async def send(self, payload, *, timeout_seconds):
                calls.append((payload, timeout_seconds))
                return {"choices": [{"message": {"role": "assistant", "content": "synthetic"}, "finish_reason": "stop"}],
                        "usage": {"prompt_tokens": 3, "completion_tokens": 2, "total_tokens": 5}}

        result = asyncio.run(chat.execute_request(prepared, transport=FakeTransport()))
        self.assertEqual(len(calls), 1)
        self.assertEqual(result.outcome, chat.Outcome.COMPLETED)
        OBSERVATIONS["ordinary_chat"] = {"injected_calls": 1, "physical_calls": 0, "classification": "POTENTIAL_LLM"}


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "weaken_unknown":
        original = s1.analyze_module
        def weakened(*args):
            result = original(*args)
            result["sites"] = [s for s in result["sites"] if not (s["traffic"] == "UNKNOWN" and s["kind"] == "dynamic.send")]
            return result
        s1.analyze_module = weakened
    elif mode == "weaken_local":
        original = s1._reconciliation
        s1._reconciliation = lambda name, tree: (True, set(), []) if name == "launcher.py" else original(name, tree)
    elif mode == "weaken_metadata":
        original = s1.unexplained_endpoint_reads
        s1.unexplained_endpoint_reads = lambda *args: [u for u in original(*args) if u[-1] != "endpoint host literal"]
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]))
    print(json.dumps({"mode": mode, "counts": {"run": result.testsRun, "fail": len(result.failures), "error": len(result.errors),
        "skip": len(result.skipped)}, "isolation_violations": s1._GUARD_VIOLATIONS, "observations": OBSERVATIONS}, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result.wasSuccessful() and not s1._GUARD_VIOLATIONS else 1)
