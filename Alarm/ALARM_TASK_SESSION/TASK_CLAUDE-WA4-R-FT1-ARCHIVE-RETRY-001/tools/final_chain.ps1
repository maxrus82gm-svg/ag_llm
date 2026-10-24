# Final evidence chain on the final source bytes, strictly sequential (no source edits while it runs).
# Every step writes only into disposable TEMP; collect_runs.py publishes sanitized copies afterwards.
$ErrorActionPreference = "Continue"
$tools = $PSScriptRoot
$py = (Resolve-Path (Join-Path $tools "..\..\..\..\.venv\Scripts\python.exe")).Path
$flaky = "test_web_alarm_aud01t02b_repair.TransportDurabilityTests.test_concurrent_processes_lose_no_transport_event"
$mirror = Join-Path ([IO.Path]::GetTempPath()) "claude-ft1-base-mirror"
"== mutA"; & $py -I -B "$tools\run_mutants.py" $py mutA test_web_alarm_runner_guard final A1-no-prefix-strip A2-explicit-prefix-stripped-too A3-no-deleted-retry A4-deleted-trusted-by-spelling A5-write-check-disabled A6-git-check-removed
"== mutBF"; & $py -I -B "$tools\run_mutants.py" $py mutBF test_web_alarm_transport_event_recovery final B1-tail-unchecked B2-receipt-ignored B3-any-outcome B4-receipt-required B5-archive-unchecked B6-replace-failure-rejected B7-result-unchecked B8-identity-unchecked B9-source-prefix-unchecked
"== flake-base"; & $py -I -B "$tools\repeat_gate.py" $py flake-base $mirror 20 $flaky
"== flake-final"; & $py -I -B "$tools\repeat_gate.py" $py flake-final repo 20 $flaky
"== full"; & $py -I -B "$tools\run_gate.py" $py full all
"== chain done"
