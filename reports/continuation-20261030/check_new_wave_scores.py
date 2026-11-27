"""Independent retained-row/source/aggregate checks, never fits or acquires labels."""
from collections import defaultdict,Counter
import csv,gzip,hashlib,json,math,sys
from pathlib import Path
from decimal import Decimal,localcontext

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'reports/verification'))
from check_empirical_diagnostic import ACTION_COUNTS,ACTION_YARDS,count,num,value
from check_label_extension import metrics

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def decode(p):return json.loads(gzip.decompress(p.read_bytes()))

def raw_labels(source,protocol):
    for d in protocol['source_ids']:assert sha(source/d['name'])==d['sha256']
    final={}
    with(source/'games.csv').open()as f:
        for r in csv.DictReader(f):
            if r['game_type']!='REG'or int(r['season'])not in range(2022,2027)or(int(r['season'])==2026 and int(r['week'])>7):continue
            hs,away,result,total=[num(r[k])for k in('home_score','away_score','result','total')]
            final[r['game_id']]=count(hs)and count(away)and result==hs-away and total==hs+away
    labels={}
    for year in range(2022,2027):
        with (source/f'stats_player_week_{year}.csv').open()as f:
            for r in csv.DictReader(f):
                if r['season_type']!='REG' or int(r['season'])!=year or(year==2026 and int(r['week'])>7):continue
                if r['position']not in ('QB','RB','WR','TE'):continue
                played=any(count(num(r[k]))and num(r[k])>0 for k in ACTION_COUNTS)or any(num(r[k])not in(None,0)for k in ACTION_YARDS)
                ys={t:value(t,r)if played else None for t in protocol.get('targets',('pass_yd','pass_td','pass_cmp','pass_att','pass_int','rush_yd','rush_att','rec','rec_yd','rush_rec_yd','anytime_td'))}
                fields={'passing_yards':'.04','passing_tds':'4','passing_interceptions':'-1','rushing_yards':'.1','rushing_tds':'6','receptions':'1','receiving_yards':'.1','receiving_tds':'6','fumbles_lost_total':'-1','passing_2pt_conversions':'2','rushing_2pt_conversions':'2','receiving_2pt_conversions':'2'}
                ys['nick-chart-ppr-v1']=sum(num(r[k])*Decimal(w)for k,w in fields.items())if played and final[r['game_id']]and num(r['fumble_recovery_tds'])==num(r['special_teams_tds'])==0 and all(num(r[k])is not None for k in fields)else None
                labels[(r['game_id'],r['player_id'])]=ys
    return labels

