// Pure managed candidate logic. No OS identity lookup, sockets, registry or native imports.
using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using System.Text.RegularExpressions;
namespace Wua.Wfp {
    public sealed class Rejected : Exception { public Rejected(string code):base(code){} }
    public static class Guard {
        public static void Need(bool ok,string code){if(!ok)throw new Rejected(code);}
        public static bool Hash(string s){return s!=null&&Regex.IsMatch(s,"\\A[0-9a-f]{64}\\z");}
        public static string Digest(byte[] b){using(var h=SHA256.Create())return BitConverter.ToString(h.ComputeHash(b)).Replace("-","").ToLowerInvariant();}
        public static Guid Key(string s){byte[] b;using(var h=SHA256.Create())b=h.ComputeHash(Encoding.UTF8.GetBytes(s));var x=b.Take(16).ToArray();x[7]=(byte)((x[7]&15)|80);x[8]=(byte)((x[8]&63)|128);return new Guid(x);}
        public static uint Address(string text){
            Need(text!=null,"ADDRESS_REQUIRED");var parts=text.Split('.');Need(parts.Length==4,"LITERAL_IPV4_ONLY");uint value=0;
            foreach(var p in parts){byte n;Need(p.Length>0&&(p.Length==1||p[0]!='0')&&Regex.IsMatch(p,"\\A[0-9]{1,3}\\z")&&byte.TryParse(p,out n),"CANONICAL_IPV4_REQUIRED");value=(value<<8)|byte.Parse(p,CultureInfo.InvariantCulture);}return value;
        }
        public static uint[] LocalSid(string text){
            Need(text!=null&&Regex.IsMatch(text,"\\AS-1-5-21(?:-[0-9]{1,10}){4}\\z"),"LOCAL_ACCOUNT_SID_SHAPE_REQUIRED");
            var p=text.Split('-');var nums=new uint[5];for(int i=0;i<5;i++){uint n;Need(uint.TryParse(p[i+3],NumberStyles.None,CultureInfo.InvariantCulture,out n),"SID_RANGE");Need(n.ToString(CultureInfo.InvariantCulture)==p[i+3],"SID_CANONICAL");nums[i]=n;}
            Need(nums[1]>0&&nums[2]>0&&nums[3]>0&&nums[4]>=1000,"TECHNICAL_ACCOUNT_SID_REQUIRED");return nums;
        }
    }
    public sealed class Request {
        public readonly Guid Owner;public readonly string HostBinding,InventoryHash,ClientSid,BrokerSid,UiSid,Remote,Profile,Provenance;
        public readonly ushort LocalPort,RemotePort;public readonly DateTime ObservedUtc,ExpiresUtc;
        public Request(Guid owner,string host,string inventory,string client,string broker,string ui,ushort local,string remote,ushort port,DateTime observed,DateTime expires,string profile,string provenance){
            Guard.Need(owner!=Guid.Empty&&Guard.Hash(host)&&Guard.Hash(inventory),"OWNER_HOST_INVENTORY_REQUIRED");
            var clientParts=Guard.LocalSid(client);var brokerParts=Guard.LocalSid(broker);Guard.LocalSid(ui);Guard.Need(client!=broker&&client!=ui&&broker!=ui,"SID_ROLE_COLLISION");
            Guard.Need(clientParts.Take(4).SequenceEqual(brokerParts.Take(4)),"LOCAL_MACHINE_SID_PREFIX_MISMATCH");
            var a=Guard.Address(remote);Guard.Need((a>>24)>0&&(a>>24)!=127&&(a>>24)<224&&(a>>16)!=0xa9fe,"REMOTE_UNICAST_REQUIRED");
            Guard.Need(local>0&&port>0,"PORT_RANGE");Guard.Need(observed.Kind==DateTimeKind.Utc&&expires.Kind==DateTimeKind.Utc&&expires>observed&&expires-observed<=TimeSpan.FromMinutes(5),"FRESHNESS_INTERVAL");
            Guard.Need(profile=="STRICT_V2RAY_BROKER","PROFILE_FALLBACK_REJECTED");Guard.Need(provenance=="SYNTHETIC"||provenance=="UNVERIFIED_LOCAL_BINDING","PROVENANCE_NOT_AUTHORITY");
            Owner=owner;HostBinding=host;InventoryHash=inventory;ClientSid=client;BrokerSid=broker;UiSid=ui;LocalPort=local;Remote=remote;RemotePort=port;ObservedUtc=observed;ExpiresUtc=expires;Profile=profile;Provenance=provenance;
        }
        internal void Write(BinaryWriter w){w.Write(1);w.Write(Owner.ToByteArray());foreach(var s in new[]{HostBinding,InventoryHash,ClientSid,BrokerSid,UiSid,Remote,Profile,Provenance})w.Write(s);w.Write(LocalPort);w.Write(RemotePort);w.Write(ObservedUtc.Ticks);w.Write(ExpiresUtc.Ticks);}
        public string Digest(){using(var m=new MemoryStream()){using(var w=new BinaryWriter(m,Encoding.UTF8,true))Write(w);return Guard.Digest(m.ToArray());}}
        public void Fresh(DateTime now){Guard.Need(now.Kind==DateTimeKind.Utc&&now>=ObservedUtc&&now<ExpiresUtc,"STALE_OR_FUTURE_INVENTORY");}
    }
    public enum Field { User, Protocol, RemoteAddress, RemotePort }
    public enum Comparison { Equal=0,NotEqual=10 }
    public sealed class Condition {
        public readonly Field Field;public readonly Comparison Match;public readonly string Text;public readonly uint Number;
        public Condition(Field field,Comparison match,string text,uint number){Field=field;Match=match;Text=text??"";Number=number;}
        internal string Canonical(){return ((int)Field)+":"+((int)Match)+":"+Text+":"+Number.ToString(CultureInfo.InvariantCulture);}
    }
    public sealed class Filter {
        public readonly Guid Key,Provider,SubLayer;public readonly string Role;public readonly int Family;public readonly uint Action,Flags;public readonly ulong Weight;
        public readonly ReadOnlyCollection<Condition> Conditions;
        public Filter(Guid key,Guid provider,Guid sub,string role,int family,uint action,uint flags,ulong weight,IEnumerable<Condition> conditions){
            Guard.Need(conditions!=null,"CONDITIONS_REQUIRED");var items=conditions.ToArray();Guard.Need(items.All(c=>c!=null),"NULL_CONDITION");Key=key;Provider=provider;SubLayer=sub;Role=role;Family=family;Action=action;Flags=flags;Weight=weight;Conditions=Array.AsReadOnly(items);
        }
        public string Canonical(){return Key.ToString("D")+"|"+Provider.ToString("D")+"|"+SubLayer.ToString("D")+"|"+Role+"|"+Family+"|"+Action+"|"+Flags+"|"+Weight+"|"+String.Join(";",Conditions.Select(c=>c.Canonical()).OrderBy(s=>s,StringComparer.Ordinal));}
    }
    public sealed class Policy {
        public readonly Request Request;public readonly Guid Provider,SubLayer;public readonly ReadOnlyCollection<Filter> Filters;public readonly string ApprovalHash;
        public Policy(Request r,Guid provider,Guid sub,IEnumerable<Filter> filters){Guard.Need(r!=null&&filters!=null,"POLICY_REQUIRED");var items=filters.ToArray();Guard.Need(items.All(f=>f!=null),"NULL_FILTER");Request=r;Provider=provider;SubLayer=sub;Filters=Array.AsReadOnly(items);ApprovalHash=ComputeHash();}
        public string ComputeHash(){using(var m=new MemoryStream()){using(var w=new BinaryWriter(m,Encoding.UTF8,true)){Request.Write(w);w.Write(Provider.ToByteArray());w.Write(SubLayer.ToByteArray());foreach(var f in Filters.OrderBy(x=>x.Key))w.Write(f.Canonical());}return Guard.Digest(m.ToArray());}}
        public byte[] OwnershipBlob(){return Encoding.ASCII.GetBytes("WUA-WFP-v1|"+Request.Owner.ToString("D")+"|"+ApprovalHash);}
    }
    public static class Builder {
        public const uint Block=0x1001;public const uint Persistent=1;public const ulong FixedWeight=0x100;
        public static Policy Build(Request r){
            Guard.Need(r!=null,"REQUEST_REQUIRED");var root=r.Owner.ToString("D")+"|"+r.Digest();var provider=Guard.Key(root+"|provider");var sub=Guard.Key(root+"|sublayer");var filters=new List<Filter>();
            foreach(var role in new[]{"client","broker"}){
                var sid=role=="client"?r.ClientSid:r.BrokerSid;uint address=role=="client"?0x7f000001:Guard.Address(r.Remote);uint port=role=="client"?r.LocalPort:r.RemotePort;
                Func<Condition> user=()=>new Condition(Field.User,Comparison.Equal,sid,0);
                Func<Comparison,Condition> tcp=m=>new Condition(Field.Protocol,m,"",6);
                Func<Comparison,Condition> addr=m=>new Condition(Field.RemoteAddress,m,"",address);
                Action<int,string,Condition[]> add=(family,kind,conditions)=>filters.Add(new Filter(Guard.Key(root+"|"+role+"|"+kind),provider,sub,role,family,Block,Persistent,FixedWeight,conditions));
                add(6,"v6",new[]{user()});add(4,"non_tcp",new[]{user(),tcp(Comparison.NotEqual)});
                add(4,"other_address",new[]{user(),tcp(Comparison.Equal),addr(Comparison.NotEqual)});
                add(4,"other_port",new[]{user(),tcp(Comparison.Equal),addr(Comparison.Equal),new Condition(Field.RemotePort,Comparison.NotEqual,"",port)});
            }return new Policy(r,provider,sub,filters);
        }
    }
    public sealed class Packet {
        public readonly string Sid;public readonly int Family;public readonly byte Protocol;public readonly uint Address;public readonly ushort Port;
        public Packet(string sid,int family,byte protocol,uint address,ushort port){Guard.Need(family==4||family==6,"PACKET_FAMILY");Sid=sid;Family=family;Protocol=protocol;Address=address;Port=port;}
    }
    public static class PredicateInterpreter {
        public static int Matches(Policy p,Packet x){return p.Filters.Count(f=>f.Family==x.Family&&f.Conditions.All(c=>Match(c,x)));}
        private static bool Match(Condition c,Packet x){bool eq;switch(c.Field){case Field.User:eq=c.Text==x.Sid;break;case Field.Protocol:eq=c.Number==x.Protocol;break;case Field.RemoteAddress:eq=c.Number==x.Address;break;case Field.RemotePort:eq=c.Number==x.Port;break;default:throw new Rejected("UNKNOWN_FIELD");}Guard.Need(c.Match==Comparison.Equal||c.Match==Comparison.NotEqual,"UNKNOWN_COMPARATOR");return c.Match==Comparison.Equal?eq:!eq;}
    }
    // Verifies schema/objects independently of Builder.Build and policy hash regeneration.
    public static class StaticVerifier {
        public static void Verify(Policy p){
            Guard.Need(p!=null&&p.Filters.Count==8&&p.Filters.Select(f=>f.Key).Distinct().Count()==8,"FILTER_CARDINALITY");
            Guard.Need(p.Provider!=Guid.Empty&&p.SubLayer!=Guid.Empty&&p.Provider!=p.SubLayer,"OBJECT_KEYS");
            foreach(var role in new[]{"client","broker"}){
                var fs=p.Filters.Where(f=>f.Role==role).ToArray();Guard.Need(fs.Length==4,"ROLE_CARDINALITY");var patterns=new HashSet<string>();
                foreach(var f in fs){
                    Guard.Need(f.Key!=Guid.Empty&&f.Key!=p.Provider&&f.Key!=p.SubLayer&&f.Provider==p.Provider&&f.SubLayer==p.SubLayer&&f.Action==0x1001&&f.Flags==1&&f.Weight==256,"OBJECT_SEMANTICS");
                    Guard.Need(f.Conditions.Select(c=>c.Field).Distinct().Count()==f.Conditions.Count,"DUPLICATE_CONDITION");
                    var user=f.Conditions.SingleOrDefault(c=>c.Field==Field.User);Guard.Need(user!=null&&user.Match==Comparison.Equal&&user.Number==0&&user.Text==(role=="client"?p.Request.ClientSid:p.Request.BrokerSid),"SID_SELECTOR");
                    var rest=f.Conditions.Where(c=>c.Field!=Field.User).ToArray();
                    foreach(var c in rest){Guard.Need(c.Text==""&&(c.Match==Comparison.Equal||c.Match==Comparison.NotEqual),"CONDITION_DOMAIN");switch(c.Field){case Field.Protocol:Guard.Need(c.Number==6,"PROTOCOL_VALUE");break;case Field.RemoteAddress:Guard.Need(c.Number==(role=="client"?0x7f000001:Guard.Address(p.Request.Remote)),"ADDRESS_VALUE");break;case Field.RemotePort:Guard.Need(c.Number==(role=="client"?p.Request.LocalPort:p.Request.RemotePort),"PORT_VALUE");break;default:throw new Rejected("UNKNOWN_FIELD");}}
                    var sig=String.Join(",",rest.OrderBy(c=>c.Field).Select(c=>c.Field+"="+c.Match));
                    string token=f.Family+":"+sig;Guard.Need(patterns.Add(token),"DUPLICATE_PREDICATE");
                }
                var expected=new HashSet<string>{"6:","4:Protocol=NotEqual","4:Protocol=Equal,RemoteAddress=NotEqual","4:Protocol=Equal,RemoteAddress=Equal,RemotePort=NotEqual"};
                Guard.Need(patterns.SetEquals(expected),"DENY_COMPLEMENT_INCOMPLETE");
            }
            Guard.Need(p.Filters.All(f=>f.Role=="client"||f.Role=="broker"),"FOREIGN_ROLE");
        }
        public static void Binding(Policy p,Request r,string approval,DateTime now){
            Guard.Need(r!=null&&p!=null&&r.Digest()==p.Request.Digest(),"REQUEST_BINDING");r.Fresh(now);Verify(p);
            Guard.Need(Guard.Hash(approval)&&approval==p.ApprovalHash&&p.ComputeHash()==approval,"APPROVAL_BINDING");
            var generated=Builder.Build(r);Guard.Need(generated.ApprovalHash==approval,"PLAN_NOT_GENERATED_FROM_REQUEST");
        }
    }
    public static class OfflineBackend {
        public static bool CanApply{get{return false;}}
        public static string Apply(Policy p,Request r,string approval,DateTime now){StaticVerifier.Binding(p,r,approval,now);return "BLOCKED:NO_LAB_ACCEPTED_NATIVE_BACKEND";}
        public static string Rollback(Policy p,bool reportedZero){return "ROLLBACK_BLOCKED:KEEP_DENY:UNTRUSTED_QUIESCENCE";}
    }
    public enum Observation { Unknown,KnownFalse,ClaimedTrue }
    public sealed class Admission {
        public readonly bool Allowed=false;public readonly ReadOnlyCollection<string> Blockers;
        public Admission(Observation broker,Observation bfe,Observation receiver,Observation child,Observation dns,Observation upstream){
            var reasons=new List<string>{"RELEASE_OFFLINE_NO_EXECUTABLE_APPLY","NO_TRUSTED_OS_LAB_PROOF"};
            var values=new[]{broker,bfe,receiver,child,dns,upstream};var names=new[]{"BROKER","BFE","RECEIVER_OWNER","CHILD_IDENTITY","DNS_DELEGATION","AUTHENTICATED_UPSTREAM"};
            for(int i=0;i<values.Length;i++){Guard.Need(Enum.IsDefined(typeof(Observation),values[i]),"UNKNOWN_OBSERVATION_ENUM");if(values[i]==Observation.KnownFalse)reasons.Add(names[i]+"_FAILED");else if(values[i]==Observation.Unknown)reasons.Add(names[i]+"_UNKNOWN");else reasons.Add(names[i]+"_CLAIM_NOT_AUTHORITY");}Blockers=Array.AsReadOnly(reasons.ToArray());
        }
    }
    public sealed class CompetingFilter {
        public readonly int Family;public readonly string Action;public readonly ushort SubLayerWeight;public readonly ulong FilterWeight;
        public CompetingFilter(int family,string action,ushort subWeight,ulong filterWeight){Guard.Need((family==4||family==6)&&(action=="BLOCK"||action=="SOFT_PERMIT"||action=="HARD_PERMIT"||action=="CALLOUT"||action=="UNKNOWN"),"SURVEY_ITEM_DOMAIN");Family=family;Action=action;SubLayerWeight=subWeight;FilterWeight=filterWeight;}
    }
    public static class ArbitrationSurvey {
        // A conservative diagnostic, deliberately NOT a Windows arbitration emulator.
        public static ReadOnlyCollection<string> Assess(IEnumerable<CompetingFilter> filters,bool snapshotComplete){
            Guard.Need(filters!=null,"SURVEY_REQUIRED");var rows=filters.ToArray();Guard.Need(rows.All(f=>f!=null),"NULL_SURVEY_ITEM");
            var reasons=new List<string>{"LAB_ARBITRATION_NOT_VERIFIED"};if(!snapshotComplete)reasons.Add("EFFECTIVE_GRAPH_INCOMPLETE");
            foreach(var f in rows)reasons.Add(f.Action=="BLOCK"?"COMPETING_BLOCK_AVAILABILITY_UNVERIFIED":"COMPETING_"+f.Action+"_PRECEDENCE_UNVERIFIED");
            return Array.AsReadOnly(reasons.ToArray());
        }
    }
    // In-memory transaction exercise only. Sealed store prevents native transport injection.
    public sealed class MemoryStore {
        internal Dictionary<Guid,string> Objects=new Dictionary<Guid,string>();internal Dictionary<Guid,string> Staged;
        public readonly List<string> Trace=new List<string>();public int FailAddAt=-1;public bool LoseCommitAck,FailAbort,FailReadback,FailReadbackAfterCommit,TaintAfterCommit;private int adds;
        public int Count{get{return Objects.Count;}}
        public void Seed(Guid key,string content){Objects.Add(key,content);}
        internal string Get(Guid key){if(FailReadback)throw new Rejected("READBACK_UNKNOWN");string s;return Objects.TryGetValue(key,out s)?s:null;}
        internal void Begin(){Guard.Need(Staged==null,"TRANSACTION_OPEN");Trace.Add("BEGIN");Staged=new Dictionary<Guid,string>(Objects);adds=0;}
        internal void Add(Guid key,string data){Trace.Add("ADD");if(adds++==FailAddAt)throw new Rejected("INJECTED_ADD_FAILURE");Guard.Need(Staged!=null&&!Staged.ContainsKey(key),"OBJECT_ALREADY_PRESENT");Staged.Add(key,data);}
        internal void Commit(){Trace.Add("COMMIT");Objects=Staged;Staged=null;if(TaintAfterCommit)Objects[Objects.Keys.First()]="INJECTED_DRIFT";if(FailReadbackAfterCommit)FailReadback=true;if(LoseCommitAck)throw new Rejected("COMMIT_OUTCOME_UNKNOWN");}
        internal void Abort(){Trace.Add("ABORT");if(FailAbort)throw new Rejected("ABORT_OUTCOME_UNKNOWN");Staged=null;}
    }
    public sealed class SimulationResult {
        public readonly string Status;public readonly bool KeepDeny=true;public readonly int MutationsToWindows=0;
        internal SimulationResult(string status){Status=status;}
    }
    public static class TransactionSimulation {
        private static Dictionary<Guid,string> Expected(Policy p){var d=new Dictionary<Guid,string>();string tag=Encoding.ASCII.GetString(p.OwnershipBlob());d.Add(p.Provider,"provider|"+tag);d.Add(p.SubLayer,"sublayer|"+tag);foreach(var f in p.Filters)d.Add(f.Key,"filter|"+tag+"|"+f.Canonical());return d;}
        public static SimulationResult Stage(MemoryStore store,Policy p,string approval,DateTime now){
            Guard.Need(store!=null,"STORE_REQUIRED");StaticVerifier.Binding(p,p.Request,approval,now);var desired=Expected(p);
            if(store.Staged!=null)return new SimulationResult("BLOCKED:PRIOR_TRANSACTION_UNKNOWN_KEEP_DENY");
            try {var actual=desired.ToDictionary(x=>x.Key,x=>store.Get(x.Key));if(actual.Any(x=>x.Value!=null)){
                if(actual.All(x=>x.Value==desired[x.Key]))return new SimulationResult("MOCK_ALREADY_PRESENT_NO_DUPLICATION");
                return new SimulationResult("BLOCKED:PARTIAL_OR_FOREIGN_READBACK");}
            }catch(Rejected){return new SimulationResult("BLOCKED:READBACK_UNKNOWN");}
            bool committed=false;try{
                store.Begin();foreach(var row in desired)store.Add(row.Key,row.Value);
                committed=true;store.Commit(); // Set before call: lost acknowledgement is an unknown outcome.
                foreach(var row in desired)Guard.Need(store.Get(row.Key)==row.Value,"READBACK_DRIFT");
                return new SimulationResult("MOCK_STAGED_ONLY_NOT_ENFORCEMENT");
            }catch(Rejected){
                if(committed)return new SimulationResult("BLOCKED:COMMIT_OR_READBACK_UNKNOWN_KEEP_DENY");
                try{store.Abort();return new SimulationResult("BLOCKED:ABORTED_NO_ACTIVATION");}catch(Rejected){return new SimulationResult("BLOCKED:ABORT_UNKNOWN_KEEP_DENY");}
            }
        }
        public static SimulationResult RemovalPlan(MemoryStore store,Policy p,Guid ledgerOwner,string ledgerHash,bool reportedZero){
            Guard.Need(store!=null&&p!=null&&ledgerOwner==p.Request.Owner&&ledgerHash==p.ApprovalHash,"FOREIGN_OR_STALE_LEDGER");
            foreach(var row in Expected(p)){Guard.Need(store.Get(row.Key)==row.Value,"OWNERSHIP_OR_DRIFT_UNKNOWN");}
            return new SimulationResult("ROLLBACK_BLOCKED:NEED_INDEPENDENT_PROCESS_FLOW_WORK_ZERO:KEEP_DENY");
        }
    }
}
