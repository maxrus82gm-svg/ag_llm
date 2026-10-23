// Local fixture transport. No networking, proxy discovery or child launch here.
using System;
using System.IO;
using System.IO.Pipes;
using System.Collections;
using System.Collections.Generic;
using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Security.Principal;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading;
using System.Web.Script.Serialization;
using Microsoft.Win32.SafeHandles;

namespace WuaNpfs {
public sealed class Refusal : Exception { public Refusal(string code) : base(code) {} }
public static class Guard {
    public const int InputLimit=8192, OutputLimit=32768, IoMs=2500, LifetimeMs=30000;
    public static void Need(bool ok,string code) { if(!ok) throw new Refusal(code); }
    public static string Str(object x) { Need(x is string,"TYPE"); return (string)x; }
    public static long Num(object x) { Need(x is long || x is int,"NUMBER"); return Convert.ToInt64(x); }
    public static string Sha(string file) { using(var h=SHA256.Create()) using(var f=File.OpenRead(file)) return Hex(h.ComputeHash(f)); }
    public static string Hex(byte[] b) { return BitConverter.ToString(b).Replace("-","").ToLowerInvariant(); }
    public static byte[] Unhex(string s) { Need(s!=null && Regex.IsMatch(s,"\\A[0-9a-f]{64}\\z"),"GRANT_FORMAT"); var b=new byte[32]; for(int i=0;i<32;i++) b[i]=Convert.ToByte(s.Substring(i*2,2),16); return b; }
    public static string PipeName(string s) { Need(Regex.IsMatch(s,"\\AWUA-NPFS-[0-9a-f]{32}\\z"),"LOCAL_PIPE_NAME"); return s; }
    public static string Sid(string s) { var sid=new SecurityIdentifier(s); Need(sid.Value==s,"SID_FORMAT"); return s; }
    public static string CurrentSid() { using(var w=WindowsIdentity.GetCurrent()) return w.User.Value; }
    public static string FullLocal(string s) { Need(!s.StartsWith("\\\\") && !s.Contains("://"),"LOCAL_PATH"); string p=Path.GetFullPath(s); var drive=new DriveInfo(Path.GetPathRoot(p)); Need(drive.DriveType==DriveType.Fixed || drive.DriveType==DriveType.Removable,"LOCAL_VOLUME"); for(var q=new FileInfo(p) as FileSystemInfo;q!=null; q=q is FileInfo ? ((FileInfo)q).Directory : ((DirectoryInfo)q).Parent) { if(q.Exists) Need((q.Attributes & FileAttributes.ReparsePoint)==0,"REPARSE_PATH"); } return p; }
    public static void Exact(Dictionary<string,object> d,params string[] keys) { Need(d.Count==keys.Length,"FIELDS"); foreach(string k in keys) Need(d.ContainsKey(k),"FIELDS"); }
    public static Dictionary<string,object> Obj(object o) { Need(o is Dictionary<string,object>,"OBJECT"); return (Dictionary<string,object>)o; }
    public static byte[] Bytes(string s) { return new UTF8Encoding(false,true).GetBytes(s); }
    public static string Text(byte[] b) { return new UTF8Encoding(false,true).GetString(b); }
}

// Strict parser: duplicate keys, noninteger numbers, excessive nesting/items and invalid UTF8 fail before SDK parsing.
public sealed class Json {
    string s; int i; Json(string text) {s=text;}
    void Space() {while(i<s.Length && (s[i]==' '||s[i]=='\n'||s[i]=='\r'||s[i]=='\t'))i++;}
    char Take() {Guard.Need(i<s.Length,"JSON_EOF"); return s[i++];}
    string String() {Guard.Need(Take()=='"',"JSON_STRING"); var b=new StringBuilder(); while(true) {char c=Take(); if(c=='"')break; Guard.Need(c>=32,"JSON_CONTROL"); if(c=='\\') { c=Take(); if(c=='u') {Guard.Need(i+4<=s.Length,"JSON_ESCAPE"); string x=s.Substring(i,4); Guard.Need(Regex.IsMatch(x,"\\A[0-9a-fA-F]{4}\\z"),"JSON_ESCAPE"); b.Append((char)Convert.ToInt32(x,16)); i+=4;} else {int n="\"\\/bfnrt".IndexOf(c); Guard.Need(n>=0,"JSON_ESCAPE"); b.Append("\"\\/\b\f\n\r\t"[n]);}} else b.Append(c); Guard.Need(b.Length<=32768,"JSON_TEXT");} string value=b.ToString(); Guard.Bytes(value); return value; }
    object Value(int depth) { Space(); Guard.Need(depth<=16 && i<s.Length,"JSON_DEPTH"); char c=s[i]; if(c=='"') return String(); if(c=='{') {i++; var d=new Dictionary<string,object>(); Space(); if(i<s.Length && s[i]=='}'){i++;return d;} while(true) {Space(); string k=String(); Guard.Need(k.Length<=128&&!d.ContainsKey(k)&&d.Count<64,"JSON_KEY"); Space(); Guard.Need(Take()==':',"JSON_COLON"); d.Add(k,Value(depth+1)); Space(); c=Take(); if(c=='}')return d; Guard.Need(c==',',"JSON_COMMA");}} if(c=='[') {i++; var a=new List<object>(); Space(); if(i<s.Length&&s[i]==']'){i++;return a;} while(true){Guard.Need(a.Count<128,"JSON_ITEMS");a.Add(Value(depth+1));Space();c=Take();if(c==']')return a;Guard.Need(c==',',"JSON_COMMA");}} foreach(string t in new[]{"true","false","null"}) if(s.Substring(i).StartsWith(t,StringComparison.Ordinal)){i+=t.Length;return t=="null"?null:(object)(t=="true");} int start=i; if(c=='-')i++; Guard.Need(i<s.Length&&char.IsDigit(s[i]),"JSON_NUMBER"); if(s[i]=='0')i++;else while(i<s.Length&&s[i]>='0'&&s[i]<='9')i++; long number; Guard.Need(long.TryParse(s.Substring(start,i-start),out number),"JSON_NUMBER"); return number; }
    public static Dictionary<string,object> Parse(byte[] b,int max) {Guard.Need(b.Length>0&&b.Length<=max,"MESSAGE_SIZE");var p=new Json(Guard.Text(b));var v=Guard.Obj(p.Value(0));p.Space();Guard.Need(p.i==p.s.Length,"JSON_TRAILING");return v;}
    public static byte[] Dump(object v) {return Guard.Bytes(new JavaScriptSerializer{MaxJsonLength=65536,RecursionLimit=20}.Serialize(v));}
}

public static class Io {
    public static int Read(Stream s,byte[] b,int offset,int count,Stopwatch clock) {int ms=Guard.IoMs-(int)clock.ElapsedMilliseconds; Guard.Need(ms>0,"IO_TIMEOUT"); var ar=s.BeginRead(b,offset,count,null,null); using(var wh=ar.AsyncWaitHandle){Guard.Need(wh.WaitOne(ms),"IO_TIMEOUT");return s.EndRead(ar);} }
    public static byte[] Exact(Stream s,int count,Stopwatch clock) {var b=new byte[count];int n=0;while(n<count){int k=Read(s,b,n,count-n,clock);Guard.Need(k>0,"PARTIAL_OR_EOF");n+=k;}return b;}
    public static void Write(Stream s,byte[] b) {var ar=s.BeginWrite(b,0,b.Length,null,null);using(var wh=ar.AsyncWaitHandle){Guard.Need(wh.WaitOne(Guard.IoMs),"WRITE_TIMEOUT");s.EndWrite(ar);}s.Flush();}
    public sealed class Lines {
        Stream stream; byte[] buffer=new byte[4096]; int pos,count;
        public Lines(Stream s){stream=s;}
        public byte[] Next(int limit) {var clock=Stopwatch.StartNew();using(var m=new MemoryStream()){while(true){if(pos==count){count=Read(stream,buffer,0,buffer.Length,clock);pos=0;if(count==0){Guard.Need(m.Length==0,"PARTIAL_LINE");return null;}}byte c=buffer[pos++];if(c==10){Guard.Need(m.Length>0,"EMPTY_LINE");return m.ToArray();}Guard.Need(m.Length<limit,"MESSAGE_SIZE");m.WriteByte(c);}}}
    }
}

public sealed class Wire {
    Stream stream; byte[] key; byte[] session; long readSeq,writeSeq; byte incoming,outgoing;
    public Wire(Stream s,string id,byte[] grant,bool client){stream=s;key=(byte[])grant.Clone();Guard.Need(Guid.Parse(id).ToString()==id,"SESSION");session=Encoding.ASCII.GetBytes(id);incoming=(byte)(client?'U':'C');outgoing=(byte)(client?'C':'U');}
    byte[] Tag(byte[] header,byte[] body){using(var h=new HMACSHA256(key)){var all=new byte[header.Length+body.Length];Buffer.BlockCopy(header,0,all,0,header.Length);Buffer.BlockCopy(body,0,all,header.Length,body.Length);return h.ComputeHash(all);}}
    public void Send(byte[] body,int limit) {Guard.Need(body.Length>0&&body.Length<=limit&&writeSeq<128,"WIRE_QUOTA");var head=new byte[53];Buffer.BlockCopy(Encoding.ASCII.GetBytes("WNP1"),0,head,0,4);head[4]=outgoing;Buffer.BlockCopy(session,0,head,5,36);Buffer.BlockCopy(BitConverter.GetBytes(writeSeq++),0,head,41,8);Buffer.BlockCopy(BitConverter.GetBytes(body.Length),0,head,49,4);var data=new byte[head.Length+body.Length+32];Buffer.BlockCopy(head,0,data,0,head.Length);Buffer.BlockCopy(body,0,data,head.Length,body.Length);Buffer.BlockCopy(Tag(head,body),0,data,head.Length+body.Length,32);Io.Write(stream,data);}
    public byte[] Receive(int limit) {var clock=Stopwatch.StartNew();var h=Io.Exact(stream,53,clock);Guard.Need(Encoding.ASCII.GetString(h,0,4)=="WNP1"&&h[4]==incoming&&Encoding.ASCII.GetString(h,5,36)==Encoding.ASCII.GetString(session),"WIRE_SESSION");Guard.Need(BitConverter.ToInt64(h,41)==readSeq++&&readSeq<=128,"WIRE_REPLAY");int len=BitConverter.ToInt32(h,49);Guard.Need(len>0&&len<=limit,"WIRE_SIZE");var b=Io.Exact(stream,len,clock);var mac=Io.Exact(stream,32,clock);var expected=Tag(h,b);int diff=0;for(int i=0;i<32;i++)diff|=mac[i]^expected[i];Guard.Need(diff==0,"WIRE_AUTH");return b;}
}

// Both peers track independent JSON-RPC id namespaces; no replay/reconnect or unsolicited response.
public sealed class Rpc {
    HashSet<string> seenC=new HashSet<string>(),seenU=new HashSet<string>(); HashSet<string> pendingC=new HashSet<string>(),pendingU=new HashSet<string>(); object mutex=new object();
    string Id(object o){if(o is string){string s=(string)o;Guard.Need(s.Length>0&&s.Length<=80,"RPC_ID");return "s:"+s;}return "n:"+Guard.Num(o).ToString(System.Globalization.CultureInfo.InvariantCulture);}
    public void Check(byte[] raw,bool fromClient) {lock(mutex){var d=Json.Parse(raw,fromClient?Guard.InputLimit:Guard.OutputLimit);Guard.Need(d.ContainsKey("jsonrpc")&&Guard.Str(d["jsonrpc"])=="2.0","RPC_VERSION");bool method=d.ContainsKey("method");if(method){Guard.Need(d.Count==(d.ContainsKey("id")?3:2)+(d.ContainsKey("params")?1:0),"RPC_FIELDS");string m=Guard.Str(d["method"]);string[] allowed=fromClient?new[]{"initialize","ping","tools/list","tools/call","notifications/initialized","notifications/cancelled"}:new[]{"ping","notifications/message","notifications/tools/list_changed"};Guard.Need(Array.IndexOf(allowed,m)>=0,"RPC_METHOD");if(d.ContainsKey("id")){Guard.Need(!m.StartsWith("notifications/"),"RPC_NOTIFICATION_ID");var seen=fromClient?seenC:seenU;var pending=fromClient?pendingC:pendingU;string id=Id(d["id"]);Guard.Need(seen.Count<96&&pending.Count<16&&seen.Add(id),"RPC_REPLAY");pending.Add(id);}else Guard.Need(m.StartsWith("notifications/"),"RPC_MISSING_ID");}else{Guard.Need(d.ContainsKey("id")&&d.Count==3&&(d.ContainsKey("result")^d.ContainsKey("error")),"RPC_RESPONSE");var pending=fromClient?pendingU:pendingC;Guard.Need(pending.Remove(Id(d["id"])),"RPC_CORRELATION");}}}
}

public static class Native {
    [DllImport("kernel32.dll",SetLastError=true)] public static extern bool GetNamedPipeServerProcessId(SafePipeHandle pipe,out uint pid);
    [DllImport("kernel32.dll",SetLastError=true)] public static extern bool GetNamedPipeClientProcessId(SafePipeHandle pipe,out uint pid);
    [DllImport("kernel32.dll",SetLastError=true)] static extern IntPtr OpenProcess(uint access,bool inherit,uint pid);
    [DllImport("advapi32.dll",SetLastError=true)] static extern bool OpenProcessToken(IntPtr p,uint access,out IntPtr token);
    [DllImport("kernel32.dll",SetLastError=true)] static extern bool QueryFullProcessImageName(IntPtr p,uint flags,StringBuilder name,ref uint size);
    [DllImport("kernel32.dll",SetLastError=true)] public static extern bool CloseHandle(IntPtr h);
    [DllImport("kernel32.dll",CharSet=CharSet.Unicode,SetLastError=true)] public static extern SafePipeHandle CreateFile(string name,uint access,uint share,IntPtr sa,uint creation,uint flags,IntPtr template);
    [DllImport("kernel32.dll",CharSet=CharSet.Unicode,SetLastError=true)] public static extern bool WaitNamedPipe(string name,uint timeout);
    public sealed class Peer : IDisposable {
        IntPtr handle;public string Sid,Image,ImageSha256;
        public Peer(uint pid,string expectedSid,string hash){handle=OpenProcess(0x101000,false,pid);Guard.Need(handle!=IntPtr.Zero,"PEER_PROCESS");try{IntPtr token;Guard.Need(OpenProcessToken(handle,8,out token),"PEER_TOKEN");try{using(var w=new WindowsIdentity(token)){Sid=w.User.Value;}}finally{CloseHandle(token);}Guard.Need(Sid==expectedSid,"PEER_SID");var n=new StringBuilder(32768);uint length=32768;Guard.Need(QueryFullProcessImageName(handle,0,n,ref length),"PEER_IMAGE");Image=Guard.FullLocal(n.ToString());ImageSha256=Guard.Sha(Image);Guard.Need(ImageSha256==hash,"PEER_IMAGE_HASH");}catch{Dispose();throw;}}
        public void Dispose(){if(handle!=IntPtr.Zero){CloseHandle(handle);handle=IntPtr.Zero;}}
    }
}

public static class Bridge {
    public static void Run(Action send,Action receive,Action close){Exception error=null;int terminal=0;using(var done=new ManualResetEvent(false)){Action<Action> run=delegate(Action action){Exception own=null;try{action();}catch(Exception e){own=e;}finally{if(Interlocked.CompareExchange(ref terminal,1,0)==0){error=own;done.Set();}}};var a=new Thread(delegate(){run(send);}){IsBackground=true,Name="bounded-input"};var b=new Thread(delegate(){run(receive);}){IsBackground=true,Name="bounded-output"};a.Start();b.Start();bool completed=done.WaitOne(Guard.LifetimeMs);Interlocked.Exchange(ref terminal,1);try{close();}finally{a.Join(1000);b.Join(1000);}Guard.Need(completed,"LIFETIME");if(error!=null)throw error;}}
}
}
