"""Disposable Windows child deliberately hard-killed in Run Store append."""
from __future__ import annotations
from pathlib import Path
from contextlib import contextmanager
import os,sys,json
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
import run_store as runs
from web_alarm.colibri_bridge_transport import OfflineColibriTransport
from web_alarm.colibri_turn import ColibriTurnAdapter
from web_alarm.turn_service import TurnService

def main():
    arg=json.loads(Path(sys.argv[1]).read_text(encoding="utf8"))
    tr=OfflineColibriTransport(Path(arg["profile"]),expected_bridge_id=arg["bridge_id"])
    adapter=ColibriTurnAdapter(tr,lambda:[],lambda:{arg["target_id"]})
    service=TurnService(test_roots=[Path(arg["root"])],colibri_adapter=adapter)
    mode=arg["mode"]
    if mode not in ("after_stream","after_index"):
        raise ValueError("Invalid deliberate kill point")
    original_append=runs._append_run_record_locked
    original_open=runs._append_file
    original_clear=runs._clear_pending

    @contextmanager
    def abrupt_stream(path):
        with original_open(path) as stream:
            yield stream
        if path.name=="server.jsonl":os._exit(91)
    def abrupt_clear(path):
        os._exit(92)
    def append_with_injection(*a,**kw):
        if kw.get("event")=="turn_bridge_terminal":
            if mode=="after_stream":runs._append_file=abrupt_stream
            if mode=="after_index":runs._clear_pending=abrupt_clear
        return original_append(*a,**kw)
    runs._append_run_record_locked=append_with_injection
    service.submit(Path(arg["root"]),arg["workspace_id"],arg["chat_id"],arg["body"])
    raise RuntimeError("The expected Run Store hard exit was missed")

if __name__=="__main__":
    main()
