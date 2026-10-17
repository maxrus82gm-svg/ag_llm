"""TLS/CONNECT reference-policy tests. This is NOT the Go tunnel-client transport.

All sockets belong to this disposable Python process. An audit hook rejects
non-loopback destinations, unowned ports, hostname DNS, and child processes.
The real tunnel-client is deliberately not launched by this suite.
"""
import datetime
from contextlib import closing
import hashlib
import http.client
import http.server
import ipaddress
import json
from pathlib import Path
import select
import socket
import socketserver
import ssl
import sys
import tempfile
import threading
import time
from urllib.parse import urlsplit
import urllib.request

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

HERE = Path(__file__).resolve().parent
OWN_PORTS = set()
EVENTS = []
LOCAL = threading.local()
LOCK = threading.Lock()
RESULTS = []


class PolicyError(RuntimeError):
    pass


def record(kind, **data):
    with LOCK:
        EVENTS.append({"kind": kind, "role": getattr(LOCAL, "role", "harness"),
                       "case": getattr(LOCAL, "case", "setup"), **data})


def audit(event, args):
    if event == "subprocess.Popen":
        raise PolicyError("ISOLATION_CHILD_PROCESS_DENIED")
    if event == "socket.getaddrinfo":
        if args[0] != "127.0.0.1":
            raise PolicyError("ISOLATION_HOSTNAME_DNS_DENIED")
        record("literal_address_resolution")
    if event == "socket.bind":
        address = args[1]
        if not isinstance(address, tuple) or address[0] != "127.0.0.1" or address[1] != 0:
            raise PolicyError("ISOLATION_BIND_DENIED")
    if event == "socket.connect":
        address = args[1]
        if not isinstance(address, tuple) or address[0] != "127.0.0.1" or address[1] not in OWN_PORTS:
            raise PolicyError("ISOLATION_CONNECT_DENIED")
        record("connect_attempt", host=address[0], port=address[1])


def certificate(directory):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "WUA disposable loopback fixture")])
    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key())
            .serial_number(x509.random_serial_number()).not_valid_before(now - datetime.timedelta(minutes=1))
            .not_valid_after(now + datetime.timedelta(hours=1))
            .add_extension(x509.SubjectAlternativeName([x509.IPAddress(ipaddress.ip_address("127.0.0.1"))]), critical=False)
            .sign(key, hashes.SHA256()))
    private = directory / "synthetic-key.pem"
    public = directory / "synthetic-cert.pem"
    private.write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                         serialization.NoEncryption()))
    public.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    server = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    server.load_cert_chain(public, private)
    client = ssl.create_default_context(cafile=str(public))
    return server, client, hashlib.sha256(public.read_bytes()).hexdigest()


class Origin(http.server.BaseHTTPRequestHandler):
    def setup(self):
        self.request.settimeout(1.0)
        super().setup()

    def log_message(self, *_):
        pass

    def do_GET(self):
        LOCAL.role = "origin"
        LOCAL.case = self.path.split("/")[1] if "/" in self.path else "unknown"
        record("origin_request", path=self.path, peer_port=self.client_address[1], server_port=self.server.server_port)
        if self.path.endswith("/redirect"):
            self.send_response(302)
            self.send_header("Location", "https://127.0.0.1:" + str(self.server.other_port) + "/" + LOCAL.case + "/ok")
            body = b"redirect"
        else:
            self.send_response(200)
            body = b"synthetic-loopback-only"
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class Server(socketserver.ThreadingTCPServer):
    daemon_threads = False
    block_on_close = True
    allow_reuse_address = False

    def handle_error(self, *_):
        record("server_handler_error", error_type=sys.exc_info()[0].__name__, error_message=str(sys.exc_info()[1]))


