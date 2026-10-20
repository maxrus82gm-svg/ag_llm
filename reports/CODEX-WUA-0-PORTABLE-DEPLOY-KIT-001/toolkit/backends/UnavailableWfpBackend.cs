// Source-only boundary contract. Not loaded, built, or used to modify Windows by this kit.
// C# 5 syntax, no NuGet, no P/Invoke, no process launches, no kernel driver.
// A real implementation requires reviewed Fwpm transaction/readback, security descriptors,
// ownership ACLs, account/logon APIs, and independent target-Windows safety proof.
using System;
namespace WuaMcp {
    public interface IProvisioningBackend {
        bool CanApply { get; }
        string CreateDisabledLocalAccount(string role, Guid owner);
        void ResolveNewLocalSids(Guid owner);
        void AssignLeastLogonRightsAndOwnedAcls(Guid owner);
        void InstallReviewedWfpPolicy(Guid owner, string planHash);
        void RegisterDisabledStartup(Guid owner);
        void ReadBackEffectiveState(Guid owner);
        void QuiesceAndVerifyNoOwnedWork(Guid owner);
        void RollbackOwnedResources(Guid owner);
    }
    public sealed class UnavailableWfpBackend : IProvisioningBackend {
        public bool CanApply { get { return false; } }
        private static Exception Blocked() { return new NotSupportedException("NO_REVIEWED_EXECUTABLE_SECURITY_BACKEND"); }
        public string CreateDisabledLocalAccount(string role, Guid owner) { throw Blocked(); }
        public void ResolveNewLocalSids(Guid owner) { throw Blocked(); }
        public void AssignLeastLogonRightsAndOwnedAcls(Guid owner) { throw Blocked(); }
        public void InstallReviewedWfpPolicy(Guid owner, string planHash) { throw Blocked(); }
        public void RegisterDisabledStartup(Guid owner) { throw Blocked(); }
        public void ReadBackEffectiveState(Guid owner) { throw Blocked(); }
        public void QuiesceAndVerifyNoOwnedWork(Guid owner) { throw Blocked(); }
        public void RollbackOwnedResources(Guid owner) { throw Blocked(); }
    }
}
