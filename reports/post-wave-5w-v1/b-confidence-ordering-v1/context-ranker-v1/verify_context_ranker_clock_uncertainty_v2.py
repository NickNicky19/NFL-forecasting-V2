"""Supplementary actual-clock and paired game-SE audit; no fit/scorer calls."""
import argparse,collections,gzip,hashlib,json,math
from datetime import datetime,timezone
from pathlib import Path
def read(p):
    b=p.read_bytes();return json.loads(gzip.decompress(b)if p.suffix=='.gz'else b)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def close(a,b):return a==b or(a is not None and b is not None and abs(a-b)<1e-10)
def epoch(v):return float(v)if isinstance(v,(int,float))else datetime.fromisoformat(v.replace('Z','+00:00')).timestamp()
def run(retained,private,out):
    source=read(retained/'PREPARED_INPUT_ROWS_V2.json.gz');payload=read(private/'MODELS_AND_SELECTION_ROWS.json.gz');pairs=read(out/'PAIRED_COMPARISONS.json');prior=read(out/'INDEPENDENT_CONTEXT_RANKER_AUDIT_V1.json');assert sha(out/'SCORES.json')==prior['scores_sha256']and sha(private/'MODELS_AND_SELECTION_ROWS.json.gz')==prior['private_model_rows_sha256'];clocks=0
    for target in('rec','pass_td'):
        d=source[target]
        for rr in(d['evaluation'],d['calibration'],d.get('gate_oof')or[]):
            for r in rr:
                assert r['label_available']==epoch(r['kickoff'])+604800 and r['decision_epoch']==epoch(r['decision_time']);clocks+=1
        if target=='pass_td':assert d['calibration_freeze']==min(r['decision_epoch']for r in d['evaluation'])and all(r['decision_epoch']<d['calibration_freeze']for r in d['gate_oof'])
    for m in payload['models'].values():
        byid={r['offer_id']:r for r in source[m['target']]['calibration']}
        assert all(byid[k]['label_available']<m['cutoff_epoch']and epoch(byid[k]['kickoff'])<m['cutoff_epoch']for k in m['training_offer_ids'])
    pairedgames=0;insufficient=0
    for p in pairs:
        byarm={a:{r['offer_id']:r for r in payload['rows']if r['target']==p['target']and r['method_key'].endswith('G'+str(a))and r['selection_policy']==p['scope']and(str(p['week_view'])=='ALL'or r['week']==int(p['week_view']))and r['statistical_state']in('WIN','LOSS')}for a in(0,1)};ids=byarm[0].keys()&byarm[1].keys();u=p['uncertainty'];games=collections.defaultdict(list)
        for k in ids:
            a,b=byarm[1][k],byarm[0][k];assert(a['game_id'],a['player_id'],a['target'],a['line'],a['actual'],a['decision_epoch'])==(b['game_id'],b['player_id'],b['target'],b['line'],b['actual'],b['decision_epoch']);games[a['game_id']].append(int(a['statistical_state']=='LOSS')-int(b['statistical_state']=='LOSS'))
        delta=sum(map(sum,games.values()))/len(ids)if ids else None;assert close(delta,u['delta'])and u['game_clusters']==len(games)and u['week_interval']is None
        if len(games)>=8:
            se=math.sqrt(len(games)/(len(games)-1)*math.fsum((sum(v)-len(v)*delta)**2 for v in games.values()))/len(ids);assert close(se,u['game_cluster_sensitivity_se'])and all(close(x,y)for x,y in zip([delta-1.96*se,delta+1.96*se],u['game_normal95_sensitivity']));pairedgames+=1
        else:assert u['game_cluster_sensitivity_se']is None;insufficient+=1
    result=dict(state='PASS_ACTUAL_SOURCE_CLOCKS_AND_PAIRED_GAME_CLUSTER_ARITHMETIC',at_utc=datetime.now(timezone.utc).isoformat(),verification_code_sha256=sha(Path(__file__)),parent_independent_receipt_sha256=sha(out/'INDEPENDENT_CONTEXT_RANKER_AUDIT_V1.json'),source_input_sha256=sha(retained/'PREPARED_INPUT_ROWS_V2.json.gz'),source_rows_sha256=sha(private/'MODELS_AND_SELECTION_ROWS.json.gz'),scores_sha256=sha(out/'SCORES.json'),source_clock_checks=clocks,actual_strict_kickoff_plus_7day_eligibility=True,PT_coefficient_freeze_before_eval_and_all_gate_origins=True,paired_contrasts_checked=len(pairs),paired_game_SEs_checked=pairedgames,insufficient_game_contrasts=insufficient,week_cluster_intervals_unavailable=True,new_fits=0,new_inference=0,new_scores=0,limitations=['Scheduled kickoff+7days is the declared historical source-availability assumption, not independently authenticated football-feed publication vintage.','Conditional common-selection contrasts differ from complete own-selected-pool differences; both remain exposed descriptive comparisons.'])
    (out/'INDEPENDENT_CONTEXT_RANKER_CLOCK_UNCERTAINTY_V2.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('retained',type=Path);p.add_argument('private',type=Path);p.add_argument('out',type=Path);a=p.parse_args();run(a.retained,a.private,a.out)
