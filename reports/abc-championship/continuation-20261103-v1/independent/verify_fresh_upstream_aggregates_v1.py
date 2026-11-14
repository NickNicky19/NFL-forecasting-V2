"""Read-only aggregate arithmetic audit; does not assert access to private A rows."""
import argparse,collections,gzip,hashlib,json,math
from pathlib import Path
import numpy as np


def read(p):return json.loads(gzip.decompress(p.read_bytes())if p.suffix=='.gz'else p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def count(v):return 0 if v is None else v

def check(r):
    for side in ('OVER','UNDER','COMBINED'):
        s=r[side];assert count(s['wins'])+count(s['losses'])==s['decided']<=s['selected']
        assert s['rate']==(s['wins']/s['decided'] if s['decided'] else None)
    for k in ('selected','wins','losses','decided'):assert count(r['COMBINED'][k])==count(r['OVER'][k])+count(r['UNDER'][k])
    assert r['COMBINED']['selected']+r['abstentions']+r['unavailable']==r['eligible']
    assert sum(r['states'].values())==r['eligible']
    assert r['states'].get('WIN',0)==count(r['COMBINED']['wins']) and r['states'].get('LOSS',0)==count(r['COMBINED']['losses'])
    assert r['coverage']==r['COMBINED']['selected']/r['eligible'] if r['eligible'] else r['coverage'] is None


def c_rows(croot):
    versions={}
    for d in read(croot/'reports/abc-championship/C_INPUT_BINDINGS.json')['datasets']:
        for r in read(croot/d['path'])['rows']:versions[r['record_id']]=r
    first={};fields=('category','game_id','player_id','method_id','method_version','selector_id','policy_id','venue','product','line_tier','evidence_tier')
    for r in versions.values():
        key=tuple(r[k]for k in fields);clock=(r['decision_UTC'],r['scoring_snapshot_id'])
        if key not in first or clock<first[key][0]:first[key]=(clock,r)
    return [r for _,r in first.values() if r['venue']=='pinnacle' and r['season']==2026 and r['week']<=8]


def run(source,root_refresh,croot,bmask,out):
    hfile=source/'A_HISTORICAL_COMMON_SCORER_V1.json';acfile=source/'A_ON_C_BOUND_OFFERS_UNCERTAINTY_APPEND_V1.json'
    assert sha(hfile)=='db0b7fe7f3700fa76954b85e7405a2f22f95dec73372b79eb81444e69dc4c2f3'
    assert sha(acfile)=='a0ec4b742fd293ab336f50aa2e3fc5160cf0fb1364934cb38daf368f0b5d10ae'
    hist=read(hfile);a=read(acfile);assert len(hist['scores'])==1092 and len(a['scores'])==87
    assert hist['protocol_id']==a['C_protocol_id']=='ABC-ACTUAL-PROP-CHAMPIONSHIP-v2-C-1'
    assert hist['scorer_SHA256']=='2ba450f91bb5fac869ce3adde031099390ec70408a91204653869032b49b2bce'
    for r in hist['scores']+a['scores']:check(r)
    # Public weekly counts reproduce all cumulative numerators/denominators.
    weekly={};cumulative=[]
    for r in hist['scores']:
        if r['period_id'].startswith('WEEKLY_'):weekly[r['period_id'],r['category'],r['procedure_id'],int(r['week_view'])]=r
        else:cumulative.append(r)
    period_map={'E1_PARTIAL_2026_W1_5':('WEEKLY_2026',range(1,6)),'E3_2024_W1_8':('WEEKLY_2024',range(1,9)),'E4_2024_FULL_REG':('WEEKLY_2024',range(1,19))}
    boot_match=0;boot_unverified=0;leaders=[]
    for r in cumulative:
        period,weeks=period_map[r['period_id']];ww=[weekly[period,r['category'],r['procedure_id'],w] for w in weeks]
        assert r['actual_weeks']==list(weeks)==r['weeks']
        for side in ('OVER','UNDER','COMBINED'):
            for k in ('selected','wins','losses','decided'):assert count(r[side][k])==sum(count(x[side][k]) for x in ww)
        for k in ('eligible','abstentions','unavailable'):assert r[k]==sum(x[k] for x in ww)
        states=collections.Counter()
        for x in ww:states.update(x['states'])
        assert dict(states)==r['states']
        blocks=[(count(x['COMBINED']['wins']),count(x['COMBINED']['losses']))for x in ww if x['COMBINED']['decided']]
        if len(blocks)>=5:
            assert r['uncertainty']['kind']=='WEEK_BLOCK_BOOTSTRAP95_2000_DRAWS'
            arr=np.asarray(blocks);idx=np.random.default_rng(661107).integers(len(arr),size=(2000,len(arr)));sampled=arr[idx].sum(axis=1);lo,hi=np.quantile(sampled[:,0]/sampled.sum(axis=1),[.025,.975])
            if abs(float(lo)-r['uncertainty']['low'])<1e-12 and abs(float(hi)-r['uncertainty']['high'])<1e-12:boot_match+=1
            else:boot_unverified+=1
    for period in period_map:
        for category in ('pass_att','rec','rush_att'):
            rr=[r for r in cumulative if r['period_id']==period and r['category']==category and r['COMBINED']['decided']];best=max(r['COMBINED']['rate'] for r in rr)
            for r in rr:
                if r['COMBINED']['rate']==best:
                    leaders.append(dict(period_id=period,category=category,procedure_id=r['procedure_id'],OVER=r['OVER'],UNDER=r['UNDER'],COMBINED=r['COMBINED'],eligible=r['eligible'],coverage=r['coverage'],eligible_board_games=r['games'],actual_weeks=r['actual_weeks'],scope='Reported owner-local source-specific panel; raw own-pool maximum, not all-method matched champion.'))
    # A-on-C weekly counts and named C controls: raw A joins remain unshared.
    afull=[r for r in a['scores']if r['week_view']=='ALL'];aweekly={(r['category'],r['procedure_id'],int(r['week_view'])):r for r in a['scores']if r['week_view']!='ALL'}
    for r in afull:
        for side in ('OVER','UNDER','COMBINED'):
            for k in ('selected','wins','losses','decided'):assert count(r[side][k])==sum(count(aweekly[r['category'],r['procedure_id'],w][side][k]) for w in (2,3))
    cr=c_rows(croot);control_checks=0
    for pair in a['paired']:
        method=pair['control'].split('::')[-1];rr=[r for r in cr if r['category']==pair['category'] and r['method_id']==method and r['status'] in ('WIN','LOSS') and (r['category']!='rush_yd' or r['position']=='RB')]
        assert len(rr)==pair['common_decided']
        assert sum(r['status']=='WIN'for r in rr)==pair['control_wins']
        assert pair['A_wins']-pair['control_wins']==pair['win_change']
        assert abs(pair['win_change'])<=pair['side_disagreements']<=pair['common_decided']
        assert (pair['side_disagreements']-pair['win_change'])%2==0
        own=next(r for r in afull if r['category']==pair['category']and r['procedure_id']==pair['procedure_id'])['COMBINED']
        assert pair['A_wins']<=own['wins']<=pair['A_wins']+(own['decided']-pair['common_decided'])
        control_checks+=1
    state_issues=[dict(category=r['category'],procedure_id=r['procedure_id'],week_view=r['week_view'],selected=r['COMBINED']['selected'],decided=r['COMBINED']['decided'],unavailable_field=r['unavailable'],unavailable_state_count=r['states'].get('UNAVAILABLE_FORECAST',0))for r in a['scores']if r['states'].get('UNAVAILABLE_FORECAST',0)!=r['unavailable']]
    hashes={p['mask_sha256']for p in a['paired']};bfile_hash=sha(bmask)
    # C public admission scope and B original control have independently verified numbers.
    pointer=read(source/'C_CURRENT_PROTOCOL.json');ledger=read(source/'C_ADMISSION_LEDGER.json');cb=read(source/'C_B_ORIGINAL_SELECTED_POOL_CONTROL.json')
    assert pointer['protocol']['SHA256']=='fa19581487519a854948269bc1ce328cbbcdc734afee2464f1ff778d1ff241a1'
    assert pointer['scorer']['SHA256']==hist['scorer_SHA256']
    assert ledger['A']['state']==ledger['B']['state']=='RECEIVED_VALIDATED_LIMITED_ADMISSION'
    assert ledger['B']['index_ref']=='7c0690bfb564db5481cc27a00a45e7f4311b1f70'
    assert cb['original_wins']==205 and cb['always_Under_wins']==128+96==224 and cb['decided']==415
    assert cb['original_selected']==cb['decided']+cb['unknown']==427
    assert cb['always_Under_wins']+cb['always_Under_losses']==cb['original_wins']+cb['original_losses']==415
    assert cb['original_rate']==205/415 and cb['always_Under_rate']==224/415 and cb['paired_win_difference']==19 and abs(cb['percentage_point_difference']-1900/415)<1e-12
    remedy=read(root_refresh/'A-STORAGE_REMEDY_RECEIPT_V1.json');assert remedy['old_actual_bytes']-remedy['old_reserve_bytes']==remedy['old_excess_bytes']==402
    assert remedy['old_actual_bytes']-remedy['actual_bytes_saved']==remedy['new_actual_bytes']==4194295
    assert remedy['old_reserve_bytes']-remedy['new_actual_bytes']==remedy['headroom_bytes']==9
    assert remedy['before_index_bytes']-remedy['after_index_bytes']==remedy['actual_bytes_saved']==411
    result=dict(state='PASS_AGGREGATE_ARITHMETIC_WITH_EXPLICIT_SOURCE_STATE_AND_MASK_LIMITS',source_A_commit='88dac5da1b261ae6f521d3f23c83b2f95fc364bd',source_C_commit='39b98567cc11835363e91c6a2b504bf9cae1f17a',historical=dict(source_sha256=sha(hfile),score_views_checked=1092,side_views_checked=3276,cumulative_weekly_reconciliations=len(cumulative),chronological_week_block_bootstraps_exactly_reproduced=boot_match,bootstrap_order_not_reproduced=boot_unverified,periods=list(period_map),missing_actual_line_seasons=[2022,2023,2025],categories=['pass_att','rec','rush_att'],leaders=leaders,source_panel='A own representative-book68/69/79, not C Pinnacle; current-vintage timing-unverified; retainedFmodel-year2024 trainedthrough2023; not new fits or original-pick recovery.'),A_on_C=dict(source_sha256=sha(acfile),score_views_checked=87,side_views_checked=261,weekly_triads_reconciled=len(afull),reported_pairs_checked=203,C_control_counts_reproduced_from_public_rows=control_checks,A_paired_outcomes_reproduced_from_private_rows=False,temporal_parity='NOT_VERIFIED',rushing_population='RB_ONLY;notB_QB_RB',state_classification_issue_views=len(state_issues),state_classification_issue='Selected A rows with unresolved C labels carry UNAVAILABLE_FORECAST states although unavailable field is0 or smaller. Decided W/L arithmetic is unaffected; A must qualify/correct state mapping in new version.',examples=state_issues[:4],mask_hash_limit=dict(distinct_reported_hashes=len(hashes),contains_whole_B_mask_file_hash=bfile_hash in hashes,individual_A_memberships_transferred=False,claim='Hashes in aggregate append do not independently restore A per-offer predictions or prove identical source/decision clocks.')),C_admission=dict(A='LIMITED_PUBLIC_AGGREGATES_AT_2be1',B='LIMITED_PUBLIC_AGGREGATES_AT_7c0690bf',new_B_v2_v4_admitted=False,raw_common_parity=False,original_selected_pool=dict(original=205,always_under=224,decided=415,unknown=12,win_change=19)),A_remedy=dict(arithmetic_verified=True,actual_bytes_reported=4194295,unchanged_cap=4194304,headroom=9,owner_private_storage_census_independently_performed=False),limits=['No access to or restoration of private A models/rows; source identity/chronology, paired A win intervals remain reported rather than independently row-reproduced.','Source-specific seasons, own-pool raw maxima, technical availability and temporal contracts remain separate; no three-way championship winner or release claim.','B/C public arithmetic admission does not waive artifact recovery or grant raw-row transfer rights.'])
    out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items()if k not in ('historical','A_on_C')},indent=2));print('HISTORICAL',len(cumulative),boot_match,boot_unverified);print('A_C_PAIRS',control_checks,'STATE_ISSUES',len(state_issues))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('root_refresh',type=Path);p.add_argument('croot',type=Path);p.add_argument('bmask',type=Path);p.add_argument('out',type=Path);a=p.parse_args();run(a.source,a.root_refresh,a.croot,a.bmask,a.out)
