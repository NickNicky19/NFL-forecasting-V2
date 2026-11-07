"""Append-only probe of the owner-merged presence repair; no NFL grading."""
import argparse,collections,hashlib,importlib.util,json,math,statistics
from pathlib import Path
from verify_missingness_scope_v1 import functions,scoring,sha
REF='a478db86e2702d9fa632a23bfaf9c575a67ea902'
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--snapshot-root',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
 root=a.snapshot_root/'website'/REF;sc=scoring(root/'pull/scoring.py')
 env=dict(scoring=sc,math=math,statistics=statistics,Counter=collections.Counter,RESULTS=('hit','miss','push','dnp','unresolved'))
 functions(root/'pull/grade.py',['_number','played','participation','result','_prop_result','tally','combine_tallies'],env)
 build=functions(root/'pull/build.py',['trim_stats','player_props'],dict(scoring=sc,statistics=statistics))
 cases=[('explicit_null_reception','rec',.5,'under',{'rec':None},None,'unresolved'),
  ('unknown_combined_component','rush_rec_yd',60.5,'under',{'rush_yd':55,'rec_yd':None},None,'unresolved'),
  ('reported_zero_reception','rec',.5,'under',{'rec':0},0,'hit'),
  ('known_combined_zero_component','rush_rec_yd',60.5,'over',{'rush_yd':55,'rec_yd':0},55,'miss'),
  ('negative_signed_yards','rush_yd',-.5,'under',{'rush_yd':-2},-2,'hit'),
  ('half_td_over','pass_td',1.5,'over',{'pass_td':2},2,'hit'),
  ('half_completions_under_loss','pass_cmp',19.5,'under',{'pass_cmp':20},20,'miss'),
  ('whole_count_push','rec',4,'over',{'rec':4},4,'push'),
  ('absent_reception','rec',.5,'under',{},None,'unresolved'),
  ('absent_combined_component','rush_rec_yd',60.5,'under',{'rush_yd':55},None,'unresolved'),
  ('nonfinite_reception','rec',.5,'under',{'rec':float('nan')},None,'unresolved'),
  ('boolean_reception','rec',.5,'under',{'rec':False},None,'unresolved')]
 rows=[]
 for label,target,line,side,values,want,state in cases:
  raw=dict(player_id='FICTIONAL',team='AAA',opponent='BBB',stats=dict(gp=1,off_snp=20,**values))
  entry=build['trim_stats']([raw],source_context=dict(adapter='sleeper-week-stats-v1',season=2026,week=8))['FICTIONAL']
  got=env['_prop_result'](dict(key=target,line=line),side,entry);assert got==(want,state),(label,got)
  assert entry['stats']['_presence']['sparse_contract']is None
  if label=='reported_zero_reception':assert 'rec'in entry['stats']and entry['stats']['rec']==0
  if label=='explicit_null_reception':assert 'rec'in entry['stats']and entry['stats']['rec']is None
  rows.append(dict(fixture=label,statistic=target,line=line,selected_side=side,actual=got[0],state=got[1]))
 sides={}
 for side in('over','under'):
  rs=[r for r in rows if r['selected_side']==side];c=collections.Counter(r['state']for r in rs);t=env['tally']([r['state']for r in rs]);assert t['n_decided']==c['hit']+c['miss']
  sides[side]=dict(selected=len(rs),wins=c['hit'],losses=c['miss'],decided=t['n_decided'],push=c['push'],unresolved=c['unresolved'])
 combined=env['combine_tallies']([env['tally']([r['state']for r in rows if r['selected_side']==s])for s in('over','under')])
 assert combined['hit']==sum(s['wins']for s in sides.values())and combined['miss']==sum(s['losses']for s in sides.values())
 class MX:
  def factor(self,*args):return 1.,0
 td=[]
 for name,proj,want in [('missing_projection',None,None),('explicit_zero_TD_components',dict(rush_td=0,rec_td=0),0.),('unknown_TD_component',dict(rush_td=0,rec_td=None),None)]:
  props=build['player_props'](dict(pos='RB'),proj,[],2026,'BBB',MX());r=next(p for p in props if p['key']=='anytime_td');assert r['td_chance']==want
  td.append(dict(fixture=name,proj=r['proj'],td_chance=r['td_chance']))
 out=dict(state='PASS_PINNED_OWNER_MERGED_A478_PRESENCE_PATH',pinned_production_commit=REF,
   source_hashes={str(p.relative_to(root)):sha(p)for p in [root/'pull/build.py',root/'pull/scoring.py',root/'pull/grade.py',root/'output/app.js']},
   reused_actual_function_harness='verify_missingness_scope_v1.py extraction/scoring helpers; old main/PR1 results not rerun or overwritten',
   synthetic_actual_function_cases=rows,fictional_side_reconciliation=sides,fictional_combined=combined,
   missing_TD_projection_producer=td,presence_version=sc.PRESENCE_VERSION,absent_component_policy='Strict unknown, including legacy stat dictionaries; no absent-as-zero fallback in component().',
   previous_receipts_preserved=['MISSINGNESS_CURRENT_PATH_AND_B_SCOPE_V1.json','CURRENT_TD_UI_GUARD_REVIEW_V1.json'],
   finding_disposition='Production source path repaired and bounded actual-function fixtures pass at this pin. Historical contamination count remains unknown without raw precompaction evidence. No change to retained B415 original grades is indicated.',
   concurrency_limit='This immutable pin is the source tested. A subsequent owner run/source edit was reported while checking; no claim this pin remains latest.',
   publication_limit='No served-byte/browser-render/new-current-board claim. Root separately verifies owner capture/publication. Oldfe369packet remains historical, never relabelled current.',
   NFL_fits=0,model_calls=0,NFL_regrading=0,upstream_writes=0)
 if a.output.exists():raise FileExistsError(a.output)
 a.output.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(dict(state=out['state'],cases=len(rows),TDcases=len(td),sha256=sha(a.output))))
if __name__=='__main__':main()
