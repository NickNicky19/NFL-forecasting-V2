"""W5 preparation adapter for the unchanged retained-leaf threshold scorer."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tools import score_recovered_leaf_laws as core
from nfl_v2 import scoring,full_provider_prop_replay
from nfl_v2.shared_subgroups import now,sha,write


def prepare(a):
    if a.output.exists() or a.private_output.exists():raise ValueError('fresh W5 outputs required')
    a.output.mkdir(parents=True);a.private_output.mkdir(parents=True)
    parent=json.loads((a.parent/'RUN_RECEIPT.json').read_bytes())
    p=dict(version='v2-w5-preparation-adapter-existing-complete-leaf-threshold-engine-v1',panel='W5',week=5,rolling=True,
        at=now(),state='FROZEN_BEFORE_W5_NEW_LEARNED_LAW_DIRECTIONS_AND_SCORES',
        code_sha256=sha(core.__file__),preparation_adapter_sha256=sha(__file__),
        core_sha256=sha(full_provider_prop_replay.__file__),scoring_sha256=sha(scoring.__file__),
        lookup_code_sha256=sha(Path(scoring.__file__).with_name('saved_leaf_law_lookup.py')),
        parent_protocol_sha256=sha(a.parent/'FROZEN_PROTOCOL.json'),parent_main_scores_sha256=sha(a.parent/'SCORES.json'),
        parent_grade_sha256=sha(a.parent_private/'GRADED_METHOD_ROWS.json.gz'),parent_plans_sha256=sha(a.parent_private/'FROZEN_SELECTIONS_AND_K.json.gz'),
        augmentation_sha256=sha(a.augmentation),augmentation_member=a.augmentation.name,
        law_lookup_receipt_sha256=sha(a.lookup_receipt),outer_offers=parent['source_offers'],
        selection='Existing core.run only: P2 higher exact Over/Under probability, ties abstain, retain push. Complete original leaf law plus same-recipe saved fallback; no P1/GLM rerun.',
        proper='All eligible law/outcome rows including ties; half multiclass Brier Over/Under/Push, categorical actual-region logloss; true zero masses remain Infinity.',
        numeric_rule='Existing strict probability range/complement rule; machine dust only, no tail floor or substantive rounding.',
        K='Existing chronological rolling-greedy K6/10/20 per category/method/history, Combined/Over/Under, only currently available candidates and remaining weekly slots; no hindsight fixed-weekly list.',
        conditioning='MODELED_APPEARANCE',bookmaker_nonvoid_conditioning='UNESTABLISHED',
        exposure='Previously exposed 2026 W5 outcomes; newly frozen same-offer method comparison, not original issuance or fresh holdout.',
        budget=dict(wall_seconds=300,max_RSS_bytes=1073741824,max_private_bytes=16777216,max_threads=2),
        new_fits=0,new_model_inference=0,new_issued_forecasts=0,Week8_outcomes_read=0)
    write(a.output/'FROZEN_PROTOCOL.json',p)
    (a.output/'PREPARATION_ADAPTER_SNAPSHOT.py').write_bytes(Path(__file__).read_bytes())
    (a.output/'SHARED_SCORER_SNAPSHOT.py').write_bytes(Path(core.__file__).read_bytes())
    print(json.dumps(dict(state=p['state'],protocol_sha256=sha(a.output/'FROZEN_PROTOCOL.json'))))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=('prepare','run'));p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--parent',type=Path,required=True);p.add_argument('--parent-private',type=Path,required=True);p.add_argument('--augmentation',type=Path,required=True);p.add_argument('--lookup-receipt',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--private-output',type=Path,required=True);a=p.parse_args();a.panel='W5'
    if a.action=='prepare':prepare(a)
    else:
        frozen=json.loads((a.output/'FROZEN_PROTOCOL.json').read_bytes())
        if sha(__file__)!=frozen['preparation_adapter_sha256']:raise ValueError('W5 adapter changed')
        core.run(a)
