"""Evidence-only M1-00..M1-12 acceptance audit; never accesses live services.

Requires exact locally reachable Git objects for pinned #107/#108/#111, and
only examines immutable WUA #664 reports and recorded local logs. This
script does NOT mark whole MVP1 accepted, does NOT turn on any Bridge,
and does NOT contact any Manager or cloud API.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

BASE="e2410c3f2273f7bda27c47818e57568de640fc45"
CONTRACT="2d9e7f6fb860fdd53747f4ba75350d15bab27877"
PRODUCER="883d91d4ad2e47fc260bfd7b1e61d230f8fb99ea"
MATRIX_SOURCE="a2796c3a4f452bb7043502c7ef1c4086e0672d6c"
MATRIX_PATH="Documents/18_Техническая_документация.md"
MATRIX_BLOB="d955e5d0fedec67d2e14582b0548308cbf7068dd"
REPORT="reports/CHATGPT-WUA-COLIBRI-MVP1-RUNSTORE-20261123-001/regression.json"

# Status is deliberately scoped; no row is full OWNER ACCEPTED.
# Evidence keys are verified against the #664 recorded PASS output below.
EVIDENCE = [
 ("M1-00","OFFLINE_PASS_SCOPED","producer_refresh",
  "Exact #107 contract and #108 producer immutable; WUA pinned consumer and independent 68/22/7 tests",
  "WUA release pipeline and exact hosted CI absent; current installed Colibri build not inspected"),
 ("M1-01","OFFLINE_PASS_SCOPED","windows_security",
  "Authenticated loopback/negative descriptor/identity/ACL cases on disposable Windows profile",
  "Actual HOME descriptor, ACL, launch identity and occupied port uninspected; OS handle and same-user race"),
 ("M1-02","OFFLINE_PASS_SCOPED","two_manager_sse",
  "Two simulated Managers, stable target_id, instance changes, READY/BUSY, independent EVM toggles",
  "Actual two-Manager concurrent LIVE operation belongs later MVP2, not claimed"),
 ("M1-03","OFFLINE_PASS_SCOPED","producer_refresh",
  "Exact #108 producer all five operations through WUA transport and fake Manager; no system/tool downgrades",
  "Real Client/Manager launch, health, status and HTTP credential context not inspected"),
 ("M1-04","OFFLINE_PASS_SCOPED","two_manager_sse",
  "Strict ordered SSE/reasoning/answer, durable batches, Chrome incremental rendering before terminal",
  "WUA browser currently polls Run Store (not native browser SSE); long idle, 48+ fragments and real engine NOT RUN"),
 ("M1-05","PARTIAL","unified_turn",
  "WUA raw usage/status/source/basis and unknown counters tracked, without fabricated cost",
  "Real engine counters/cache basis and all partial-usage combinations not verified in LIVE"),
 ("M1-06","OFFLINE_PASS_SCOPED","previous_owner_crash",
  "Duplicate admission, no rerun, same Turn/RAW, OS owner lease, crashed Run append and explicit recovery",
  "Remote inference may continue after WUA process death; real status/tombstones and installed profiles untested"),
 ("M1-07","OFFLINE_PASS_SCOPED","unified_turn",
  "Pre-dispatch cancel, ACK not terminal proof, race, UNKNOWN partial never assistant RAW/replayed",
  "Real worker cancellation and actual engine stop NOT RUN, remote status during crash unresolved"),
 ("M1-08","OFFLINE_PASS_SCOPED","chrome_two_manager",
  "Actual isolated Chrome normal one-chat mock-cloud to fake-Colibri to mock-cloud, six messages and F5",
  "Real cloud paid API and actual locally running Colibri are NOT RUN; custom user system instructions unsupported"),
 ("M1-09","PARTIAL","python_compat",
  "WUA focused tests, 51 pytest Run Store, TurnService 19, 207 JS and Chrome PASS; Bridge still opt-in",
  "WUA full hosted Windows CI/packaging and historical S1/S2/D8 failures NOT CLOSED"),
 ("M1-10","NOT_RUN",None,
  "Separate bounded OWNER LIVE read-only health/ACL/ports identity preflight proposed, not executed",
  "Owner GO required; no real Manager request, production profile change or model start/stop"),
 ("M1-11","NOT_RUN",None,
  "Optional real paid/cloud-local-cloud flow not attempted",
  "Separate provider/cost authorization and GigaChat live issue; mock cloud is NOT real cloud"),
 ("M1-12","PARTIAL","append_hard_kill",
  "WUA evidence and shared plan row plus Colibri #111 proposal; full provenance/scopes recorded",
  "Joint coordinators and owner have not ACCEPTED full MVP1; no archive, no M1-10/11"),
]


def git(repo:Path,*args:str)->bytes:
    return subprocess.check_output(["git","-C",str(repo),*args],stderr=subprocess.PIPE)


def run(wua:Path,colibri:Path,producer_log:Path,vault:Path|None)->dict:
    base=git(wua,"rev-parse","HEAD").decode().strip()
    # Candidate commits may be descendants, never detached from the pinned base.
    subprocess.run(["git","-C",str(wua),"merge-base","--is-ancestor",BASE,base],
                   check=True,capture_output=True)
    document_blob=git(colibri,"rev-parse",MATRIX_SOURCE+":"+MATRIX_PATH).decode().strip()
    if document_blob!=MATRIX_BLOB:
        raise ValueError("Colibri #111 matrix source drift")
    matrix=git(colibri,"show",MATRIX_SOURCE+":"+MATRIX_PATH).decode("utf-8")
    # Extract only the canonical 13 rows; no invented changes to Colibri source.
    items={}
    for line in matrix.splitlines():
        if not line.startswith("| M1-"):continue
        cells=[c.strip() for c in line.strip("|").split("|")]
        if len(cells)!=3 or not re.fullmatch(r"M1-(?:0\d|1[0-2])",cells[0]):
            raise ValueError("Invalid pinned Colibri matrix row")
        if cells[0] in items:raise ValueError("Duplicate Colibri gate")
        items[cells[0]]=dict(criterion=cells[1],colibri_as_of_111=cells[2])
    expected=[f"M1-{x:02d}" for x in range(13)]
    if sorted(items)!=expected:
        raise ValueError(f"Colibri matrix not exactly M1-00..12: {sorted(items)}")
    contract_names=[x.decode("utf-8") for x in
        git(colibri,"ls-tree","-r","--name-only","-z",CONTRACT,"--","Contracts/ClientBridge/v1").split(b"\0") if x]
    if len(contract_names)!=10:raise ValueError("Expected ten canonical contract blobs")
    contract_blobs={}
    for file in contract_names:
        c=git(colibri,"rev-parse",CONTRACT+":"+file).decode().strip()
        p=git(colibri,"rev-parse",PRODUCER+":"+file).decode().strip()
        if c!=p:raise ValueError("Contract source drift "+file)
        contract_blobs[file]=c
    source=git(wua,"show",BASE+":"+REPORT)
    recorded=json.loads(source)
    if recorded.get("failed"):raise ValueError("WUA #664 failures in committed manifest")
    expected_success={
        "append_hard_kill":"Ran 6 tests",
        "previous_owner_crash":"Ran 3 tests",
        "windows_security":"Ran 3 tests",
        "unified_turn":"Ran 13 tests",
        "two_manager_sse":"Ran 4 tests",
        "ordinary_evm":"Ran 2 tests",
        "run_store_v2_pytest":"51 passed",
        "turn_service_compat":"Ran 19 tests",
        "python_compat":"Ran 70 tests",
        "js_compat":"# pass 207",
        "chrome_two_manager":"CHROME_JOINT_PASS",
    }
    results={}
    for name,marker in expected_success.items():
        matching=[v for v in recorded["results"] if v["name"]==name]
        if len(matching)!=1 or matching[0]["code"]!=0 or marker not in matching[0]["summary"]:
            raise ValueError("Unverified WUA #664 gate "+name)
        results[name]={"status":"PASS_RECENT_AS_664","summary":matching[0]["summary"]}
    log=producer_log.read_text(encoding="utf-8")
    for required in (
        "EXACT PRODUCER BLOBS 35",
        "PASS 68 fixture/schema/sequence checks",
        "Ran 22 tests",
        "Ran 7 tests",
    ):
        if required not in log:raise ValueError("New producer independent tests incomplete: "+required)
    if log.count("\nOK")<2 or "FAILED" in log or "ERROR" in log:
        raise ValueError("New producer tests have a failure or incomplete verdict")
    # The archive is outside Git and the operator can choose not to have it.
    # If provided, test every byte against the committed #664 SHA inventory.
    logs_verified=0
    if vault:
        inventories={v["name"]:v for v in recorded["log_manifest"]}
        for name,item in inventories.items():
            blob=(vault/name).read_bytes()
            if (len(blob)!=item["bytes"] or
                hashlib.sha256(blob).hexdigest()!=item["sha256"]):
                raise ValueError("Local evidence log integrity mismatch "+name)
            logs_verified+=1
    entries=[]
    status_counts={}
    for gid,status,key,verified,open_item in EVIDENCE:
        if gid not in items:raise ValueError("Unpinned gate")
        if key and key!="producer_refresh" and key not in results:
            raise ValueError("Missing supporting WUA suite "+key)
        status_counts[status]=status_counts.get(status,0)+1
        entries.append({
            "id":gid,"status":status,"colibri_criterion":items[gid]["criterion"],
            "colibri_source_status":items[gid]["colibri_as_of_111"],
            "wua_evidence":verified,
            "source":("#107+#108 68/22/7 fresh" if key=="producer_refresh" else
                     "#664 WUA "+key if key else "NONE, NOT_RUN"),
            "remaining":open_item,
        })
    overall="PARTIAL_OFFLINE_NOT_ACCEPTED"
    if len(entries)!=13 or status_counts.get("NOT_RUN")!=2:
        raise ValueError("Full MVP1 accepted or missing NOT_RUN is forbidden")
    return {
        "integration_id":"WUA-COLIBRI-BRIDGE-001",
        "wua_base":BASE,"wua_current_head":base,
        "colibri_contract":CONTRACT,"colibri_producer":PRODUCER,
        "colibri_matrix":MATRIX_SOURCE,"colibri_matrix_blob":MATRIX_BLOB,
        "verified_contract_blobs":len(contract_blobs),
        "independent_refresh":{"contract_shape":68,"bridge_tests":22,"joint_transport_tests":7,
                               "raw_log_sha256":hashlib.sha256(log.encode("utf-8")).hexdigest()},
        "last_WUA_664_successful_suites":list(results),
        "archived_WUA_raw_logs_sha256_verified":logs_verified,
        "statuses":status_counts,"overall":overall,
        "real_manager": "NOT_ACCESSED","real_cloud":"NOT_ACCESSED",
        "hosted_ci_WUA":"NOT_RUN","historical_S1_S2_D8":"OPEN",
        "owner_joint_acceptance":"NOT_RUN",
        "matrix":entries,
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--colibri-repo",required=True,type=Path)
    p.add_argument("--wua-repo",type=Path,default=Path(__file__).resolve().parents[2])
    p.add_argument("--producer-log",type=Path,default=Path(__file__).with_name("producer-refresh.txt"))
    p.add_argument("--local-vault",type=Path)
    args=p.parse_args()
    state=run(args.wua_repo,args.colibri_repo,args.producer_log,args.local_vault)
    root=Path(__file__).resolve().parent
    (root/"matrix.json").write_text(
        json.dumps(state,ensure_ascii=False,indent=2)+"\n",encoding="utf-8",newline="\n")
    lines=[
      "# WUA MVP-1 joint M1-00..M1-12 — independent OFFLINE matrix",
      "",
      "**Overall: PARTIAL / NOT ACCEPTED. LIVE NOT RUN. MVP2 NOT STARTED.**",
      "",
      f"Exact WUA base: {BASE}; Colibri #107 {CONTRACT}, #108 {PRODUCER}; #111 matrix {MATRIX_SOURCE}.",
      f"Evidence: fresh pinned 68 contract, 22 Bridge, 7 transport; #664 WUA suites; verified archived log bytes: {state['archived_WUA_raw_logs_sha256_verified']}.",
      "",
      "| Gate | WUA assessment | Independently verified scope | Remains open |",
      "| --- | --- | --- | --- |",
    ]
    for row in state["matrix"]:
        lines.append("| "+row["id"]+" | "+row["status"]+" | "+
                     row["wua_evidence"]+" | "+row["remaining"]+" |")
    lines.extend(["", "## Stop conditions", "",
      "No isolated OWNER LIVE GO; no verified real Client/Manager launch identity/ACL/ports/idle READY target; "+
      "no status-proof of stopped remote inference after lost WUA process; actual nonempty PROJECT CONTEXT "+
      "system/tool role unsupported; WUA hosted CI and historical S1/S2/D8 still OPEN. "+
      "M1-10 and M1-11 remain NOT_RUN and cannot be inferred from mocked clouds or Managers.",
      "",
      "## Next independent action", "",
      "Colibri Ultra 14 review exact unchanged PROJECT CONTEXT template classification and real Manager readiness "+
      "without sharing secrets. WUA to coordinate scoped read-only Windows HOME preflight after explicit owner GO; "+
      "real text-generation/cancel and cloud costs require separate GO. Do not enable Bridge, start/stop a model, "+
      "or copy production profiles as part of this source-only audit.",
      "",
    ])
    (root/"matrix.md").write_text("\n".join(lines),encoding="utf-8",newline="\n")
    print("MATRIX_VERIFIED",state["overall"],state["statuses"],
          "PINNED_CONTRACT",state["verified_contract_blobs"],
          "PRODUCER_68_22_7","LOGS",state["archived_WUA_raw_logs_sha256_verified"])


if __name__=="__main__":main()
