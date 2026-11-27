"""Versioned measurement of unchanged website sides with qualified INT labels.

Use the established statistical grader. This adapter creates neither forecasts,
new selections, settlement rules, a common evaluator nor production writes.
"""
import argparse
import collections
import hashlib
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from nfl_v2 import scoring
from nfl_v2.full_provider_prop_replay import score_row, check_triplet
from nfl_v2.paired_uncertainty import paired_losses
from tools.score_player_context_wave import read, write, sha, now, digest

VERSION='B-WEBSITE-PASS-INT-MEASUREMENT-20261112-v1'
SUPPORT='EXPLICIT_NFLVERSE_PASSING_INTERCEPTIONS_AND_ESPN_PASSING_INTERCEPTIONS_AGREE'


def key(row):
    return int(row['season']),int(row['week']),str(row['game_id']),str(row['player_id'])


def valid_count(value):
    return scoring.valid_actual('pass_int',value)


def played(row):
    return any(scoring.finite(v) and v>0 for v in row.get('played_evidence',{}).values())


def original_actual(row):
    if not played(row) or not row.get('pass_int_field_present'):
        return None
    value=row.get('reported_pass_int')
    return int(value) if valid_count(value) else None


def qualified_actual(row,label):
    """Only explicit supported final source values, never participation fills."""
    if label is None:
        return None
    expected=(int(row['season']),int(row['week']),str(row['game_id']),str(row['player_id']))
    actual=(int(label['season']),int(label['week']),str(label['source_game_id']),str(label['source_player_id']))
    if actual!=expected or label.get('team')!=row.get('team') or label.get('opponent')!=row.get('opponent'):
        raise ValueError('Exact player/game/season/week/team/opponent mismatch')
    if not label.get('player_id') or not label.get('game_id'):
        raise ValueError('Canonical identity missing')
    if label.get('label_support')!=SUPPORT or label.get('finality')!='STATUS_FINAL':
        return None
    for name in ('weekly_source_sha256','espn_source_sha256','finality_source_sha256'):
        value=label.get(name)
        if not isinstance(value,str) or len(value)!=64 or any(c not in '0123456789abcdef'for c in value):
            return None
    if 'corrected_pass_int'not in label or not valid_count(label['corrected_pass_int']):
        return None
    if not played(row):
        return None
    return int(label['corrected_pass_int'])


def normalize_board(rows):
    result=[]
    for i,r in enumerate(rows):
        prop=r['prop'];stats=r['stats_entry']['stats']
        result.append(dict(r,source_row_index=i,line=prop['line'],line_from=prop['line_from'],
            side=prop.get('lean') if prop.get('lean')in('over','under')else None,
            top_over=prop.get('top_over',False),top_under=prop.get('top_under',False),
            pass_int_field_present='pass_int'in stats,reported_pass_int=stats.get('pass_int'),
            played_evidence={k:stats.get(k)for k in('gp','off_snp','pass_att')},target='pass_int'))
    return result


