"""Explicit allowlisted GET-only observations; no inference, redirects, proxies or auth."""
from pathlib import Path
import datetime
import hashlib
import json
import time
import urllib.request
import urllib.error

WORK = Path(__file__).resolve().parents[1]
TARGETS = {
    'http://127.0.0.1:11434': ['/api/version', '/api/tags', '/api/ps', '/v1/models'],
    'http://127.0.0.1:8000': ['/health', '/v1/models', '/openapi.json'],
    'http://192.168.0.77:8000': ['/health', '/v1/models', '/openapi.json'],
}
LIMIT = 512 * 1024
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl): return None
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
def sanitized(value):
    if isinstance(value, dict):
        return {k: sanitized(v) for k,v in value.items() if not any(x in k.lower() for x in ['secret','token','password','authorization','credential','api_key','apikey','cookie'])}
    if isinstance(value, list): return [sanitized(x) for x in value[:500]]
    if isinstance(value, str): return value[:2000]
    return value

results = []
for base, routes in TARGETS.items():
    for route in routes:
        url = base + route
        item = {'url': url, 'method': 'GET', 'time_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'timeout_seconds': 2, 'proxy': False, 'redirects': False, 'auth_sent': False}
        started = time.monotonic()
        try:
            try:
                response = opener.open(urllib.request.Request(url, method='GET', headers={'Accept':'application/json'}), timeout=2)
            except urllib.error.HTTPError as e:
                response = e
            with response:
                raw = response.read(LIMIT+1)
                item.update(status=response.code, content_type=response.headers.get('Content-Type',''), bytes_observed=len(raw), truncated=len(raw)>LIMIT, body_sha256=hashlib.sha256(raw).hexdigest())
                try:
                    obj = json.loads(raw[:LIMIT])
                    if route == '/openapi.json' and isinstance(obj,dict):
                        # Keep schema facts only, not examples/defaults or opaque application configuration.
                        item['schema'] = {'openapi':obj.get('openapi'), 'info': sanitized(obj.get('info',{})), 'paths':{k: [m for m in v if m.lower() in ['get','post','delete','put','patch','options','head']] for k,v in obj.get('paths',{}).items() if isinstance(v,dict)}, 'security':obj.get('security'), 'security_scheme_names':list(obj.get('components',{}).get('securitySchemes',{}))}
                    elif route == '/v1/models' and isinstance(obj,dict):
                        item['data'] = sanitized(obj)
                    elif route in ['/api/version','/api/tags','/api/ps','/health']:
                        item['data'] = sanitized(obj)
                    else: item['json_shape'] = type(obj).__name__
                except (ValueError,UnicodeError):
                    item['body_note'] = 'Non-JSON content deliberately not stored; hash/status only.'
            item['classification'] = 'HTTP_OBSERVED; not an inference or identity proof'
        except Exception as e:
            item.update(error_type=type(e).__name__, error=str(e)[:300], classification='NOT ACCESSIBLE FROM DIAGNOSTIC HOST')
        item['elapsed_ms'] = round(1000*(time.monotonic()-started),1)
        results.append(item)
out = WORK/'evidence/http_inventory.json';out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
for r in results:
    print(json.dumps({k:v for k,v in r.items() if k in ['url','status','error_type','error','elapsed_ms','data','schema']},ensure_ascii=False))
