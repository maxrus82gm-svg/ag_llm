# Original local attempt 01

15 collected: 13 PASS, 2 FAIL, 0 ERROR/SKIP. See local_attempt_01.json.

1. Stopped loopback HTTP produced HTTP_TIMEOUT on this Windows host, while the
test accepted only immediate HTTP_UNAVAILABLE. Both are explicit fail-closed
transport errors; network/VPN/proxy/firewall settings were not changed. The
corrected oracle requires one of these two exact transport codes, no ready
result, unchanged synthetic storage, and completion within three seconds.
This is not acceptance of an arbitrary exception or unknown successful result.

2. The isolated audit-hook probe successfully denied all three operations, but
its own TemporaryDirectory cleanup was outside its incorrectly narrowed write
root. Correct the probe's writable root to the whole owned disposable root;
attempt the denied write outside that root (denied before file creation).
Keep exact denial counters, absent outside file, and zero child exit checks.

No production source change. Original failed evidence is retained.
