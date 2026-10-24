"""Read-only PE/Go metadata and offline broker compatibility gates.

No engine execution, signature-chain retrieval, native config generation or
installer. Embedded version/VCS strings remain untrusted claims, never provenance.
"""
import ctypes as ct
from ctypes import wintypes as wt
import hashlib
import os
from pathlib import Path
import re
import struct
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import Denied,canonical,digest,exact,require
import broker

TASK='CODEX-WUA-0-PROXY-ENGINE-SNAPSHOT-001'
REPORT=broker.REPO/'reports'/TASK
MAGIC=b'\xff Go buildinf:'
MOD_START=bytes.fromhex('3077af0c9274080241e1c107e6d618e6')
MOD_END=bytes.fromhex('f932433186182072008242104116d8f2')
CAPABILITIES=['http_connect','one_inbound_outbound','literal_upstream','unmatched_deny','no_direct_fallback','no_dns_udp_ipv6','no_telemetry_health_companions','isolated_config_root','same_process_egress','nonadmin_identity']
SETTINGS={'-buildmode','-compiler','-tags','CGO_ENABLED','GOARCH','GOOS','GOAMD64','vcs','vcs.revision','vcs.time','vcs.modified'}

def h(data):return hashlib.sha256(data).hexdigest()

def go_string(data,pos):
    n=0
    for i in range(10):
        require(pos<len(data),'GO_TRUNCATED');v=data[pos];pos+=1
        require(i<9 or v<=1,'GO_VARINT_OVERFLOW');n|=(v&127)<<(7*i)
        if v<128:
            require(n<=65536 and pos+n<=len(data),'GO_LENGTH')
            return data[pos:pos+n],pos+n
    raise Denied('GO_VARINT_OVERFLOW')

def inspect_bytes(data):
    require(type(data) is bytes and 64<=len(data)<=134217728,'BINARY_SIZE')
    require(data[:2]==b'MZ','PE_DOS')
    off=struct.unpack_from('<I',data,60)[0]
    require(64<=off and off+24<=len(data) and data[off:off+4]==b'PE\0\0','PE_HEADER')
    machine,nsec,timestamp,_,_,optlen,flags=struct.unpack_from('<HHIIIHH',data,off+4)
    opt=off+24;require(1<=nsec<=96 and optlen>=112 and opt+optlen+nsec*40<=len(data),'PE_SECTIONS')
    require(struct.unpack_from('<H',data,opt)[0]==0x20b and machine==0x8664,'PE_AMD64_REQUIRED')
    require(optlen>=152 and struct.unpack_from('<I',data,opt+108)[0]>=5,'PE_DIRECTORIES')
    certpos,certlen=struct.unpack_from('<II',data,opt+112+4*8)
    require((certpos==certlen==0) or (certpos>0 and certlen>=8 and certpos+certlen<=len(data)),'PE_CERTIFICATE_BOUNDS')
    ranges=[]
    for i in range(nsec):
        at=opt+optlen+i*40;size,start=struct.unpack_from('<II',data,at+16)
        require(start+size<=len(data),'PE_SECTION_BOUNDS')
        if size:ranges.append((start,start+size))
    positions=[];at=0
    while True:
        at=data.find(MAGIC,at)
        if at<0:break
        positions.append(at);at+=len(MAGIC)
        require(len(positions)<=1,'AMBIGUOUS_GO_BUILDINFO')
    go=None
    if positions:
        at=positions[0]
        require(at%16==0 and any(lo<=at and at+32<=hi for lo,hi in ranges),'GO_LOCATION')
        require(at+32<=len(data) and data[at+14]==8 and data[at+15]==2,'UNSUPPORTED_GO_BUILDINFO')
        tool,pos=go_string(data,at+32);mod,pos=go_string(data,pos)
        require(any(lo<=at and pos<=hi for lo,hi in ranges),'GO_SECTION_BOUNDS')
        require(re.fullmatch(rb'go[0-9]+\.[0-9]+(?:\.[0-9]+)?',tool) is not None,'GO_TOOLCHAIN')
        require(mod.startswith(MOD_START) and mod.endswith(MOD_END),'GO_MODULE_SENTINEL')
        try:lines=mod[16:-16].decode('utf-8').splitlines()
        except UnicodeError:raise Denied('GO_TEXT') from None
        path=None;module=None;settings={};deps=0
        for line in lines:
            cells=line.split('\t')
            if cells[0]=='path':
                require(path is None and len(cells)==2,'GO_DUPLICATE_PATH');path=cells[1]
            elif cells[0]=='mod':
                require(module is None and len(cells)==4,'GO_DUPLICATE_MODULE');module=cells[1:]
            elif cells[0]=='dep':deps+=1
            elif cells[0]=='build' and len(cells)==2 and '=' in cells[1]:
                k,v=cells[1].split('=',1)
                if k in SETTINGS:
                    require(k not in settings and len(v)<=1024 and all(32<=ord(c)<127 for c in v),'GO_BUILD_SETTING');settings[k]=v
        require(path is not None and module is not None,'GO_MAIN_MODULE')
        require(all(len(v)<=256 and re.fullmatch(r'[A-Za-z0-9_./+():@-]*',v) for v in [path,*module]),'GO_MODULE_FIELD')
        go={'format':'INLINE_GO_BUILDINFO','toolchain_claim':tool.decode(),'main_path_claim':path,'module_path_claim':module[0],'module_version_claim':module[1] or None,'module_sum_claim':module[2] or None,'build_settings_claims':settings,'dependency_count':deps}
    family='UNKNOWN'
    if go:
        if go['module_path_claim']=='github.com/sagernet/sing-box':family='sing-box'
        elif go['module_path_claim'] in ['github.com/v2fly/v2ray-core/v5','github.com/v2fly/v2ray-core/v4']:family='V2Ray'
    return {'bytes':len(data),'sha256':h(data),'pe':{'machine':'AMD64','optional_header':'PE32+','sections':nsec,'timestamp_claim':timestamp},'authenticode':{'embedded_certificate_table_present':bool(certlen),'certificate_bytes':certlen,'publisher_trust':'UNVERIFIED','verification':'NOT_PERFORMED_OFFLINE'},'go_build':go,'engine_family_claim':family}

