"""Independent saved-row week partition arithmetic; no parent scorer imports."""
import argparse,collections,gzip,hashlib,json,math
from datetime import datetime
from decimal import Decimal
from pathlib import Path


def read(p):return json.loads(gzip.decompress(p.read_bytes()) if p.suffix=='.gz' else p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def mask(ids):return hashlib.sha256(json.dumps(sorted(ids),sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def grade(y,line,side):
    a,b=Decimal(str(y)),Decimal(str(line))
    return 'PUSH' if a==b else 'WIN' if ((a>b)==(side=='over')) else 'LOSS'
def close(a,b):return a==b or(a is not None and b is not None and abs(a-b)<max(1e-10,abs(b)*1e-12))
def quantile(values,p):
    a=sorted(values);x=(len(a)-1)*p;i=int(x);f=x-i
    return a[i]+f*(a[min(i+1,len(a)-1)]-a[i])


def run(source,parent,out):
    protocol=read(parent/'FROZEN_PROTOCOL.json');focal={t:(t,*v)for t,v in protocol['focals'].items()};data=collections.defaultdict(dict);raw=read(source)
    assert sha(source)==read(out/'RUN_RECEIPT.json')['source_rows_sha256']
    assert sha(parent/'SCORES.json')==read(out/'RUN_RECEIPT.json')['parent_score_sha256']
    cross_identity={};cutoffs=0;source_ids={d['week']:d['source_id']for d in protocol['source_bindings']if d['member']=='GRADED_METHOD_ROWS.json.gz'}
    for r in raw['rows']:
        if r.get('population_diagnostic'):continue
        key=tuple(r['recipe']);idx=r['week'],r['source_row_index'];assert idx not in data[key];data[key][idx]=r
        assert key[0]==r['target'] and r['source_field']=='ranking_point' and r['source_id']==source_ids[r['week']]
        assert int(r['game_id'].split('_')[0])==2026 and int(r['game_id'].split('_')[1])==r['week']
        ident=tuple(r[k]for k in ('game_id','player_id','target','line','actual','decision_time','kickoff'))
        crosskey=r['target'],idx
        if crosskey in cross_identity:assert cross_identity[crosskey]==ident
        cross_identity[crosskey]=ident
        if r['admitted']:
            assert r['point'] is not None
            p,L=Decimal(str(r['point'])),Decimal(str(r['line']));expected='over'if p>L else'under'if p<L else None
            assert expected==r['selected_side']
            if expected and r['actual']is not None and r['participation']=='VERIFIED_PLAYED_POSITIVE_PHYSICAL':assert grade(r['actual'],r['line'],expected)==r['statistical_state']
            decision=datetime.fromisoformat(r['decision_time'].replace('Z','+00:00'));kickoff=datetime.fromisoformat(r['kickoff'].replace('Z','+00:00'));assert decision.tzinfo and kickoff.tzinfo and decision<kickoff;cutoffs+=1
    # Build admissible own/common/learned masks without looking at outcomes.
    possible=collections.defaultdict(dict)
    def add(key,ids):possible[key][mask(ids)]=set(ids)
    for key,dd in data.items():
        ff=data[focal[key[0]]];own={k for k,r in dd.items()if r['admitted']};common={k for k in dd.keys()&ff.keys()if dd[k]['admitted']and ff[k]['admitted']}
        learned={k for k in common if dd[k]['fallback']=='none'and ff[k]['fallback']=='none'and key[1]not in ('SAVED_ADJUSTED_POINT_DIRECTION_RETAINED_PRECISION','SAVED_RAW_PROJECTION_DIRECTION_RETAINED_PRECISION')}
        for target,ids in [(key,own),(key,common),(focal[key[0]],common)]:add(target,ids)
        if key[1]not in ('SAVED_ADJUSTED_POINT_DIRECTION_RETAINED_PRECISION','SAVED_RAW_PROJECTION_DIRECTION_RETAINED_PRECISION'):add(key,learned);add(focal[key[0]],learned)
    parents={r['record_id']:r for r in read(parent/'SCORES.json')if r['record_kind']=='prop_selection_evaluation'and r['side']=='Combined'};assert len(parents)==63
    expected={};parent_source={}
    for record,p in parents.items():
        key=p['target'],p['procedure_id'],p['history_regime'],p['product_id'];ids=possible[key][p['membership_sha256']];dd=data[key];own=p['cohort_id']=='OWN_DECISION_ELIGIBLE_FULL_SYSTEM';pool=set(dd)if own else ids
        parent_source[record]=key,pool,ids
        for week in(5,6,7):expected[record,week]=[dd[k]for k in sorted(pool)if k[0]==week]
    scores=read(out/'SCORES.json');sides=[s for s in scores if s['record_kind']=='prop_selection_evaluation'];numeric=[s for s in scores if s['record_kind']=='forecast_evaluation_view'];assert len(sides)==567 and len(numeric)==189
    def selected(rows,side,constant=None):
        subset=[]
        for r in rows:
            available=r['admitted']and r['point']is not None;s=constant if constant else r['selected_side']if available else None
            if s is not None and(side=='Combined'or side==s):
                state=grade(r['actual'],r['line'],s)if r['actual']is not None and r['participation']=='VERIFIED_PLAYED_POSITIVE_PHYSICAL'else 'UNKNOWN_PARTICIPATION'
                subset.append((r,state))
        return subset
    def side_check(s,rows,constant=None):
        sub=selected(rows,s['side'],constant);c=collections.Counter(state for r,state in sub);m=s['selection_metrics'];assert (s['forecast_rows'],s['n'],m['WIN'],m['LOSS'],m['PUSH'])==(len(sub),c['WIN']+c['LOSS'],c['WIN'],c['LOSS'],c['PUSH'])
        assert m['hit_rate']==(c['WIN']/(c['WIN']+c['LOSS'])if c['WIN']+c['LOSS']else None)
        assert m['selection_pool_count']==len(rows)
        assert m['selection_coverage']==(len(sub)/len(rows)if rows else None)
        if constant is None:
            un=sum(not(r['admitted']and r['point']is not None)for r in rows);ab=sum(r['admitted']and r['point']is not None and r['selected_side']is None for r in rows)
            assert m['technical_unavailable']==un and m['admitted_rule_abstentions']==ab
            # Issued forecasts are learned; missing rows are not assigned completed fallback predictions.
            known_fallback=sum(r['admitted']and r['fallback']not in('none',None)for r in rows)
            assert m['fallback_issued']==known_fallback
        return c,len(sub)
    def numeric_check(s,rows):
        valid=[r for r in rows if r['admitted']and r['point']is not None and r['actual']is not None and r['participation']=='VERIFIED_PLAYED_POSITIVE_PHYSICAL'];e=[r['point']-r['actual']for r in valid];a=list(map(abs,e));n=len(e)
        assert s['forecast_rows']==len(rows)and s['n']==n
        assert s['admitted_forecast_rows']==sum(r['admitted']and r['point']is not None for r in rows)
        assert s['unavailable_forecasts']==len(rows)-s['admitted_forecast_rows']
        met=dict(mae=math.fsum(a)/n,mse=math.fsum(v*v for v in e)/n,bias=math.fsum(e)/n,p90_abs=quantile(a,.9),p95_abs=quantile(a,.95),max_abs=max(a))if n else dict(mae=None,mse=None,bias=None)
        if n:met['rmse']=math.sqrt(met['mse'])
        for k,v in met.items():assert close(v,s[k]),(k,v,s[k])
        for k,pc in s['precision_counts'].items():
            num=sum(v==0 for v in a)if k=='exact_rate'else sum(v<=int(k.split('_')[-1])for v in a)if '_le_'in k else sum(v<int(k.split('_')[-1])for v in a)
            assert pc['numerator']==num and pc['denominator']==n
            if k in s:assert close(s[k],num/n if n else None)
    for s in sides:
        rows=expected[s['parent_cumulative_record_id'],s['week']];side_check(s,rows)
        ids=parent_source[s['parent_cumulative_record_id']][2];assert s['source_mask_sha256']==mask(k for k in ids if k[0]==s['week'])
    for s in numeric:numeric_check(s,expected[s['parent_cumulative_record_id'],s['week']])
    # Every parent side, not just Combined, reconciles across the three partitions.
    parent_all=read(parent/'SCORES.json');parent_side={}
    for p in parent_all:
        if p['record_kind']=='prop_selection_evaluation':parent_side[p['procedure_id'],p['history_regime'],p['product_id'],p['target'],p['cohort_id'],p['side']]=p
    for record,p in parents.items():
        for side in('over','under','Combined'):
            pp=parent_side[p['procedure_id'],p['history_regime'],p['product_id'],p['target'],p['cohort_id'],side];rr=[s for s in sides if s['parent_cumulative_record_id']==record and s['side']==side]
            assert len(rr)==3
            for field in('WIN','LOSS','PUSH'):assert sum(s['selection_metrics'][field]for s in rr)==pp['selection_metrics'][field]
            assert sum(s['forecast_rows']for s in rr)==pp['forecast_rows']
    manifests=read(out/'WEEKLY_MEMBERSHIP_MANIFEST.json');assert len(manifests)==189
    for m in manifests:
        rows=expected[m['parent_record_id'],m['week']];assert m['eligible']==len(rows)and m['admitted']==sum(r['admitted']and r['point']is not None for r in rows)
        assert m['mask_sha256']==mask(k for k in parent_source[m['parent_record_id']][2]if k[0]==m['week'])
    # Full-system supplements restore all28queries, independently of a canonical mask alias.
    full=read(out/'FULL_SYSTEM_FOCAL_SCORES.json');assert len(full)==24;focal_summary=[]
    for s in full:
        rows=[r for idx,r in data[focal[s['target']]].items()if idx[0]==s['week']];assert len(rows)==28
        if s['record_kind']=='prop_selection_evaluation':side_check(s,rows)
        else:numeric_check(s,rows)
    for target in('pass_yd','pass_cmp'):
        total=collections.Counter();byweek=[]
        for week in(5,6,7):
            rows=[r for idx,r in data[focal[target]].items()if idx[0]==week];entry=dict(week=week,eligible=28,unavailable=sum(not r['admitted']for r in rows),sides={})
            for side in('over','under','Combined'):
                c,n=side_check(next(s for s in full if s['record_kind']=='prop_selection_evaluation'and s['target']==target and s['week']==week and s['side']==side),rows)
                entry['sides'][side]=dict(wins=c['WIN'],losses=c['LOSS'],decided=c['WIN']+c['LOSS'],rate=c['WIN']/(c['WIN']+c['LOSS'])if c['WIN']+c['LOSS']else None)
                if side=='Combined':total.update(c)
            byweek.append(entry)
        assert (total['WIN'],total['WIN']+total['LOSS'])==((28,80)if target=='pass_yd'else(33,76))
        own={k for k,r in data[focal[target]].items()if r['admitted']};aliases=[p for p in parents.values()if(p['target'],p['procedure_id'],p['history_regime'],p['product_id'])==focal[target]and p['membership_sha256']==mask(own)];assert len(aliases)==1 and aliases[0]['cohort_id'].startswith('FOCAL_COMMON')
        focal_summary.append(dict(target=target,procedure=focal[target][1:],cumulative=dict(wins=total['WIN'],losses=total['LOSS'],decided=total['WIN']+total['LOSS']),weekly=byweek,source_own_mask_canonical_alias=aliases[0]['cohort_id']))
    constants=read(out/'CONSTANT_CONTROL_SCORES.json');assert len(constants)==72
    for s in constants:
        rows=[r for idx,r in data[focal[s['target']]].items()if idx[0]==s['week']and(s['cohort_id']=='FULL_RETAINED_BOARD'or r['admitted'])]
        side_check(s,rows,constant='over'if s['strategy']=='alwaysOver'else'under');assert s['mae']is None and s['bias']is None
    examples=[]
    for ex in raw['worked_examples']:
        r=ex['example'];assert grade(r['actual'],r['line'],ex['side'])==ex['state']
        source_row=data[focal[ex['target']]][r['week'],r['source_row_index']]
        assert all(source_row[k]==r[k]for k in('game_id','player_id','target','line','actual','point','decision_time','selected_side','statistical_state'))
        examples.append(dict(target=ex['target'],selected_side=ex['side'],state=ex['state'],week=r['week'],source_record_hash=hashlib.sha256(json.dumps([r['week'],r['source_row_index'],ex['target']],separators=(',',':')).encode()).hexdigest()))
    qualification=out/'NATIVE_FALLBACK_SCOPE_QUALIFICATION.json'
    result=dict(state='PASS_SELECTION_NUMERICAL_MASKS_WITH_EXPLICIT_FALLBACK_SCOPE_QUALIFICATION',source_sha256=sha(source),parent_score_sha256=sha(parent/'SCORES.json'),new_score_sha256=sha(out/'SCORES.json'),full_system_score_sha256=sha(out/'FULL_SYSTEM_FOCAL_SCORES.json'),parent_triads=63,weekly_triads=189,weekly_side_views_verified=567,weekly_native_views_verified=189,full_system_views_verified=24,constant_side_views_verified=72,member_masks_verified=189,source_recipe_rows=3024,admitted_decision_before_kickoff_checks=cutoffs,representative_correct_wrong_examples_verified=examples,focals=focal_summary,native_fallback_scope=dict(qualification_path='NATIVE_FALLBACK_SCOPE_QUALIFICATION.json',qualification_present=qualification.exists(),issued_focal_forecasts='Every available focal output has known fallback none; no completed fallback forecast was issued.',unavailable_focal_queries='Missing output rows retain unknown fallback state; PY0/1/3 andPC0/2/6, not learned/fallback outcomes.',native_fallback_unknown_zero='Issued-only scope in the full-system supplement; do not interpret as all28query fallback states known.'),limitations=['No new fits/inference/forecasts/outcomes or private derivatives; same exposed W5-W7 records partitioned.','Admitted row clocks and exact P1 boundaries checked; full model training/tuning chronology and historical source publication not reauthenticated.','Provider-labelled retained thresholds remain a different source/horizon panel from C Pinnacle kickoff diagnostics.','Old empty focal presentation attempts preserved; original emitter alias deduplication, not tuple/list comparison, explains their empty OWN-label lookup.','Numerical and selected-side results remain separate; severe weekly losses do not validate inversion or a causal remedy.'])
    (out/'INDEPENDENT_WEEKLY_PARTITION_VERIFICATION_V1.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items()if k not in('representative_correct_wrong_examples_verified','focals')},indent=2));print('FOCALS',json.dumps(focal_summary,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('parent',type=Path);p.add_argument('out',type=Path);a=p.parse_args();run(a.source,a.parent,a.out)
