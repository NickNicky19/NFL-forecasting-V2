"""Independent raw-value, weekly-loss and chronological selector verification."""
import argparse
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal
import csv
import gzip
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import resource
import time
from zoneinfo import ZoneInfo

spec = importlib.util.spec_from_file_location('independent_numeric', Path(__file__).with_name('check_numerical_pairs.py'))
independent = importlib.util.module_from_spec(spec)
spec.loader.exec_module(independent)
sha, canonical, close = independent.sha, independent.canonical, independent.close


def model3(raw):
    t, p, h, v = independent.model(raw)
    return t, p, v


def stable(key):return '|'.join(key)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo-root',type=Path,required=True);ap.add_argument('--public-root',type=Path,required=True);ap.add_argument('--private-root',type=Path,required=True);ap.add_argument('--schedule',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();start=time.monotonic()
    p=json.loads((a.public_root/'FROZEN_PROTOCOL.json').read_bytes());receipt=json.loads((a.public_root/'RUN_RECEIPT.json').read_bytes())
    assert receipt['protocol_sha256']==sha(a.public_root/'FROZEN_PROTOCOL.json')
    assert receipt['score_sha256']==sha(a.public_root/'SCORES.json')
    assert receipt['mask_sha256']==sha(a.public_root/'EXACT_MASK_ADMISSION.json')
    assert p['schedule_sha256']==sha(a.schedule)
    for b in p['source_aggregates']:assert sha(a.repo_root/b['path'])==b['sha256']
    byweek=defaultdict(list)
    with a.schedule.open()as f:
        for game in csv.DictReader(f):
            y,w=int(game['season']),int(game['week'])
            if game['game_type']!='REG'or y not in(2025,2026)or not 1<=w<=(18 if y==2025 else 7):continue
            kickoff=datetime.fromisoformat(game['gameday']+'T'+game['gametime']).replace(tzinfo=ZoneInfo('America/New_York')).timestamp()
            byweek[y,w].append(kickoff)
    for (y,w),clocks in byweek.items():
        assert p['origins'][f'{y}-{w}']==min(clocks)
        assert p['week_score_available'][f'{y}-{w}']==max(clocks)+604800
        assert p['gamecounts'][f'{y}-{w}']==len(clocks)
    roster={tuple(k)for k in p['roster']};assert len(roster)==120 and len({k[0]for k in roster})==12
    labels={};query_indices={};masks=defaultdict(lambda:[set(),set()]);metrics=defaultdict(lambda:dict(errors=[],squares=[],fallback=0,prec=defaultdict(int)))
    scanned=selected=0
    for source in p['raw_sources']:
        year=source['season']
        for binding in source['members']:
            file=a.private_root/binding['member'];assert sha(file)==binding['sha256']
            it=independent.packets(file)if binding['kind']=='packet'else csv.DictReader(gzip.open(file,'rt'))
            for raw in it:
                scanned+=1
                if int(raw.get('season',year))!=year or raw.get('population')!='primary'or raw.get('history_regime')!='H-MULTI':continue
                w=int(raw['week'])
                if not 1<=w<=(18 if year==2025 else 7):continue
                if binding['source_id']=='empirical':raw['procedure_id']='empirical-player-history-control-v1'
                elif binding['source_id']=='hgb':raw['procedure_id']='hgb-direct-history-controls-v1:'+raw['objective']
                key=model3(raw)
                if key not in roster or(year==2025 and binding['source_id']=='season'and'qb-rb-specialization'in key[1]):continue
                q=tuple(raw[k]for k in('game_id','player_id','target','population','position'));label=independent.number(raw.get('actual'));point=independent.number(raw.get('prediction'))
                identity=(year,q)
                if identity in labels:assert labels[identity]==label,'cross-recipe actual VALUE mismatch'
                else:labels[identity]=label;query_indices[identity]=len(query_indices)
                index=query_indices[identity];mask=masks[year,key,w];assert index not in mask[0];mask[0].add(index)
                mm=metrics[year,key,w];mm['fallback']+=raw['fallback']!='none';selected+=1
                if label is None:continue
                assert point is not None
                if key[0]in('pass_td','pass_cmp','pass_att','pass_int','rush_att','rec'):assert label>=0 and label==int(label)
                if key[0]=='anytime_td':assert label in(0,1)and 0<=point<=1
                if key[0]in('pass_yd','rush_yd','rec_yd','rush_rec_yd'):assert label==int(label)
                mask[1].add(index);error=abs(point-label);mm['errors'].append(error);mm['squares'].append((point-label)**2)
                grid=key[0]=='nick-chart-ppr-v1'and key[2]=='lower_median'
                exacterror=abs(Decimal(str(point))-Decimal(str(label)))if grid else error
                if grid:
                    for val in(point,label):assert Decimal(str(val))*50==(Decimal(str(val))*50).to_integral_value()
                mm['prec']['exact_rate']+=error==0
                for value in(1,5,10):
                    mm['prec'][f'abs_lt_{value}']+=exacterror<value
                    mm['prec'][f'abs_le_{value}']+=exacterror<=value
    assert scanned==receipt['raw_rows_scanned']
    reverse={value:key for key,value in query_indices.items()};maskrows=json.loads((a.public_root/'EXACT_MASK_ADMISSION.json').read_bytes())
    for m in maskrows:
        year,w=m['season'],m['week'];key=(m['target'],m['procedure_id'],m['product_id']);mask=masks[year,key,w]
        qq=sorted(reverse[i][1]for i in mask[0]);ss=sorted(reverse[i][1]for i in mask[1])
        assert m['query_n']==len(qq)and m['supported_n']==len(ss)
        assert m['query_sha256']==hashlib.sha256(canonical(qq)).hexdigest()
        assert m['support_sha256']==hashlib.sha256(canonical(ss)).hexdigest()
        values=sorted((reverse[i][1],labels[reverse[i]])for i in mask[1])
        assert m['label_values_sha256']==hashlib.sha256(canonical(values)).hexdigest()
        base=tuple(m['reference']);assert mask==masks[year,base,w]
        old=p['weekly2025'if year==2025 else'weekly2026'][stable(key)][str(w)];computed=metrics[year,key,w]
        n=len(computed['errors']);assert n==int(old['n'])
        actual_loss=math.fsum(computed['squares']if key[0]=='anytime_td'else computed['errors'])/n
        close(float(old['brier'if key[0]=='anytime_td'else'mae']),actual_loss,'weekly raw loss')
        assert int(old.get('fallback_rows')or 0)==computed['fallback']
        prec=old.get('precision_counts')or{}
        if isinstance(prec,str):prec=json.loads(prec)
        for name,pair in prec.items():
            numerator,denominator=pair if isinstance(pair,list)else(pair['numerator'],pair['denominator'])
            assert int(numerator)==computed['prec'][name]and int(denominator)==n,(year,w,key[0],name)
    assert len(maskrows)==receipt['mask_checks']==3000
    bytarget=defaultdict(list)
    for k in roster:bytarget[k[0]].append(k)
    decisions=json.loads((a.public_root/'DECISIONS.json').read_bytes());observed={(r['target'],r['policy_id'],r['evaluation_week']):r for r in decisions}
    scores=json.loads((a.public_root/'SCORES.json').read_bytes());published={(r['target'],r['procedure_id'].rsplit(':',1)[1]):r for r in scores}
    def loss_sum(year,k,weeks):
        mm=[metrics[year,k,w]for w in weeks]
        total=math.fsum(math.fsum(m['squares']if k[0]=='anytime_td'else m['errors'])for m in mm)
        return total,sum(len(m['errors'])for m in mm)
    def choose(keys,origins):
        values={}
        for k in keys:
            sums=[loss_sum(year,k,weeks)for year,weeks in origins];values[k]=math.fsum(s for s,n in sums)/sum(n for s,n in sums)
        best=min(values.values());return min(k for k,v in values.items()if abs(v-best)<=1e-12)
    for target,keys in bytarget.items():
        base=[k for k in keys if':ordered_leaf_cdf'in k[1]and k[2]==('event_probability'if target=='anytime_td'else'lower_median')]
        assert len(base)==1;base=base[0]
        prior=choose(keys,[(2025,range(1,19))])
        for policy in p['policies']:
            cumulative=[];point_fallback=0;forecast=0;prec=defaultdict(int)
            for w in range(1,8):
                origin=min(byweek[2026,w]);eligible=[u for u in range(1,w)if max(byweek[2026,u])+604800<origin]
                if policy=='FROZEN_2025_BEST':chosen=prior
                elif policy=='EARLIER_AVAILABLE_2026_SCORE_MEMORY':chosen=choose(keys,[(2026,eligible)])if eligible else base
                else:chosen=choose(keys,[(2025,range(1,19)),(2026,eligible)])
                decision=observed[target,policy,w]
                assert(decision['chosen_procedure_id'],decision['chosen_product_id'])==chosen[1:]
                assert decision['current_score_weeks_available']==eligible and decision['fit_origin_unix']==origin
                assert decision['startup_fallback']==(policy=='EARLIER_AVAILABLE_2026_SCORE_MEMORY'and not eligible)
                sums=loss_sum(2026,chosen,[w]);close(decision['native_loss'],sums[0]/sums[1],'chosen weekly loss');assert decision['n']==sums[1]
                cumulative.append(sums);mm=metrics[2026,chosen,w];point_fallback+=mm['fallback'];forecast+=len(masks[2026,chosen,w][0])
                for name,value in mm['prec'].items():prec[name]+=value
            out=published[target,policy];n=sum(v[1]for v in cumulative);close(out['brier'if target=='anytime_td'else'mae'],math.fsum(v[0]for v in cumulative)/n,'policy loss')
            assert out['n']==n and out['forecast_rows']==forecast and out['fallback_rows']==point_fallback
            for name,counts in out['precision_counts'].items():assert counts['numerator']==prec[name]and counts['denominator']==n
    assert len(decisions)==252 and len(scores)==36
    report=dict(state='PASS_INDEPENDENT_RAW_VALUES_LOSSES_AND_EARLIER_ONLY_SELECTOR',checked_at_utc=datetime.now(timezone.utc).isoformat(),protocol_sha256=receipt['protocol_sha256'],score_sha256=receipt['score_sha256'],raw_rows_scanned=scanned,selected_recipe_query_rows=selected,exact_mask_and_label_checks=len(maskrows),candidate_output_recipes=len(roster),policy_decisions=len(decisions),policy_score_views=len(scores),new_fits=0,new_inference=0,new_forecasts=0,new_NFL_observations=0,current2026_Week8_outcomes_read=0,limits=['Exposed retrospective roster/selection rules, never authenticated original routing or untouched holdout.','Current-score-memory chooses among historically trained H-MULTI models, with historical Leaf startup fallback; not strict current information.','Seven-day source availability is the inherited reconstruction assumption, not authenticated historical publication.','Point-choice policy results establish neither offered-line probability nor Over/Under/price performance.'],resources=dict(wall_seconds=time.monotonic()-start,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024))
    with a.output.open('x')as f:json.dump(report,f,indent=2);f.write('\n')
    print(json.dumps(report))


if __name__=='__main__':main()
