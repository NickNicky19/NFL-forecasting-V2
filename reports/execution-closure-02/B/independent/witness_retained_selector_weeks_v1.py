"""Verify existing selector decisions against saved weekly scores; no selection."""
import argparse,csv,hashlib,json,math
from pathlib import Path
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
    base=a.repo/'reports/championship-20261030f/category-selector-v2'
    decisions=json.loads((base/'DECISIONS.json').read_bytes());p=json.loads((base/'FROZEN_PROTOCOL.json').read_bytes());scores=json.loads((base/'SCORES.json').read_bytes())
    sources={};witness=[];policies=[]
    for target in ('rush_att','rush_rec_yd','anytime_td'):
      metric='brier'if target=='anytime_td'else'mae'
      for policy in sorted({r['policy_id']for r in decisions}):
        rr=[(i,r)for i,r in enumerate(decisions)if r['target']==target and r['policy_id']==policy]
        assert sorted(r['evaluation_week']for _,r in rr)==list(range(1,8))
        for index,r in rr:
          week=r['evaluation_week'];expected=[u for u in range(1,week)if p['week_score_available'][f'2026-{u}']<r['fit_origin_unix']]
          assert expected==r['current_score_weeks_available']
          assert r['fit_origin_unix']==p['origins'][f'2026-{week}'] and r['not_originally_issued']
          k='|'.join((target,r['chosen_procedure_id'],r['chosen_product_id']));frozen=p['weekly2026'][k][str(week)]
          assert int(frozen['n'])==r['n'] and float(frozen[metric])==r['native_loss']
          rel=r['source_score_artifact'];path=a.repo/rel
          if rel not in sources:
            rows=list(csv.DictReader(path.open()))if path.suffix=='.csv'else json.loads(path.read_bytes())
            sources[rel]=dict(sha256=sha(path),rows=rows)
          matches=[]
          for j,s in enumerate(sources[rel]['rows']):
            st=s.get('target',s.get('category'));sw=s.get('week');sh=s.get('history_regime')
            if st!=target or str(sw)!=str(week)or str(s.get('season',2026))!='2026'or sh!='H-MULTI'or s.get('population')!='primary'or s.get('position')!='ALL':continue
            if s.get('fallback_view','ALL')!='ALL':continue
            if 'hgb-history-v1' in rel:proc='hgb-direct-history-controls-v1:'+s['objective'];product=s['objective']
            elif 'history-diagnostic-v1' in rel:proc='empirical-player-history-control-v1';product=s['product']
            else:proc=s['procedure_id'].removesuffix(':common-feature-memory');product=s['product_id']
            if proc==r['chosen_procedure_id']and product==r['chosen_product_id']:matches.append((j,s))
          assert len(matches)==1,(target,week,policy,len(matches))
          j,s=matches[0];n=int(s.get('n',s.get('scored_n')));loss=float(s[metric]);assert n==r['n']and loss==r['native_loss']
          witness.append(dict(selector_procedure_id=p['version']+':'+policy,target=target,
            product_id='event_probability_policy'if target=='anytime_td'else'point_choice_policy',
            season=2026,week=week,n=n,native_metric=metric,native_loss=loss,
            decision_row_index=index,source_score_artifact=rel,source_score_artifact_sha256=sources[rel]['sha256'],source_row_index=j,
            chosen_procedure_id=r['chosen_procedure_id'],chosen_product_id=r['chosen_product_id'],
            earlier_current_score_weeks=expected,startup=r['startup_fallback'],
            original_issuance=False,actual_line_qualification=False))
        ss=next(s for s in scores if s['target']==target and s['procedure_id']==p['version']+':'+policy)
        den=sum(r['n']for _,r in rr);weighted=math.fsum(r['n']*r['native_loss']for _,r in rr)/den
        assert den==ss['n']and abs(weighted-ss[metric])<1e-14
        policies.append(dict(procedure_id=ss['procedure_id'],target=target,product_id=ss['product_id'],history='H-MULTI',
             scored_season_weeks=[[2026,w]for w in range(1,8)],distinct_scored_week_count=7,n=den,
             native_metric=metric,native_error=ss[metric],cumulative_record_id=ss['record_id'],
             scope='RETAINED_NUMERICAL_OR_EVENT_PROBABILITY_SELECTOR_WEEK_WITNESS_ONLY_NOT_OFFER_OR_TOP_PICKS',
             source_vintage=ss['source_vintage'],minimum_five_numerical_week_count='MET_NOT_ADMISSION'))
    result=dict(state='PASS_INDEPENDENT_EXISTING_SELECTOR_WEEK_WITNESS',
      source_bindings={str((base/f).relative_to(a.repo)):sha(base/f)for f in ('DECISIONS.json','FROZEN_PROTOCOL.json','SCORES.json')},
      original_source_bindings={k:v['sha256']for k,v in sources.items()},policies=policies,weekly_witnesses=witness,
      new_fits=0,new_inference=0,new_selections=0,new_scoring=0,new_test_weeks=0,
      qualification='Existing decisions explicitly bind evaluated week/n/native loss and chosen source weekly score. This closes metadata witness omission, not new testing, model inference, actual-line history or operational admission. Earlier-only current validation clocks checked; original past-year argmin policy is not rerun.')
    if a.output.exists():raise FileExistsError(a.output)
    a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(state=result['state'],policies=len(policies),weekly_witnesses=len(witness),sha256=sha(a.output))))
if __name__=='__main__':main()
