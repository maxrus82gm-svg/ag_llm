"""Focused existing launcher/activation modules; strict offline, synthetic storage."""
from pathlib import Path
import json, os, subprocess, sys, tempfile

ROOT = Path(__file__).resolve().parents[2]
PKG = Path(__file__).resolve().parent
TESTS = ["test_web_alarm_launcher.ConfigTests", "test_web_alarm_launcher.BannerAndPageTests",
         "test_web_alarm_launcher.StableEntryTests",
         "test_web_alarm_launcher.RunTests.test_r7_script_profile_warns_then_runs_the_script_and_cannot_self_test",
         "test_web_alarm_launcher.RunTests.test_r8_a_refused_configuration_stops_with_a_red_message_and_nothing_starts",
         "test_web_alarm_ordinary_test_activation.ActivationTests.test_active_profile_uses_bridge_and_old_stage5_is_available",
         "test_web_alarm_ordinary_test_activation.ActivationTests.test_missing_test_config_cannot_fall_back_to_standard"]

if __name__ == "__main__":
    stage = sys.argv[1]
    if "--child" in sys.argv:
        import runpy
        runpy.run_path(str(ROOT / "reports/CODEX-WUA-CHAT-ORDINARY-CORE-BRIDGE-001/guard/sitecustomize.py"))
        import unittest
        names = TESTS if stage != "red" else ["test_web_alarm_launcher.StableEntryTests.test_require_test_denies_script_args_name_kind_and_path_substitutions"]
        result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromNames(names))
        print(json.dumps(dict(tests=result.testsRun, failures=len(result.failures), errors=len(result.errors), skipped=len(result.skipped), guard_installed=True)))
        sys.exit(not result.wasSuccessful())
    prefix = PKG / "evidence" / stage
    assert not prefix.with_suffix(".result.json").exists()
    with tempfile.TemporaryDirectory(prefix="f01_checks_") as temp:
        env = {k:v for k,v in os.environ.items() if not k.upper().startswith("GIGACHAT_") and k.upper() not in ("PYTHONPATH", "PYTHONSTARTUP")}
        env.update(PYTHONPATH=str(ROOT), PYTHONDONTWRITEBYTECODE="1", LOCALAPPDATA=temp,
                   ORDINARY_GUARD_LOG=str(prefix.with_suffix(".guard.jsonl")), ORDINARY_GUARD_NETWORK="deny", ORDINARY_GUARD_ROOT=str(ROOT))
        cmd = [str(ROOT / ".venv/Scripts/python.exe"), "-B", "-X", "utf8", str(Path(__file__).resolve()), stage, "--child"]
        run = subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, timeout=60)
    prefix.with_suffix(".stdout.txt").write_bytes(run.stdout)
    prefix.with_suffix(".stderr.txt").write_bytes(run.stderr)
    facts = json.loads(run.stdout.decode("utf-8").strip().splitlines()[-1])
    log = prefix.with_suffix(".guard.jsonl")
    facts.update(exit_code=run.returncode, command=cmd, python=sys.version, guard_violations=len(log.read_text().splitlines()) if log.exists() else 0)
    prefix.with_suffix(".result.json").write_text(json.dumps(facts, indent=2), encoding="utf-8")
    print(json.dumps(facts, indent=2)); print(run.stderr.decode("utf-8", errors="replace")[-650:])
    sys.exit(run.returncode)
