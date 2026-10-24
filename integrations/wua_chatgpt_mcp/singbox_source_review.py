"""Pinned, bounded source-review tripwires; NOT a Go interpreter/config validator.

No fetch/build/engine execution. Lexical assertions protect reviewed loci; hashes
bind the rest. Neither lexical checks nor a release ZIP prove native security.
"""
import base64,hashlib,re,stat,unicodedata,zipfile
from pathlib import PurePosixPath
from common import require
REVISION='d09182614c7778c1e0f51d990635c5d4249c437e'
ZIP_SHA='ecf6cbedda4c35073656c902722b74daaf9fb89bb6f52de9ed0bdfd3a7729c1c'
SING_VERSION='v0.8.3-0.20260315153529-ed51f65fbfde'
SING_SUM='h1:RNQzlpnsXIuu1HGts/fIzJ1PR7RhrzaNlU52MDyiX1c='
FIELDS={'RawMessage','Schema','Log','DNS','NTP','Certificate','Endpoints','Inbounds','Outbounds','Route','Services','Experimental'}
LOCI={
 'http_dispatch':('protocol/http/inbound.go','Inbound.NewConnectionEx',['Network:           []string{N.NetworkTCP}','auth.NewAuthenticator(options.Users)','http.HandleConnectionEx(','uot.NewRouter(router, logger)']),
 'listener':('common/listener/listener_tcp.go','Listener.ListenTCP',['func (l *Listener) ListenTCP()','return listenConfig.Listen(l.ctx,']),
 'system_proxy':('common/listener/listener.go','Listener.Start',['if l.setSystemProxy {','err = systemProxy.Enable()']),
 'selected_outbound':('route/route.go','Router.routeConnection',['selectedOutbound, loaded = r.outbound.Outbound(action.Outbound)','if selectedRule == nil {','defaultOutbound := r.outbound.Default()','return action.Error(ctx)']),
 'direct_default':('box.go','New default fallback factories',['outboundManager.Initialize(func()','return direct.NewOutbound(','option.DirectOutboundOptions{}','dnsTransportManager.Initialize(func()','option.LocalDNSServerOptions{}']),
 'manager_default':('adapter/outbound/manager.go','Manager.Start/Create',['if m.defaultOutbound == nil {','m.defaultOutboundFallback()','m.defaultTag == "" && m.defaultOutbound == nil']),
 'connection_failure':('route/conn.go','ConnectionManager.NewConnection',['remoteConn, err = this.DialContext(ctx, N.NetworkTCP, metadata.Destination)','N.CloseOnHandshakeFailure(conn, onClose, err)']),
 'one_server_example':('protocol/trojan/outbound.go','trojanDialer.DialContext (illustration, not selected protocol)',['serverAddr: options.ServerOptions.Build()','h.tlsDialer.DialTLSContext(ctx, h.serverAddr)','h.dialer.DialContext(ctx, N.NetworkTCP, h.serverAddr)','return trojan.NewClientConn(conn, h.key, destination)']),
 'resolve':('common/dialer/dialer.go','NewWithOptions',['if dialOptions.Detour != "" {','if options.RemoteIsDomain &&','NewResolveDialer(']),
 'local_dns':('dns/transport/local/resolv_windows.go','dnsReadConfig/adapterAddresses',['windows.GetAdaptersAddresses(','conf.servers = defaultNS']),
 'uot':('common/uot/router.go','Router.RouteConnectionEx',['case uot.MagicAddress:','r.router.RoutePacketConnectionEx(']),
 'health':('protocol/group/urltest.go','URLTestGroup.PostStart',['g.ticker = time.NewTicker(g.interval)']),
 'remote_rules':('route/rule/rule_set_remote.go','RemoteRuleSet.StartContext/PostStart',['s.fetch(ctx, startContext)','s.updateTicker = time.NewTicker(s.updateInterval)','go s.loopUpdate()']),
 'ntp':('box.go','New conditional services',['if ntpOptions.Enabled {','ntp.NewService(ntp.Options{']),
 'tor_helper':('protocol/tor/outbound.go','Outbound.start',['tor.Start(t.ctx, t.startConf)','socks.NewClient(N.SystemDialer,']),
 'ech_dns':('common/tls/ech.go','ECHClientConfig.fetchAndHandshake',['s.dnsRouter.Exchange(ctx, message, adapter.DNSQueryOptions{})']),
 'reality_cover':('common/tls/reality_client.go','realityClientFallback',['go realityClientFallback(','return uConn, nil','client.Do(request)']),
 'config_default':('cmd/sing-box/cmd.go','preRun',['if len(configPaths) == 0 && len(configDirectories) == 0 {','configPaths = append(configPaths, "config.json")','os.Chdir(workingDir)']),
 'config_merge':('cmd/sing-box/cmd_run.go','readConfig/readConfigAndMerge',['if path == "stdin" {','for _, directory := range configDirectories {','sort.Slice(optionsList,','badjson.MergeJSON(']),
 'schema':('option/options.go','Options.UnmarshalJSONContext',['decoder.DisallowUnknownFields()','return checkOptions(o)'])
}