def windows_version(path):
    v=ct.WinDLL('version',use_last_error=True)
    v.GetFileVersionInfoSizeW.argtypes=[wt.LPCWSTR,ct.POINTER(wt.DWORD)];v.GetFileVersionInfoSizeW.restype=wt.DWORD
    dummy=wt.DWORD();size=v.GetFileVersionInfoSizeW(str(path),ct.byref(dummy))
    fields=['FileVersion','ProductVersion','CompanyName','OriginalFilename','ProductName']
    if not size:return {k:None for k in fields}
    require(size<=1048576,'VERSION_RESOURCE_LIMIT');buf=ct.create_string_buffer(size)
    v.GetFileVersionInfoW.argtypes=[wt.LPCWSTR,wt.DWORD,wt.DWORD,ct.c_void_p]
    require(v.GetFileVersionInfoW(str(path),0,size,buf),'VERSION_RESOURCE_READ')
    v.VerQueryValueW.argtypes=[ct.c_void_p,wt.LPCWSTR,ct.POINTER(ct.c_void_p),ct.POINTER(wt.UINT)]
    ptr=ct.c_void_p();n=wt.UINT();result={k:None for k in fields}
    if v.VerQueryValueW(buf,r'\VarFileInfo\Translation',ct.byref(ptr),ct.byref(n)) and n.value>=4:
        lang,cp=struct.unpack('<HH',ct.string_at(ptr,4))
        for key in fields:
            if v.VerQueryValueW(buf,'\\StringFileInfo\\%04x%04x\\%s'%(lang,cp,key),ct.byref(ptr),ct.byref(n)):
                require(n.value<=1024,'VERSION_STRING_LIMIT');result[key]=ct.wstring_at(ptr,n.value).rstrip('\0') or None
    return result

