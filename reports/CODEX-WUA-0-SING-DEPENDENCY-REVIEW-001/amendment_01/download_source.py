"""Single authorized module ZIP acquisition through existing HTTP CONNECT only.

No redirect, retry, ambient proxy bypass, credentials, Go, subprocess or direct DNS.
Reuses the explicit HTTPSConnection/set_tunnel pattern of the prior source task.
An application audit hook constrains this Python process; it is not OS WFP proof.
"""
from pathlib import Path
import datetime, hashlib, http.client, json, ssl, sys, urllib.parse, urllib.request

OUT = Path(__file__).resolve().parent
DEST = Path('M:/WUA_SOURCE_REVIEW/sing/v0.8.3-0.20260315153529-ed51f65fbfde')
URL = 'https://proxy.golang.org/github.com/sagernet/sing/@v/v0.8.3-0.20260315153529-ed51f65fbfde.zip'
ADDRESS = ('127.0.0.1', 10808)


def main():
    evidence = OUT / 'evidence'
    receipt_path = evidence / 'download_receipt.json'
    reservation = evidence / 'download_attempt.json'
    # The exclusive reservation is written before any socket operation, retained on failure.
    if reservation.exists() or receipt_path.exists():
        raise SystemExit('ONE_ATTEMPT_ONLY: existing receipt/reservation retained')
    pre = json.loads((evidence / 'proxy_preflight.json').read_text(encoding='utf-8-sig'))
    assert len(pre['listeners']) == 1
    listener = pre['listeners'][0]
    assert listener['local_address'] == ADDRESS[0] and listener['local_port'] == ADDRESS[1]
    assert listener['process_name'] == 'sing-box'
    assert (OUT / 'USER_GO.md').is_file()
    proxies = urllib.request.getproxies()
    value = proxies.get('https') or proxies.get('http')
    assert value, 'EXISTING_HTTP_PROXY_REQUIRED'
    u = urllib.parse.urlsplit(value if '://' in value else 'http://' + value)
    assert u.scheme == 'http' and u.hostname == ADDRESS[0] and u.port == ADDRESS[1]
    assert not u.username and not u.password, 'NO_CREDENTIAL_COLLECTION'
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    base = {'task': 'CODEX-WUA-0-SING-DEPENDENCY-REVIEW-001', 'amendment': 1,
            'started_at': started, 'url': URL, 'proxy': 'http://127.0.0.1:10808',
            'redirects_allowed': False, 'retries_allowed': False, 'direct_fallback': False,
            'permission_sha256': hashlib.sha256((OUT / 'USER_GO.md').read_bytes()).hexdigest(),
            'preflight_sha256': hashlib.sha256((evidence / 'proxy_preflight.json').read_bytes()).hexdigest()}
    with reservation.open('x', encoding='utf-8') as f:
        json.dump(base, f, indent=2)
    receipt = dict(base, status='BLOCKED', connect_events=[], redirect_followed=False)
    def guard(event, args):
        if event == 'socket.connect':
            assert args[1] == ADDRESS, 'ONLY_EXISTING_LITERAL_PROXY'
            receipt['connect_events'].append({'address': ADDRESS[0], 'port': ADDRESS[1]})
        if event == 'socket.getaddrinfo':
            assert args[0] == ADDRESS[0], 'NO_EXTERNAL_LOCAL_DNS'
        if event in ('subprocess.Popen', 'os.system', 'os.posix_spawn'):
            raise PermissionError('NO_CHILD_PROCESS')
    sys.addaudithook(guard)
    conn = None
    try:
        assert not DEST.exists(), 'NEW_DESTINATION_REQUIRED'
        for p in DEST.parents:
            if p.exists():
                assert not p.is_symlink() and not getattr(p.lstat(), 'st_file_attributes', 0) & 0x400, 'REPARSE_PARENT'
        DEST.mkdir(parents=True)
        target = DEST / 'sing-module-source.zip'
        conn = http.client.HTTPSConnection(ADDRESS[0], ADDRESS[1], timeout=40, context=ssl.create_default_context())
        conn.set_tunnel('proxy.golang.org', 443)
        conn.request('GET', urllib.parse.urlsplit(URL).path,
                     headers={'User-Agent': 'WUA-authorized-source-only-review', 'Accept-Encoding': 'identity'})
        response = conn.getresponse()
        receipt['http_status'] = response.status
        if response.status in (301, 302, 303, 307, 308):
            receipt['redirect_seen'] = True  # Never record/query/follow arbitrary Location.
            raise RuntimeError('UNAPPROVED_REDIRECT_STOP')
        assert response.status == 200, 'HTTP_STATUS_' + str(response.status)
        assert response.getheader('Content-Encoding', 'identity') == 'identity', 'CONTENT_ENCODING'
        total = 0
        digest = hashlib.sha256()
        with target.open('xb') as f:
            while True:
                block = response.read(65536)
                if not block:
                    break
                total += len(block)
                assert total <= 32 * 1024 * 1024, 'ARCHIVE_SIZE_LIMIT'
                digest.update(block)
                f.write(block)
        assert total, 'EMPTY_ZIP'
        length = response.getheader('Content-Length')
        assert length is None or int(length) == total, 'INCOMPLETE_BODY'
        receipt.update(status='DOWNLOADED / INTEGRITY NOT YET VERIFIED', archive_path=target.as_posix(),
                       bytes=total, sha256=digest.hexdigest(), received_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                       content_type=response.getheader('Content-Type'))
    except BaseException as exc:
        receipt['reason'] = str(exc) if isinstance(exc, (AssertionError, RuntimeError)) else type(exc).__name__
    finally:
        if conn:
            conn.close()
        with receipt_path.open('x', encoding='utf-8') as f:
            json.dump(receipt, f, indent=2)
    print(json.dumps(receipt))
    return 0 if receipt['status'].startswith('DOWNLOADED') else 20


if __name__ == '__main__':
    sys.exit(main())
