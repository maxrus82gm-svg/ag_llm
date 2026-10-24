"""One approved ZIP through existing literal loopback HTTP proxy, no DIRECT.

No retry, dependency fetch, Git, credential export, config change or engine run.
"""
from pathlib import Path
import datetime,hashlib,http.client,ipaddress,json,os,ssl,sys,urllib.parse,urllib.request
sys.dont_write_bytecode=True
OUT=Path(__file__).resolve().parent
DEST=Path('M:/WUA_SOURCE_REVIEW/sing-box/v1.13.4')
URL='https://github.com/SagerNet/sing-box/archive/refs/tags/v1.13.4.zip'
EXPECTED='d09182614c7778c1e0f51d990635c5d4249c437e'

def main():
    receipt={'task':'CODEX-WUA-0-SINGBOX-SOURCE-REVIEW-001','amendment':1,'status':'DOWNLOAD BLOCKED','release_url':'https://github.com/SagerNet/sing-box/releases/tag/v1.13.4','requested_url':URL,'expected_revision':EXPECTED,'started_at':datetime.datetime.now().astimezone().isoformat(),'direct_fallback':False,'network_tests':0,'redirects':[],'artifacts_requested':1}
    try:
        assert not (OUT/'evidence/download_receipt.json').exists(),'ONE_ATTEMPT_ONLY'
        # Windows urllib reads only existing OS/environment proxy metadata.
        # Never print its raw values, bypass list or credentials.
        proxies=urllib.request.getproxies();value=proxies.get('https') or proxies.get('http')
        assert value,'EXISTING_HTTP_PROXY_REQUIRED_NO_DIRECT'
        if '://' not in value:value='http://'+value
        proxy=urllib.parse.urlsplit(value)
        assert proxy.scheme=='http' and proxy.hostname=='127.0.0.1' and proxy.port and not proxy.username and not proxy.password,'LITERAL_LOOPBACK_HTTP_PROXY_REQUIRED'
        address=('127.0.0.1',proxy.port)
        receipt['route']='EXPLICIT_EXISTING_LOOPBACK_HTTP_CONNECT_PROXY; NO_PROXY ignored; no direct fallback'
        receipt['proxy_port']=proxy.port
        def guard(event,args):
            if event=='socket.connect':assert args[1]==address,'OWNED_DOWNLOAD_ONLY_PROXY_SOCKET'
            if event=='socket.getaddrinfo':assert args[0]=='127.0.0.1','NO_EXTERNAL_LOCAL_DNS'
            if event in ['subprocess.Popen','os.system']:raise PermissionError('NO_CHILD')
        sys.addaudithook(guard)
        DEST.mkdir(parents=True,exist_ok=True)
        for p in [DEST,*DEST.parents]:assert not p.is_symlink() and not getattr(p.lstat(),'st_file_attributes',0)&0x400,'LOCAL_NONREPARSE_DEST'
        target=DEST/'sing-box-v1.13.4-source.zip';assert not target.exists(),'DESTINATION_ALREADY_EXISTS'
        url=URL
        for _ in range(3):
            u=urllib.parse.urlsplit(url)
            assert u.scheme=='https' and u.hostname in ['github.com','codeload.github.com'] and not u.query and not u.fragment,'SOURCE_URL_ONLY'
            assert u.path in ['/SagerNet/sing-box/archive/refs/tags/v1.13.4.zip','/SagerNet/sing-box/zip/refs/tags/v1.13.4'],'EXACT_SOURCE_PATH'
            conn=http.client.HTTPSConnection(address[0],address[1],timeout=45,context=ssl.create_default_context());conn.set_tunnel(u.hostname,443)
            try:
                conn.request('GET',u.path,headers={'User-Agent':'WUA-authorized-source-review','Accept':'application/zip','Accept-Encoding':'identity'})
                response=conn.getresponse()
                if response.status in [301,302,303,307,308]:
                    location=response.getheader('Location');assert location,'REDIRECT_WITHOUT_LOCATION'
                    url=urllib.parse.urljoin(url,location);receipt['redirects'].append({'status':response.status,'url':url});continue
                assert response.status==200,'HTTP_STATUS_'+str(response.status)
                count=0;digest=hashlib.sha256()
                with target.open('xb') as f:
                    while True:
                        chunk=response.read(65536)
                        if not chunk:break
                        count+=len(chunk);assert count<=33554432,'ZIP_SIZE_LIMIT';digest.update(chunk);f.write(chunk)
                assert count>0,'EMPTY_ARCHIVE'
                receipt.update(status='DOWNLOADED_NOT_YET_REVIEWED',final_url=url,archive_path=str(target),bytes=count,sha256=digest.hexdigest(),received_at=datetime.datetime.now().astimezone().isoformat(),content_type=response.getheader('Content-Type'))
                break
            finally:conn.close()
        else:raise RuntimeError('REDIRECT_LIMIT')
    except BaseException as exc:
        receipt['reason']=str(exc) if isinstance(exc,(AssertionError,RuntimeError)) else type(exc).__name__
    with (OUT/'evidence/download_receipt.json').open('x',encoding='utf-8') as f:json.dump(receipt,f,indent=2)
    print(json.dumps(receipt));return 0 if receipt['status']=='DOWNLOADED_NOT_YET_REVIEWED' else 20
if __name__=='__main__':sys.exit(main())
