using System;
using System.IO;
using System.IO.Pipes;
using System.Threading;
using WuaNpfs;

// C-owned executable has no child-launch or socket APIs. All configuration is fixture-only.
public static class Relay {
    public static int Main(string[] args) {
        using(var watchdog=new Timer(delegate{Environment.Exit(20);},null,40000,Timeout.Infinite)) {
        try {using(var tcp=new System.Net.Sockets.TcpClient("127.0.0.1",51845)) {System.Threading.Thread.Sleep(400);} Guard.Need(args.Length==5,"FIXTURE_ARGUMENTS");Guard.Need(args[0]=="synthetic_fixture_only","FIXTURE_ONLY");string name=Guard.PipeName(args[1]);uint expectedPid;Guard.Need(uint.TryParse(args[2],out expectedPid)&&expectedPid>0,"SERVER_PID");string sid=Guard.Sid(args[3]),hash=args[4];byte[] grant=Guard.Unhex(Environment.GetEnvironmentVariable("WUA_NPFS_GRANT"));string session=Environment.GetEnvironmentVariable("WUA_NPFS_SESSION");Environment.SetEnvironmentVariable("WUA_NPFS_GRANT",null);Environment.SetEnvironmentVariable("WUA_NPFS_SESSION",null);
            string path="\\\\.\\pipe\\"+name;Guard.Need(Native.WaitNamedPipe(path,1200),"PIPE_UNAVAILABLE");
            // Exact data/attributes/synchronize rights: no FILE_CREATE_PIPE_INSTANCE. Identification-only SQOS.
            using(var handle=Native.CreateFile(path,0x00100083,0,IntPtr.Zero,3,0x40110000,IntPtr.Zero)) {
                Guard.Need(!handle.IsInvalid,"PIPE_OPEN");using(var pipe=new NamedPipeClientStream(PipeDirection.InOut,true,true,handle)) {
                    uint pid;Guard.Need(Native.GetNamedPipeServerProcessId(handle,out pid)&&pid==expectedPid,"SERVER_PID_MISMATCH");
                    using(var peer=new Native.Peer(pid,sid,hash)) {
                        var wire=new Wire(pipe,session,grant,true);wire.Send(Guard.Bytes("hello"),Guard.InputLimit);Guard.Need(Guard.Text(wire.Receive(Guard.OutputLimit))=="ready","HANDSHAKE");Array.Clear(grant,0,grant.Length);
                        Console.Error.WriteLine("RELAY_AUTHENTICATED");var rpc=new Rpc();Stream input=Console.OpenStandardInput(),output=Console.OpenStandardOutput();var lines=new Io.Lines(input);
                        Bridge.Run(delegate{while(true){var raw=lines.Next(Guard.InputLimit);if(raw==null){wire.Send(Guard.Bytes("close"),Guard.InputLimit);return;}rpc.Check(raw,true);wire.Send(raw,Guard.InputLimit);}},delegate{while(true){var raw=wire.Receive(Guard.OutputLimit);rpc.Check(raw,false);Io.Write(output,raw);Io.Write(output,new byte[]{10});}},delegate{pipe.Dispose();input.Dispose();output.Dispose();});
                    }
                }
            }
            return 0;
        }catch(Exception e){Console.Error.WriteLine("RELAY_STOP:"+(e is Refusal?e.Message:e.GetType().Name));return 20;}
        }
    }
}
