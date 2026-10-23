using System;
using System.IO;
using System.IO.Pipes;
using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Security.Principal;
using System.Security.AccessControl;
using System.Threading;
using WuaNpfs;
using Microsoft.Win32.SafeHandles;

// Create the reviewed SDK child suspended, with an explicit three-handle list.
// Assign its kill-on-close job BEFORE its first instruction (including venv redirector).
sealed class SdkChild : IDisposable {
    [StructLayout(LayoutKind.Sequential)] struct SA {public int size;public IntPtr sd;public int inherit;}
    [StructLayout(LayoutKind.Sequential,CharSet=CharSet.Unicode)] struct SI {public int size;public string reserved,desktop,title;public int x,y,xsize,ysize,xchars,ychars,fill,flags;public short show,bytes;public IntPtr reserved2,input,output,error;}
    [StructLayout(LayoutKind.Sequential)] struct SX {public SI startup;public IntPtr attributes;}
    [StructLayout(LayoutKind.Sequential)] struct PI {public IntPtr process,thread;public uint pid,tid;}
    [DllImport("kernel32.dll",SetLastError=true)] static extern bool CreatePipe(out IntPtr read,out IntPtr write,ref SA sa,uint size);
    [DllImport("kernel32.dll",SetLastError=true)] static extern bool SetHandleInformation(IntPtr h,uint mask,uint flags);
    [DllImport("kernel32.dll",SetLastError=true)] static extern bool InitializeProcThreadAttributeList(IntPtr list,int count,uint flags,ref IntPtr size);
    [DllImport("kernel32.dll",SetLastError=true)] static extern bool UpdateProcThreadAttribute(IntPtr list,uint flags,IntPtr key,IntPtr value,IntPtr size,IntPtr previous,IntPtr returned);
    [DllImport("kernel32.dll")] static extern void DeleteProcThreadAttributeList(IntPtr list);
    [DllImport("kernel32.dll",CharSet=CharSet.Unicode,SetLastError=true)] static extern bool CreateProcess(string app,System.Text.StringBuilder command,IntPtr pa,IntPtr ta,bool inherit,uint flags,IntPtr environment,string cwd,ref SX startup,out PI process);
    [DllImport("kernel32.dll",SetLastError=true)] static extern bool AssignProcessToJobObject(IntPtr job,IntPtr process);
    [DllImport("kernel32.dll",SetLastError=true)] static extern uint ResumeThread(IntPtr thread);
    [DllImport("kernel32.dll",SetLastError=true)] static extern uint WaitForSingleObject(IntPtr h,uint ms);
    [DllImport("kernel32.dll",SetLastError=true)] static extern bool TerminateProcess(IntPtr process,uint code);
    IntPtr handle; public Stream Input,Output,Error;
    public SdkChild(string executable,string arguments,string cwd,IntPtr job) {
        IntPtr ir=IntPtr.Zero,iw=IntPtr.Zero,or=IntPtr.Zero,ow=IntPtr.Zero,er=IntPtr.Zero,ew=IntPtr.Zero,list=IntPtr.Zero,array=IntPtr.Zero,environment=IntPtr.Zero;PI pi=new PI();bool listReady=false;
        try {
            var sa=new SA{size=Marshal.SizeOf(typeof(SA)),inherit=1};Guard.Need(CreatePipe(out ir,out iw,ref sa,16384)&&CreatePipe(out or,out ow,ref sa,65536)&&CreatePipe(out er,out ew,ref sa,4096),"SDK_PIPES");
            Guard.Need(SetHandleInformation(iw,1,0)&&SetHandleInformation(or,1,0)&&SetHandleInformation(er,1,0),"SDK_PARENT_HANDLE_FLAGS");
            IntPtr size=IntPtr.Zero;InitializeProcThreadAttributeList(IntPtr.Zero,1,0,ref size);list=Marshal.AllocHGlobal(size);Guard.Need(InitializeProcThreadAttributeList(list,1,0,ref size),"SDK_ATTRIBUTES");listReady=true;array=Marshal.AllocHGlobal(IntPtr.Size*3);Marshal.WriteIntPtr(array,0,ir);Marshal.WriteIntPtr(array,IntPtr.Size,ow);Marshal.WriteIntPtr(array,IntPtr.Size*2,ew);Guard.Need(UpdateProcThreadAttribute(list,0,new IntPtr(0x20002),array,new IntPtr(IntPtr.Size*3),IntPtr.Zero,IntPtr.Zero),"SDK_HANDLE_LIST");
            var vars=new System.Collections.Generic.SortedDictionary<string,string>(StringComparer.OrdinalIgnoreCase);foreach(string k in new[]{"SystemRoot","WINDIR","COMSPEC"}){string v=Environment.GetEnvironmentVariable(k);if(v!=null)vars[k]=v;}vars["PYTHONDONTWRITEBYTECODE"]="1";var block=new System.Text.StringBuilder();foreach(var pair in vars)block.Append(pair.Key+"="+pair.Value+"\0");block.Append('\0');environment=Marshal.StringToHGlobalUni(block.ToString());
            var sx=new SX{attributes=list,startup=new SI{size=Marshal.SizeOf(typeof(SX)),flags=0x100,input=ir,output=ow,error=ew}};
            Guard.Need(CreateProcess(executable,new System.Text.StringBuilder("\""+executable+"\" "+arguments),IntPtr.Zero,IntPtr.Zero,true,0x8080404,environment,cwd,ref sx,out pi),"SDK_CREATE_SUSPENDED");handle=pi.process;pi.process=IntPtr.Zero;
            Guard.Need(AssignProcessToJobObject(job,handle),"SDK_JOB_BEFORE_RUN");
            Input=new FileStream(new SafeFileHandle(iw,true),FileAccess.Write,4096,false);iw=IntPtr.Zero;Output=new FileStream(new SafeFileHandle(or,true),FileAccess.Read,4096,false);or=IntPtr.Zero;Error=new FileStream(new SafeFileHandle(er,true),FileAccess.Read,4096,false);er=IntPtr.Zero;
            Guard.Need(ResumeThread(pi.thread)!=0xffffffff,"SDK_RESUME");
        }catch{Dispose();throw;}
        finally {foreach(IntPtr h in new[]{ir,iw,or,ow,er,ew,pi.process,pi.thread})if(h!=IntPtr.Zero)Native.CloseHandle(h);if(listReady)DeleteProcThreadAttributeList(list);foreach(IntPtr p in new[]{list,array,environment})if(p!=IntPtr.Zero)Marshal.FreeHGlobal(p);}
    }
    public void Dispose() {try{if(Input!=null){Input.Dispose();Input=null;}if(handle!=IntPtr.Zero){if(WaitForSingleObject(handle,1200)!=0){TerminateProcess(handle,20);WaitForSingleObject(handle,1500);}Native.CloseHandle(handle);handle=IntPtr.Zero;}}finally{if(Output!=null){Output.Dispose();Output=null;}if(Error!=null){Error.Dispose();Error=null;}}}
}

