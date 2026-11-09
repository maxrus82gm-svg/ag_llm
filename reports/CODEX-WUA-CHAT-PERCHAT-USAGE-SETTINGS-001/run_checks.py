from pathlib import Path
import hashlib,json,os,subprocess,sys,time
root=Path(__file__).resolve().parents[2]; pkg=Path(__file__).resolve().parent
stage=sys.argv[1]
commands=[("python",[str(root/".venv/Scripts/python.exe"),"-B","-X","utf8","-m","unittest","-v","test_web_alarm_perchat_usage_settings"]),("js",["node","--test","test_web_alarm_ultra_chat_ui.js"])]
if stage=="ui_final":commands=[item for item in commands if item[0]=="js"]
failed=False
for label,cmd in commands:
 prefix=pkg/"evidence"/(stage+"_"+label)
 assert not prefix.with_suffix(".result.json").exists()
 env={k:os.environ[k] for k in os.environ if not k.upper().startswith("GIGACHAT_") and k.upper()!="NODE_OPTIONS"}
 env.update(PYTHONDONTWRITEBYTECODE="1",PYTEST_DISABLE_PLUGIN_AUTOLOAD="1")
 if label=="python":
  env.update(PYTHONPATH=str(root/"reports/CODEX-WUA-CHAT-ORDINARY-CORE-BRIDGE-001/guard")+os.pathsep+str(root),ORDINARY_GUARD_LOG=str(prefix.with_suffix(".guard.jsonl")),ORDINARY_GUARD_NETWORK="loopback",ORDINARY_GUARD_ROOT=str(root))
 start=time.monotonic(); result=subprocess.run(cmd,cwd=root,env=env,capture_output=True,timeout=90)
 for suffix,data in [(".stdout.txt",result.stdout),(".stderr.txt",result.stderr)]:prefix.with_suffix(suffix).write_bytes(data)
 pins={n:hashlib.sha256((root/n).read_bytes()).hexdigest() for n in ["web_alarm/ultra_chat.py","web_alarm/ui.py","test_web_alarm_perchat_usage_settings.py","test_web_alarm_ultra_chat_ui.js"]}
 prefix.with_suffix(".result.json").write_text(json.dumps({"command":cmd,"exit_code":result.returncode,"elapsed_seconds":time.monotonic()-start,"source_sha256":pins},indent=2),encoding="utf-8")
 print(label,result.returncode,(result.stderr if label=="python" else result.stdout).decode("utf-8",errors="replace")[-1800:])
 failed |= result.returncode!=0
raise SystemExit(1 if failed else 0)
