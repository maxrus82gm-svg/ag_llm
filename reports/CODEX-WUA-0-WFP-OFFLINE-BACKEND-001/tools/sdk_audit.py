"""Read only installed SDK declarations; produce task-local source/provenance."""
from pathlib import Path
import re,json,hashlib
OUT=Path(__file__).resolve().parents[1]
BASE=Path('C:/Program Files (x86)/Windows Kits/10/Include')
NAMES=['FWPM_LAYER_ALE_AUTH_CONNECT_V4','FWPM_LAYER_ALE_AUTH_CONNECT_V6','FWPM_CONDITION_ALE_USER_ID','FWPM_CONDITION_IP_PROTOCOL','FWPM_CONDITION_IP_REMOTE_ADDRESS','FWPM_CONDITION_IP_REMOTE_PORT']
FUNCTIONS=['FwpmEngineOpen0','FwpmEngineClose0','FwpmTransactionBegin0','FwpmTransactionCommit0','FwpmTransactionAbort0','FwpmProviderAdd0','FwpmProviderGetByKey0','FwpmProviderDeleteByKey0','FwpmSubLayerAdd0','FwpmSubLayerGetByKey0','FwpmSubLayerDeleteByKey0','FwpmFilterAdd0','FwpmFilterGetByKey0','FwpmFilterDeleteByKey0','FwpmFreeMemory0']
def guids(text):
    result={}
    for name in NAMES:
        m=re.search(r'DEFINE_GUID\(\s*'+name+r'\s*,(.*?)\);',text,re.S);assert m,name
        nums=[int(n,16) for n in re.findall(r'0x[0-9a-fA-F]+',m[1])];assert len(nums)==11
        result[name]=f'{nums[0]:08x}-{nums[1]:04x}-{nums[2]:04x}-{nums[3]:02x}{nums[4]:02x}-'+''.join(f'{n:02x}' for n in nums[5:])
    return result
rows=[];all_values=[];declarations={}
for version in ['10.0.19041.0','10.0.22621.0','10.0.26100.0']:
    folder=BASE/version
    for ref in ['um/fwpmu.h','shared/fwpmtypes.h','shared/fwptypes.h']:
        p=folder/ref;b=p.read_bytes();rows.append({'sdk':version,'header':ref,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
    text=(folder/'um/fwpmu.h').read_text(encoding='utf-8-sig');values=guids(text);all_values.append(values)
    for name in FUNCTIONS:
        assert re.search(r'\b'+name+r'\s*\(',text),name
    if version=='10.0.19041.0':
        for name in FUNCTIONS:
            m=re.search(r'(?:DWORD\s+WINAPI\s+|void WINAPI )'+name+r'\s*\(.*?\);',text,re.S);assert m,name
            declarations[name]=m[0]
assert all(v==all_values[0] for v in all_values)
source='// Generated from installed Windows SDK declarations by tools/sdk_audit.py.\nnamespace Wua.Wfp.Abi { public static class Sdk {\n'
for key,value in all_values[0].items():source+=f'public static readonly System.Guid {key} = new System.Guid("{value}");\n'
source+='} }\n'
(OUT/'source/SdkConstants.cs').write_text(source,encoding='ascii')
(OUT/'evidence').mkdir(exist_ok=True)
(OUT/'evidence/sdk_declarations.json').write_text(json.dumps({'headers':rows,'guids':all_values[0],'guid_versions_equal':True,'declarations':declarations,'scope':'Declarations only; headers do not establish valid conditions at a layer, arbitration or OS enforcement.'},indent=2)+'\n',encoding='utf-8')
print(json.dumps({'sdk_versions':3,'headers_hashed':len(rows),'guid_values':len(NAMES),'prototypes':len(declarations)}))
