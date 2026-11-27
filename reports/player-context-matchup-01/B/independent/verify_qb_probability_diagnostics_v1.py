"""Independent pairwise AUC and reliability arithmetic on retained exact-line rows."""
import argparse, importlib.util, json, math
from pathlib import Path
sp=importlib.util.spec_from_file_location('primitive',Path(__file__).with_name('verify_qb_scores_v1.py'));v=importlib.util.module_from_spec(sp);sp.loader.exec_module(v)
def main():
 ap=argparse.ArgumentParser()
 for f in('base-wave','chart-wave','base-scores','chart-scores','inputs','output'):ap.add_argument('--'+f,type=Path,required=True)
 for w in range(5,9):ap.add_argument('--week'+str(w),type=Path,required=True)
 a=ap.parse_args();offers=[]
 for w in range(5,9):
  for r in v.read(getattr(a,'week'+str(w)))['rows']:
   if r.get('target')not in('pass_cmp','pass_att'):continue
   if w==8 and not(r.get('panel')=='ORIGINAL_PROVIDER_T90'and r.get('strategy')=='original'and not r.get('method_key')):continue
   offers.append(r)
 source=v.read(a.inputs);qby={(r['game_id'],r['player_id']):r for r in source};good=[r for r in source if r['physical_participation']and r['target_parity']]
 predictions=[r for wave in(a.base_wave,a.chart_wave)for p in sorted((wave/'predictions').glob('*.json.gz'))for r in v.read(p)['rows']];by={(r['procedure_id'],v.k(r)):r for r in predictions};checked=0;outputs=[]
 for scorepath in(a.base_scores/'SCORES.json',a.chart_scores/'SCORES.json'):
  for s in v.read(scorepath):
   if s['record_kind']!='prop_threshold_probability_evaluation':continue
   rows=[]
   for r in offers:
    if r['target']!=s['target']or(s['week']!='ALL'and r['week']!=s['week']):continue
    pred=by.get((s['procedure_id'],v.k(r)));p=None
    if pred:p=v.probs(pred['law'],r['line'])
    elif s['procedure_id']=='NEUTRAL_HALFPOINT'and r['line']%1==.5:p=dict(over=.5,under=.5,push=0.)
    elif s['procedure_id']=='EARLIER_LINE_PREVALENCE':
     q=qby[r['game_id'],r['player_id']];field='official_completions'if r['target']=='pass_cmp'else'official_attempts';values=[z[field]for z in good if z['season']>=q['season']-1 and z['available']<q['kickoff']];whole=r['line']%1==0;den=len(values)+(3 if whole else 2);p=dict(over=(sum(x>r['line']for x in values)+1)/den,under=(sum(x<r['line']for x in values)+1)/den,push=(sum(x==r['line']for x in values)+1)/den if whole else 0.)
    assert p is not None;event='over'if r['actual']>r['line']else'under'if r['actual']<r['line']else'push';rows.append((p,event))
   assert len(rows)==s['n'];pos=[p['over']for p,e in rows if e=='over'];neg=[p['over']for p,e in rows if e!='over']
   auc=sum(float(x>y)+.5*float(x==y)for x in pos for y in neg)/(len(pos)*len(neg))if pos and neg and all(p['push']==0 for p,e in rows)else None;v.eq(auc,s['over_event_AUC'])
   ties=sum(p['over']==p['under']for p,e in rows);assert s['probability_direction_ties']==ties
   for interval in s['reliability']:
    lo,hi=interval['lower'],interval['upper'];members=[(p,e)for p,e in rows if p['over']!=p['under']and lo<=max(p['over'],p['under'])and(max(p['over'],p['under'])<hi or hi==1 and max(p['over'],p['under'])==1)]
    assert interval['n']==len(members)
    v.eq(interval['mean_predicted'],sum(max(p['over'],p['under'])for p,e in members)/len(members)if members else None);v.eq(interval['correct_direction_rate'],sum(('over'if p['over']>p['under']else'under')==e for p,e in members)/len(members)if members else None)
   checked+=1;outputs.append(dict(procedure_id=s['procedure_id'],target=s['target'],window=s['week'],n=len(rows),over_event_AUC=auc,probability_direction_ties=ties))
 assert checked==70
 out=dict(state='PASS_INDEPENDENT_PAIRWISE_AUC_AND_RELIABILITY',proper_score_views_checked=checked,source_score_hashes=[v.sha(a.base_scores/'SCORES.json'),v.sha(a.chart_scores/'SCORES.json')],witnesses=outputs,method='AUC calculated through every positive-negative probability pair with exact 0.5 tie credit, independently of rankdata. Reliability uses frozen confidence-bin memberships and actual threshold events; exact-line laws rebuilt using independent primitives. No calibration or selector fitting.',scope='Same224retainedCMP/ATToffers,2026W5-W8only; FTN112CMPsubset. Current-revised source reconstruction and quote-time limits persist. Direction discrimination separate from calibration/proper score.',new_fits=0,parent_scorer_calls=0,private_row_exports=0)
 if a.output.exists():raise FileExistsError(a.output)
 a.output.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(dict(state=out['state'],views=checked,sha256=v.sha(a.output))))
if __name__=='__main__':main()
