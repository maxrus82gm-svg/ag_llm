"""Only launched by disposable #663 test; forcibly exits itself at a selected boundary."""
from pathlib import Path
import os,sys,json
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from web_alarm.colibri_bridge_transport import OfflineColibriTransport
from web_alarm.colibri_turn import ColibriTurnAdapter
from web_alarm.turn_service import TurnService

def main():
    args=json.loads(Path(sys.argv[1]).read_text(encoding="utf8"))
    tr=OfflineColibriTransport(Path(args["profile"]),
        expected_bridge_id=args["bridge_id"])
    adapter=ColibriTurnAdapter(tr,lambda:[],lambda:{args["target_id"]})
    service=TurnService(test_roots=[Path(args["root"])],colibri_adapter=adapter)
    mode=args["mode"]
    if mode=="before_start":
        original=TurnService._event
        def die(root,turn,event,payload):
            if event=="turn_started":
                os._exit(86)  # ATTEMPTING summary exists but no start evidence
            return original(root,turn,event,payload)
        TurnService._event=staticmethod(die)
    if mode=="after_terminal":
        original=TurnService._settle_colibri
        def die(self,root,turn):
            if turn["state"]=="ATTEMPTING" and any(
                item["event"]=="turn_bridge_terminal" for item in self._records(root,turn)):
                os._exit(87)  # journal has verified terminal; assistant RAW not yet
            return original(self,root,turn)
        TurnService._settle_colibri=die
    result=service.submit(Path(args["root"]),args["workspace_id"],args["chat_id"],args["body"])
    if mode=="ordinary":
        print(json.dumps({"state":result["state"],"turn_id":result["turn_id"]}),flush=True)
        return
    raise RuntimeError("Expected hard exit before completion")

if __name__=="__main__":
    main()
