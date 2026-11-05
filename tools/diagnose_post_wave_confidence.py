"""Saved-row confidence diagnosis; no fitting or forecast/selection changes."""
import argparse
import collections
import gzip
import hashlib
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sklearn.metrics import roc_auc_score
from nfl_v2.exact_line_repair import choose, confidence
from tools import abc_b_c_bound_replay as a


def metrics(rows):
    valid = [r for r in rows if r['probabilities'] is not None and r['actual'] is not None
             and r['participation'] == 'VERIFIED_PLAYED_POSITIVE_PHYSICAL']
    ys = [int(r['actual'] > r['line']) for r in valid]
    ps = [r['probabilities']['over'] for r in valid]
    correct = [int((r['actual'] > r['line']) == (choose(r['probabilities']) == 'over')) for r in valid]
    conf = [confidence(r['probabilities']) for r in valid]
    n = len(valid)
    def auc(y, p):
        return float(roc_auc_score(y, p)) if len(set(y)) == 2 else None
    return dict(outer=len(rows), available=sum(r['probabilities'] is not None for r in rows),
                unavailable=sum(r['probabilities'] is None for r in rows), decided=n,
                selected_unknown=sum(r['probabilities'] is not None for r in rows) - n,
                wins=sum(correct), losses=n-sum(correct),
                hit_rate=sum(correct)/n if n else None,
                over_auc=auc(ys, ps), confidence_correctness_auc=auc(correct, conf),
                brier=sum((p-y)**2 for p,y in zip(ps,ys))/n if n else None,
                mean_selected_confidence=sum(conf)/n if n else None,
                mean_predicted_over=sum(ps)/n if n else None,
                over_frequency=sum(ys)/n if n else None,
                min_confidence=min(conf,default=None), max_confidence=max(conf,default=None),
                unique_games=len({r['game_id'] for r in valid}),
                actual_weeks=sorted({(r['season'],r['week']) for r in valid}),
                no_fits_or_inference=True)


def profiles(evidence):
    answer = {}
    for name in ['memberships.json.gz','future-memberships.json.gz']:
        for row in a.load(evidence/'pregame-cohort-scorecards-v2'/name):
            game,player,target,population=row['key']
            if target in ['rec','pass_td'] and population in ['primary','frozen_exante_feed']:
                key=game,player,target
                assert key not in answer
                answer[key]=row
    return answer


def support(row, membership):
    m=membership.get((row['game_id'],row['player_id'],row['target']))
    if m is None or m['ranking_cutoff']>row['decision_epoch']:
        return dict(state='MEMBERSHIP_NOT_AVAILABLE',slots=None,history_slots=None,age_days=None)
    assert m['latest_available'] is None or m['latest_available']<m['ranking_cutoff']
    return dict(state='FROZEN_EARLIER_OPPORTUNITY_MEMORY_NOT_BASE_MODEL_INPUT_TRACE',
                slots=m['supported_slots'],history_slots=m['history_slots'],
                age_days=(row['decision_epoch']-m['latest_available'])/86400 if m['latest_available'] is not None else None)


def run(private,evidence,out,development_only):
    out.mkdir(parents=True,exist_ok=False)
    data=a.load(private/'PREPARED_INPUT_ROWS_V2.json.gz')
    membership=profiles(evidence)
    records=[]
    for target in ['rec','pass_td']:
        if development_only:
            arms={'B0':[r for r in data[target]['evaluation'] if r['week']==2]} if target=='rec' else {'B0':data[target]['calibration']}
        else:
            raw=a.load(private/'CALIBRATOR_MODELS_AND_ROWS.json.gz')['rows']
            arms={arm:[r for r in raw if r['target']==target and r['selection_policy']=='ALL'
                       and r['method_key'].endswith('::'+arm)] for arm in ['B0','B1']}
        for arm,rows in arms.items():
            groups=collections.defaultdict(list)
            for r in rows:
                h=support(r,membership)
                labels=[('ALL','ALL'),('ROLE',r['position']),('EXACT_LINE',str(r['line'])),
                        ('ROLE_X_LINE',r['position']+':'+str(r['line'])),
                        ('HISTORY_SUPPORT',str(h['slots']) if h['slots'] is not None else 'UNKNOWN'),
                        ('BASE_FALLBACK',str(r['fallback'])),
                        ('REPAIR_STATE',r.get('repair_state','UNCHANGED_BASELINE'))]
                if r['probabilities'] is not None:
                    labels.append(('CONFIDENCE_BIN',str(min(9,int(confidence(r['probabilities'])*10)))))
                    labels.append(('SELECTED_SIDE',str(choose(r['probabilities']))))
                else:labels.append(('CONFIDENCE_BIN','UNAVAILABLE'))
                if h['age_days'] is None:age='UNKNOWN'
                elif h['age_days']<=7:age='LE7D'
                elif h['age_days']<=14:age='GT7_LE14D'
                else:age='GT14D'
                labels.append(('FROZEN_OPPORTUNITY_MEMORY_AGE',age))
                for label in labels:groups[label].append(r)
            for (dimension,value),rr in groups.items():
                records.append(dict(target=target,arm=arm,dimension=dimension,value=value,
                    source_scope='EARLIER_DEVELOPMENT_ONLY' if development_only else 'RETAINED_EXPOSED_EVALUATION',
                    membership_sha256=hashlib.sha256(json.dumps(sorted(r['offer_id'] for r in rr),separators=(',',':')).encode()).hexdigest(),
                    **metrics(rr)))
    a.save(out/'DIAGNOSTIC_RESULTS.json',records)
    a.save(out/'RUN_RECEIPT.json',dict(state='SAVED_ROW_DIAGNOSIS_COMPLETE',development_only=development_only,
        source_input_sha256=a.sha(private/'PREPARED_INPUT_ROWS_V2.json.gz'),source_model_rows_sha256=a.sha(private/'CALIBRATOR_MODELS_AND_ROWS.json.gz'),
        group_views=len(records),new_fits=0,new_base_inference=0,new_issued_forecasts=0,new_private_bytes=0,new_NFL_observations=0,
        actual_consumed_base_feature_age='NOT_RETAINED_HERE; frozen opportunity-memory age is a separate admitted pregame diagnostic, not a claim about C/P3 or C02 consumed inputs.',
        causal_limit='Confidence ordering, scale and subgroup/transfer associations are descriptive. No causal attribution, post-hoc offset or inverted picks.'))
    print(json.dumps(dict(views=len(records),development_only=development_only,new_fits=0)))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('private',type=Path);p.add_argument('evidence',type=Path);p.add_argument('out',type=Path);p.add_argument('--development-only',action='store_true');args=p.parse_args()
    run(args.private,args.evidence,args.out,args.development_only)