// U-owned fixture authority, never installed into production. One pipe, one fixed SDK child.
public static class Gateway {
    [StructLayout(LayoutKind.Sequential)] struct SA {public int length;public IntPtr descriptor;public int inherit;}
    [DllImport("advapi32.dll",CharSet=CharSet.Unicode,SetLastError=true)] static extern bool ConvertStringSecurityDescriptorToSecurityDescriptor(string s,uint revision,out IntPtr sd,out uint size);
    [DllImport("kernel32.dll")] static extern IntPtr LocalFree(IntPtr p);
    [DllImport("kernel32.dll",CharSet=CharSet.Unicode,SetLastError=true)] static extern SafePipeHandle CreateNamedPipe(string name,uint access,uint mode,uint instances,uint outsize,uint insize,uint timeout,ref SA sa);
    [DllImport("kernel32.dll",SetLastError=true)] static extern IntPtr CreateJobObject(IntPtr sa,string name);
    [DllImport("kernel32.dll",SetLastError=true)] static extern bool SetInformationJobObject(IntPtr job,int kind,IntPtr info,uint size);
    static IntPtr Job(){IntPtr h=CreateJobObject(IntPtr.Zero,null);Guard.Need(h!=IntPtr.Zero,"JOB_CREATE");var bytes=new byte[IntPtr.Size==8?144:112];BitConverter.GetBytes(0x2000).CopyTo(bytes,16);IntPtr p=Marshal.AllocHGlobal(bytes.Length);try{Marshal.Copy(bytes,0,p,bytes.Length);if(!SetInformationJobObject(h,9,p,(uint)bytes.Length)){Native.CloseHandle(h);throw new Refusal("JOB_POLICY");}}finally{Marshal.FreeHGlobal(p);}return h;}
    static string Quote(string s){Guard.Need(!s.Contains("\"")&&!s.EndsWith("\\"),"ARGV");return "\""+s+"\"";}
    public static int Main(string[] args) {
        SdkChild child=null;IntPtr job=IntPtr.Zero;
        try {
            Guard.Need(args.Length==2&&args[0]=="synthetic_fixture_only","FIXTURE_ARGUMENTS");string configPath=Guard.FullLocal(args[1]);var c=Json.Parse(File.ReadAllBytes(configPath),8192);Guard.Exact(c,"schema","mode","pipe","session_id","client_sid","relay_sha256","run_root","python_sha256","worker_sha256");Guard.Need(Guard.Num(c["schema"])==1&&Guard.Str(c["mode"])=="synthetic_fixture_only","FIXTURE_ONLY");
            string name=Guard.PipeName(Guard.Str(c["pipe"])),session=Guard.Str(c["session_id"]),sid=Guard.Sid(Guard.Str(c["client_sid"]));Guard.Need(sid==Guard.CurrentSid(),"CURRENT_USER_FIXTURE_ONLY");
            string build=AppDomain.CurrentDomain.BaseDirectory;string root=Guard.FullLocal(Path.Combine(build,"..","..",".."));string report=Path.Combine(root,"reports","CODEX-WUA-0-MCP-NOTCP-NPFS-001");string run=Guard.FullLocal(Guard.Str(c["run_root"]));Guard.Need(run.StartsWith(report+"\\runs\\",StringComparison.OrdinalIgnoreCase)&&Path.GetDirectoryName(configPath)==run,"RUN_SCOPE");
            string python=Guard.FullLocal(Path.Combine(root,".venv","Scripts","python.exe")),worker=Guard.FullLocal(Path.Combine(root,"integrations","wua_chatgpt_mcp","npfs","gateway_worker.py"));Guard.Need(Guard.Sha(python)==Guard.Str(c["python_sha256"])&&Guard.Sha(worker)==Guard.Str(c["worker_sha256"]),"SDK_SOURCE_PIN");byte[] grant=Guard.Unhex(Environment.GetEnvironmentVariable("WUA_NPFS_GRANT"));Environment.SetEnvironmentVariable("WUA_NPFS_GRANT",null);
            IntPtr descriptor;uint size;string sddl="D:P(A;;0x00100083;;;"+sid+")";Guard.Need(ConvertStringSecurityDescriptorToSecurityDescriptor(sddl,1,out descriptor,out size),"DACL");SafePipeHandle handle;
            try {var sa=new SA{length=Marshal.SizeOf(typeof(SA)),descriptor=descriptor,inherit=0};handle=CreateNamedPipe("\\\\.\\pipe\\"+name,0x40080003,8,1,65536,16384,0,ref sa);}finally{LocalFree(descriptor);}
            using(handle){Guard.Need(!handle.IsInvalid,"EXCLUSIVE_PIPE_CREATE_"+Marshal.GetLastWin32Error());using(var pipe=new NamedPipeServerStream(PipeDirection.InOut,true,false,handle)) {
                var security=pipe.GetAccessControl();var rules=security.GetAccessRules(true,true,typeof(SecurityIdentifier));Guard.Need(security.AreAccessRulesProtected&&rules.Count==1,"DACL_READBACK");var rule=(PipeAccessRule)rules[0];Guard.Need(rule.AccessControlType==AccessControlType.Allow&&rule.IdentityReference.Value==sid&&(int)rule.PipeAccessRights==0x00100083,"DACL_READBACK");
                Console.Out.WriteLine("GATEWAY_LISTENING");Console.Out.Flush();var waiting=pipe.BeginWaitForConnection(null,null);using(var wh=waiting.AsyncWaitHandle){Guard.Need(wh.WaitOne(5000),"ACCEPT_TIMEOUT");pipe.EndWaitForConnection(waiting);}
                uint pid;Guard.Need(Native.GetNamedPipeClientProcessId(handle,out pid),"CLIENT_PID");using(var peer=new Native.Peer(pid,sid,Guard.Str(c["relay_sha256"]))) {
                    var wire=new Wire(pipe,session,grant,false);Guard.Need(Guard.Text(wire.Receive(Guard.InputLimit))=="hello","HANDSHAKE");string effective=null;TokenImpersonationLevel level=TokenImpersonationLevel.None;
                    pipe.RunAsClient(delegate{using(var w=WindowsIdentity.GetCurrent()){effective=w.User.Value;level=w.ImpersonationLevel;}});Guard.Need(effective==sid&&level==TokenImpersonationLevel.Identification,"CLIENT_EFFECTIVE_TOKEN");
                    Console.Out.WriteLine("GATEWAY_AUTHENTICATED:"+pid);Console.Out.WriteLine("DACL_TOKEN_VERIFIED:Identification:current-user");Console.Out.Flush();
                    job=Job();child=new SdkChild(python,"-I -X utf8 -B "+Quote(worker)+" "+Quote(run),Path.GetDirectoryName(worker),job);
                    wire.Send(Guard.Bytes("ready"),Guard.OutputLimit);Array.Clear(grant,0,grant.Length);var rpc=new Rpc();var lines=new Io.Lines(child.Output);
                    Bridge.Run(delegate{while(true){var raw=wire.Receive(Guard.InputLimit);if(Guard.Text(raw)=="close")return;rpc.Check(raw,true);Io.Write(child.Input,raw);Io.Write(child.Input,new byte[]{10});}},delegate{while(true){var raw=lines.Next(Guard.OutputLimit);if(raw==null)return;rpc.Check(raw,false);wire.Send(raw,Guard.OutputLimit);}},delegate{pipe.Dispose();child.Input.Dispose();child.Output.Dispose();});
                }
            }} return 0;
        }catch(Exception e){Console.Error.WriteLine("GATEWAY_STOP:"+(e is Refusal?e.Message:e.GetType().Name));return 20;}
        finally {try{if(child!=null)child.Dispose();}finally{if(job!=IntPtr.Zero)Native.CloseHandle(job);}}
    }
}
