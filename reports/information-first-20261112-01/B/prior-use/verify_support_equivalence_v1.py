"""Verify FTN support is determined by the ordinary canonical QB history.

This is an input-information equivalence check, not an NFL score or model fit.
"""
import argparse
import datetime
import gzip
import hashlib
import json
import math
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT))
from nfl_v2.player_context_matchup import ContextHistory
from nfl_v2.qb_ftn_information import QBFTNInformation,FLAGS


def read(p):return json.loads(gzip.decompress(p.read_bytes()))


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,default=ROOT)
    ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();root=a.root
    p=root/'reports/information-first-20261112-01/B'
    old=root/'reports/player-context-matchup-01/B/source-fields-v3/DERIVED_QB_GAME_INPUTS.json.gz'
    extra=p/'source-qualification/QB_CONTEXT_W9_EXTENSION_V1.json.gz'
    quality=p/'source-qualification/FTN_BALL_QUALITY_QB_GAME_INPUTS_V1.json.gz'
    rows=read(old)+read(extra);history=ContextHistory(rows,8,20)
    ftn=QBFTNInformation(history,read(quality));checks=0;age_differences=[];none_history=0;zero_own=0
    for q in rows:
        d=ftn.describe(q);own=history.player_rows(q['player_id'],q['kickoff'])
        eligible=history.eligible(q['kickoff']);n=sum(r['attempts']for r in own)
        pool=sum(r['attempts']for r in eligible);observed=[r for r in own if r['attempts']>0]
        latest=max((r['available']for r in observed),default=None)
        age=None if latest is None else(q['kickoff']-latest)/86400
        expected={'charted_fraction':1. if n else None,'charted_fraction_missing':not n,
                  'charted_throws_log1p':math.log1p(n)}
        for flag in FLAGS:
            prefix=flag+':'
            expected.update({prefix+'known_fraction':1. if n else None,
                prefix+'known_fraction_missing':not n,prefix+'known_log1p':math.log1p(n),
                prefix+'own_age_days':age,prefix+'own_age_missing':age is None,
                prefix+'own_known_missing':not n,prefix+'pooled_known_missing':not pool})
        assert d['support']==expected
        assert d['complete_required_charting'];checks+=len(expected)+1
        none_history+=not own;zero_own+=bool(own and n==0)
        if own and observed and abs(age+7-(q['kickoff']-own[-1]['kickoff'])/86400)>1e-9:
            age_differences.append((q['season'],q['week']))
    x=dict(id='B-FTN-SUPPORT-EQUIVALENCE-v1',at_UTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        scope='Every2939canonicalQBgamequeryincludingold2901and38Week9extension; no fit or score.',
        canonical_rows=len(rows),rows_by_season={str(y):sum(r['season']==y for r in rows)for y in sorted({r['season']for r in rows})},
        sourcefree_support_projection_assertions=checks,own_no_history_queries=none_history,
        own_history_but_zero_attempt_total_queries=zero_own,actual_source_full_match_known_coverage=True,
        source_unknown_clock_rows=ftn.source_row_diagnostics['unknown_clock_rows'],
        source_non_target_rows=ftn.source_row_diagnostics['non_target_rows'],
        conclusion='CurrentFTNsupportisreconstructablefromunchangedordinaryQBattempt/appearancehistory. B1isexplicitoutput-preservingB0aliaswithzeroaddedlearnercolumns/fits; B2addsONLY2substantivevalues.',
        age_representation_caveat=dict(latest_positive_attempt_chart_age_differs_from_latest_any_appearance_age_count=len(age_differences),
            meaning='Zero-attemptappearancescanmakelastchartedageadifferentrepresentationthanR3lastgameagecolumn. Bothderivefromordinaryhistory; thispackagedoesnotadd/testthatrepresentation orclaimall17diagnosticsliterallyduplicatevectorcolumns.'),
        future_partial_coverage='complete_required_chartingfalse requires exactfrozenB0fallback; B2feature_valuesraises onpartialrequiredhistory.',
        bindings=[dict(path=str(f.relative_to(root)),sha256=hashlib.sha256(f.read_bytes()).hexdigest(),bytes=f.stat().st_size)
                  for f in [old,extra,quality,root/'nfl_v2/qb_ftn_information.py']],new_fits=0,new_NFL_scores_or_weeks=0)
    a.out.write_text(json.dumps(x,indent=2)+'\n')
    print(json.dumps(dict(rows=len(rows),assertions=checks,age_representation_cases=len(age_differences))))


if __name__=='__main__':main()