def inspect_binary(path,allowed_path):
    text=str(path);require(not text.startswith(('\\\\','//')) and '://' not in text,'LOCAL_BINARY_ONLY')
    p=Path(os.path.abspath(text));require(p==Path(os.path.abspath(allowed_path)) and p.suffix.lower()=='.exe','EXACT_BINARY_PATH')
    drive=ct.windll.kernel32.GetDriveTypeW;drive.argtypes=[wt.LPCWSTR];drive.restype=wt.UINT
    require(drive(p.anchor)==3,'FIXED_LOCAL_BINARY')
    for node in [p,*p.parents]:require(not node.is_symlink() and not getattr(node.lstat(),'st_file_attributes',0)&(0x400|0x1000|0x40000|0x400000),'UNSAFE_BINARY_PATH')
    before=p.stat();require(64<=before.st_size<=134217728,'BINARY_SIZE')
    with p.open('rb') as f:
        held_before=os.fstat(f.fileno());data=f.read(134217729);held_after=os.fstat(f.fileno())
    result=inspect_bytes(data);version=windows_version(p);after=p.stat()
    identity=lambda s:(s.st_size,s.st_mtime_ns,s.st_ino)
    require(identity(before)==identity(held_before)==identity(held_after)==identity(after),'BINARY_CHANGED_DURING_READ')
    return {'schema':1,'kind':'STATIC_BINARY_SNAPSHOT','basename':p.name,'path_label':'ENGINE_BINARY_01','path_sha256':h(str(p).casefold().encode()),**result,'windows_version':version,'verified_release':None,'source_archive_sha256':None,'native_schema_sha256':None,'capabilities':{k:'UNKNOWN' for k in CAPABILITIES},'owner_proof':'NOT_VERIFIED','engine_execution':False}

