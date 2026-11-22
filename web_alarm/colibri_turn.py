"""Isolated Colibri provider binding for the existing Turn/RAW/RUN.

No alternate chat store, ledger, or real provider authority. V3 snapshots
contain the exact local wire and no bearer or discovery credentials. Readers
can validate durable v3 evidence without an active bridge or an adapter.
"""
from dataclasses import asdict
from functools import lru_cache
import hashlib
import math
import re

from .colibri_bridge_transport import (
    BridgeFault, Contract, FrozenBridgeRequest, OfflineColibriTransport,
    MAX_BODY, canonical, strict_json,
)

CONFIG_REF = "colibri-offline:v1"
TARGET = re.compile(r"tgt_[0-9a-f]{64}")
# Existing shared RAW/read projection limits, not model token limits.
# Oversized replies remain partial UNKNOWN, never silently truncated.
MAX_RAW_JSON = 1024 * 1024 - 8192  # existing bounded RAW/context JSON reader
FIELDS = set(FrozenBridgeRequest.__dataclass_fields__) - {"wire"}
STATES = {"SUCCEEDED", "FAILED", "CANCELLED", "UNKNOWN"}
ERROR_CODE = re.compile(r"[a-z0-9_]{1,80}")


@lru_cache(maxsize=1)
def schema():
    return Contract()


def model_ref(value):
    return type(value) is str and TARGET.fullmatch(value) is not None


def restore(snapshot, turn):
    if (type(snapshot) is not dict
            or set(snapshot) != {"wire_utf8", "request_ref", "binding"}
            or type(snapshot["binding"]) is not dict
            or set(snapshot["binding"]) != FIELDS
            or type(snapshot["wire_utf8"]) is not str):
        raise ValueError("Damaged local snapshot")
    try:
        f = FrozenBridgeRequest(wire=snapshot["wire_utf8"].encode("utf-8"),
                                **snapshot["binding"])
        req = schema().check("ChatRequest", strict_json(f.wire))
        if (len(f.wire)>MAX_BODY or canonical(req)!=f.wire
                or hashlib.sha256(f.wire).hexdigest()!=f.sha256
                or snapshot["request_ref"]!="sha256:"+f.sha256
                or f.target_id!=turn["references"]["model_ref"]
                or req["conversation_id"]!=turn["chat_id"]
                or req["turn_id"]!=turn["turn_id"]
                or f.request_id!=turn["attempt_id"].removeprefix("attempt_")[:32]
                or any(req[k]!=getattr(f,k) for k in ("request_id","target_id","instance_id"))
                or not model_ref(f.target_id)
                or type(f.idle_timeout) is not int or not 1<=f.idle_timeout<=3600
                or any(type(getattr(f,k)) is not str or not getattr(f,k) or len(getattr(f,k))>256
                       for k in FIELDS-{"idle_timeout"})
                or not re.fullmatch(r"[0-9a-f]{32}",f.launch_identity)
                or req["messages"][-1]["role"]!="user"
                or any(m["role"] not in {"user","assistant"} for m in req["messages"])):
            raise ValueError("Damaged local binding")
        return f,req
    except (BridgeFault, TypeError, KeyError, UnicodeError, ValueError, IndexError):
        raise ValueError("Damaged local binding") from None


class ColibriTurnAdapter:
    """Server-created, exact offline authority. Registry admission is a callable
    from the owning service, never a browser-provided set or credential."""
    def __init__(self, transport, context_loader, enabled_targets):
        if type(transport) is not OfflineColibriTransport or not callable(context_loader) or not callable(enabled_targets):
            raise ValueError("Explicit offline transport and server admission required")
        self.transport=transport
        self.context_loader=context_loader
        self.enabled_targets=enabled_targets

    def freeze(self, body, ids, chat_id):
        try:
            f=self.transport.prepare(request_id=ids["attempt_id"].removeprefix("attempt_")[:32],
                target_id=body["model_ref"],
                messages=[*self.context_loader(),{"role":"user","content":body["text"]}],
                conversation_id=chat_id,turn_id=ids["turn_id"],
                enabled_targets=self.enabled_targets())
            b=asdict(f);b.pop("wire")
            return dict(wire_utf8=f.wire.decode("utf-8"),request_ref="sha256:"+f.sha256,binding=b)
        except BridgeFault as exc:
            from .ultra_chat import UltraChatError
            raise UltraChatError(409, exc.code, "Local model admission refused") from None

    def execute(self, f, *, on_event, before_dispatch):
        return self.transport.run(f,on_event=on_event,before_dispatch=before_dispatch)

    def cancel(self, f):
        return self.transport.cancel(f)


def start(turn):
    return dict(attempt_id=turn["attempt_id"],mode="COLIBRI_OFFLINE",
                request_ref=turn["prepared"]["request_ref"],binding_sha256=turn["binding_sha256"])