class TLSOrigin(http.server.ThreadingHTTPServer):
    daemon_threads = False
    block_on_close = True

    def get_request(self):
        raw, address = super().get_request()
        raw.settimeout(1.0)
        try:
            return self.tls_context.wrap_socket(raw, server_side=True), address
        except BaseException:
            raw.close()
            raise

    def handle_error(self, *_):
        record("origin_handler_error", error_type=sys.exc_info()[0].__name__, error_message=str(sys.exc_info()[1]))


class Proxy(socketserver.StreamRequestHandler):
    def handle(self):
        LOCAL.role, LOCAL.case = "proxy", self.server.case
        self.connection.settimeout(1.0)
        line = self.rfile.readline(4096).decode("ascii")
        for _ in range(32):
            if self.rfile.readline(4096) in {b"\r\n", b"\n", b""}:
                break
        with self.server.lock:
            self.server.accepted += 1
            number = self.server.accepted
        record("proxy_connect_received", request=line.strip(), ordinal=number, mode=self.server.mode)
        self.server.reached.set()
        if self.server.mode == "reject":
            self.wfile.write(b"HTTP/1.1 503 Synthetic refusal\r\nContent-Length: 0\r\n\r\n")
            return
        if self.server.mode == "timeout":
            self.server.release.wait(1.5)
            return
        if self.server.mode == "close" or (self.server.mode == "drop_after_success" and number > 1):
            record("proxy_injected_disconnect")
            return
        if self.server.mode == "redirect":
            self.wfile.write(b"HTTP/1.1 302 Found\r\nLocation: https://127.0.0.1/\r\nContent-Length: 0\r\n\r\n")
            return
        method, authority, _ = line.split()
        host, port = authority.split(":")
        port = int(port)
        if method != "CONNECT" or host != "127.0.0.1" or port not in self.server.targets:
            raise PolicyError("PROXY_TARGET_NOT_OWNED")
        with socket.create_connection((host, port), timeout=0.7) as target:
            record("proxy_forward_socket", local_port=target.getsockname()[1], target_port=port)
            self.wfile.write(b"HTTP/1.1 200 Connection established\r\n\r\n")
            self.wfile.flush()
            sockets = [self.connection, target]
            deadline = time.monotonic() + 2
            while time.monotonic() < deadline and not self.server.release.is_set():
                readable, _, _ = select.select(sockets, [], [], 0.05)
                for source in readable:
                    data = source.recv(65536)
                    if not data:
                        return
                    (target if source is self.connection else self.connection).sendall(data)


def start(server):
    OWN_PORTS.add(server.server_address[1])
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.03}, daemon=True)
    thread.start()
    return thread


def stop(server, thread):
    owned_port = server.server_address[1]
    if hasattr(server, "release"):
        server.release.set()
    server.shutdown()
    server.server_close()
    thread.join(2)
    if thread.is_alive():
        raise RuntimeError("OWN_SERVER_NOT_REAPED")
    OWN_PORTS.discard(owned_port)


class ReferenceProxyOnlyClient:
    """Explicit test policy; does not represent the implementation of tunnel-client."""
    def __init__(self, proxy_port, context, targets, *, overrides=None, extra_transports=None):
        if proxy_port not in OWN_PORTS:
            raise PolicyError("EXPLICIT_PROXY_REQUIRED")
        if extra_transports:
            raise PolicyError("EXTRA_TRANSPORT_NOT_APPROVED")
        if any(value != proxy_port for value in (overrides or {}).values()):
            raise PolicyError("CONFLICTING_COMPONENT_PROXY")
        self.port, self.context, self.targets = proxy_port, context, set(targets)

    def fetch(self, url, *, retries=0, environment=None):
        # Ambient NO_PROXY/HTTP(S)_PROXY must not override this explicit test policy.
        for redirect in range(3):
            parsed = urlsplit(url)
            if parsed.scheme != "https" or parsed.hostname != "127.0.0.1" or parsed.port not in self.targets:
                raise PolicyError("TARGET_NOT_OWNED_LITERAL_LOOPBACK")
            for attempt in range(retries + 1):
                try:
                    with closing(http.client.HTTPSConnection("127.0.0.1", self.port, timeout=0.3, context=self.context)) as conn:
                        conn.set_tunnel("127.0.0.1", parsed.port)
                        conn.request("GET", parsed.path or "/")
                        response = conn.getresponse()
                        data = response.read(4096)
                        location = response.getheader("Location")
                        status = response.status
                    break
                except (OSError, http.client.HTTPException):
                    if attempt == retries:
                        raise
            if status not in {301, 302, 303, 307, 308}:
                return status, data
            if not location:
                raise PolicyError("REDIRECT_LOCATION_MISSING")
            url = location
        raise PolicyError("REDIRECT_LIMIT")


