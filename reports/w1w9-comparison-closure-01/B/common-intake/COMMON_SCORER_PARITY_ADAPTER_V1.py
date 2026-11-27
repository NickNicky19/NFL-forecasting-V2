"""B row adapter into C's exact pinned status/summary/interval functions.

This checks an already-scored native panel. It is neither a collector nor a
new common grader, source admission, model fit, or championship.
FTN-dependent checks: CC-BY-SA-4.0, FTN Data via nflverse.
"""
import argparse
import ast
import collections
import hashlib
import importlib.util
import json
import math
import sys
import types
from datetime import datetime,timezone
from decimal import Decimal
from pathlib import Path

PINNED_SCORER='2ba450f91bb5fac869ce3adde031099390ec70408a91204653869032b49b2bce'
PINNED_INTERVAL='92260304be31b0fbee42faa3ab78616f77c3791bd2613edb9d322f9bbf29aa2a'
PROCEDURE='B-FTN-BALL-QUALITY-COMPLETION-v1:'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_common_functions(scorer_path,interval_path):
    """Execute only named definitions from hash-authenticated C source.

    Full modules are not imported, avoiding their filesystem/controller side
    effects and unrelated dependency loading. The function ASTs are unchanged.
    """
    if sha(scorer_path)!=PINNED_SCORER or sha(interval_path)!=PINNED_INTERVAL:
        raise ValueError('Pinned C source hash mismatch')
    def exact_defs(path,names,namespace):
        tree=ast.parse(Path(path).read_text())
        nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
        if {n.name for n in nodes}!=set(names):raise ValueError('Missing C function')
        module=ast.Module(body=nodes,type_ignores=[])
        exec(compile(module,'PINNED_C_SOURCE_FUNCTIONS','exec'),namespace)
    interval_ns=dict(defaultdict=collections.defaultdict,math=math)
    exact_defs(interval_path,['interval'],interval_ns)
    scope=dict(Decimal=Decimal,Counter=collections.Counter,
               a=types.SimpleNamespace(interval=interval_ns['interval']))
    exact_defs(scorer_path,['status','summary'],scope)
    return scope['status'],scope['summary'],interval_ns['interval']


def typed_side(prediction,line,policy,probabilities):
    """Preserve the B procedure's side rule; C's grader does not choose sides."""
    if prediction is None:return None
    if policy in ('P1_MEAN','P1_LOWER_MEDIAN'):
        value=prediction['mean' if policy=='P1_MEAN' else 'lower_median']
        if value is None or not math.isfinite(float(value)):return None
        return 'OVER' if value>line else 'UNDER' if value<line else 'ABSTAIN'
    if policy!='P2_STATISTICAL_LAW':raise ValueError('Unregistered policy')
    if probabilities is None:return None
    # The existing B policy uses exact mass comparison. Do not silently apply
    # another C selector's tolerance, margin, gate, or confidence threshold.
    return ('OVER' if probabilities['over']>probabilities['under'] else
            'UNDER' if probabilities['under']>probabilities['over'] else 'ABSTAIN')


def common_row(offer,selected_side,*,appearance,status):
    """Contract mapping only; caller must supply qualified appearance/status."""
    if offer['target']!='pass_cmp' or offer['position']!='QB':
        raise ValueError('Separate role/target contract required')
    return dict(game_id=offer['game_id'],player_id=offer['player_id'],
        category='pass_cmp',position='QB',season=offer['season'],week=offer['week'],
        selected_side=selected_side,actual=offer['actual'],appearance=appearance,
        status=status,line=offer['line'],comparator='STRICT_OVER_UNDER',
        period='FULL_GAME_INCLUDING_OT',scoring_contract_id='OFFICIAL_FULL_GAME_PASS_COMPLETIONS',
        record_kind='ACTUAL_OFFER',evidence_tier='TIMING_UNVERIFIED_ACTUAL_LINE_DIAGNOSTIC',
        source_scope='Existing B qualified native W5-9 diagnostic; not a new quote admission')


