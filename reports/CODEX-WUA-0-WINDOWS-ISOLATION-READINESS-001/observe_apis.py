"""Read-only export availability/current-token metadata. Never invokes WFP/NPFS APIs.

DLLs restricted to Windows System32. No network, subprocess, ACL or registry access.
No token identity, group membership or privilege dump is serialized.
"""
import ctypes as c
from ctypes import wintypes as w
import datetime, json, os

def collect():
    result = {"schema": 1, "collected_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "classification": "OBSERVED_READ_ONLY", "exports": {}, "native_network_tests_run": 0}
    if os.name != 'nt':
        return dict(result, classification='BLOCKED', reason='HOST_READ_ONLY_UNAVAILABLE')
    def load(name):
        return c.WinDLL(name, use_last_error=True, winmode=0x800)  # LOAD_LIBRARY_SEARCH_SYSTEM32
    modules = {
        'fwpuclnt.dll': ['FwpmEngineOpen0','FwpmFilterAdd0','FwpmFilterGetByKey0','FwpmTransactionBegin0','FwpmEngineClose0'],
        'kernel32.dll': ['CreateNamedPipeW','GetNamedPipeClientProcessId','GetNamedPipeServerProcessId'],
        'advapi32.dll': ['GetTokenInformation','OpenProcessToken','GetNamedSecurityInfoW','AccessCheck','ImpersonateNamedPipeClient','CreateProcessAsUserW'],
    }
    for name, exports in modules.items():
        try:
            module = load(name)
            result['exports'][name] = {symbol: hasattr(module, symbol) for symbol in exports}
        except OSError as exc:
            result['exports'][name] = {'classification': 'BLOCKED', 'winerror': exc.winerror}
    try:
        kernel, adv = load('kernel32.dll'), load('advapi32.dll')
        kernel.GetCurrentProcess.restype = w.HANDLE
        kernel.CloseHandle.argtypes = [w.HANDLE]
        adv.OpenProcessToken.argtypes = [w.HANDLE,w.DWORD,c.POINTER(w.HANDLE)]
        adv.GetTokenInformation.argtypes = [w.HANDLE,c.c_int,c.c_void_p,w.DWORD,c.POINTER(w.DWORD)]
        token = w.HANDLE()
        if not adv.OpenProcessToken(kernel.GetCurrentProcess(), 8, c.byref(token)):
            raise c.WinError(c.get_last_error())
        try:
            elevated, needed = w.DWORD(), w.DWORD()
            if not adv.GetTokenInformation(token,20,c.byref(elevated),c.sizeof(elevated),c.byref(needed)):
                raise c.WinError(c.get_last_error())
            result['current_token_elevated'] = bool(elevated.value)
        finally:
            kernel.CloseHandle(token)
    except OSError as exc:
        result['current_token_query'] = {'classification': 'BLOCKED', 'winerror': exc.winerror}
    result['limitation'] = 'Exports are presence only; no WFP session, filter access, pipe creation, impersonation or identity launch attempted.'
    return result

if __name__ == '__main__':
    print(json.dumps(collect(), indent=2))