def main():
    ap=argparse.ArgumentParser();ap.add_argument('action',choices=['prepare','score'])
    ap.add_argument('--board',type=Path,required=True);ap.add_argument('--selected',type=Path,required=True)
    ap.add_argument('--labels',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args();a.out=a.out.resolve()
    inputs={'board':a.board,'selected':a.selected,'labels':a.labels}
    if a.action=='prepare':
        a.out.mkdir(parents=True,exist_ok=False)
        write(a.out/'FROZEN_SCORING_PROTOCOL.json',dict(id=VERSION,registered_UTC=now(),state='FROZEN_BEFORE_DETERMINISTIC_REGRADE',
            owner='B_independent_measurement',coordinator='C',code_sha256=sha(__file__),grader_sha256=sha(ROOT/'nfl_v2/scoring.py'),
            aggregation_sha256=sha(ROOT/'nfl_v2/full_provider_prop_replay.py'),uncertainty_sha256=sha(ROOT/'nfl_v2/paired_uncertainty.py'),
            input_bindings={k:dict(sha256=sha(v),bytes=v.stat().st_size)for k,v in inputs.items()},
            category='pass_int',season=2026,weeks=[5,6,7,8,9],role='QB',board=144,selected=86,original_missing=46,
            baseline='Actualpublishedpresence-strict-v5 currenttrack_record, notstaleW4-8originalrecordedreport. Reproduce same86archived sides; preserveabsent/nullunknown.',
            correction='Same frozenpoints/sides/lines; appendcurrent-vintage explicitNFLverse+ESPNpassingINTagree/final-labelversion. No guessingzero fromappearance.',
            unknowns='Missing/unqualified/conflictingstatstaysunknown; countintegerzero validonlywithexplicitqualifiedsource.',
            products=['CURRENT_PUBLISHED_PRESENCE_V5','CORRECTED_CURRENT_FINAL_LABELS','CONSTANT_OVER_ON_SAME86','CONSTANT_UNDER_ON_SAME86','CONSTANT_OVER_FULL144','CONSTANT_UNDER_FULL144','RECORDED_TOP_FLAGS_ORIGINAL','RECORDED_TOP_FLAGS_CORRECTED'],
            controls='Bothconstant sides onidentical86selected opportunities; full144controls separatelydeclared, notissuedmodelselections.',
            scopes='OwnOver/Under/Combined, eachweekandcumulative;144eligible/86storedleans/58storednoleans. Topflags3separatefrom86andnotcompleteTopPickspolicyreplay.',
            original_issuance='Storedarchiveselectionsareobservedcurrentbytes; originaldecision/quoteclocksnotauthenticatedbythisregrade. No newlyissuedpick.',
            model_and_fallback='Exactunderlyingforecast/fallbackrecipe notboundbythisgradeaudit; fallbackcountUNKNOWN, notzero oralllearned.',
            source_tier='CURRENT_VINTAGE_FINAL_LABEL_CORRECTION;ARCHIVED_OFFER_LABELS_WITH_UNVERIFIED_ORIGINAL_QUOTE_TIMING',
            exposure='Originalandcurrentlabelsinspectedforsourceaudit; deterministicmeasurement, notnewholdoutoralgorithmtest.',
            budget=dict(new_fits=0,new_predictions=0,new_selection_searches=0,wall_seconds=240,public_bytes=4194304,protected_row_exports=0),
            release='No primaryadmission/sitewrite;5actualscoredweekblocks donotupgradeprovenance orproveforecastskill.'))
        print('FROZEN_REGRADE');return
    p=read(a.out/'FROZEN_SCORING_PROTOCOL.json')
    assert p['code_sha256']==sha(__file__)and p['grader_sha256']==sha(ROOT/'nfl_v2/scoring.py')
    assert p['aggregation_sha256']==sha(ROOT/'nfl_v2/full_provider_prop_replay.py')and p['uncertainty_sha256']==sha(ROOT/'nfl_v2/paired_uncertainty.py')
    for name,path in inputs.items():assert sha(path)==p['input_bindings'][name]['sha256']
    board=normalize_board(read(a.board));selected=read(a.selected);labels=read(a.labels)
    assert len(board)==144 and len(selected)==86 and len(labels)==144
    bm={key(r):r for r in board};lm={(r['season'],r['week'],str(r['source_game_id']),str(r['source_player_id'])):r for r in labels}
    assert len(bm)==len(lm)==144 and set(bm)==set(lm)
    for r in selected:
        b=bm[key(r)];assert r['side']==b['side']and scoring.exact_decimal(r['line'])==scoring.exact_decimal(b['line'])and r['line_from']==b['line_from']
        b['top_over']=r['top_over'];b['top_under']=r['top_under']
    assert sum(r['side']is not None for r in board)==86
    strategies=p['products'];allgrades={};scores=[];transitions=collections.Counter();membership=[]
    for strategy in strategies:
        grades=[]
        for r in board:
            sd=r['side']
            if strategy.startswith('CONSTANT_'):
                sd='over'if 'OVER_'in strategy else'under'
                if strategy.endswith('SAME86')and r['side']is None:sd=None
            elif strategy.startswith('RECORDED_TOP_FLAGS'):
                sd=r['side']if(r['top_over']and r['side']=='over')or(r['top_under']and r['side']=='under')else None
            original=strategy in('CURRENT_PUBLISHED_PRESENCE_V5','RECORDED_TOP_FLAGS_ORIGINAL')
            value=original_actual(r)if original else qualified_actual(r,lm[key(r)])
            state='ABSTAIN'if sd is None else'UNKNOWN_PARTICIPATION'if not played(r)else scoring.threshold_crossing(value,r['line'],sd,target='pass_int')
            grades.append(dict(r,actual=value,selected_side=sd,statistical_state=state,settlement_state='UNRESOLVED_CONTRACT',net_return=None))
        allgrades[strategy]=grades
        membership.append(dict(strategy=strategy,rows=len(grades),calculation_sha256=digest([{k:r.get(k)for k in('game_id','player_id','week','line','selected_side','actual','statistical_state')}for r in grades]),raw_rows_published=False))
        for window,pool in [('ALL',grades)]+[(w,[r for r in grades if r['week']==w])for w in range(5,10)]:
            vv=[]
            for side in('over','under','Combined'):
                rr=[r for r in pool if r['selected_side']and(side=='Combined'or r['selected_side']==side)]
                v=score_row(rr,pool,strategy=strategy,target='pass_int',cohort='EXACT_FROZEN_REAL_LINE_BOARD',side=side)
                v.update(record_id='B-INT-AUDIT-'+digest([strategy,window,side])[:24],procedure_id=VERSION+':'+strategy,product_id='UNCHANGED_STORED_SIDE_STATISTICAL_CROSSING',
                    season=2026,week=window,evaluation_weeks=sorted({r['week']for r in pool}),population='ARCHIVED_WEBSITE_QB_REAL_LINE_BOARD',position='QB',
                    history_regime='ARCHIVED_WEBSITE_PROCEDURE_NO_RETRAINING_IN_THIS_AUDIT',time_panel_id='2026_W5_W9_PASS_INT',evaluation_panel_id=VERSION,
                    horizon_id='ARCHIVED_DECISION_AND_QUOTE_CLOCKS_NOT_AUTHENTICATED',source_vintage=p['source_tier'],evidence='VERSIONED_MEASUREMENT_OF_FROZEN_ARCHIVE_SIDES',
                    selection_evidence='ARCHIVED_STORED_SIDES_NOT_REISSUED;CONSTANTS_RETROSPECTIVE_CONTROLS',fallback_rows=None,fallback_reason='UNDERLYING_FALLBACK_ATTRIBUTION_NOT_BOUND',
                    technical_unavailable=0,eligible_offer_rows=len(pool),stored_lean_rows=sum(r['side']is not None for r in pool),
                    outcome_version='ORIGINAL_PRESENCE_STRICT_V5'if original else'B-OFFICIAL-PASSING-INTERCEPTIONS-20261112-v1')
                scores.append(v);vv.append(v)
            check_triplet(vv)
    before=allgrades['CURRENT_PUBLISHED_PRESENCE_V5'];after=allgrades['CORRECTED_CURRENT_FINAL_LABELS']
    for a1,b1 in zip(before,after):
        assert a1['selected_side']==b1['selected_side']and a1['line']==b1['line']
        if a1['selected_side']:transitions[a1['statistical_state']+' -> '+b1['statistical_state']]+=1
    base=next(r for r in scores if(r['strategy'],r['week'],r['side'])==('CURRENT_PUBLISHED_PRESENCE_V5','ALL','Combined'))['selection_metrics']
    assert(base['WIN'],base['LOSS'],base['denominators']['unresolved'])==(33,7,46)
    pairs=[]
    for control in('CONSTANT_OVER_ON_SAME86','CONSTANT_UNDER_ON_SAME86'):
        same=[(a1,b1)for a1,b1 in zip(after,allgrades[control])if a1['selected_side']and a1['statistical_state']in('WIN','LOSS')and b1['statistical_state']in('WIN','LOSS')]
        pairs.append(dict(candidate='CORRECTED_CURRENT_FINAL_LABELS',control=control,kind='OFFER_DIRECTION_PAIRED_LOSS',season=2026,policy='FROZEN_RECORDED_SIDE',
            candidate_only_wins=sum(a1['statistical_state']=='WIN'and b1['statistical_state']=='LOSS'for a1,b1 in same),control_only_wins=sum(a1['statistical_state']=='LOSS'and b1['statistical_state']=='WIN'for a1,b1 in same),
            **paired_losses([float(a1['statistical_state']=='LOSS')for a1,b1 in same],[float(b1['statistical_state']=='LOSS')for a1,b1 in same],[(2026,a1['week'])for a1,b1 in same],[a1['game_id']for a1,b1 in same])))
    write(a.out/'SCORES.json',scores);write(a.out/'PAIRED_CONTROLS.json',pairs)
    write(a.out/'MEASUREMENT_TRANSITIONS_V1.json',dict(transitions=dict(transitions),predictions_changed=0,sides_changed=0,lines_changed=0,original_rows_overwritten=0,
        corrected_values_from_explicit_sources=True,new_original_issues=0,new_NFL_games=0,scope='Measurementcorrectiononly; no forecast-accuracyimprovementclaim.'))
    write(a.out/'OWNER_LOCAL_COMMITMENTS.json',membership)
    write(a.out/'RUN_RECEIPT.json',dict(state='COMPLETE_LOCAL_INDEPENDENT_REPRODUCTION_NOT_C_ADMITTED',at_UTC=now(),new_fits=0,new_predictions=0,new_sides=0,
        eligible=144,selected=86,original_decided=40,original_unknown=46,corrected_decided=sum(r['statistical_state']in('WIN','LOSS')for r in after),
        scored_weeks=[5,6,7,8,9],unique_selected_games=len({r['game_id']for r in after if r['selected_side']}),canonical_views=len(scores),paired_views=len(pairs),
        source_timing_not_upgraded=True,new_primary_switches=0,original_site_writes=0))
    print(json.dumps(read(a.out/'RUN_RECEIPT.json')))


if __name__=='__main__':main()