def boundary_fixtures(common_status):
    base=dict(selected_side='OVER',actual=2,line=1.5,appearance='PLAYED',
              status='READY',comparator='STRICT_OVER_UNDER')
    cases=[('win',{},'WIN'),('loss',dict(actual=0),'LOSS'),
        ('known_zero_under',dict(actual=0,selected_side='UNDER',line=.5),'WIN'),
        ('integer_push',dict(line=2),'PUSH'),
        ('abstain',dict(selected_side='ABSTAIN',status='ABSTAIN'),'ABSTAIN'),
        ('unavailable',dict(selected_side=None,status='UNAVAILABLE_FORECAST'),'UNAVAILABLE_FORECAST'),
        ('played_missing',dict(actual=None,status='MISSING_ACTUAL'),'MISSING_ACTUAL'),
        ('unknown_presence',dict(actual=None,appearance='UNKNOWN',status='UNKNOWN_PARTICIPATION'),'UNKNOWN_PARTICIPATION'),
        ('DNP',dict(actual=None,appearance='DNP',status='DNP'),'DNP'),
        ('AT_LEAST',dict(line=2,comparator='AT_LEAST'),'WIN'),
        ('YES_event',dict(actual=1,selected_side='YES',comparator='AT_LEAST_ONE_RUSH_REC_TD'),'WIN')]
    for name,change,expected in cases:
        if common_status(dict(base,**change))!=expected:raise AssertionError(name)
    return len(cases)


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--repo',type=Path,default=Path(__file__).resolve().parents[4])
    ap.add_argument('--source-bindings',type=Path,required=True)
    ap.add_argument('--scorer-source',type=Path,required=True)
    ap.add_argument('--interval-source',type=Path,required=True)
    ap.add_argument('--receipt',type=Path,required=True)
    args=ap.parse_args();repo=args.repo.resolve();sys.path.insert(0,str(repo))
    from tools import score_player_context_wave as b
    from nfl_v2 import player_context_matchup as ctx
    from nfl_v2 import scoring as b_scoring
    status,summary,interval=load_common_functions(args.scorer_source,args.interval_source)
    fixture_count=boundary_fixtures(status)
    spec=importlib.util.spec_from_file_location('EXISTING_RETAINED_OFFER_ITERATOR',
        repo/'reports/player-context-matchup-01/B/independent/inventory_retained_qb_offers_v1.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    sources={int(k):Path(v)for k,v in json.loads(args.source_bindings.read_bytes()).items()}
    offers=[r for w,p in sorted(sources.items())for r in module.iter_offers(p,w)if r['target']=='pass_cmp']
    if len(offers)!=142 or len({b.key(r)for r in offers})!=142:raise ValueError('Not the frozen native142 panel')
    # Explicit upstream source states qualify these rows. No numeric or
    # participation-only inference is used to manufacture a statistic zero.
    if any(r['participation']!='VERIFIED_PLAYED_POSITIVE_PHYSICAL' or r['label_state']!='SUPPORTED' or r['actual']is None for r in offers):
        raise ValueError('This parity panel requires already-qualified explicit counts')
    wave=repo/'reports/information-first-20261112-01/B/completion-wave-v1'
    predictions={(r['method'],b.key(r)):r for p in (wave/'predictions').glob('2026-W*.json.gz')for r in b.read(p)['rows']}
    retained=b.read(repo/'reports/information-first-20261112-01/B/completion-scores-v1/COMMON_CONTROL_TABLE.json')
    grade_checks=0;aggregate_checks=0;views=[]
    for arm in ['B0','B1','B2']:
        for policy in ['P1_MEAN','P1_LOWER_MEDIAN','P2_STATISTICAL_LAW']:
            rows=[]
            for offer in offers:
                pred=predictions[arm,b.key(offer)]
                if pred['actual']!=offer['actual']:raise ValueError('Source label mismatch')
                probs=ctx.exact_probabilities(b.law(pred),offer['line'])
                side=typed_side(pred,offer['line'],policy,probs)
                state='UNAVAILABLE_FORECAST'if side is None else'ABSTAIN'if side=='ABSTAIN'else'READY'
                row=common_row(offer,side,appearance='PLAYED',status=state)
                c_grade=status(row)
                reference='UNAVAILABLE_FORECAST'if side is None else'ABSTAIN'if side=='ABSTAIN'else b_scoring.threshold_crossing(offer['actual'],offer['line'],side.lower(),target='pass_cmp')
                if c_grade!=reference:raise AssertionError('C/B grade mismatch')
                row['status']=c_grade # C interval consumes already-graded status.
                rows.append(row);grade_checks+=1
            result=summary(rows)
            old=next(r for r in retained if r['method']==PROCEDURE+arm and r['policy']==policy and r['window']=='ALL')
            for c_side,b_side in [('OVER','over'),('UNDER','under'),('COMBINED','Combined')]:
                expected=next(r['metrics']for r in old['sides']if r['side']==b_side)
                for key,old_key in [('wins','WIN'),('losses','LOSS')]:
                    if result[c_side][key]!=expected[old_key]:raise AssertionError('Aggregate mismatch')
                    aggregate_checks+=1
                if result[c_side]['decided']!=expected['denominators']['decided']:raise AssertionError('Decided mismatch')
                aggregate_checks+=1
            # Verification evidence only, not new canonical score views/ranking.
            views.append(dict(arm=arm,policy=policy,C_summary=result,
                membership_sha256=hashlib.sha256(json.dumps(sorted((r['game_id'],r['player_id'])for r in rows),separators=(',',':')).encode()).hexdigest()))
    receipt=dict(id='B_NATIVE142_PINNED_C_COMMON_SCORER_PARITY_v1',at_UTC=datetime.now(timezone.utc).isoformat(),
        state='PASS_EXISTING_PANEL_COMMON_STATUS_SUMMARY_INTERVAL_REUSE',C_scorer_sha256=PINNED_SCORER,
        C_interval_dependency_sha256=PINNED_INTERVAL,source_functions=['status','summary','interval'],
        method='Hashchecked unchanged function ASTs executed with original required globals; no unrelated C module/controller import or copied replacement grader',
        boundary_fixtures=fixture_count,grade_checks=grade_checks,aggregate_checks=aggregate_checks,
        native_offers=142,policy_views=views,source_bindings=[dict(week=w,bytes=p.stat().st_size,sha256=sha(p))for w,p in sorted(sources.items())],
        scope='Existingnative142W5-9parityonly;doesnotadmitAprivate84union,rights,sourceclocks,mainlineclassification,standalone-lawoperationalcoherenceorCproduction.',
        probability='Bexactlawcalculations and originalBsidepolicy preserved;C reusedstatisticalgrader/summary/interval,notprospectivelawloader',
        new_common_grader=False,new_fits=0,new_forecasts=0,new_NFL_observations=0,new_canonical_score_views=0,
        code_sha256=sha(__file__))
    if args.receipt.exists():raise FileExistsError(args.receipt)
    args.receipt.write_text(json.dumps(receipt,indent=2,allow_nan=False)+'\n')
    print(json.dumps({k:v for k,v in receipt.items()if k not in ['policy_views','source_bindings']}))


if __name__=='__main__':main()
