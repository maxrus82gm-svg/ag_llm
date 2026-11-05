"""Reconstruct one failed wait against live holder intervals; distinguish measured facts from CI attribution."""
from pathlib import Path
import json

REPORT=Path(__file__).resolve().parent
folder=REPORT/'evidence/slow500live/2'
summaries=[json.loads(f.read_text()) for f in (folder/'trace').glob('*.json')]
failures=[(v['pid'],e) for v in summaries for e in v['events'] if e['kind']=='lock' and e['error']]
assert len(failures)==1
pid,failure=failures[0];begin,end=failure['start'],failure['end']
intervals=[];partial=[]
for path in (folder/'trace').glob('*.live.jsonl'):
    stack=[]
    for line in path.read_text().splitlines():
        try:value=json.loads(line)
        except json.JSONDecodeError:partial.append(path.name);continue
        if value['nested']:continue
        if value['kind']=='acquired':stack.append(value)
        elif value['kind']=='body_end':
            start=stack.pop();intervals.append(dict(pid=int(path.name.split('.')[0]),start=start['time'],end=value['time'],phase=start['phase']))
other=sorted((v for v in intervals if v['pid']!=pid and v['end']>begin and v['start']<end),key=lambda v:v['start'])
held=sum(max(0,min(v['end'],end)-max(v['start'],begin)) for v in other)
gaps=[other[n]['start']-other[n-1]['end'] for n in range(1,len(other))]
attempts=[e for v in summaries if v['pid']==pid for e in v['events'] if e['kind']=='byte_refusal' and begin<=e['start']<=end]
value=dict(failed_pid=pid,failed_phase=failure['phase'],failed_wait_seconds=end-begin,
           failed_byte_attempts=len(attempts),errno_counts={str(n):sum(e['errno']==n for e in attempts) for n in {e['errno'] for e in attempts}},
           competing_critical_sections=len(other),competing_body_seconds_within_wait=held,
           max_single_competing_body_seconds=max(v['end']-v['start'] for v in other),
           max_observed_body_gap_seconds=max(gaps,default=0),poll_seconds=.01,
           intervals=other,incomplete_live_lines=partial,
           interpretation='Repeated short competing acquisitions exhaust the absolute wait deadline; no single >10s holder required. Body intervals underestimate actual OS ownership.',
           ci_attribution='Same selector/error/deadline mechanism reproduced under explicitly injected slow I/O. Original CI per-lock timings and exact I/O source remain unavailable.')
(REPORT/'evidence/timeline_analysis.json').write_text(json.dumps(value,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in value.items() if k!='intervals'},indent=2))
