"""Independently check retained event masses and direction; does not infer a law."""
import argparse, collections, gzip, hashlib, json
from decimal import Decimal
from pathlib import Path


def read(p):return json.loads(gzip.decompress(p.read_bytes()) if p.suffix=='.gz' else p.read_bytes())


def run(root,output):
    binding=read(root/'reports/abc-championship/C_INPUT_BINDINGS.json')
    rows={}
    for d in binding['datasets']:
        p=root/d['path'];assert hashlib.sha256(p.read_bytes()).hexdigest()==d['SHA256']
        for r in read(p)['rows']:rows[r['record_id']]=r
    prob=[];direction=0;half=0;monotone_pairs=0;groups=collections.defaultdict(list)
    for r in rows.values():
        if r.get('p_over') is None:continue
        ps=[r['p_under'],r['p_push'],r['p_over']]
        assert all(0<=p<=1 for p in ps) and abs(sum(ps)-1)<1e-10
        expected='ABSTAIN' if abs(ps[2]-ps[0])<=1e-12 else 'OVER' if ps[2]>ps[0] else 'UNDER'
        assert r['selected_side']==expected
        assert r['probability_line']==r['line'];direction+=1
        if Decimal(str(r['line']))%1==Decimal('.5'):
            assert abs(ps[1])<1e-12;half+=1
        key=tuple(r.get(k) for k in ('game_id','player_id','category','method_id','method_version','information_set_id'))
        groups[key].append(r);prob.append(r)
    for rs in groups.values():
        rs=sorted(rs,key=lambda r:Decimal(str(r['line'])))
        for a,b in zip(rs,rs[1:]):
            assert a['p_over']+1e-10>=b['p_over'] and a['p_under']<=b['p_under']+1e-10
            monotone_pairs+=1
    byoffer=collections.defaultdict(dict)
    for r in rows.values():byoffer[(r['offer_id'],r['venue'])][r['method_id']]=r
    count_consistency=0
    for pair in byoffer.values():
        a,b=pair.get('P1_MEDIAN'),pair.get('P2_LAW')
        if not(a and b and a['category']=='rec' and a['selected_side'] in ('OVER','UNDER') and b['selected_side'] in ('OVER','UNDER')):continue
        if Decimal(str(a['line']))%1!=Decimal('.5'):continue
        assert a['selected_side']==b['selected_side'];count_consistency+=1
    result=dict(state='PASS',probability_rows=len(prob),complement_checks=len(prob),direction_checks=direction,half_point_zero_push_checks=half,monotonic_adjacent_pairs=monotone_pairs,half_integer_reception_median_law_direction_checks=count_consistency,limits=['Checks retained probabilities, not new law reconstruction or calibration-fit chronology.','One threshold alone cannot authenticate a full CDF.','Source timing remains unverified; no price/EV or live-release claim.'])
    output.write_text(json.dumps(result,indent=2)+'\n');print(result)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('output',type=Path);a=p.parse_args();run(a.root,a.output)
