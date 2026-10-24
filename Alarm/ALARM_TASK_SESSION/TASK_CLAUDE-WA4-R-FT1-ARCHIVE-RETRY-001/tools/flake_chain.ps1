# TEST-FLAKY bounded repeats after the first full run (its F-S1 failure is kept as is), then a second full run.
$ErrorActionPreference = "Continue"
$tools = $PSScriptRoot
$py = (Resolve-Path (Join-Path $tools "..\..\..\..\.venv\Scripts\python.exe")).Path
$mirror = Join-Path ([IO.Path]::GetTempPath()) "claude-ft1-base-mirror"
$picker = "test_web_alarm_folder_picker.PickerHttpTests.test_wrong_origin_host_token_and_fetch_metadata_never_reach_helper"
"== fs1-base"; & $py -I -B "$tools\repeat_gate.py" $py fs1-base $mirror 10 $picker
"== fs1-final"; & $py -I -B "$tools\repeat_gate.py" $py fs1-final repo 10 $picker
"== ft1mod-base"; & $py -I -B "$tools\repeat_gate.py" $py ft1mod-base $mirror 10 test_web_alarm_aud01t02b_repair
"== ft1mod-final"; & $py -I -B "$tools\repeat_gate.py" $py ft1mod-final repo 10 test_web_alarm_aud01t02b_repair
"== full2"; & $py -I -B "$tools\run_gate.py" $py full2 all
"== chain done"
