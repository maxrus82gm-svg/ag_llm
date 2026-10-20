// Offline RSA-PKCS1/SHA256 verification and SYNTHETIC-only ephemeral fixture signer.
// No persistent key container, certificate-store, network, VM or WFP operation.
using System;using System.IO;using System.Linq;using System.Collections.Generic;
using System.Security.Cryptography;using System.Web.Script.Serialization;
internal static class Signatures {
    static byte[] Hash(string s){if(s==null||s.Length!=64||s.Any(c=>!"0123456789abcdef".Contains(c)))throw new Exception("HASH_FORMAT");return Enumerable.Range(0,32).Select(i=>Convert.ToByte(s.Substring(i*2,2),16)).ToArray();}
    static RSACng New(){return new RSACng(2048);} // unnamed, ephemeral CNG key; never exported private
    static int Main(string[] args){try{
        if(args.Length!=1)return 20;
        if(args[0]=="verify"){
            var n=Convert.FromBase64String(Console.ReadLine());var e=Convert.FromBase64String(Console.ReadLine());var h=Hash(Console.ReadLine());var s=Convert.FromBase64String(Console.ReadLine());
            if(n.Length!=256||e.Length!=3||e[0]!=1||e[1]!=0||e[2]!=1||s.Length!=256)return 10;
            using(var rsa=New()){rsa.ImportParameters(new RSAParameters{Modulus=n,Exponent=e});return rsa.VerifyHash(h,s,HashAlgorithmName.SHA256,RSASignaturePadding.Pkcs1)?0:10;}
        }
        if(args[0]!="synthetic-session")return 20;
        var keys=new Dictionary<string,RSACng>();try{
            var pub=new Dictionary<string,object>();foreach(var role in new[]{"host","guest","review"}){var rsa=New();keys.Add(role,rsa);var p=rsa.ExportParameters(false);pub.Add(role,new{n=Convert.ToBase64String(p.Modulus),e=Convert.ToBase64String(p.Exponent)});}
            Console.WriteLine(new JavaScriptSerializer().Serialize(pub));Console.Out.Flush();
            for(int i=0;i<256;i++){var line=Console.ReadLine();if(line==null||line=="close")return 0;var parts=line.Split(' ');if(parts.Length!=2||!keys.ContainsKey(parts[0]))return 21;Console.WriteLine(Convert.ToBase64String(keys[parts[0]].SignHash(Hash(parts[1]),HashAlgorithmName.SHA256,RSASignaturePadding.Pkcs1)));Console.Out.Flush();}
            return 22;
        }finally{foreach(var k in keys.Values)k.Dispose();}
    }catch{Console.WriteLine("BLOCKED:CRYPTO_INPUT_OR_RUNTIME");return 23;}}
}