def oracle(events, proxy_port):
    attempts = [e for e in events if e["kind"] == "connect_attempt" and e["role"] == "client"]
    return bool(attempts) and all(e["host"] == "127.0.0.1" and e["port"] == proxy_port for e in attempts)


def run_case(name, mode, action, expected, targets, context, *, refused=False, quality=False):
    LOCAL.role, LOCAL.case = "client", name
    before = len(EVENTS)
    reservation = None
    server = thread = None
    if refused:
        reservation = socket.socket()
        reservation.bind(("127.0.0.1", 0))
        port = reservation.getsockname()[1]
        OWN_PORTS.add(port)  # Bound but never listening: cannot be reused by another application.
    else:
        server = Server(("127.0.0.1", 0), Proxy)
        server.case, server.mode, server.targets = name, mode, targets
        server.lock, server.reached, server.release = threading.Lock(), threading.Event(), threading.Event()
        server.accepted = 0
        thread = start(server)
        port = server.server_address[1]
    error = None
    error_message = None
    value = None
    try:
        value = action(port)
    except (OSError, http.client.HTTPException, PolicyError) as exc:
        error = type(exc).__name__
        error_message = str(exc)
    finally:
        if server:
            stop(server, thread)
        if reservation:
            reservation.close()
            OWN_PORTS.discard(port)
    events = EVENTS[before:]
    attempts = [e for e in events if e["kind"] == "connect_attempt" and e["role"] == "client"]
    origins = [e for e in events if e["kind"] == "origin_request"]
    proxy_reached = any(e["kind"] == "proxy_connect_received" for e in events)
    accepted_policy = oracle(events, port)
    forward_ports = {e["local_port"] for e in events if e["kind"] == "proxy_forward_socket"}
    origin_path_correlated = all(e["peer_port"] in forward_ports for e in origins)
    if expected == "success":
        good = value and value[0] == 200 and error is None and proxy_reached and origins and accepted_policy and origin_path_correlated
    elif expected == "refusal":
        good = error is not None and not origins and accepted_policy and (refused or proxy_reached)
    elif expected == "policy_rejection":
        codes = {"S11_component_override_rejected": "CONFLICTING_COMPONENT_PROXY",
                 "S12_missing_explicit_proxy": "EXPLICIT_PROXY_REQUIRED",
                 "S13_hostname_dns_rejected": "TARGET_NOT_OWNED_LITERAL_LOOPBACK",
                 "S14_extra_transport_rejected": "EXTRA_TRANSPORT_NOT_APPROVED"}
        good = error == "PolicyError" and error_message == codes[name] and not attempts and not origins
    elif expected == "quality_detect_direct":
        good = bool(origins) and not accepted_policy and any(e["port"] in targets for e in attempts)
    elif expected == "drop_after_success":
        good = error is not None and len(origins) == 1 and accepted_policy and origin_path_correlated and sum(e["kind"] == "proxy_injected_disconnect" for e in events) == 2
    else:
        raise RuntimeError("Unknown expected oracle")
    fixture_errors = [e for e in events if "handler_error" in e["kind"]]
    unexpected_errors = [e for e in fixture_errors if not (
        name == "S15_untrusted_tls_rejected" and e["error_type"] in {"ConnectionResetError", "BrokenPipeError"})]
    good = good and not unexpected_errors
    row = {"id": name, "status": "PASS" if good else "FAIL", "layer": "QUALITY" if quality else "ISOLATED_REFERENCE_MODEL",
           "mode": mode, "expected": expected, "error_type": error, "error_message": error_message, "client_connect_attempts": len(attempts),
           "proxy_fault_reached": proxy_reached, "origin_http_requests": len(origins),
           "proxy_only_oracle": accepted_policy, "events": events,
           "origin_peer_correlated_with_proxy_forward_socket": origin_path_correlated,
           "expected_fixture_error_count": len(fixture_errors) - len(unexpected_errors),
           "unexpected_fixture_error_count": len(unexpected_errors),
           "real_tunnel_client_test": False}
    RESULTS.append(row)
    print(json.dumps({k: v for k, v in row.items() if k != "events"}), flush=True)
    if (error_message and error_message.startswith("ISOLATION_")) or any(e.get("error_type") == "PolicyError" for e in fixture_errors):
        (HERE / "isolation_stop.json").write_text(json.dumps(row, indent=2) + "\n", encoding="utf-8")
        raise RuntimeError("ISOLATION_BOUNDARY_ATTEMPT; test execution stopped")


