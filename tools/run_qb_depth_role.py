"""One timestamped source-rank information increment; no learner/timing search."""
import argparse
import collections
import importlib.util
import json
import platform
import sys
from pathlib import Path

import numpy as np
import sklearn
from threadpoolctl import threadpool_limits

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from nfl_v2 import player_context_matchup as ctx
from nfl_v2 import qb_depth_role as role
from nfl_v2.distribution_laws import prior
from nfl_v2.distribution_wave_v2 import FittedLawModel
from tools.run_player_context_wave import Budget, now, prediction, read, sha, write

BASE = ROOT / 'reports/player-context-matchup-01/B'
OLD = ROOT / 'reports/profile-increment-to-release-01/B/opportunity-wave-v1'
VERSION = 'B-QB-SOURCE-DEPTH-ROLE-INCREMENT-v1'
SOURCE_TIER = 'CURRENT_VINTAGE_TIMESTAMPED_DEPTH_ASOF_RECONSTRUCTION_NOT_ORIGINAL_ISSUANCE'


def retained():
    return { (r['game_id'], r['player_id']): r
             for path in sorted((OLD / 'predictions').glob('*.json.gz'))
             for r in read(path)['rows'] if r['method'] == 'R3' }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('action', choices=['prepare', 'run'])
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--depth2025', type=Path)
    ap.add_argument('--depth2026', type=Path)
    ap.add_argument('--max-origins', type=int)
    a = ap.parse_args(); a.out = a.out.resolve()
    inputs = BASE / 'source-fields-v3/DERIVED_QB_GAME_INPUTS.json.gz'
    rows = ctx.load_inputs(inputs)
    old = retained()
    if a.action == 'prepare':
        a.out.mkdir(parents=True, exist_ok=False)
        helper = ROOT / 'reports/next-generation-information-research-01/B/source-qualification/qb_depth_source_v1.py'
        spec = importlib.util.spec_from_file_location('read_depth_source', helper)
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        source_bindings = [(a.depth2025, '14f74185b3c2c48df234ced284ba3596bda3333d0b2a8df40841f68cd34539fa'),
                           (a.depth2026, '8633b61b70c35eaf919c8aef9934c8802723de4dfb6aeb7f354dfc09237a5ced')]
        source = module.QBDepthSource(source_bindings)
        depth = role.DepthRoleHistory(source.records, team_snapshots=source.team_snapshots)
        history = ctx.ContextHistory(rows, 8, 20)
        derived = []
        for q in rows:
            if (q['game_id'], q['player_id']) not in old:
                continue
            eligible = history.player_rows(q['player_id'], q['kickoff'])
            previous = eligible[-1] if eligible else None
            d = depth.describe(q, previous=previous)
            # Independently implemented source admission must agree on rank/clock.
            control = source.asof(team=q['team'], player_id=q['player_id'], cutoff=q['kickoff'])
            expected = control.get('rank') if control.get('available') else None
            assert d['values']['current_depth_rank'] == expected
            derived.append(dict(game_id=q['game_id'], player_id=q['player_id'],
                                season=q['season'], week=q['week'], team=q['team'],
                                kickoff=q['kickoff'], previous_game_id=previous['game_id'] if previous else None,
                                source_tier=SOURCE_TIER, description=d))
        write(a.out / 'DERIVED_QB_ROLE_INPUTS_V1.json.gz', derived)
        order = read(OLD / 'FEATURE_ORDER_V1.json')['orders']['R3']
        orders = {'S0': order}
        for arm in ('S1', 'S2'):
            orders[arm] = order + role.feature_names(arm)
        write(a.out / 'FEATURE_ORDER_V1.json', dict(orders=orders))
        files = [Path(__file__), ROOT / 'nfl_v2/qb_depth_role.py', helper,
                 ROOT / 'nfl_v2/player_context_matchup.py', ROOT / 'nfl_v2/distribution_wave_v2.py',
                 ROOT / 'nfl_v2/distribution_laws.py', ROOT / 'nfl_v2/hgb_control.py']
        write(a.out / 'FROZEN_PROTOCOL.json', dict(
            id=VERSION, assignment='NFL-NEXT-GENERATION-INFORMATION-RESEARCH-01',
            registered_UTC=now(), state='FROZEN_BEFORE_NEW_FITS_AND_SCORES', owner='B', coordinator='C',
            code_sha256={str(p.relative_to(ROOT)): sha(p) for p in files},
            inputs_sha256=sha(inputs), role_inputs_sha256=sha(a.out / 'DERIVED_QB_ROLE_INPUTS_V1.json.gz'),
            feature_order_sha256=sha(a.out / 'FEATURE_ORDER_V1.json'),
            source_bindings=[dict(season=y, sha256=h, bytes=p.stat().st_size) for y, (p,h) in zip((2025,2026), source_bindings)],
            reused_predictions=[dict(path=str(p.relative_to(ROOT)), sha256=sha(p)) for p in sorted((OLD / 'predictions').glob('*.json.gz'))],
            hypothesis='Source-reported current QB depth rank and change since last eligible own-game role add decision-time information beyond retained lagged workload/context/defense.',
            new_information='Source-authored timestamped appended QB depth snapshots; no confirmed-starter/health probability, injury multiplier, receiver absence or future realized exposure.',
            arms=dict(S0='Reuse exact retained R3; highest observed inspected B native completion law, not proven strongest global method.',
                      S1='Same R3 learner plus source age/current-rank missing and prior-role support indicators.',
                      S2='S1 plus current projected QB rank and current-minus-prior rank; prior only last eligible same-team own game. No rank1 filter.'),
            contrasts=['S1-S0 support/availability', 'S2-S1 rank values beyond support', 'S2-S0 total new information'],
            family='Unchanged 32-tree ExtraTrees Leaf-CDF seed1701,95% empirical+5% same-origin prior; fixed settings/no tuning.',
            chronology='H-RECENT previous season+earlier current labels; strict available<weekly earliest kickoff, original seven-day outcome availability and all original base features unchanged. New depth dt strictly<each historical query kickoff.',
            information_tier=SOURCE_TIER,
            source_limit='dt is source LOADED time; current cumulative archive/append contract. No independent immutable earlier HTTP bytes or original forecast issuance proof. No backdating.',
            population='Same277retrospective official-QB-stat-row queries2026W1-8; backups retained. This does not authenticate full pregame roster or future starter population.',
            evaluation=[dict(season=2026,weeks=list(range(1,9)))],
            actual_offers='Same retained112CMP offers2026W5-8, timing-unverified actual-line diagnostics. EarlierA88annualboard is separate owner join and not inherited.',
            controls='ExactR3/E3, savedadjusted/raw, strict-current retained84where restored, bothconstant sides, earlier-only prevalence, neutral0.25; no invented market odds.',
            outputs=['mean','lower_median','standalone_completion_count_law'],
            joint_support='No new joint ATT/CMP law or separate attempt product is claimed. Do not cap unrelated saved marginals.',
            fallback='Same registered5%prior inside law. Missing rank neutral encoded only with explicit missing/support indicators; no technical failure reclassified as abstention.',
            stopping='Exactly16newfit calls/8origins, no outcome-driven repeat/lags/seeds/gates. Existing support/tie rules; inconclusive is not equivalence. Four offerweeks cannot qualify new primarydirection/probability.',
            retention='Publish/readback source/code/derivedinputs/protocol and two pilot typedmodels before completing remaining origins; CC-BY4derived lane, no raw sources/offers or unsafe loading.',
            environment=dict(python=platform.python_version(),numpy=np.__version__,sklearn=sklearn.__version__),
            budget=dict(max_optimizer_fits=16,wall_seconds=1200,cpu_seconds=1800,max_threads=2,max_RSS_bytes=2147483648,public_retention_bytes=16777216,reserve_bytes=2097152,new_private_restricted_bytes=0),
            prior_season_queue='2025 numerical and older panels retained; this finite first fit package evaluates2026only and does not claim their completion.',
            original_issuance=False,production_changes=0))
        print(json.dumps(dict(state='FROZEN',role_rows=len(derived),source_bytes=sum(p.stat().st_size for p,h in source_bindings))))
        return
    p = read(a.out / 'FROZEN_PROTOCOL.json')
    for name,h in p['code_sha256'].items(): assert sha(ROOT/name)==h, name
    assert sha(inputs)==p['inputs_sha256']
    assert sha(a.out/'DERIVED_QB_ROLE_INPUTS_V1.json.gz')==p['role_inputs_sha256']
    assert sha(a.out/'FEATURE_ORDER_V1.json')==p['feature_order_sha256']
    for r in p['reused_predictions']: assert sha(ROOT/r['path'])==r['sha256']
    descriptions={(r['game_id'],r['player_id']):r['description'] for r in read(a.out/'DERIVED_QB_ROLE_INPUTS_V1.json.gz')}
    rows=[q for q in rows if (q['game_id'],q['player_id']) in old]
    # Saved typed JSON uses null for numeric NaN. Restore the numeric array
    # before the unchanged learner's earlier-only median/missing transform.
    matrices={arm:np.asarray([list(old[q['game_id'],q['player_id']]['features'])+role.feature_values(descriptions[q['game_id'],q['player_id']],arm) for q in rows], dtype=float) for arm in ('S1','S2')}
    history=ctx.ContextHistory(ctx.load_inputs(inputs),8,20)
    budget=Budget(a.out,p); completed=[]
    with threadpool_limits(limits=2):
        for week in range(1,9):
            dest=a.out/'predictions'/f'2026-W{week:02}.json.gz'
            if dest.exists(): completed.append(week); continue
            if a.max_origins is not None and len(completed)>=a.max_origins: break
            cutoff=read(OLD/'predictions'/f'2026-W{week:02}.json.gz')['fit_cutoff']
            indices=[i for i,q in enumerate(rows) if q['physical_participation'] and q['target_parity'] and q['season']>=2025 and q['available']<cutoff]
            queries=[(i,q)for i,q in enumerate(rows)if(q['season'],q['week'])==(2026,week)]
            y=np.asarray([rows[i]['official_completions']for i in indices]); pr=prior(y,'pass_cmp')
            forecasts=[]
            for i,q in queries:
                r=old[q['game_id'],q['player_id']]
                forecasts.append(dict(r,method='S0',procedure_id=VERSION+':S0',reused_original_procedure_id=r['procedure_id'],new_inference=False,depth_role=descriptions[q['game_id'],q['player_id']]))
            for arm in ('S1','S2'):
                slot=f'2026-W{week:02}-{arm}'; fp=a.out/'fits'/(slot+'.json.gz')
                if fp.exists(): payload=read(fp)['model']
                else:
                    budget.fit(slot); started=now()
                    m=FittedLawModel('ordered_leaf_cdf','pass_cmp').fit(matrices[arm][indices],y,['QB']*len(indices))
                    payload=ctx.export_forest(m)
                    sample=matrices[arm][queries[0][0]]
                    original=m.predict(sample[None,:],['QB'],{'QB':pr})[0][0]
                    restored=ctx.restored_forest_law(payload,sample,pr)
                    assert abs(original.mean-restored.mean)<1e-10 and original.quantile(.5)==restored.quantile(.5)
                    write(fp,dict(slot=slot,model=payload,training_rows=len(indices),fit_cutoff=cutoff,
                        latest_training_label=max(rows[i]['available']for i in indices),new_optimizer_fits=1,
                        training_membership_sha256=__import__('hashlib').sha256(json.dumps([(rows[i]['game_id'],rows[i]['player_id'])for i in indices]).encode()).hexdigest(),
                        feature_count=matrices[arm].shape[1],feature_order_sha256=p['feature_order_sha256'],actual_started_UTC=started,actual_completed_UTC=now()))
                for i,q in queries:
                    law=ctx.restored_forest_law(payload,matrices[arm][i],pr)
                    r=prediction(q,arm,'pass_cmp',law,cutoff,history,model_slot=slot,features=matrices[arm][i],fallback='none')
                    fixed=old[q['game_id'],q['player_id']]
                    r.update(procedure_id=VERSION+':'+arm,profile_priority=fixed['profile_priority'],new_inference=True,
                             depth_role=descriptions[q['game_id'],q['player_id']],source_vintage=SOURCE_TIER)
                    forecasts.append(r)
            write(dest,dict(season=2026,week=week,fit_cutoff=cutoff,rows=forecasts,actual_persisted_UTC=now(),original_issuance=False,resources=budget.resources()))
            completed.append(week); print(json.dumps(dict(week=week,fits=budget.fit_calls)),flush=True)
    complete=len(completed)==8
    write(a.out/('RUN_RECEIPT.json'if complete else'PILOT_RECEIPT_V1.json'),dict(state='COMPLETE'if complete else'PILOT_RETAINED',completed_weeks=completed,remaining_weeks=[w for w in range(1,9)if w not in completed],resources=budget.resources(),new_original_forecasts=0,new_real_calendar_weeks=0,source_vintage=SOURCE_TIER))


if __name__=='__main__': main()
