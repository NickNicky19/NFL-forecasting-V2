"""Read-only preflight: source binding, earlier prefixes and policy mechanics; no fit."""
import argparse,collections,gzip,hashlib,json,math,sys
from datetime import datetime,timezone
from pathlib import Path


def read(p):return json.loads(gzip.decompress(p.read_bytes())if p.suffix=='.gz'else p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def epoch(s):
    d=datetime.fromisoformat(s.replace('Z','+00:00'));assert d.tzinfo is not None;return d.timestamp()
def eligible(rows,t):return[r for r in rows if r['label_available']<t and r['probabilities']is not None and r['actual']is not None and r['participation']=='VERIFIED_PLAYED_POSITIVE_PHYSICAL'and r['line']%1==.5]


def run(repo,evidence,croot,prepared,out):
    protocol=read(out/'FROZEN_PROTOCOL.json');assert sha(prepared)==protocol['input_rows_sha256'];assert sha(repo/'tools/run_b_predictive_improvement_01.py')==protocol['code_sha256'];assert sha(repo/'nfl_v2/exact_line_repair.py')==protocol['mechanism_sha256'];d=read(prepared)
    prefixes=[];available={}
    for target in('rec','pass_td'):
        panel=d[target];evaluation=panel['evaluation'];available[target]=sum(r['probabilities']is not None for r in evaluation)
        assert len({r['offer_id']for r in evaluation})==len(evaluation)and len({(r['game_id'],r['player_id'],r['line'])for r in evaluation})==len(evaluation)
        for phase in('evaluation','calibration','gate_oof','baseline_selection_rows'):
            for r in panel.get(phase)or[]:
                assert r['decision_epoch']==epoch(r['decision_time'])<=epoch(r['kickoff'])
                assert r['label_available']==epoch(r['kickoff'])+7*86400
                if r['actual']is not None:assert r['actual']==int(r['actual'])and r['actual']>=0
                p=r['probabilities']
                if p is not None:assert min(p.values())>=0 and max(p.values())<=1 and abs(sum(p.values())-1)<1e-10
        origins=sorted({r['decision_epoch']for r in evaluation})if target=='rec'else sorted({panel['calibration_freeze'],*(r['decision_epoch']for r in panel['gate_oof'])})
        for t in origins:
            rr=eligible(panel['calibration'],t);games={r['game_id']for r in rr};positives=sum(r['actual']>r['line']for r in rr)
            assert all(r['decision_epoch']<t and r['label_available']<t for r in rr)
            # Changing unavailable future outcomes cannot change earlier training membership.
            changed=[dict(r,actual=999 if r['label_available']>=t else r['actual'])for r in panel['calibration']]
            assert [r['offer_id']for r in rr]==[r['offer_id']for r in eligible(changed,t)]
            prefixes.append(dict(target=target,simulated_origin=t,eligible_rows=len(rr),games=len(games),positive=positives,negative=len(rr)-positives,min_support_passes=len(rr)>=20 and len(games)>=5 and min(positives,len(rr)-positives)>=3,latest_label_available=max((r['label_available']for r in rr),default=None)))
    # C's retained direct exact-line probabilities, correction chain and source unavailability.
    versions={}
    for binding in read(croot/'reports/abc-championship/C_INPUT_BINDINGS.json')['datasets']:
        p=croot/binding['path'];assert sha(p)==binding['SHA256']
        for r in read(p)['rows']:versions[r['record_id']]=r
    cc={r['offer_id']:r for r in versions.values()if r['venue']=='pinnacle'and r['category']=='rec'and r['method_id']=='P3_DIRECT'};assert len(cc)==362
    for r in d['rec']['evaluation']:
        c=cc[r['offer_id']];assert(r['game_id'],r['player_id'],r['line'],r['actual'],r['decision_time'])==(c['game_id'],c['player_id'],c['line'],c['actual'],c['decision_UTC'])
        assert 'P3_HGB/H-MULTI/E0_OP'in c['method_version']
        if r['probabilities']is None:assert c.get('p_over')is None
        else:
            assert c['probability_line']==r['line'];assert all(r['probabilities'][k]==c['p_'+k]for k in('under','push','over'))
    assert available['rec']==340
    # Verify the earliest fixed baseline choice against the actual public Week5 scoreboard.
    choice=d['pt_baseline_choice'];binding=next(b for b in protocol['input_sources']if b['safe_id']=='B_WEEK5_COMPLETE_LAW_ROWS');file=repo/binding['public_scores'];assert sha(file)==binding['public_scores_sha256'];sc=[r for r in read(file)if r['target']=='pass_td'and r['record_kind']=='prop_threshold_probability_evaluation'and r['brier']is not None];assert len(sc)==8
    selected=min(sc,key=lambda r:(r['brier'],r['procedure_id'],r['history_regime']));assert selected['procedure_id']==choice['procedure_id']and selected['history_regime']==choice['history']and selected['brier']==choice['earlier_brier']and selected['n']==choice['earlier_n']
    pt=d['pass_td'];freeze=pt['calibration_freeze'];assert freeze==min(r['decision_epoch']for r in pt['evaluation']);assert all(r['label_available']<freeze for r in pt['calibration']+pt['baseline_selection_rows']);assert max(r['label_available']for r in pt['baseline_selection_rows'])<min(r['decision_epoch']for r in pt['gate_oof']);assert all(r['decision_epoch']<freeze for r in pt['gate_oof'])
    bindings={'B_WEEK5_COMPLETE_LAW_ROWS':evidence/'baselines-coverage-20261031h-w5-complete-leaf-law-v1/GRADED_COMPLETE_LEAF_LAWS.json.gz','B_WEEK6_COMPLETE_LAW_ROWS':evidence/'completion-20261031g-w6-complete-leaf-law-v1/GRADED_COMPLETE_LEAF_LAWS.json.gz','B_WEEK7_COMPLETE_LAW_ROWS':evidence/'completion-20261031g-w7-complete-leaf-law-v1/GRADED_COMPLETE_LEAF_LAWS.json.gz','B_WEEK8_RETAINED_ORIGINAL_LAW_ROWS_V2':evidence/'week8-grading-20261102l/WEEK8_ORIGINAL_LAW_THRESHOLD_ROWS_V2.json.gz','B_CURRENT_FINAL_WEEK8_LABEL_BINDINGS':evidence/'abc-b-20261103/LOCAL_GRADED_ROWS.json.gz'}
    for b in protocol['input_sources']:assert sha(bindings[b['safe_id']])==b['sha256']and bindings[b['safe_id']].stat().st_size==b['bytes']
    # No numerical optimization: verify only mathematical endpoint/order mechanics.
    sys.path.insert(0,str(repo));from nfl_v2 import exact_line_repair as module
    tests=0
    for alpha in(-1.5,0.,1.5):
        xs=[0.,.01,.1,.5,.9,.99,1.];ys=[module.cdf_shift(x,alpha)for x in xs];assert ys[0]==0 and ys[-1]==1 and all(a<=b for a,b in zip(ys,ys[1:]));tests+=1
        for base in[dict(under=.2,push=.1,over=.7),dict(under=.7,push=0.,over=.3),dict(under=1.,push=0.,over=0.)]:
            p=module.repair(base,alpha);assert min(p.values())>=0 and abs(sum(p.values())-1)<1e-12;tests+=1
    result=dict(state='PREFIT_PASS_NO_BLOCKING_SOURCE_OR_CHRONOLOGY_DEFECT_IDENTIFIED',observed_at_utc=datetime.now(timezone.utc).isoformat(),protocol_sha256=sha(out/'FROZEN_PROTOCOL.json'),runner_sha256=sha(repo/'tools/run_b_predictive_improvement_01.py'),mechanism_sha256=sha(repo/'nfl_v2/exact_line_repair.py'),prepared_input_sha256=sha(prepared),no_calibration_fit_called=True,no_base_fit_or_inference_called=True,evaluation_outer=dict(rec=362,pass_td=28),available_base_probabilities=available,source_training_prefixes=prefixes,PT_W5_choice=dict(procedure=choice['procedure_id'],history=choice['history'],candidate_library=8,brier=choice['earlier_brier'],n=choice['earlier_n'],already_worse_than_neutral_025=choice['earlier_brier']>.25),endpoint_complement_order_software_checks=tests,limits=['All seasons/results already research-exposed; a chronological reconstruction is not fresh prospective confirmation.','C rec has one directly predicted event probability per offered line; nontrivial base CDF ordering across different lines is not established. Monotone postprocessing preserves only base ordering that actually holds.','PT calibration/gate historical known-target-time product transfers to an original early captured C02 law paired with later retained thresholds; source/query equivalence and executable quote clocks remain unverified.','Two Thursday PT offers lack that original C02 capture and remain technical unavailable.','Original PT baseline mean remains unchanged ancillary output; no repaired-distribution mean or new full outcome law is claimed.','The old C2025 two-parameter synthetic-grid calibration differs in procedure, objective regularization and population; its adverse numeric results remain reported, not newly row-reproduced here.','Game weighting, prior and support rules are fixed before new fits; actual coefficients and all new scores still require independent post-run verification.'])
    (out/'INDEPENDENT_PREFIT_SOURCE_AND_CHRONOLOGY_V1.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items()if k!='source_training_prefixes'},indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('repo',type=Path);p.add_argument('evidence',type=Path);p.add_argument('croot',type=Path);p.add_argument('prepared',type=Path);p.add_argument('out',type=Path);a=p.parse_args();run(a.repo,a.evidence,a.croot,a.prepared,a.out)