def main():
    temp = tempfile.TemporaryDirectory(prefix="wua-a05-loopback-")
    directory = Path(temp.name).resolve()
    if not directory.is_relative_to(Path(tempfile.gettempdir()).resolve()) or not directory.name.startswith("wua-a05-loopback-"):
        raise RuntimeError("TEMP_SCOPE_INVALID")
    server_context, client_context, cert_sha = certificate(directory)
    sys.addaudithook(audit)
    origins = []
    try:
        for _ in range(2):
            server = TLSOrigin(("127.0.0.1", 0), Origin)
            server.tls_context = server_context
            origins.append((server, start(server)))
        targets = [s.server_port for s, _ in origins]
        origins[0][0].other_port = targets[1]
        origins[1][0].other_port = targets[0]
        def url(case, ending="ok"):
            return "https://127.0.0.1:" + str(targets[0]) + "/" + case + "/" + ending
        def client(port, **kwargs):
            return ReferenceProxyOnlyClient(port, client_context, targets, **kwargs)
        run_case("S01_success", "forward", lambda p: client(p).fetch(url("S01_success")), "success", targets, client_context)
        run_case("S02_port_not_listening", "refused", lambda p: client(p).fetch(url("S02_port_not_listening")), "refusal", targets, client_context, refused=True)
        run_case("S03_explicit_refusal", "reject", lambda p: client(p).fetch(url("S03_explicit_refusal")), "refusal", targets, client_context)
        run_case("S04_accept_then_close", "close", lambda p: client(p).fetch(url("S04_accept_then_close")), "refusal", targets, client_context)
        run_case("S05_timeout", "timeout", lambda p: client(p).fetch(url("S05_timeout")), "refusal", targets, client_context)
        run_case("S06_retry_refused", "refused", lambda p: client(p).fetch(url("S06_retry_refused"), retries=2), "refusal", targets, client_context, refused=True)
        def disconnected(port):
            c = client(port)
            c.fetch(url("S07_drop_after_success"))
            return c.fetch(url("S07_drop_after_success"), retries=1)
        run_case("S07_drop_after_success", "drop_after_success", disconnected, "drop_after_success", targets, client_context)
        run_case("S08_origin_redirect", "forward", lambda p: client(p).fetch(url("S08_origin_redirect", "redirect")), "success", targets, client_context)
        run_case("S09_proxy_redirect_rejected", "redirect", lambda p: client(p).fetch(url("S09_proxy_redirect_rejected")), "refusal", targets, client_context)
        for suffix, bypass in [("all", "*"), ("literal", "127.0.0.1"), ("named", "localhost,api.openai.com")]:
            name = "S10_no_proxy_" + suffix
            run_case(name, "forward", lambda p, n=name, v=bypass: client(p).fetch(url(n), environment={"NO_PROXY": v, "HTTP_PROXY": "DIRECT", "HTTPS_PROXY": "DIRECT"}), "success", targets, client_context)
        run_case("S11_component_override_rejected", "forward", lambda p: client(p, overrides={"control-plane": targets[0]}), "policy_rejection", targets, client_context)
        run_case("S12_missing_explicit_proxy", "forward", lambda p: ReferenceProxyOnlyClient(None, client_context, targets), "policy_rejection", targets, client_context)
        run_case("S13_hostname_dns_rejected", "forward", lambda p: client(p).fetch("https://localhost:" + str(targets[0]) + "/S13_hostname_dns_rejected/ok"), "policy_rejection", targets, client_context)
        run_case("S14_extra_transport_rejected", "forward", lambda p: client(p, extra_transports=["quic"]), "policy_rejection", targets, client_context)
        untrusted_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)  # No trust anchors, no system changes.
        run_case("S15_untrusted_tls_rejected", "forward", lambda p: ReferenceProxyOnlyClient(p, untrusted_context, targets).fetch(url("S15_untrusted_tls_rejected")), "refusal", targets, client_context)
        def broken_direct(name):
            with closing(http.client.HTTPSConnection("127.0.0.1", targets[0], context=client_context, timeout=0.5)) as c:
                c.request("GET", "/" + name + "/ok")
                response = c.getresponse()
                return response.status, response.read(4096)
        def broken_fallback(port):
            try:
                return client(port).fetch(url("Q01_direct_fallback_detected"))
            except (OSError, http.client.HTTPException):
                return broken_direct("Q01_direct_fallback_detected")
        run_case("Q01_direct_fallback_detected", "close", broken_fallback, "quality_detect_direct", targets, client_context, quality=True)
        def ambient_bypass(port):
            if not urllib.request.proxy_bypass_environment("127.0.0.1", proxies={"no": "*"}):
                raise RuntimeError("NO_PROXY_COUNTEREXAMPLE_NOT_REACHED")
            return broken_direct("Q02_ambient_no_proxy_detected")
        run_case("Q02_ambient_no_proxy_detected", "forward", ambient_bypass, "quality_detect_direct", targets, client_context, quality=True)
    finally:
        for server, thread in origins:
            stop(server, thread)
        # The resolved owned TEMP target was checked before creation/use. It has
        # only our disposable certificate/key; no live paths or symlinks.
        temp.cleanup()
    outcome = {"suite": "ISOLATED TLS/CONNECT REFERENCE POLICY; NOT tunnel-client",
               "collected": len(RESULTS), "pass": sum(r["status"] == "PASS" for r in RESULTS),
               "fail": sum(r["status"] == "FAIL" for r in RESULTS), "error": 0, "skip": 0,
               "results": RESULTS, "certificate_sha256": cert_sha,
               "synthetic_private_key_published": False, "temporary_fixture_removed": not directory.exists(),
               "resource_cleanup": {"owned_ports_remaining": len(OWN_PORTS), "serving_and_handler_threads_joined": True},
               "isolation": {"all_connected_hosts": sorted({e["host"] for e in EVENTS if e["kind"] == "connect_attempt"}),
                    "child_processes": 0, "external_requests": 0, "existing_v2ray_listener_used": False,
                    "guard": "Python audit: literal loopback, process-owned ports, no hostname resolution, no subprocess"},
               "real_client_fail_closed": "NOT VERIFIED", "ordinary_chat_e2e": "NOT VERIFIED"}
    (HERE / "isolated_results.json").write_text(json.dumps(outcome, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in outcome.items() if k != "results"}), flush=True)
    return 0 if outcome["fail"] == 0 and outcome["collected"] > 0 and not OWN_PORTS and not directory.exists() else 1


if __name__ == "__main__":
    raise SystemExit(main())