def archive_identity(path,expected_sha=ZIP_SHA,expected_revision=REVISION):
    require(hashlib.sha256(path.read_bytes()).hexdigest()==expected_sha,'ARCHIVE_HASH_MISMATCH')
    with zipfile.ZipFile(path) as z:
        require(z.comment.decode('ascii')==expected_revision,'ARCHIVE_REVISION_MISMATCH')
    return {'archive_hash_matches':True,'revision_comment_matches':True,'signature_verified':False,'binary_correspondence_verified':False}

def check_pins(files,pins):
    for name,pin in pins.items():
        require(name in files,'SOURCE_FILE_MISSING:'+name)
        require(hashlib.sha256(files[name]).hexdigest()==pin,'SOURCE_FILE_DRIFT:'+name)

def module_zip_identity(path,expected_h1=SING_SUM):
    """Bounded Go module Hash1 + conservative Windows-safe archive admission.

    Hash1: sort full ZIP member names, hash each uncompressed body, concatenate
    '<lowercase hex sha256>  <full name>\\n', hash that UTF-8 summary, base64 it.
    ZIP headers/compression/order are intentionally absent from h1. Raw ZIP SHA
    is reported separately. This admits only a source subset, not all valid ZIPs.
    No extraction, Go tool invocation or trust in ZIP comments/tags.
    """
    module='github.com/sagernet/sing';prefix=module+'@'+SING_VERSION+'/'
    raw=path.read_bytes();require(len(raw)<=32*1024*1024,'MODULE_ZIP_SIZE')
    members=[];names=set();total=0;summary=hashlib.sha256()
    with zipfile.ZipFile(path) as archive:
        entries=archive.infolist();require(0<len(entries)<=5000,'MODULE_ZIP_COUNT')
        for entry in entries:
            name=entry.filename
            require(name.startswith(prefix),'MODULE_ZIP_PREFIX')
            relative=name[len(prefix):];parts=relative.split('/')
            require(relative and all(p not in ('','.', '..') for p in parts),'MODULE_ZIP_PATH')
            require(not any(ord(c)<32 or c in '\\:<>"|?*' for c in relative),'MODULE_ZIP_PATH')
            require(not entry.is_dir() and not entry.flag_bits&1,'MODULE_ZIP_ENTRY_TYPE')
            require(stat.S_IFMT(entry.external_attr>>16) in (0,stat.S_IFREG),'MODULE_ZIP_ENTRY_TYPE')
            require(not entry.external_attr&0x400,'MODULE_ZIP_REPARSE')
            for part in parts:
                require(part==part.rstrip(' .') and part.casefold()!='.git','MODULE_ZIP_WINDOWS_PATH')
                stem=part.split('.')[0].upper()
                require(stem not in {'CON','PRN','AUX','NUL',*(f'COM{i}' for i in range(1,10)),*(f'LPT{i}' for i in range(1,10))},'MODULE_ZIP_WINDOWS_PATH')
            folded=unicodedata.normalize('NFC',relative).casefold()
            require(folded not in names,'MODULE_ZIP_COLLISION');names.add(folded)
            require(PurePosixPath(relative).suffix.lower() not in ('.exe','.dll','.so','.dylib','.pyd'),'MODULE_ZIP_EXECUTABLE')
            require(entry.compress_type in (zipfile.ZIP_STORED,zipfile.ZIP_DEFLATED),'MODULE_ZIP_COMPRESSION')
            total+=entry.file_size
            require(entry.file_size<=8*1024*1024 and total<=64*1024*1024,'MODULE_ZIP_EXPANSION')
        for name in names:
            require(not any(str(p) in names for p in PurePosixPath(name).parents if str(p)!='.'),'MODULE_ZIP_FILE_DIRECTORY_COLLISION')
        for entry in sorted(entries,key=lambda e:e.filename):
            body=archive.read(entry)  # Reads to EOF and verifies ZIP CRC.
            digest=hashlib.sha256(body).hexdigest()
            summary.update((digest+'  '+entry.filename+'\n').encode('utf-8'))
            members.append({'path':entry.filename[len(prefix):],'bytes':len(body),'sha256':digest})
        require(archive.read(prefix+'go.mod').startswith(('module '+module+'\n').encode()),'MODULE_DECLARATION')
    actual='h1:'+base64.b64encode(summary.digest()).decode('ascii')
    require(actual==expected_h1,'MODULE_ZIP_H1_MISMATCH')
    return {'module':module,'version':SING_VERSION,'h1':actual,'h1_matches':True,
            'raw_zip_sha256':hashlib.sha256(raw).hexdigest(),'archive_bytes':len(raw),
            'file_count':len(members),'uncompressed_bytes':total,'files':members,
            'crc_paths_case_links_checked':True,'signature_verified':False,
            'native_security_verified':False,'can_apply':False,'can_start_tunnel':False}

