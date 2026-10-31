"""Independently check saved-row joins, clocks and law-parameter admission."""
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import csv
import gzip
import hashlib
import importlib.util
import json
import math
from pathlib import Path
from zoneinfo import ZoneInfo


spec=importlib.util.spec_from_file_location('independent_row_reader',Path(__file__).resolve().parents[2]/'championship-20261030f/independent/check_numerical_pairs.py')
ind=importlib.util.module_from_spec(spec);spec.loader.exec_module(ind)
sha,canon=ind.sha,ind.canonical
def read(p):return json.loads(p.read_bytes())
def epoch(x):
    if x in('',None):return None
    try:return float(x)
    except(ValueError,TypeError):return datetime.fromisoformat(x.replace('Z','+00:00')).timestamp()


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo-root',type=Path,required=True);ap.add_argument('--private-root',type=Path,required=True);ap.add_argument('--source-root',type=Path,required=True);ap.add_argument('--public-root',type=Path,required=True);ap.add_argument('--mask',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
    p=read(a.public_root/'FROZEN_PROTOCOL.json');receipt=read(a.public_root/'RUN_RECEIPT.json');assert sha(a.public_root/'FROZEN_PROTOCOL.json')==receipt['protocol_sha256'];assert sha(a.mask)==receipt['mask_sha256']
    mask=json.loads(gzip.decompress(a.mask.read_bytes()))['rows'];assert len(mask)==receipt['matched_recipe_offer_rows']==24224
    assert sha(a.source_root/'games.csv')==p['schedule_sha256'];games={}
    with(a.source_root/'games.csv').open()as f:
        for r in csv.DictReader(f):
            if r['game_type']=='REG':games[r['game_id']]=dict(kickoff=datetime.fromisoformat(r['gameday']+'T'+r['gametime']).replace(tzinfo=ZoneInfo('America/New_York')).timestamp(),home=r['home_team'],away=r['away_team'])
    t=epoch(p['decision_time']);history=defaultdict(list)
    for b in p['history_context_sources']:
        file=a.source_root/b['name'];assert sha(file)==b['sha256']
        if not b['name'].startswith('stats_player_week_'):continue
        with file.open()as f:
            for r in csv.DictReader(f):
                if r['season_type']!='REG'or(int(r['season'])==2026 and int(r['week'])>7):continue
                g=games.get(r['game_id'])
                if g and g['kickoff']+604800<t:history[r['player_id']].append((g['kickoff']+604800,r['position'],r['team']))
    for rows in history.values():rows.sort()
    bound=read(a.repo_root/'reports/championship-20261030f/offer-expansion/full-pool-v1/RUN_RECEIPT.json');f=a.private_root/'championship-20261030f-full-pool-v1/JOINED_ROWS.json.gz';assert sha(f)==bound['private_joined_sha256'];offers=json.loads(gzip.decompress(f.read_bytes()))['rows'];by_source={r['source_row_index']:r for r in offers}
    assert len(by_source)==462
    lookup={(m['source_member'],m['source_row_index_in_member']):m for m in mask};assert len(lookup)==len(mask)
    fits={b['path']:b for b in p['fit_receipts']};fitdata={}
    for path,b in fits.items():
        f=a.repo_root/path;assert sha(f)==b['sha256'];fitdata[path]=read(f)
    checked=set();params_count=0;reason_counts=Counter();law_kinds=Counter();groups=defaultdict(list)
    for b in p['raw_sources']['members']:
        if not any(member==b['member']for member,index in lookup):continue
        file=a.private_root/b['member'];assert sha(file)==b['sha256'];source=b['source_id']
        it=ind.packets(file)if b['kind']=='packet'else csv.DictReader(gzip.open(file,'rt'))
        for index,raw in enumerate(it):
            m=lookup.get((b['member'],index))
            if m is None:continue
            checked.add((b['member'],index));o=by_source[m['source_row_index']];q=tuple(raw[k]for k in('game_id','player_id','target'));assert q==tuple(o[k]for k in('game_id','player_id','target'))
            assert hashlib.sha256(canon([q,o['source_row_index']])).hexdigest()==m['offer_safe_id']
            if source=='empirical':raw['procedure_id']='empirical-player-history-control-v1'
            elif source=='hgb':raw['procedure_id']='hgb-direct-history-controls-v1:'+raw['objective']
            normalized=ind.model(raw);assert normalized==(m['target'],m['procedure_id'],m['history_regime'],m['product_id'])
            assert(raw['population'],raw['position'],raw['fallback'])==(m['population'],m['position'],m['fallback'])
            fit=fitdata.get(m['fit_receipt']);reasons=[]
            if source!='empirical'and fit is None:reasons.append('FIT_METADATA_REQUIRED')
            if fit:
                slot=raw.get('fit_slot')
                if source=='count':slot=f"W07-{raw['target']}-{raw['policy_id']}-{raw['procedure_family_id']}"
                assert fit['slot']==slot and fits[m['fit_receipt']]['source_id']==source
                cutoff=epoch(fit.get('fit_cutoff_utc',fit.get('training_label_fit_cutoff_utc')))
                actual_clocks=[epoch(fit.get(k))for k in('latest_training_label_available','latest_training_feature_available','latest_training_consumed_feature_available')]
                if cutoff is None or cutoff>=t or any(x is not None and x>=t for x in actual_clocks):reasons.append('FIT_TRAINING_OR_PRIOR_AFTER_DECISION')
                assert cutoff==m['fit_cutoff']
                if int(fit.get('training_n',0))>0:assert 'latest_training_label_available'in fit
            if raw['position']!=o['position']:reasons.append('PREGAME_POSITION_PARITY_REQUIRED')
            if raw.get('prediction')in(None,''):reasons.append('PREDICTION_UNAVAILABLE')
            cutoff=epoch(raw.get('cutoff',raw.get('cutoff_epoch_utc')));kickoff=epoch(o['kickoff']);assert kickoff>t and m['foreknown_target_kickoff']==kickoff
            if cutoff!=kickoff:reasons.append('SAVED_QUERY_CUTOFF_NOT_BOUND_TARGET_KICKOFF')
            latest=epoch(raw.get('latest_feature_available'));fallback=raw['fallback']
            if source=='empirical':
                used=epoch(raw.get('latest_training_available_epoch_utc'))
                if used is not None and used>=t:reasons.append('TARGET_HISTORY_AFTER_DECISION')
            elif source=='hgb'and fallback not in(None,'none'):
                used=epoch(raw.get('latest_fallback_available'))
                if used is not None and used>=t:reasons.append('FALLBACK_AFTER_DECISION')
            elif source=='count'and fallback not in(None,'none'):
                used=None;reasons.append('COUNT_FALLBACK_CHUNK_TIMING_REQUIRED')
            else:
                used=latest
                if latest is not None and latest>=t:reasons.append('QUERY_SOURCE_AFTER_DECISION')
            assert used==m['latest_consumed_available']and latest==m['latest_feature_available']and cutoff==m['query_cutoff']
            if source=='defense':
                hh=history.get(raw['player_id']);team=raw.get('team');g=games[raw['game_id']]
                if not hh or hh[-1][2]!=team or team not in(g['home'],g['away'])or raw.get('defense')!=(g['away']if team==g['home']else g['home']):reasons.append('PREGAME_TEAM_DEFENSE_CONTEXT_REQUIRED')
            assert sorted(reasons)==sorted(m['reasons']);assert(m['p1_state']=='ELIGIBLE_NEW_RETROSPECTIVE_SAVED_VECTOR')==(not reasons)
            law=raw.get('law_reference')or{}
            if isinstance(law,str):law=json.loads(law)
            params=law.get('fallback_prior',law.get('parametric'));complete=isinstance(params,dict)and params.get('kind')in('zero','bernoulli','geometric','poisson','signed')
            assert complete==m['full_law_parameters_retained'];assert('leaf_ids'in law)==m['leaf_ids_without_weights']
            if complete:
                kind=params['kind'];law_kinds[kind]+=1;params_count+=1
                if kind=='bernoulli':assert 0<=params['p']<=1
                if kind=='poisson':assert math.isfinite(params['mean'])and params['mean']>=0
                if kind in('signed','geometric'):assert math.isfinite(params['q'])and 0<=params['q']<1
                if kind=='signed':assert params['center']==int(params['center'])
            eligible=not reasons and complete;assert(m['p2_state']=='ELIGIBLE_COMPLETE_SAVED_PARAMETRIC_LAW')==eligible
            assert m['original_issuance']is False;reason_counts.update(reasons);groups[m['target'],m['procedure_id'],m['history_regime'],m['product_id']].append(m)
    assert len(checked)==len(mask)
    summary=read(a.public_root/'THRESHOLD_ADMISSIBILITY.json');assert sha(a.public_root/'THRESHOLD_ADMISSIBILITY.json')==receipt['summary_sha256'];assert len(summary)==len(groups)==548
    for row in summary:
        rr=groups[row['target'],row['procedure_id'],row['history_regime'],row['product_id']];n=sum(o['target']==row['target']for o in offers)
        p1=[m for m in rr if m['p1_state']=='ELIGIBLE_NEW_RETROSPECTIVE_SAVED_VECTOR'];p2=[m for m in rr if m['p2_state']=='ELIGIBLE_COMPLETE_SAVED_PARAMETRIC_LAW']
        assert(row['saved_query_rows'],row['eligible_offer_universe'],row['P1_admissible'],row['P2_complete_law_admissible'])==(len(rr),n,len(p1),len(p2))
        for name,admitted in(('P1',p1),('P2',p2)):assert row[name+'_eligible_mask_sha256']==hashlib.sha256(canon(sorted(m['offer_safe_id']for m in admitted))).hexdigest()
        assert row['selection_performance']is None
    report=dict(state='PASS_INDEPENDENT_SAVED_ROW_ADMISSION_JOINS_CLOCKS_AND_PARAMETERS',at=datetime.now(timezone.utc).isoformat(),protocol_sha256=receipt['protocol_sha256'],mask_sha256=receipt['mask_sha256'],summary_sha256=receipt['summary_sha256'],offer_universe=462,matched_recipe_offer_rows=len(mask),summary_cells=len(summary),P1_admissible=sum(m['p1_state']=='ELIGIBLE_NEW_RETROSPECTIVE_SAVED_VECTOR'for m in mask),P2_admissible=sum(m['p2_state']=='ELIGIBLE_COMPLETE_SAVED_PARAMETRIC_LAW'for m in mask),complete_parameter_records_checked=params_count,law_kinds=dict(law_kinds),reason_counts=dict(reason_counts),new_fits=0,new_inference=0,new_scores=0,new_grades=0,new_NFL_observations=0,limits=['Admission only, no NFL direction/probability performance scored.','New known-target-time reconstruction is distinct from original issuance and earlier-clock feature refresh.','Count fallback chunk metadata and nominal-fit-origin cases remain executable follow-ups; not evidence of absent NFL sources.','Leaf IDs alone remain insufficient for a recovered CDF.'])
    with a.output.open('x')as f:json.dump(report,f,indent=2);f.write('\n')
    print(json.dumps({k:report[k]for k in('state','matched_recipe_offer_rows','summary_cells','P1_admissible','P2_admissible')}))


if __name__=='__main__':main()