def verify(public,private,source):
    p=json.loads((public/'FROZEN_PROTOCOL.json').read_text());run=json.loads((public/'RUN_RECEIPT.json').read_text())
    chart='chart-wave'in public.name
    distribution='distribution-'in public.name or chart
    labels=raw_labels(source,p);rows=[];groups=defaultdict(list);future=[];hashes=[];source_checks=0
    for fp in sorted(public.glob('*-FORECAST.json')):
        receipt=json.loads(fp.read_text());d=receipt['packet'];base=private
        name=d.get('bundle_name',d.get('name'))
        if d.get('reused_from')or receipt.get('reused_from'):base=private.with_name('distribution-wave-v1')
        file=base/name;assert sha(file)==d['sha256'];hashes.append((receipt['slot'],d['sha256']))
        packet=decode(file);rs=packet['rows'];assert len(rs)==receipt.get('output_views',receipt.get('rows'))
        for r in rs:
            if r['week']==8:
                assert r['actual']is None;future.append(r)
                if r['prediction']is not None:
                    from datetime import datetime
                    clock=lambda x:datetime.fromisoformat(x.replace('Z','+00:00'))
                    assert clock(r['issued_at_utc'])<=clock(receipt['actual_persistence_completed_at'])<clock(r['owner_input_cutoff_utc'])<clock(r['kickoff_utc'])
                continue
            expected=labels[(r['game_id'],r['player_id'])][r['target']]
            assert (expected is None and r['actual']is None)or(expected is not None and num(str(r['actual']))==expected)
            source_checks+=1
            if distribution and r['prediction']is None:continue
            family=r.get('family',r.get('procedure_family_id'))
            endings=[('ALL','ALL','ALL'),(str(r['week']),'ALL','ALL'),('ALL',r['position'],'ALL')]
            if r['fallback']=='none':endings.append(('ALL','ALL','LEARNED_ONLY'))
            for suffix in endings:groups[(family,r['policy_id'],r['target'],r['population'],r['history_regime'],r['product_id'])+suffix].append(r)
            rows.append(r)
    scores=json.loads((public/'SCORES.json').read_text());checks=0;maxdelta=0.;census=[]
    for s in scores:
        family=s['procedure_family_id']if distribution else s['procedure_id'].split(':')[0]
        key=(family,s['policy_id'],s['target'],s['population'],s['history_regime'],s['product_id'],str(s['week']),s['position'],s['fallback_view'])
        rs=groups[key];pairs=[(r['prediction'],r['actual'])for r in rs if r['prediction']is not None and r['actual']is not None]
        n=len(pairs);assert n==s['n'];checks+=1
        assert len(rs)==s['forecast_rows'];checks+=1
        games=len({r['game_id']for r in rs if r['prediction']is not None and r['actual']is not None})
        assert games==s['unique_games'];checks+=1
        census.append(dict(procedure_id=s['procedure_id'],policy_id=s['policy_id'],history_regime=s['history_regime'],product_id=s['product_id'],target=s['target'],population=s['population'],week=s['week'],position=s['position'],fallback_view=s['fallback_view'],scored_games=games,forecast_games=len({r['game_id']for r in rs}),n=n))
        if n:
            expected=metrics(pairs,s['target'])
            # Reproduce the frozen IEEE754 subtraction contract independently:
            # subtract exact binary floats in Decimal, then round once to float.
            # Decimal(str(prediction)) alone is a different boundary convention.
            with localcontext()as binary_exact:
                binary_exact.prec=1200
                errors=[abs(float(Decimal.from_float(float(a))-Decimal.from_float(float(b))))for a,b in pairs]
            for tolerance in (1,5,10):
                expected[f'abs_lt_{tolerance}']=Decimal(sum(e<tolerance for e in errors))/n
                expected[f'abs_le_{tolerance}']=Decimal(sum(e<=tolerance for e in errors))/n
            for metric,v in expected.items():
                if metric=='n':continue
                if v.is_infinite():assert s[metric]is None and s['infinite_log_losses']>0
                else:
                    delta=abs(float(v)-s[metric]);maxdelta=max(maxdelta,delta)
                    assert math.isclose(float(v),s[metric],rel_tol=4e-12,abs_tol=2e-8),(key,metric,v,s[metric])
                checks+=1
        if distribution:
            selected=[r for r in rs if r['actual']is not None]
            inf=sum(r['distribution_summary']['infinite_nll']for r in selected);assert inf==s['infinite_NLL'];checks+=1
            for output,field in [('CRPS','crps'),('interval90_width','interval90_width'),('interval90_coverage','interval90_covered'),('mean_zero_mass','zero_mass')]:
                expected=sum(Decimal(int(r['distribution_summary'][field]))if isinstance(r['distribution_summary'][field],bool)else Decimal(str(r['distribution_summary'][field]))for r in selected)/len(selected)if selected else None
                assert (expected is None and s[output]is None)or math.isclose(float(expected),s[output],rel_tol=4e-12,abs_tol=2e-8);checks+=1
            if inf:assert s['NLL']is None
            elif selected:assert math.isclose(sum(r['distribution_summary']['nll']for r in selected)/len(selected),s['NLL'],rel_tol=4e-12,abs_tol=2e-8)
            else:assert s['NLL']is None
            checks+=1
            assert dict(Counter(r['fallback']for r in rs))==s['fallback_source_counts'];checks+=1
    assert len(rows)+len(future)==run.get('forecast_output_views',run.get('actual_output_rows'))
    cohorts=defaultdict(dict)
    for s in scores:
        if str(s['week'])=='ALL'and s['position']=='ALL'and s['fallback_view']=='ALL':
            key=(s['target'],s['population'],s['product_id']);family=s['procedure_family_id']if distribution else s['procedure_id'].split(':')[0]
            rs=groups[(family,s['policy_id'],s['target'],s['population'],s['history_regime'],s['product_id'],'ALL','ALL','ALL')]
            cohorts[key][family+':'+s['policy_id']]=frozenset((r['game_id'],r['player_id'],r['target'])for r in rs)
    assert all(len(set(views.values()))==1 for views in cohorts.values())
    pairs=[];examples=[]
    oldroot=ROOT/'reports/continuation-20261029/hgb-history-v1';oldprivate=private.parent/'hgb-history-v1';old={}
    for fp in([]if chart else oldroot.glob('W0[1-7]-*-FORECAST.json')):
        d=json.loads(fp.read_text())['packet'];file=oldprivate/d['name'];assert sha(file)==d['sha256']
        for r in decode(file)['rows']:
            if r['actual']is not None:old[(r['game_id'],r['player_id'],r['target'],r['population'],r['history_regime'],r['objective'])]=r
    if chart:
        d=run['empirical_prediction_packet'];file=private/d['bundle_name'];assert sha(file)==d['sha256']
        for r in decode(file)['rows']:
            if r['season']==2026 and r['actual']is not None:
                objective='absolute_error_point'if r['product_id']=='lower_median'else'squared_error_mean'
                old[(r['game_id'],r['player_id'],r['target'],r['population'],r['history_regime'],objective)]=r
    for s in scores:
        if str(s['week'])!='ALL'or s['position']!='ALL'or s['fallback_view']!='ALL':continue
        family=s['procedure_family_id']if distribution else s['procedure_id'].split(':')[0]
        rs=groups[(family,s['policy_id'],s['target'],s['population'],s['history_regime'],s['product_id'],'ALL','ALL','ALL')]
        objective='log_loss_probability'if s['target']=='anytime_td'else'absolute_error_point'if s['product_id']in('lower_median','absolute_loss_point')else'squared_error_mean'
        deltas=[]
        for r in rs:
            if r['prediction']is None or r['actual']is None:continue
            o=old[(r['game_id'],r['player_id'],r['target'],r['population'],r['history_regime'],objective)]
            y=Decimal(str(r['actual']));assert y==Decimal(str(o['actual']))
            a=abs(Decimal(str(r['prediction']))-y);b=abs(Decimal(str(o['prediction']))-y)
            if r['target']=='anytime_td':a=a*a;b=b*b
            delta=a-b;deltas.append(delta)
            if s['population']=='primary'and delta!=0 and not any(e['kind']==('win'if delta<0 else'loss')for e in examples):
                examples.append(dict(kind='win'if delta<0 else'loss',opaque_query_id=hashlib.sha256((r['game_id']+r['player_id']+r['target']).encode()).hexdigest()[:16],target=r['target'],family=family,policy_id=r['policy_id'],new_loss=str(a),old_loss=str(b),difference=str(delta)))
        pairs.append(dict(family=family,policy_id=s['policy_id'],history_regime=s['history_regime'],target=s['target'],population=s['population'],product_id=s['product_id'],n=len(deltas),mean_paired_loss_difference=float(sum(deltas)/len(deltas))if deltas else None,row_wins=sum(x<0 for x in deltas),row_losses=sum(x>0 for x in deltas),ties=sum(x==0 for x in deltas),old_objective=objective))
    result=dict(status='PASS_INDEPENDENT_SOURCE_JOIN_AND_RETAINED_ROW_SCORE_REPLAY',code_sha256=run['code_sha256'],protocol_sha256=sha(public/'FROZEN_PROTOCOL.json'),run_receipt_sha256=sha(public/'RUN_RECEIPT.json'),forecast_packet_manifest_sha256=hashlib.sha256(json.dumps(hashes,separators=(',',':')).encode()).hexdigest(),source_join_checks=source_checks,aggregate_views=len(scores),independent_metric_checks=checks,max_metric_absolute_difference=maxdelta,historical_output_views=len(rows),week8_output_views=len(future),week8_issued=sum(r['prediction']is not None for r in future),week8_abstentions=sum(r['prediction']is None for r in future),week8_games=len({r['game_id']for r in future}),first_game_excluded=all(r['game_id']!='2026_08_CAR_GB'for r in future),all_policy_cohorts_identical=True,worked_examples=examples,paired_old_control_views=pairs,new_fits=0,new_forecasts=0,actual_week8_labels_read=0,distribution_scope='All distribution-score aggregates recomputed; individual law calculations are separately reviewed, not authenticated merely by these saved summaries.'if distribution else None,uncertainty='Seven evaluated weeks: insufficient week clusters under inherited >=8rule; no significance assertion')
    return result,census

if __name__=='__main__':
    with localcontext()as ctx:
        ctx.prec=50;result,census=verify(Path(sys.argv[1]),Path(sys.argv[2]),Path(sys.argv[3]))
    stem='CHART'if'chart-wave'in sys.argv[1]else'DISTRIBUTION'if'distribution-'in sys.argv[1]else'COUNT_ABLATION'
    root=Path(__file__).parent
    (root/(stem+'_INDEPENDENT_SCORE_REVIEW.json')).write_text(json.dumps(result,indent=2)+'\n')
    (root/(stem+'_VIEW_GAME_COUNTS.json')).write_text(json.dumps(dict(source_run_sha256=result['run_receipt_sha256'],forecast_packet_manifest_sha256=result['forecast_packet_manifest_sha256'],rows=census),indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items()if k!='paired_old_control_views'},indent=2))