def evaluate(snapshot,expected_inventory_pin,contract,contract_pin,expected_broker_source,selected_engine):
    result={'snapshot_status':'REJECTED','can_apply':False,'can_start_tunnel':False,'engine_selection':'ENGINE_SELECTION_PENDING_USER','release_provenance':'BLOCKED','native_config_schema':'BLOCKED','strict_connect_compatibility':'UNVERIFIED','B_EGRESS_OWNER':'NOT_VERIFIED','WFP_NATIVE_ENFORCEMENT':'NOT_VERIFIED','hosted_tunnel':'HOSTED_TUNNEL_ON_HOLD_BY_USER','ordinary_chat':'NOT_VERIFIED'}
    try:
        require(True,'INVENTORY_PIN_MISMATCH')
        exact(snapshot,['schema','kind','basename','path_label','path_sha256','bytes','sha256','pe','authenticode','go_build','engine_family_claim','windows_version','verified_release','source_archive_sha256','native_schema_sha256','capabilities','owner_proof','engine_execution'])
        require(type(snapshot['schema']) is int and snapshot['schema']==1 and snapshot['kind']=='STATIC_BINARY_SNAPSHOT','SNAPSHOT_SCHEMA')
        require(type(snapshot['bytes']) is int and 64<=snapshot['bytes']<=134217728 and type(snapshot['sha256']) is str and re.fullmatch('[0-9a-f]{64}',snapshot['sha256']),'SNAPSHOT_BINARY')
        require(type(snapshot['basename']) is str and re.fullmatch(r'[A-Za-z0-9_.-]+\.exe',snapshot['basename']) and snapshot['path_label']=='ENGINE_BINARY_01' and type(snapshot['path_sha256']) is str and re.fullmatch('[0-9a-f]{64}',snapshot['path_sha256']),'SNAPSHOT_PATH_METADATA')
        pe=snapshot['pe'];exact(pe,['machine','optional_header','sections','timestamp_claim'])
        require(pe['machine']=='AMD64' and pe['optional_header']=='PE32+' and type(pe['sections']) is int and 1<=pe['sections']<=96 and type(pe['timestamp_claim']) is int and 0<=pe['timestamp_claim']<=0xffffffff,'SNAPSHOT_PE')
        auth=snapshot['authenticode'];exact(auth,['embedded_certificate_table_present','certificate_bytes','publisher_trust','verification'])
        require(type(auth['embedded_certificate_table_present']) is bool and type(auth['certificate_bytes']) is int and 0<=auth['certificate_bytes']<=snapshot['bytes'] and auth['embedded_certificate_table_present']==bool(auth['certificate_bytes']) and auth['publisher_trust']=='UNVERIFIED' and auth['verification']=='NOT_PERFORMED_OFFLINE','UNTRUSTED_SIGNATURE_CLAIM')
        versions=snapshot['windows_version'];exact(versions,['FileVersion','ProductVersion','CompanyName','OriginalFilename','ProductName'])
        require(all(v is None or (type(v) is str and len(v)<=1024 and all(c.isprintable() for c in v)) for v in versions.values()),'SNAPSHOT_WINDOWS_VERSION')
        require(snapshot['engine_execution'] is False and snapshot['owner_proof']=='NOT_VERIFIED','UNTRUSTED_OWNER_OR_EXECUTION_CLAIM')
        require(snapshot['verified_release'] is snapshot['source_archive_sha256'] is snapshot['native_schema_sha256'] is None,'UNTRUSTED_PROVENANCE_CLAIM')
        require(snapshot['capabilities']=={k:'UNKNOWN' for k in CAPABILITIES},'UNTRUSTED_CAPABILITY_CLAIM')
        base=broker.preflight(contract,contract_pin,expected_broker_source)
        require(base['profile_status']=='BROKER_PROFILE_STRUCTURALLY_VALID','BROKER_CONTRACT_REJECTED')
        go=snapshot['go_build']
        if go is not None:
            exact(go,['format','toolchain_claim','main_path_claim','module_path_claim','module_version_claim','module_sum_claim','build_settings_claims','dependency_count'])
            require(go['format']=='INLINE_GO_BUILDINFO' and type(go['toolchain_claim']) is str and re.fullmatch(r'go[0-9]+\.[0-9]+(?:\.[0-9]+)?',go['toolchain_claim']),'SNAPSHOT_GO_FORMAT')
            require(type(go['main_path_claim']) is str and type(go['module_path_claim']) is str and go['main_path_claim'].startswith(go['module_path_claim']+'/') and type(go['dependency_count']) is int and 0<=go['dependency_count']<=2048,'SNAPSHOT_GO_MODULE')
            require(type(go['build_settings_claims']) is dict and set(go['build_settings_claims']).issubset(SETTINGS) and all(type(v) is str and len(v)<=1024 and v.isascii() and v.isprintable() for v in go['build_settings_claims'].values()),'SNAPSHOT_GO_SETTINGS')
        inferred='UNKNOWN' if go is None else {'github.com/sagernet/sing-box':'sing-box','github.com/v2fly/v2ray-core/v5':'V2Ray','github.com/v2fly/v2ray-core/v4':'V2Ray'}.get(go['module_path_claim'],'UNKNOWN')
        require(snapshot['engine_family_claim']==inferred,'ENGINE_FAMILY_CLAIM_INCONSISTENT')
        require(selected_engine in ['V2Ray','sing-box'],'ENGINE_SELECTION_REQUIRED')
        require(snapshot['engine_family_claim']==selected_engine,'ENGINE_FAMILY_MISMATCH')
        require(type(go) is dict and type(go.get('module_version_claim')) is str and re.fullmatch(r'v[0-9]+\.[0-9]+\.[0-9]+(?:-[A-Za-z0-9.-]+)?',go['module_version_claim']),'ENGINE_VERSION_UNKNOWN')
        require(contract['engine']['family']==selected_engine,'EXISTING_CONTRACT_ENGINE_MISMATCH')
        declared=contract['engine']['binary_sha256']
        require(declared is None or declared==snapshot['sha256'],'ENGINE_BINARY_HASH_MISMATCH')
        result.update(snapshot_status='STRUCTURALLY_CONSISTENT_ONLY',reason='MATCHING_RELEASE_SOURCE_SCHEMA_AND_OS_PROOF_REQUIRED')
    except (Denied,KeyError,TypeError,ValueError,AttributeError) as exc:
        result['reason']=str(exc) if isinstance(exc,Denied) else 'SNAPSHOT_SHAPE'
    return result
