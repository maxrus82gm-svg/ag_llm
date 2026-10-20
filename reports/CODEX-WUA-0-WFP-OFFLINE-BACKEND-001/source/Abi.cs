// Managed memory ABI candidate, x64 only. No DllImport or Windows security calls here.
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Runtime.InteropServices;
namespace Wua.Wfp.Abi {
    [StructLayout(LayoutKind.Sequential)] public struct Blob {public uint Size;public IntPtr Data;}
    [StructLayout(LayoutKind.Sequential)] public struct Display {public IntPtr Name,Description;}
    [StructLayout(LayoutKind.Explicit,Size=8)] public struct ValueUnion {
        [FieldOffset(0)] public byte U8;[FieldOffset(0)] public ushort U16;[FieldOffset(0)] public uint U32;[FieldOffset(0)] public IntPtr Pointer;
    }
    [StructLayout(LayoutKind.Sequential)] public struct Value {public uint Type;public ValueUnion Union;}
    [StructLayout(LayoutKind.Sequential)] public struct NativeCondition {public Guid Field;public uint Match;public Value Value;}
    [StructLayout(LayoutKind.Sequential)] public struct NativeAction {public uint Type;public Guid Key;}
    [StructLayout(LayoutKind.Explicit,Size=16)] public struct Context { [FieldOffset(0)]public ulong Raw;[FieldOffset(0)]public Guid ProviderContext;}
    [StructLayout(LayoutKind.Sequential)] public struct NativeFilter {
        public Guid Key;public Display Display;public uint Flags;public IntPtr Provider;public Blob Data;public Guid Layer,SubLayer;
        public Value Weight;public uint Count;public IntPtr Conditions;public NativeAction Action;public Context Context;
        public IntPtr Reserved;public ulong Id;public Value EffectiveWeight;
    }
    [StructLayout(LayoutKind.Sequential)] public struct NativeProvider {public Guid Key;public Display Display;public uint Flags;public Blob Data;public IntPtr ServiceName;}
    [StructLayout(LayoutKind.Sequential)] public struct NativeSubLayer {public Guid Key;public Display Display;public uint Flags;public IntPtr Provider;public Blob Data;public ushort Weight;}
    [StructLayout(LayoutKind.Sequential)] public struct NativeSession {public Guid Key;public Display Display;public uint Flags,Timeout,Pid;public IntPtr Sid,Username;public int KernelMode;}
    public static class SecurityDescriptor {
        // Self-relative SD with one allow ACE granting FWP_ACTRL_MATCH_FILTER to exact SID.
        // This is filter-condition data, NOT an OS ACL assignment or identity proof.
        public static byte[] ForUser(string text){
            var sid=Guard.LocalSid(text);using(var m=new MemoryStream()){using(var w=new BinaryWriter(m)){
                w.Write((byte)1);w.Write((byte)0);w.Write((ushort)0x8004);w.Write(0u);w.Write(0u);w.Write(0u);w.Write(20u);
                w.Write((byte)2);w.Write((byte)0);w.Write((ushort)(8+8+8+sid.Length*4));w.Write((ushort)1);w.Write((ushort)0);
                w.Write((byte)0);w.Write((byte)0);w.Write((ushort)(8+8+sid.Length*4));w.Write(1u);
                w.Write((byte)1);w.Write((byte)sid.Length);w.Write(new byte[]{0,0,0,0,0,5});foreach(var n in sid)w.Write(n);
            }return m.ToArray();}
        }
    }
    public sealed class Arena:IDisposable {
        private readonly List<IntPtr> owned=new List<IntPtr>();private bool disposed;
        public int Count{get{return owned.Count;}}
        public IntPtr Bytes(byte[] bytes){Guard.Need(!disposed&&bytes!=null&&bytes.Length>0&&bytes.Length<=65536,"ARENA_INPUT");var p=Marshal.AllocHGlobal(bytes.Length);owned.Add(p);Marshal.Copy(bytes,0,p,bytes.Length);return p;}
        public IntPtr Struct<T>(T value) where T:struct{Guard.Need(!disposed,"ARENA_DISPOSED");Guard.Need(typeof(T)==typeof(Guid)||typeof(T)==typeof(Blob),"ARENA_BLITTABLE_TYPE_REQUIRED");var p=Marshal.AllocHGlobal(Marshal.SizeOf(typeof(T)));owned.Add(p);Marshal.StructureToPtr(value,p,false);return p;}
        public IntPtr String(string value){Guard.Need(!disposed,"ARENA_DISPOSED");var p=Marshal.StringToHGlobalUni(value);owned.Add(p);return p;}
        public Blob Blob(byte[] bytes){return new Blob{Size=(uint)bytes.Length,Data=Bytes(bytes)};}
        public void Dispose(){if(disposed)return;for(int i=owned.Count-1;i>=0;i--)Marshal.FreeHGlobal(owned[i]);owned.Clear();disposed=true;}
    }
    public sealed class FilterLease:IDisposable {
        public readonly NativeFilter Filter;public readonly Arena Memory=new Arena();
        public FilterLease(Policy p,Filter f){
            Guard.Need(IntPtr.Size==8,"X64_ABI_ONLY");StaticVerifier.Verify(p);Guard.Need(p.Filters.Contains(f),"FOREIGN_FILTER");
            try {
                var conditions=new List<NativeCondition>();foreach(var c in f.Conditions){var n=new NativeCondition{Match=(uint)c.Match};switch(c.Field){
                    case Field.User:n.Field=Sdk.FWPM_CONDITION_ALE_USER_ID;n.Value.Type=14;n.Value.Union.Pointer=Memory.Struct(Memory.Blob(SecurityDescriptor.ForUser(c.Text)));break;
                    case Field.Protocol:n.Field=Sdk.FWPM_CONDITION_IP_PROTOCOL;n.Value.Type=1;n.Value.Union.U8=checked((byte)c.Number);break;
                    case Field.RemoteAddress:n.Field=Sdk.FWPM_CONDITION_IP_REMOTE_ADDRESS;n.Value.Type=3;n.Value.Union.U32=c.Number;break;
                    case Field.RemotePort:n.Field=Sdk.FWPM_CONDITION_IP_REMOTE_PORT;n.Value.Type=2;n.Value.Union.U16=checked((ushort)c.Number);break;
                    default:throw new Rejected("UNKNOWN_ABI_FIELD");}conditions.Add(n);}
                var stride=Marshal.SizeOf(typeof(NativeCondition));var block=Memory.Bytes(new byte[stride*conditions.Count]);
                for(int i=0;i<conditions.Count;i++)Marshal.StructureToPtr(conditions[i],IntPtr.Add(block,i*stride),false);
                Filter=new NativeFilter{Key=f.Key,Display=new Display{Name=Memory.String("WUA owned deny candidate")},Flags=1,Provider=Memory.Struct(p.Provider),Data=Memory.Blob(p.OwnershipBlob()),Layer=f.Family==4?Sdk.FWPM_LAYER_ALE_AUTH_CONNECT_V4:Sdk.FWPM_LAYER_ALE_AUTH_CONNECT_V6,SubLayer=p.SubLayer,Weight=new Value{Type=4,Union=new ValueUnion{Pointer=Memory.Bytes(BitConverter.GetBytes(f.Weight))}},Count=(uint)conditions.Count,Conditions=block,Action=new NativeAction{Type=0x1001}};
            }catch{Memory.Dispose();throw;}
        }
        public void Dispose(){Memory.Dispose();}
    }
    // Input pointers must originate from owned arenas (tests) or trusted FWPM readback (future lab).
    // This is NOT a parser for arbitrary user-supplied addresses or a trusted-lineage proof.
    public static class Readback {
        private static T At<T>(IntPtr p) where T:struct{Guard.Need(p!=IntPtr.Zero,"NULL_READBACK_POINTER");return (T)Marshal.PtrToStructure(p,typeof(T));}
        private static byte[] Bytes(Blob b){Guard.Need(b.Size<=65536&&(b.Size==0||b.Data!=IntPtr.Zero),"READBACK_BLOB_BOUNDS");var bytes=new byte[(int)b.Size];if(bytes.Length>0)Marshal.Copy(b.Data,bytes,0,bytes.Length);return bytes;}
        public static void Provider(Policy p,NativeProvider actual){Guard.Need(actual.Key==p.Provider&&actual.Flags==1&&actual.ServiceName==IntPtr.Zero&&Bytes(actual.Data).SequenceEqual(p.OwnershipBlob()),"PROVIDER_DRIFT_OR_FOREIGN");}
        public static void SubLayer(Policy p,NativeSubLayer actual){Guard.Need(actual.Key==p.SubLayer&&actual.Flags==1&&At<Guid>(actual.Provider)==p.Provider&&actual.Weight==256&&Bytes(actual.Data).SequenceEqual(p.OwnershipBlob()),"SUBLAYER_DRIFT_OR_FOREIGN");}
        private static void Condition(NativeCondition a,NativeCondition b){
            Guard.Need(a.Field==b.Field&&a.Match==b.Match&&a.Value.Type==b.Value.Type,"CONDITION_READBACK_MISMATCH");
            switch(a.Value.Type){case 1:Guard.Need(a.Value.Union.U8==b.Value.Union.U8,"U8_READBACK");break;case 2:Guard.Need(a.Value.Union.U16==b.Value.Union.U16,"U16_READBACK");break;case 3:Guard.Need(a.Value.Union.U32==b.Value.Union.U32,"U32_READBACK");break;case 14:Guard.Need(Bytes(At<Blob>(a.Value.Union.Pointer)).SequenceEqual(Bytes(At<Blob>(b.Value.Union.Pointer))),"SD_READBACK");break;default:throw new Rejected("UNSUPPORTED_READBACK_VALUE");}
        }
        public static void Filter(Policy p,Filter filter,NativeFilter actual){using(var expected=new FilterLease(p,filter)){var e=expected.Filter;var a=actual;
            Guard.Need(a.Key==e.Key&&At<Guid>(a.Provider)==p.Provider&&a.Layer==e.Layer&&a.SubLayer==e.SubLayer&&a.Flags==1&&a.Action.Type==0x1001&&a.Action.Key==Guid.Empty&&a.Context.ProviderContext==Guid.Empty&&a.Reserved==IntPtr.Zero&&a.Id!=0,"FILTER_READBACK_MISMATCH");
            Guard.Need(Bytes(a.Data).SequenceEqual(p.OwnershipBlob())&&a.Weight.Type==4&&a.Weight.Union.Pointer!=IntPtr.Zero&&(ulong)Marshal.ReadInt64(a.Weight.Union.Pointer)==256,"FILTER_OWNERSHIP_WEIGHT");
            Guard.Need(a.Count==e.Count&&a.Count>=1&&a.Count<=4&&a.Conditions!=IntPtr.Zero,"CONDITION_COUNT");int stride=Marshal.SizeOf(typeof(NativeCondition));
            for(int i=0;i<a.Count;i++)Condition(At<NativeCondition>(IntPtr.Add(a.Conditions,i*stride)),At<NativeCondition>(IntPtr.Add(e.Conditions,i*stride)));
        }}
    }
}
