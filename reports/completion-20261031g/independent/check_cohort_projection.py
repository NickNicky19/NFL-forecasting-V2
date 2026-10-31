"""Verify v3 diagnostic membership clocks and saved-grade-only score projection."""
import argparse,collections,gzip,hashlib,importlib.util,json
from datetime import datetime
from pathlib import Path
sp=importlib.util.spec_from_file_location('prior',Path(__file__).with_name('check_w7_methods.py'));q=importlib.util.module_from_spec(sp);sp.loader.exec_module(q)
read,zipped,sha,canon,member,close=q.read,q.zipped,q.sha,q.canon,q.member,q.close

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);ap.add_argument('--private',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();out=[]
 for w in(6,7):
  source=a.root/'reports/completion-20261031g/source-expansion';source=source/'w7-rolling-v1'if w==7 else source;pub=source/'cohort-projection-v3';priv=a.private/('completion-20261031g-source-w7'if w==7 else'completion-20261031g-source');bind=read(priv/'GRADING_INPUT_BINDING_V2.json');mf=Path(bind['memberships']);p=read(pub/'FROZEN_PROTOCOL.json');e=read(pub/'JOIN_METADATA_EXTENSION.json');run=read(pub/'RUN_RECEIPT.json');assert sha(mf)==p['memberships_sha256']==e['memberships_sha256'];members={tuple(r['key']):r for r in zipped(mf)};old=zipped(priv/'JOINED_ROWS.json.gz')['rows'];new=zipped(priv/'COHORT_QUALIFIED_JOIN_V3.json.gz')['rows'];grades=zipped(priv/'GRADED_ROWS.json.gz')['rows'];assert sha(priv/'JOINED_ROWS.json.gz')==e['original_join_sha256'];assert sha(priv/'COHORT_QUALIFIED_JOIN_V3.json.gz')==e['corrected_join_sha256'];assert sha(priv/'GRADED_ROWS.json.gz')==run['source_grade_sha256'];assert sha(source/'SCORES.json')==run['source_score_sha256'];assert sha(pub/'SCORES.json')==run['score_sha256'];expected={};clocks=set();qualified=0
  for oldr,r in zip(old,new):
   assert {k:v for k,v in oldr.items()if k not in('source_cohorts','cohort_clock_qualification')}=={k:v for k,v in r.items()if k not in('source_cohorts','cohort_clock_qualification')};m=members.get((r['game_id'],r['player_id'],r['target'],r['population']));t=datetime.fromisoformat(r['source_server_clock'].replace('Z','+00:00')).timestamp();ok=bool(m and m['ranking_cutoff']<=t and(m.get('latest_available')is None or m['latest_available']<m['ranking_cutoff']));cohorts=list(m['cohorts'])if ok else[];assert r['source_cohorts']==cohorts;expected[r['source_row_index']]=cohorts;qualified+=bool(cohorts)
   if m:clocks.add(m['ranking_cutoff'])
  assert len(old)==len(new)==run['source_outer_rows'];assert qualified==e['qualified_membership_rows']==run['qualified_membership_rows'];by=collections.defaultdict(list)
  for r in grades:r=dict(r,source_cohorts=expected[r['source_row_index']]);by[r['strategy']].append(r)
  trip=collections.defaultdict(dict)
  for r in read(pub/'SCORES.json'):
   pool=[v for v in by[r['strategy']]if(r['target']=='ALL'or v['target']==r['target'])and member(v,r['cohort_id'])];selected=[v for v in pool if v['selected_side']and(r['side']=='Combined'or v['selected_side']==r['side'])];c=collections.Counter(v['statistical_state']for v in selected);n=c['WIN']+c['LOSS'];m=r['selection_metrics'];assert r['n']==n and r['forecast_rows']==len(selected);assert m['status_counts']=={s:c[s]for s in m['status_counts']};close(m['hit_rate'],c['WIN']/n if n else None);close(m['selection_coverage'],len(selected)/len(pool)if pool else None);assert r['query_membership_sha256']==hashlib.sha256(canon(sorted(v['source_row_index']for v in selected))).hexdigest();trip[r['strategy'],r['target'],r['cohort_id']][r['side']]=[len(selected),n]+[c[s]for s in('WIN','LOSS','PUSH','VOID','PENDING','MISSING_ACTUAL','UNKNOWN_PARTICIPATION')]
  for t in trip.values():assert set(t)=={'over','under','Combined'}and t['Combined']==[x+y for x,y in zip(t['over'],t['under'])]
  supers=read(pub/'COHORT_SUPERSESSION_MAP.json');out.append(dict(week=w,source_rows=len(new),qualified_membership_rows=qualified,ranking_clocks_utc=[datetime.fromtimestamp(t).isoformat()for t in sorted(clocks)],score_views=run['score_views'],side_triplets=len(trip),source_predictions_sides_labels_grades_unchanged=True,score_sha256=run['score_sha256']))
 report=dict(state='PASS_INDEPENDENT_COHORT_CLOCK_ADMISSION_AND_SAVED_GRADE_PROJECTION',weeks=out,new_fits=0,new_inference=0,new_grades=0,scope='Source memberships, strict latest-before-ranking clock and ranking-before-actual-source receipt; complete newview side partitions. No originalissuedstarlist claim or re-ranking from outcomes.')
 with a.output.open('x')as f:json.dump(report,f,indent=2);f.write('\n')
 print(json.dumps(report))
if __name__=='__main__':main()
