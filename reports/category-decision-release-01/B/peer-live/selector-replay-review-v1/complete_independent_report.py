"""Append deterministic membership differences from the independent local run.

No new ranking, scoring rule, data retrieval, model fitting or observations.
"""
from pathlib import Path
import json,hashlib,collections,sys,platform
D=Path(__file__).parent
r=json.loads((D/'B_INDEPENDENT_SELECTOR_VERIFICATION_V1.json').read_bytes())
rows=json.loads((D/'B_CANONICAL_PICKS.local.json').read_bytes());differences=[]
for week in [5,6,7,8]:
    b=json.loads((D/'selector-inputs'/f'W{week}_FULL_ORIGINAL_BOARD.private.json').read_bytes())
    names={p['id']:p['name'] for p in b['players']}
    groups={n:[x for x in rows if x['week']==week and x['policy']==n] for n in ['saved_control','candidate']}
    key=lambda x:(x['game_id'],x['player_id'],x['key'],x['direction'])
    sets={n:{key(x) for x in v} for n,v in groups.items()};common=sets['saved_control']&sets['candidate']
    for name,rr in groups.items():
        for x in rr:
            if key(x) not in common:differences.append({**x,'name':names[x['player_id']]})
r['membership_disagreements']={'common_same_side_policy_memberships':sum(w['membership_common_same_side'] for w in r['weeks']),'control_removed':8,'candidate_added':8,'removed_states':dict(collections.Counter(x['result'] for x in differences if x['policy']=='saved_control')),'added_states':dict(collections.Counter(x['result'] for x in differences if x['policy']=='candidate')),'net_hits':2,'rows':differences}
r['unknown_membership']=[{k:x[k] for k in ['week','policy','game_id','player_id','key','direction','line','actual','result']} for x in rows if x['result']=='unresolved']
r['owner_protocol_file_sha256']=hashlib.sha256((D/'block0.json').read_bytes()).hexdigest()
assert r['owner_protocol_file_sha256']=='a69a34eb9f38592c27d01b596428cbba49c581baebc487d9e2f86f0993afd31d'
r['owner_uncertainty_statement']='Four exposed weekly clusters; owner provides no formal interval and makes no supported replacement-superiority or calibrated-confidence claim. This verification adds no new acceptance threshold or guarantee.'
r.pop('descriptive_week_cluster_sensitivity',None)
r['saved_policy_pick_rows_independently_regraded']=192
r['original_grades_modified']=0
r['known_zero_coverage']='No reported-zero NFL selected row found in these lists; exact reported-zero and explicit-null/composite/equality boundaries covered only by four labeled synthetic fixtures, not extra NFL evidence.'
r['environment']={'Python':sys.version.split()[0],'platform':platform.platform(),'dependencies':'Python standard library only; immutable owner production ranker/overlay/grader/scoring/gamemodel imported from pinned public source. No model deserialization.'}
r['reproduction_commands']=['python fetch_inputs.py  # restore only 29 pinned public Git objects, verify every SHA/size; no provider acquisition','python independent_selector_check.py','python complete_independent_report.py']
(D/'B_INDEPENDENT_SELECTOR_VERIFICATION_V1.json').write_text(json.dumps(r,indent=2,allow_nan=False)+'\n')
print(json.dumps({'verification':'PASS','membership_sha256':r['canonical_membership_sha256'],'removed':8,'added':8,'owner_protocol_sha256':r['owner_protocol_file_sha256']}))