def inspect(files):
    require('go.mod' in files and 'go.sum' in files,'MODULE_FILES_REQUIRED')
    mod=files['go.mod'].decode();sums=files['go.sum'].decode()
    require(mod.startswith('module github.com/sagernet/sing-box\n'),'MODULE_IDENTITY')
    require('github.com/sagernet/sing '+SING_VERSION in mod,'SING_DEPENDENCY_REVISION')
    require('github.com/sagernet/sing '+SING_VERSION+' '+SING_SUM in sums,'SING_DEPENDENCY_SUM')
    findings=[];locators=[]
    for key,(path,function,anchors) in LOCI.items():
        require(path in files,'SOURCE_FILE_MISSING:'+path)
        text=files[path].decode()
        for anchor in anchors:
            require(anchor in text,'SOURCE_BRANCH_DRIFT:'+key)
            locators.append({'id':key,'path':path,'function':function,'line':text[:text.index(anchor)].count('\n')+1,'anchor':anchor,'file_sha256':hashlib.sha256(files[path]).hexdigest()})
    options=files['option/options.go'].decode().split('type _Options struct {',1)[1].split('\n}',1)[0]
    actual=set(re.findall(r'^\s*(\w+)\s+',options,re.M));require(actual==FIELDS,'OPTION_FIELD_SET_DRIFT')
    dependency_http='vendor/github.com/sagernet/sing/protocol/http/server.go' in files
    # Even an arbitrary file with this name cannot establish dependency identity.
    findings.extend(['EMPTY_OUTBOUND_CREATES_DIRECT','UNMATCHED_USES_DEFAULT_OUTBOUND','DEFAULT_DNS_LOCAL_TRANSPORT','HTTP_TCP_INBOUND_CAN_DISPATCH_UOT','HTTP_PARSER_AUTH_AND_JSON_DEPENDENCY_CLOSURE_BLOCKED'])
    return {'status':'PARTIAL / BOUNDED SOURCE REVIEW','findings':findings,'locators':locators,'dependency_http_path_present':dependency_http,'http_connect_source':'UNVERIFIED / DEPENDENCY_CLOSURE_REQUIRED','strict_route_source':'CONDITIONAL_PRIMITIVES_OBSERVED / STRICT_CONFIG_NOT_VERIFIED','hidden_egress_review':'BOUNDED_LOCATIONS_REVIEWED / GLOBAL_ABSENCE_NOT_PROVEN','can_apply':False,'can_start_tunnel':False,'native_config':None,'engine_selection':'PENDING_USER'}
