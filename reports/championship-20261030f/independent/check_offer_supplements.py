"""Independent check of later metadata and paired supplement, not a regrade."""
import argparse
from collections import Counter, defaultdict
import csv
from datetime import datetime, timezone
import gzip
import hashlib
import json
import math
from pathlib import Path
import numpy as np


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def canon(v):return json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def read(p):return json.loads(p.read_bytes())
def close(a,b):
    if a is None or b is None:assert a is b
    else:assert math.isclose(a,b,abs_tol=1e-12,rel_tol=1e-12)
def cohort(r,c):
    if c=='ALL':return True
    if c=='ORIGINAL_SELECTED':return r['original_side'] in ('over','under')
    if c=='ORIGINAL_ABSTAINED':return r['original_side'] not in ('over','under')
    if c.startswith('position:'):return r['position']==c.split(':',1)[1]
    if c.startswith('source:'):return r['line_from']==c.split(':',1)[1]
    if c.startswith('original_top_'):return r['top_'+c.rsplit('_',1)[1]]
    if c=='cohort_unknown':return not r['source_cohorts']
    assert c.startswith('reconstructed:')
    return c.split(':',1)[1] in r['source_cohorts']


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--public-root',type=Path,required=True);ap.add_argument('--private-root',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
    scores=read(a.public_root/'SCORES.json');receipt=read(a.public_root/'RUN_RECEIPT.json');assert sha(a.public_root/'SCORES.json')==receipt['public_score_sha256']
    assert sha(a.private_root/'GRADED_ROWS.json.gz')==receipt['private_grade_sha256']
    grades=json.loads(gzip.decompress((a.private_root/'GRADED_ROWS.json.gz').read_bytes()))['rows']
    ks=json.loads(gzip.decompress((a.private_root/'FROZEN_K_MEMBERSHIPS.json.gz').read_bytes()))['rows']
    masks={(k['strategy'],k['target'],k['rank_scope'],k['K']):set(k['source_row_indices'])for k in ks}
    meta=read(a.public_root/'METADATA_SUPPLEMENT.json');annotations=read(a.public_root/'COMPARISON_ANNOTATIONS.json')
    assert meta['source_score_sha256']==annotations['source_score_sha256']==receipt['public_score_sha256']
    baseline={r['source_row_index']:r for r in grades if r['strategy']=='SAVED_ADJUSTED_POINT_DIRECTION_RETAINED_PRECISION'}
    by=defaultdict(list)
    for r in grades:by[r['strategy']].append(r)
    cache={};paired=0;flat=list(csv.DictReader((a.public_root/'ALL_SELECTION_VIEWS.csv').open()))
    for i,r in enumerate(scores):
        selected=[x for x in by[r['strategy']]if x['selected_side']and(r['target']=='ALL'or x['target']==r['target'])]
        if r['K'] is None:selected=[x for x in selected if cohort(x,r['cohort_id'])]
        else:selected=[x for x in selected if x['source_row_index']in masks[r['strategy'],r['target'],r['rank_scope'],r['K']]]
        selected=[x for x in selected if r['side']=='Combined'or x['selected_side']==r['side']]
        decided=[x for x in selected if x['statistical_state']in ('WIN','LOSS')]
        m=meta['rows'][i];assert m['record_id']==r['record_id'] and m['alias_of_record_id']is None
        assert m['unique_players']==len({x['player_id']for x in selected})
        assert m['unique_player_games']==len({(x['game_id'],x['player_id'])for x in selected})
        assert m['decided_unique_games']==len({x['game_id']for x in decided})
        assert m['decided_unique_players']==len({x['player_id']for x in decided})
        assert m['decided_unique_player_games']==len({(x['game_id'],x['player_id'])for x in decided})
        assert m['selected_week_count']==int(bool(selected)) and m['decided_week_count']==int(bool(decided))
        c=annotations['rows'][i];assert c['source_row_index']==i;c=c['comparison']
        if not decided:assert c['status']=='UNESTABLISHED';continue
        assert c['paired_n']==len(decided)
        assert c['membership_sha256']==hashlib.sha256(canon(sorted(x['source_row_index']for x in decided))).hexdigest()
        va=sum(x['statistical_state']=='LOSS'for x in decided)/len(decided)
        vb=sum(baseline[x['source_row_index']]['statistical_state']=='LOSS'for x in decided)/len(decided)
        close(c['candidate_error'],va);close(c['comparator_error'],vb)
        games=defaultdict(list)
        for x in decided:games[x['game_id']].append(int(x['statistical_state']=='LOSS')-int(baseline[x['source_row_index']]['statistical_state']=='LOSS'))
        u=c['uncertainty'];close(u['estimate'],va-vb);assert u['game_clusters']==len(games)and u['paired_n']==len(decided)
        if len(games)<8:assert u['game_interval']is None
        else:
            signature=tuple((sum(games[k]),len(games[k]))for k in sorted(games))
            if signature not in cache:
                draw=np.random.Generator(np.random.PCG64(1703)).integers(len(games),size=(500,len(games)))
                weights=np.array([np.bincount(v,minlength=len(games))for v in draw]);nums=np.array([x[0]for x in signature]);dens=np.array([x[1]for x in signature])
                cache[signature]=np.percentile((weights@nums)/(weights@dens),[2.5,97.5],method='linear').tolist()
            for x,y in zip(u['game_interval'],cache[signature]):close(x,y)
        assert flat[i]['record_id']==r['record_id'];close(float(flat[i]['paired_error_change']),va-vb)
        paired+=1
    report=dict(state='PASS_INDEPENDENT_OFFER_METADATA_AND_PAIRED_ANNOTATIONS',checked_at_utc=datetime.now(timezone.utc).isoformat(),source_score_sha256=receipt['public_score_sha256'],metadata_sha256=sha(a.public_root/'METADATA_SUPPLEMENT.json'),annotation_sha256=sha(a.public_root/'COMPARISON_ANNOTATIONS.json'),metadata_rows=len(meta['rows']),paired_comparisons_checked=paired,interval_masks_independently_checked=len(cache),new_grades=0,new_fits=0,new_forecasts=0,limits='Same selected cases versus saved adjusted-point control; descriptive one-week game-cluster sensitivity, not a pure learner comparison when selected pools differ.')
    with a.output.open('x')as f:json.dump(report,f,indent=2);f.write('\n')
    print(json.dumps(report))


if __name__=='__main__':main()
