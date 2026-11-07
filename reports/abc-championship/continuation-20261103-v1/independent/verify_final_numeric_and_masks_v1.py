"""Independent arithmetic on retained points and public-opportunity masks.

Does not import/invoke the existing scorer or modify registries.
"""
import argparse,collections,gzip,hashlib,json,math
from datetime import datetime,timezone
from pathlib import Path


def read(p):return json.loads(gzip.decompress(p.read_bytes()) if p.suffix=='.gz' else p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def close(a,b):return a==b or (a is not None and b is not None and abs(a-b)<max(1e-10,1e-12*abs(b)))
def quantile(values,p):
    a=sorted(values);index=(len(a)-1)*p;low=math.floor(index);fraction=index-low
    return a[low]+fraction*(a[min(low+1,len(a)-1)]-a[low])


def run(private,croot,package_root,receipt):
    combined=collections.defaultdict(list);stored={}
    for suffix,folder in [('MATCHED_ROWS_V2','continuation-20261103-v2'),('ADDITIONAL_ROWS_V3','continuation-20261103-v3'),('GLM_LAW_ROWS_V4','continuation-20261103-v4')]:
        f=private/('B_OWNER_LOCAL_C_'+suffix+'.json.gz');m=read(package_root/folder/'PRIVATE_DERIVATIVE_MANIFEST.json');assert sha(f)==m['sha256'];rows=read(f)['rows'];stored[folder]=rows
        if suffix!='GLM_LAW_ROWS_V4':
            for r in rows:combined[r['method_key'],r['target']].append(r)
    scores=read(package_root/'continuation-20261103-v4/numerical-offer-panel-v1/SCORES.json');assert len(scores)==636
    equality_unique=set();equality_views=0;tolerance_checks=0
    for s in scores:
        rr=[r for r in combined[s['procedure_id'],s['target']] if s['week']=='ALL' or r['week']==s['week']]
        valid=[r for r in rr if r['prediction'] is not None and r['actual'] is not None and r['participation']=='VERIFIED_PLAYED_POSITIVE_PHYSICAL'];n=len(valid);errors=[r['prediction']-r['actual'] for r in valid];a=list(map(abs,errors))
        assert s['forecast_rows']==len(rr) and s['n']==s['supported_rows']==n and s['missing_actual_or_output']==len(rr)-n
        assert s['unique_games']==len({r['game_id'] for r in valid}) and s['unique_player_games']==len({(r['game_id'],r['player_id']) for r in valid})
        assert s['fallback_rows']==sum(r['fallback'] not in ('none',None) for r in rr)
        got=dict(mae=math.fsum(a)/n,mse=math.fsum(e*e for e in errors)/n,bias=math.fsum(errors)/n,p90_abs=quantile(a,.9),p95_abs=quantile(a,.95),max_abs=max(a));got['rmse']=math.sqrt(got['mse'])
        for k,value in got.items():assert close(value,s[k]),(k,value,s[k])
        prec={'exact_rate':sum(v==0 for v in a)}
        for tol in (1,5,10):
            prec['abs_lt_'+str(tol)]=sum(v<tol for v in a);prec['abs_le_'+str(tol)]=sum(v<=tol for v in a)
        for k,numerator in prec.items():
            assert s['precision_counts'][k]==dict(numerator=numerator,denominator=n)
            assert close(s[k],numerator/n);tolerance_checks+=1
        eq=[r for r in valid if r['prediction']==r['line']]
        for r in eq:
            assert r['statistical_state']=='ABSTAIN' and r['selected_side'] is None
            equality_unique.add((r['method_key'],r['target'],r['offer_id']))
        equality_views+=len(eq)
    # Source C corrections, unique primary opportunity board, independent of B masks.
    versions={}
    for d in read(croot/'reports/abc-championship/C_INPUT_BINDINGS.json')['datasets']:
        p=croot/d['path'];assert sha(p)==d['SHA256']
        for r in read(p)['rows']:versions[r['record_id']]=r
    first={};fields=('category','game_id','player_id','method_id','method_version','selector_id','policy_id','venue','product','line_tier','evidence_tier')
    for r in versions.values():
        key=tuple(r[k] for k in fields);order=(r['decision_UTC'],r['scoring_snapshot_id'])
        if key not in first or order<first[key][0]:first[key]=(order,r)
    c=[r for _,r in first.values() if r['venue']=='pinnacle' and r['season']==2026 and r['week']<=8];byoffer=collections.defaultdict(dict)
    for r in c:byoffer[r['offer_id']][r['method_id']]=r
    masks=read(package_root/'continuation-20261103-v4/OWNER_LOCAL_MASK_MEMBERSHIP.json.gz');assert len(masks)==684
    allowed={'procedure_id','target','week_view','eligible','common_decided_offer_ids','common_decided_sha256','actual_weeks','source','scope'};maskindex={}
    for m in masks:
        assert set(m)==allowed
        ids=m['common_decided_offer_ids'];assert len(ids)==len(set(ids)) and ids==sorted(ids)
        assert hashlib.sha256(json.dumps(ids,separators=(',',':')).encode()).hexdigest()==m['common_decided_sha256']
        assert set(ids)<=set(byoffer)
        key=m['procedure_id'],m['target'],m['week_view'];assert key not in maskindex;maskindex[key]=m
        matches=[r for rows in stored.values() for r in rows if r['method_key']==m['procedure_id'] and r['target']==m['target'] and (m['week_view']=='ALL' or r['week']==int(m['week_view']))]
        assert m['eligible']==len(matches)
        assert ids==sorted(r['offer_id'] for r in matches if r['statistical_state'] in ('WIN','LOSS'))
        for oid in ids:
            q=byoffer[oid]['ALWAYS_OVER'];assert q['category']==m['target'] and (m['week_view']=='ALL' or q['week']==int(m['week_view']))
    checked_pairs=0
    for folder in stored:
        for p in read(package_root/folder/'PAIRED_CONTROLS.json'):
            m=maskindex[p['procedure_id'],p['target'],p['week_view']]
            controls=[byoffer[oid][p['control_id']] for oid in m['common_decided_offer_ids'] if p['control_id'] in byoffer[oid] and byoffer[oid][p['control_id']]['status'] in ('WIN','LOSS')]
            assert len(controls)==p['common_decided'] and sum(r['status']=='WIN' for r in controls)==p['control_wins'];checked_pairs+=1
    result=dict(state='PASS',at_utc=datetime.now(timezone.utc).isoformat(),numeric=dict(views_verified=len(scores),source_method_category_cells=len(combined),precision_numerator_denominator_checks=tolerance_checks,unique_numeric_equality_abstention_method_offer_rows=len(equality_unique),equality_row_appearances_across_overlapping_week_and_cumulative_views=equality_views,source_scores_sha256=sha(package_root/'continuation-20261103-v4/numerical-offer-panel-v1/SCORES.json'),scope='Full available numeric rows include equality-abstention cases; no new forecast or NFL observation.'),masks=dict(cells_verified=len(masks),paired_control_totals_recomputed=checked_pairs,unique_public_C_offers=len(byoffer),mask_file_sha256=sha(package_root/'continuation-20261103-v4/OWNER_LOCAL_MASK_MEMBERSHIP.json.gz'),allowed_fields=sorted(allowed),contains_B_private_numeric_values=False,scope='Public C offer IDs and declared metadata/counts only; no B point, actual, probability, player-level source or private locator fields.'),limits=['Read-only independent arithmetic; did not import scorers or change registries.','Source rights/privacy legal scope is not created by this structural audit.','Current/revised football source and timing-unverified quote limitations remain.'])
    receipt.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('private',type=Path);p.add_argument('croot',type=Path);p.add_argument('package_root',type=Path);p.add_argument('receipt',type=Path);a=p.parse_args();run(a.private,a.croot,a.package_root,a.receipt)
