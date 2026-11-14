"""Independent arithmetic on frozen empirical/geometric count laws.

No author grader or inference function is imported. FTN-dependent derivatives:
CC-BY-SA-4.0, FTN Data via nflverse.
"""
import gzip
import hashlib
import json
import math
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'reports/wave-closure-next-comparison-20261114/B'
OLD=ROOT/'reports/information-first-20261112-01/B/current-conditional-shadow-v1'


def read(path):
    body=path.read_bytes()
    return json.loads(gzip.decompress(body) if path.suffix=='.gz' else body)


def main():
    original=OLD/'FORECAST_ONLY_PACKET.json.gz'
    h=hashlib.sha256(original.read_bytes()).hexdigest()
    assert h=='f9889584338bf7b85f5de3889fbc78f73fee97e2052faea7cc91a28fb203c7bb'
    capsule=read(OLD/'COMPLETE_LAW_CAPSULE_V1.json.gz')
    labels={r['player_id']:r for r in read(BASE/'forward-grading/DERIVED_LABELS_V1.json')['rows']}
    graded={(r['method'],r['player_id']):r for r in read(BASE/'forward-grading/GRADED_FORECASTS_V1.json')['rows']}
    aggregates={};max_error=0.;checks=0
    for row in capsule['forecasts']:
        arm,pid=row['method'],row['player_id'];label=labels[pid];saved=graded[arm,pid]
        assert saved['mean']==row['mean'] and saved['lower_median']==row['lower_median']
        assert saved['actual_offer'] is None and saved['selected_side'] is None
        checks+=4
        if row['output_state']!='CONDITIONAL_FORECAST':
            assert not saved['graded'] and saved['actual'] is None and label['appearance'] is None
            continue
        if label['appearance'] is not True:
            assert not saved['graded'] and saved['actual'] is None and label['appearance'] is False
            continue
        y=label['actual_completions'];assert saved['actual']==y and saved['graded']
        law=row['law'];q=law['prior']['q'];b=law['mixture']
        support,weights=law['support'],law['weights']
        assert law['prior']['kind']=='geometric' and abs(sum(weights)-1.)<1e-12
        assert all(w>=0 for w in weights) and all(v>=0 and int(v)==v for v in support)
        def cdf(k):
            return (1-b)*sum(w for v,w in zip(support,weights)if v<=k)+b*(1-q**(k+1)) if k>=0 else 0.
        mean=(1-b)*sum(v*w for v,w in zip(support,weights))+b*q/(1-q)
        median=next(k for k in range(2048)if cdf(k)>=.5)
        mass=(1-b)*sum(w for v,w in zip(support,weights)if v==y)+b*(1-q)*q**y
        nll=-math.log(mass)
        last=max(int(max(support)),y)+100
        crps=sum((cdf(k)-float(y<=k))**2 for k in range(last+1))
        # Beyond last the empirical CDF and indicator are one; integrate the
        # remaining geometric squared tail exactly rather than truncate it.
        crps+=b*b*q**(2*(last+2))/(1-q*q)
        for actual,expected in [(mean,row['mean']),(median,row['lower_median']),
                                (nll,saved['law_score']['NLL']),(crps,saved['law_score']['CRPS'])]:
            error=abs(actual-expected);max_error=max(max_error,error);assert error<1e-10
            checks+=1
        aggregates.setdefault(arm,[]).append(dict(y=y,mean=mean,lower_median=median,NLL=nll,CRPS=crps))
    for score in read(BASE/'forward-grading/SCORES.json'):
        arm=score['procedure_id'].split(':')[-1];rows=aggregates[arm];product=score['product_id']
        assert len(rows)==score['n']==3 and score['forecast_rows']==4 and score['outer_query_rows']==5
        errors=[r[product]-r['y']for r in rows]
        measured=dict(mae=sum(abs(e)for e in errors)/3,mse=sum(e*e for e in errors)/3,
                      bias=sum(errors)/3,NLL=sum(r['NLL']for r in rows)/3,CRPS=sum(r['CRPS']for r in rows)/3)
        for key,value in measured.items():
            error=abs(value-score[key]);max_error=max(max_error,error);assert error<1e-10;checks+=1
        assert score['DNP_rows']==1 and score['IR_unavailable_rows']==1 and score['O_U_results'] is None
    out=dict(id='B_FROZEN_FORWARD_GRADE_INDEPENDENT_ARITHMETIC_v1',actual_UTC=datetime.now(timezone.utc).isoformat(),
        state='PASS',checks=checks,maximum_numeric_difference=max_error,tolerance=1e-10,
        independent_method='Manual empirical/geometric PMF/CDF/mean/median and squaredCDF countCRPS with exact geometric tail; no authorgrader/inference imports',
        original_packet_sha256=h,original_bytes_preserved=True,unique_appearing_QB_games=3,game_clusters=1,
        scored_arm_rows=6,DNP_arm_rows=2,IR_unavailable_slots=2,O_U_picks=0,new_fits=0,new_forecasts=0,
        limits='Checks arithmetic against qualified suppliedlabelcontracts; rawsource/finality qualification separatelyboundbyforward-grading owner. No independent pregame source-clock/authentic historical-vintage or websiteconsumptionclaim.',
        code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    dest=BASE/'INDEPENDENT_FORWARD_ARITHMETIC_V1.json'
    if dest.exists():raise FileExistsError(dest)
    dest.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))


if __name__=='__main__':main()
