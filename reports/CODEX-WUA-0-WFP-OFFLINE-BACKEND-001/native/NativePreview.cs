// INACTIVE SOURCE/BUILD PREVIEW ONLY. This assembly has NO public types/entrypoint.
// It is NOT referenced or loaded by OfflineTests, Core, Abi or the existing installer.
// Internal methods are future-lab code, not an authorization boundary against reflection.
// A new reviewed source release + isolated-lab USER GO is required before any call here.
using System;
using System.Linq;
using System.Runtime.InteropServices;
using Wua.Wfp;
using Wua.Wfp.Abi;
[assembly: DefaultDllImportSearchPaths(DllImportSearchPath.System32)]
namespace Wua.Wfp.NativePreview {
    internal static class WinApi {
        private const string Dll="fwpuclnt.dll";
        [DllImport(Dll,ExactSpelling=true,CharSet=CharSet.Unicode,CallingConvention=CallingConvention.Winapi)]internal static extern uint FwpmEngineOpen0(string server,uint authn,IntPtr identity,IntPtr session,out IntPtr handle);
        [DllImport(Dll,ExactSpelling=true)]internal static extern uint FwpmEngineClose0(IntPtr handle);
        [DllImport(Dll,ExactSpelling=true)]internal static extern uint FwpmTransactionBegin0(IntPtr handle,uint flags);
        [DllImport(Dll,ExactSpelling=true)]internal static extern uint FwpmTransactionCommit0(IntPtr handle);
        [DllImport(Dll,ExactSpelling=true)]internal static extern uint FwpmTransactionAbort0(IntPtr handle);
        [DllImport(Dll,ExactSpelling=true)]internal static extern uint FwpmProviderAdd0(IntPtr handle,ref NativeProvider provider,IntPtr sd);
        [DllImport(Dll,ExactSpelling=true)]internal static extern uint FwpmProviderGetByKey0(IntPtr handle,ref Guid key,out IntPtr provider);
        [DllImport(Dll,ExactSpelling=true)]internal static extern uint FwpmProviderDeleteByKey0(IntPtr handle,ref Guid key);
        [DllImport(Dll,ExactSpelling=true)]internal static extern uint FwpmSubLayerAdd0(IntPtr handle,ref NativeSubLayer sublayer,IntPtr sd);
        [DllImport(Dll,ExactSpelling=true)]internal static extern uint FwpmSubLayerGetByKey0(IntPtr handle,ref Guid key,out IntPtr sublayer);
        [DllImport(Dll,ExactSpelling=true)]internal static extern uint FwpmSubLayerDeleteByKey0(IntPtr handle,ref Guid key);
        [DllImport(Dll,ExactSpelling=true)]internal static extern uint FwpmFilterAdd0(IntPtr handle,ref NativeFilter filter,IntPtr sd,out ulong id);
        [DllImport(Dll,ExactSpelling=true)]internal static extern uint FwpmFilterGetByKey0(IntPtr handle,ref Guid key,out IntPtr filter);
        [DllImport(Dll,ExactSpelling=true)]internal static extern uint FwpmFilterDeleteByKey0(IntPtr handle,ref Guid key);
        [DllImport(Dll,ExactSpelling=true)]internal static extern void FwpmFreeMemory0(ref IntPtr pointer);
    }
    internal sealed class LabSourceSession:IDisposable {
        private IntPtr handle;private bool disposed;
        private static void Ok(uint code){if(code!=0)throw new Rejected("FWPM_CALL_FAILED_"+code.ToString("x8"));}
        // Constructor intentionally has no caller in this release.
        internal LabSourceSession(){Guard.Need(IntPtr.Size==8,"X64_ONLY");Ok(WinApi.FwpmEngineOpen0(null,10,IntPtr.Zero,IntPtr.Zero,out handle));}
        private void Open(){Guard.Need(!disposed&&handle!=IntPtr.Zero,"SESSION_CLOSED");}
        private static T Value<T>(IntPtr p) where T:struct{Guard.Need(p!=IntPtr.Zero,"NULL_READBACK");return (T)Marshal.PtrToStructure(p,typeof(T));}
        internal bool ProviderMatches(Policy p){
            Open();IntPtr memory=IntPtr.Zero;Guid key=p.Provider;try{
                uint code=WinApi.FwpmProviderGetByKey0(handle,ref key,out memory);if(code==0x80320005)return false;Ok(code);
                Readback.Provider(p,Value<NativeProvider>(memory));return true;
            }finally{if(memory!=IntPtr.Zero)WinApi.FwpmFreeMemory0(ref memory);}
        }
        internal bool SubLayerMatches(Policy p){
            Open();IntPtr memory=IntPtr.Zero;Guid key=p.SubLayer;try{
                uint code=WinApi.FwpmSubLayerGetByKey0(handle,ref key,out memory);if(code==0x80320007)return false;Ok(code);
                Readback.SubLayer(p,Value<NativeSubLayer>(memory));return true;
            }finally{if(memory!=IntPtr.Zero)WinApi.FwpmFreeMemory0(ref memory);}
        }
        internal bool FilterMatches(Policy p,Filter expected){
            Open();IntPtr memory=IntPtr.Zero;Guid key=expected.Key;try{
                uint code=WinApi.FwpmFilterGetByKey0(handle,ref key,out memory);if(code==0x80320003)return false;Ok(code);
                Readback.Filter(p,expected,Value<NativeFilter>(memory));return true;
            }finally{if(memory!=IntPtr.Zero)WinApi.FwpmFreeMemory0(ref memory);}
        }
        internal string StageCandidateObjectsOnly(Policy p,string approval,DateTime now,byte[] futureObjectAcl){
            Open();StaticVerifier.Binding(p,p.Request,approval,now);
            // A trusted controller/object ACL and host provenance are NOT supplied by this release.
            Guard.Need(futureObjectAcl!=null&&futureObjectAcl.Length>=20&&futureObjectAcl.Length<=65536,"TRUSTED_OBJECT_ACL_REQUIRED");
            int found=ProviderMatches(p)?1:0;found+=SubLayerMatches(p)?1:0;foreach(var f in p.Filters)found+=FilterMatches(p,f)?1:0;
            if(found==10)return "EXISTING_CANDIDATE_REQUIRES_TRUSTED_LINEAGE_AND_SECURITY_GATES";
            Guard.Need(found==0,"PARTIAL_READBACK_STOP_NO_DELETE");
            bool commitAttempted=false;Ok(WinApi.FwpmTransactionBegin0(handle,0));try{
                using(var arena=new Arena()){
                    var acl=arena.Bytes(futureObjectAcl);
                    var provider=new NativeProvider{Key=p.Provider,Display=new Display{Name=arena.String("WUA candidate owner")},Flags=1,Data=arena.Blob(p.OwnershipBlob())};
                    Ok(WinApi.FwpmProviderAdd0(handle,ref provider,acl));
                    var sub=new NativeSubLayer{Key=p.SubLayer,Display=new Display{Name=arena.String("WUA candidate deny")},Flags=1,Provider=arena.Struct(p.Provider),Data=arena.Blob(p.OwnershipBlob()),Weight=256};
                    Ok(WinApi.FwpmSubLayerAdd0(handle,ref sub,acl));
                    foreach(var f in p.Filters)using(var lease=new FilterLease(p,f)){var filter=lease.Filter;ulong id;Ok(WinApi.FwpmFilterAdd0(handle,ref filter,acl,out id));Guard.Need(id!=0,"FILTER_ID_REQUIRED");}
                }
                commitAttempted=true;Ok(WinApi.FwpmTransactionCommit0(handle));
                Guard.Need(ProviderMatches(p)&&SubLayerMatches(p)&&p.Filters.All(f=>FilterMatches(p,f)),"POSTCOMMIT_READBACK_UNKNOWN");
                return "OBJECTS_ONLY_NOT_ENFORCEMENT_NO_ACTIVATION";
            }catch{
                if(!commitAttempted)Ok(WinApi.FwpmTransactionAbort0(handle));
                // No retry/reconnect/delete/permit fallback on ambiguous commit or readback.
                throw;
            }
        }
        internal void RemoveCandidate(Policy p,bool reportedZero){
            // reportedZero, providerData and a ledger are NOT trusted quiescence authority.
            // Do not implement an exploitable boolean override for deny removal.
            throw new Rejected("ROLLBACK_BLOCKED_KEEP_DENY_NEED_TRUSTED_LIVE_QUIESCENCE");
        }
        public void Dispose(){if(disposed)return;disposed=true;if(handle!=IntPtr.Zero){var h=handle;handle=IntPtr.Zero;Ok(WinApi.FwpmEngineClose0(h));}}
    }
}
