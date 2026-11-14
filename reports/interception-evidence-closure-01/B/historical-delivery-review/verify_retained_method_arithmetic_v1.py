"""Independent aggregate arithmetic on retained public A receipts; no NFL regrade.

Usage: python verify_retained_method_arithmetic_v1.py --source-cache CACHE --out OUT
Private model, offer, selected membership and original source clocks are not loaded.
"""
import argparse
import csv
import gzip
import hashlib
import json
from decimal import Decimal
from pathlib import Path


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source-cache',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    base=a.source_cache/'reports/abc-championship/category-decision-release-01'
    checks=[]
    def ok(label,value):
        assert value,label
        checks.append(label)
    rows=[]
    for part in [1,2]:
        rows+=list(csv.DictReader((base/f'A_EVIDENCE_EXISTING_FULL_POLICY_ANNUAL_00{part}.csv').open()))
    chosen=[r for r in rows if (r['category']=='pass_cmp'and r['method']in('CATBOOST_MEDIUM','HGB_MAE_DIRECT'))or(r['category']=='rush_att'and r['method']=='BACKFIELD_CDF'and r['output']=='mean')]
    for r in chosen:
        for side in ['over','under','combined']:
            w,l,n=[int(r[side+'_'+v])for v in ['wins','losses','decided']]
            ok(r['method']+side+'denominator',w+l==n)
        for key in ['wins','losses','decided']:
            ok(r['method']+'weighted_'+key,int(r['over_'+key])+int(r['under_'+key])==int(r['combined_'+key]))
        n=int(r['combined_decided'])
        ok(r['method']+'combined_rate',abs(Decimal(r['combined_rate'])-Decimal(r['combined_wins'])/n)<Decimal('1e-12'))
        ok(r['method']+'actual_weeks',r['actual_weeks']=='1,2,3,4,5')
    by={r['method']:r for r in chosen}
    ok('CatBoost_record',(int(by['CATBOOST_MEDIUM']['combined_wins']),int(by['CATBOOST_MEDIUM']['combined_decided']))==(52,88))
    ok('HGB_record',(int(by['HGB_MAE_DIRECT']['combined_wins']),int(by['HGB_MAE_DIRECT']['combined_decided']))==(52,88))
    ok('samecase_constant_over_48',by['CATBOOST_MEDIUM']['always_over_own_decided']==by['HGB_MAE_DIRECT']['always_over_own_decided']=='48')
    contribution=json.loads((base/'A_CATEGORY_PRODUCT_CONTRIBUTION_V1.json').read_text())
    cmp=next(r for r in contribution['rows']if r['category']=='pass_cmp')
    pair=cmp['registered_learned_pairs'][0]
    ok('Cat_HGB_pair_n',pair['common_decided']==88)
    ok('Cat_HGB_pair_win_delta',pair['left_wins']-pair['right_wins']==0)
    ok('Cat_HGB_pair_same_mask',pair['decided_mask_sha256']==pair['numerical_mask_sha256'])
    ok('Cat_HGB_disagreements',pair['side_disagreements']==8)
    source=next((a.source_cache/'reports/abc-championship/post-wave-5w-v1').glob('*rush_att*'))
    obj=json.loads(gzip.decompress(source.read_bytes()))
    top=next(r for r in obj['records']if r['key_sha256']=='03987dde683658f5cabc4f4a0407b459e42e8f3861730ea3612e40bba53fc4f2')
    weekly=top['weekly_support'];aggregate=[]
    for name,ww in [('ANNUAL_W1_5',[r for r in weekly if r['week']<=5]),('SEPARATE_W6_7_DIAGNOSTIC',[r for r in weekly if r['week']>=6]),('MIXED_W1_7',weekly)]:
        sums={s:{k:sum(r[s][k]for r in ww)for k in ['wins','losses','decided','unresolved','DNP','push']}for s in ['over','under']}
        for side in ['over','under']:ok(name+side+'N',sums[side]['wins']+sums[side]['losses']==sums[side]['decided'])
        total={k:sum(sums[s][k]for s in ['over','under'])for k in sums['over']}
        aggregate.append(dict(period=name,own_sides=sums,combined=total,rate=total['wins']/total['decided'],weeks=[r['week']for r in ww]))
    ok('annual_top6_23of30',aggregate[0]['combined']['wins']==23 and aggregate[0]['combined']['decided']==30)
    ok('mixed_top6_29of42',aggregate[2]['combined']['wins']==29 and aggregate[2]['combined']['decided']==42)
    ok('W6_W7_each_adverse3of6',all(sum(r[s]['wins']for s in ['over','under'])==3 and r['scored']==6 for r in weekly if r['week']>=6))
    reconciliation=json.loads((base/'LAW_DIRECTION_RECONCILIATION_V1.json').read_text())
    reported=next(z for z in reconciliation['selective_raw_maxima']if z['category']=='rush_att'and z['policy']=='P2_EXACT_LINE::TOP_6_PER_CATEGORY_WEEK')['own_population_raw_maxima'][0]
    ok('annual_reconciliation_exactkey',reported['key']==top['key_sha256'])
    ok('annual_selectedcoverage',reported['selected']==30 and reported['fullE']==266 and abs(reported['coverage']-30/266)<1e-12)
    result=dict(state='PASS_PUBLIC_AGGREGATE_AND_DECLARED_POLICY_REVIEW',checks=len(checks),check_names=checks,
        retained_CMP_records=[r for r in chosen if r['category']=='pass_cmp'],Top6_exact_key=top['key'],Top6_periods=aggregate,
        newly_added_NFL_weeks=0,new_fits=0,new_model_inference=0,new_NFL_grades=0,
        not_verified=['private selected player-game membership','same-selected30 strong-control rows','raw training features/labels or actual fitted model parity','original quote/vintage clocks','new 2026W8-W9 or2022-2025 exact procedure expansion'],
        Top6_schedule_limit='Inspected source sorts full week by confidence then head6; no chronological decision-batch simulator. Conditional retrospective week ranking, not proof of an executable advance weekly list.',
        fallback='Apply existing A_WEEKLY_COVERAGE_MATRIX_V1 clarification: blank A79 markers UNSPECIFIED, CSVzero alone is not verified nofallback.',
        publication_members=[{'path':r['path'],'ref':r['ref'],'bytes':r['bytes'],'sha256':r['sha256']}for r in json.loads((a.source_cache/'FETCHES.json').read_text())])
    a.out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'state':result['state'],'checks':len(checks),'new_NFL_weeks':0}))


if __name__=='__main__':main()