def evidence(turn,records):
    """Check the ordered append-only evidence and derive partial text strictly
    from validated SSE packets, never from a separate answer or chat store."""
    f,_=restore(turn["prepared"],turn)
    expected=start(turn)
    started=dispatched=cancelled=False
    ack=None;terminal=None;done=None;error=None;usage=None;telemetry=None
    answers=[];reasoning=[];seq=0;rank=-1
    for rec in records:
        kind,p=rec["event"],rec["payload"]
        if type(p) is not dict:
            raise ValueError("Invalid local event")
        if kind=="turn_started":
            if started or cancelled or p!=expected:
                raise ValueError("Duplicate local start")
            started=True
        elif kind=="turn_bridge_dispatch":
            if not started or dispatched or cancelled or terminal or p!=expected:
                raise ValueError("Invalid local dispatch")
            dispatched=True
        elif kind=="turn_cancel_requested":
            if cancelled or terminal or p!=expected:
                raise ValueError("Invalid local cancel")
            cancelled=True
        elif kind=="turn_bridge_cancel_ack":
            if not cancelled or ack is not None or not dispatched:
                raise ValueError("Unexpected local cancel acknowledgement")
            if p.get("ack") is not None:
                schema().check("CancelResponse",p["ack"])
                match_identity(f,p["ack"])
            if set(p)!={"ack"}:
                raise ValueError("Invalid acknowledgement")
            ack=p
        elif kind=="turn_bridge_packet":
            if not dispatched or terminal or done or set(p)!={"packet"}:
                raise ValueError("Invalid local packet ordering")
            e=schema().check("Event",p["packet"])
            t=e["type"]
            if e["sequence"]!=seq or e["request_id"]!=f.request_id or (seq==0)!=(t=="meta"):
                raise ValueError("Local packet sequence/identity mismatch")
            seq+=1
            if t=="meta":
                if any(e[k]!=getattr(f,k) for k in ("bridge_id","target_id","instance_id","manager_id","slot_id","model_id")):
                    raise ValueError("Local meta mismatch")
            elif t=="status":
                n={"ACCEPTED":0,"RUNNING":1,"CANCEL_REQUESTED":2}[e["state"]]
                if n<rank:raise ValueError("Local status regressed")
                rank=n
            elif t=="delta":answers.append(e["text"])
            elif t=="reasoning":reasoning.append(e["text"])
            elif t=="usage":usage=schema().check("Usage",e["usage"])
            elif t=="telemetry":telemetry=e["telemetry"]
            elif t=="error":
                if error is not None:raise ValueError("Duplicate local error")
                error=e["error"]["code"]
            elif t=="done":
                final=schema().check("Usage",e["usage"])
                if (usage is not None and usage!=final
                        or (e["error"] or {}).get("code")!=error
                        or (e["state"] in {"FAILED","UNKNOWN"})!=(e["error"] is not None)):
                    raise ValueError("Local terminal packet mismatch")
                usage=final;done=e
        elif kind=="turn_bridge_terminal":
            if not started or terminal is not None or set(p)!={"state","error_code","remote_state","ttft_ms","elapsed_ms"}:
                raise ValueError("Invalid local terminal")
            state=p["state"]
            if state not in STATES:
                raise ValueError("Invalid local state")
            if p["error_code"] is not None and (type(p["error_code"]) is not str or not ERROR_CODE.fullmatch(p["error_code"])):
                raise ValueError("Invalid local diagnostic")
            if p["remote_state"] is not None:
                schema().check("RequestStatus",p["remote_state"]);match_identity(f,p["remote_state"])
                if p["remote_state"]["usage"] is not None:
                    schema().check("Usage",p["remote_state"]["usage"])
            for k in ("ttft_ms","elapsed_ms"):
                v=p[k]
                if v is not None and (type(v) not in (int,float) or not math.isfinite(v) or v<0):
                    raise ValueError("Invalid local time")
            if state=="SUCCEEDED" and (not done or done["state"]!="SUCCEEDED" or not "".join(answers).strip()
                    or len(canonical("".join(answers)))>MAX_RAW_JSON):
                raise ValueError("Success without complete local answer")
            if state=="CANCELLED" and not (turn["cancel_requested"] and not dispatched or done and done["state"]=="CANCELLED"):
                raise ValueError("Unproved local cancellation")
            if state=="FAILED" and dispatched and not (done and done["state"]=="FAILED"
                    or seq==0 and p["error_code"] in {"unauthorized","forbidden","invalid_request","unknown_target",
                    "stale_instance","target_not_ready","slot_busy","unsupported_capability","request_too_large",
                    "context_limit","output_limit"} and p["remote_state"] is None):
                raise ValueError("Unproved local failure")
            terminal=p
        else:
            raise ValueError("Unexpected local event")
    state=turn["state"]
    if (state in {"ACCEPTING","READY"} and records
            or state=="ATTEMPTING" and not started and records
            or state in STATES and terminal is None and not (state=="CANCELLED" and turn["cancel_requested"] and not started)
            or terminal and state not in {"ATTEMPTING",terminal["state"]}
            or cancelled and not turn["cancel_requested"]):
        raise ValueError("Local projection contradicts evidence")
    return dict(started=started,dispatched=dispatched,terminal=terminal,
                answer="".join(answers),reasoning="".join(reasoning),
                usage=usage,telemetry=telemetry,cancel_ack=ack,done=done)


def match_identity(f,value):
    if any(value[k]!=getattr(f,k) for k in ("request_id","target_id","instance_id")):
        raise ValueError("Local identity mismatch")
