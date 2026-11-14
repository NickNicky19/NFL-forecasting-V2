"""Independent complete saved-row chart arithmetic/control replay; no fitting."""
from collections import defaultdict,Counter
from decimal import Decimal,localcontext
from pathlib import Path
import csv,gzip,json,math,sys
from check_new_wave_scores import raw_labels,sha,decode
from check_new_wave_prefixes import load
from check_label_extension import metrics

def audit(public,private,source):
    p=json.loads((public/'FROZEN_PROTOCOL.json').read_text());run=json.loads((public/'RUN_RECEIPT.json').read_text());labels=raw_labels(source,p);raw,_,_=load(source,p)
    lookup={(r['game_id'],r['player_id']):r for r in raw};d=run['empirical_prediction_packet'];path=private/d['bundle_name'];assert sha(path)==d['sha256'];rows=decode(path)['rows'];groups=defaultdict(list);counts=Counter();states=Counter()
    labelpacket=decode(private/'qualified-chart-labels.json.gz')
    for r in labelpacket['rows']:
        label=r['label'];y=labels[(r['game_id'],r['player_id'])]['nick-chart-ppr-v1'];expected_grid=None if y is None else int(y*50)
        assert label['points_times_50']==expected_grid
        assert (label['points']is None and y is None)or(label['points']is not None and Decimal(str(label['points']))==y)
        states[(r['season'],label['status'])]+=1;counts['qualified_label_values_checked']+=2
    # Rebuild eligible histories with exact floor/current-row cutoff, preserving
    # unavailable and unresolved rows in the evaluation population.
    for r in rows:
        target='nick-chart-ppr-v1';source_row=lookup[(r['game_id'],r['player_id'])];y=labels[(r['game_id'],r['player_id'])][target]
        assert (y is None and r['actual']is None)or(y is not None and Decimal(str(r['actual']))==y)
        assert r['cutoff']==source_row['kickoff']
        assert r['latest_training_label_available']is None or r['latest_training_label_available']<r['cutoff']
        year=r['season']
        for season,week,pos in[(str(year),'ALL','ALL'),(str(year),str(r['week']),'ALL'),(str(year),'ALL',r['position']),('POOLED_2022_2026','ALL','ALL')]:groups[(r['history_regime'],r['product_id'],season,week,pos)].append(r)
        counts['source_value_and_clock_checks']+=3
    # Stratified deterministic saved rows across season/history/product/role.
    samples={}
    for r in rows:samples.setdefault((r['season'],r['history_regime'],r['product_id'],r['position']),r)
    for r in samples.values():
        year=r['season'];floor=year if r['history_regime']=='H-CURRENT'else max(2022,year-1)if r['history_regime']=='H-RECENT'else 2022
        eligible=[s for s in raw if floor<=s['season']<=year and s['position']==r['position']and s['available']<r['cutoff']and s['values']['nick-chart-ppr-v1']is not None]
        own=[s for s in eligible if s['player_id']==r['player_id']];chosen=own or eligible;ys=sorted(s['values']['nick-chart-ppr-v1']for s in chosen)
        pred=(sum(ys)/len(ys)if r['product_id']=='mean'else ys[(len(ys)-1)//2])/50 if ys else 0.
        assert math.isclose(float(pred),r['prediction'],rel_tol=4e-13,abs_tol=4e-12);counts['raw_history_predictions_checked']+=1
    scores=json.loads((public/'EMPIRICAL_SCORES.json').read_text());maxdelta=0.
    for s in scores:
        rs=groups[(s['history_regime'],s['product_id'],str(s['season']),str(s['week']),s['position'])];pairs=[(r['prediction'],r['actual'])for r in rs if r['actual']is not None]
        assert len(pairs)==s['n']and len(rs)==s['forecast_rows'];counts['score_checks']+=2
        if not pairs:continue
        expected=metrics(pairs,'nick-chart-ppr-v1')
        with localcontext()as exact:
            exact.prec=1200;errors=[abs(float(Decimal.from_float(float(a))-Decimal.from_float(float(b))))for a,b in pairs]
        for tol in(1,5,10):expected['abs_lt_'+str(tol)]=Decimal(sum(e<tol for e in errors))/len(errors);expected['abs_le_'+str(tol)]=Decimal(sum(e<=tol for e in errors))/len(errors)
        for name,v in expected.items():
            if name=='n':continue
            delta=abs(float(v)-s[name]);maxdelta=max(maxdelta,delta);assert math.isclose(float(v),s[name],rel_tol=4e-12,abs_tol=2e-8);counts['score_checks']+=1
    return dict(status='PASS_ALL_PARTIAL_CHART_LABEL_VALUES_AND_EMPIRICAL_SCORE_VIEWS',counts=dict(counts),empirical_output_views=len(rows),empirical_score_views=len(scores),max_metric_difference=maxdelta,current_2026_label_states={status:n for(year,status),n in states.items()if year==2026},all_labels=len(labelpacket['rows']),new_fits=0,new_forecasts=0,week8_actuals_read=0,source_contract_limit='Provider-qualified partialchartzeros;164rarepositive/unknownrows allsource, one in currentregistered4rolecohort; no rarepositive reconstruction or full-eventcensus authentication',run_receipt_sha256=sha(public/'RUN_RECEIPT.json'))

if __name__=='__main__':
    with localcontext()as ctx:
        ctx.prec=50;result=audit(Path(sys.argv[1]),Path(sys.argv[2]),Path(sys.argv[3]))
    (Path(__file__).parent/'CHART_EMPIRICAL_INDEPENDENT_REVIEW.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
