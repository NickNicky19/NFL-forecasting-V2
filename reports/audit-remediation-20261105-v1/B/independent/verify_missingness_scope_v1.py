"""Actual pinned functions plus saved-source presence audit, no NFL regrading."""
import argparse,ast,collections,csv,gzip,hashlib,importlib.util,json,math,statistics,sys,types
from decimal import Decimal
from pathlib import Path
PROD='fe369c7462e4e4f290727b2d03b696d28ef5454b'
DEV='81c3fc2a612ced916f4c54814f978c509058bca5'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def functions(path,names,env):
 tree=ast.parse(path.read_text());nodes=[n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))and n.name in names]
 assert {n.name for n in nodes}==set(names)
 exec(compile(ast.Module(body=nodes,type_ignores=[]),str(path),'exec'),env)
 return env
def scoring(path):
 spec=importlib.util.spec_from_file_location('pinned_scoring_'+path.parent.parent.name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def main():
 ap=argparse.ArgumentParser()
 for k in ('repo','snapshots','b-private','output'):ap.add_argument('--'+k,type=Path,required=True)
 a=ap.parse_args();sys.path.insert(0,str(a.repo));outputs={};bindings={}
 cases=[('explicit_null_reception','rec',.5,'under',{'rec':None}),
  ('unknown_combined_component','rush_rec_yd',60.5,'under',{'rush_yd':55,'rec_yd':None}),
  ('reported_zero_reception','rec',.5,'under',{'rec':0}),
  ('known_combined_zero_component','rush_rec_yd',60.5,'over',{'rush_yd':55,'rec_yd':0}),
  ('negative_signed_yards','rush_yd',-.5,'under',{'rush_yd':-2}),
  ('half_td_over','pass_td',1.5,'over',{'pass_td':2}),
  ('half_completions_under_loss','pass_cmp',19.5,'under',{'pass_cmp':20}),
  ('whole_count_push','rec',4,'over',{'rec':4})]
 for ref in (PROD,DEV):
  root=a.snapshots/'website'/ref;sc=scoring(root/'pull/scoring.py')
  env=dict(scoring=sc,math=math,statistics=statistics,Counter=collections.Counter,RESULTS=('hit','miss','push','dnp','unresolved'))
  functions(root/'pull/grade.py',['_number','played','participation','result','_prop_result','tally','combine_tallies'],env)
  build=functions(root/'pull/build.py',['trim_stats','player_props'],dict(scoring=sc,statistics=statistics))
  rows=[]
  for label,target,line,side,values in cases:
   raw=dict(player_id='FICTIONAL',team='AAA',opponent='BBB',stats=dict(gp=1,off_snp=20,**values))
   kwargs={'source_context':dict(adapter='sleeper-week-stats-v1',season=2026,week=8)}if ref==DEV else{}
   entry=build['trim_stats']([raw],**kwargs)['FICTIONAL']
   actual,state=env['_prop_result'](dict(key=target,line=line),side,entry)
   rows.append(dict(fixture=label,target=target,line=line,selected_side=side,actual=actual,state=state,
     explicit_input_fields=values,retained_input_fields={k:v for k,v in entry['stats'].items()if k!='_presence'}))
  assert [(r['actual'],r['state'])for r in rows[:2]]==([(0,'hit'),(55,'hit')]if ref==PROD else[(None,'unresolved')]*2)
  assert [(r['actual'],r['state'])for r in rows[2:]]==[(0,'hit'),(55,'miss'),(-2,'hit'),(2,'hit'),(20,'miss'),(4,'push')]
  sides={}
  for side in ('over','under'):
   rr=[r for r in rows if r['selected_side']==side];t=env['tally']([r['state']for r in rr]);w=sum(r['state']=='hit'for r in rr);l=sum(r['state']=='miss'for r in rr)
   assert (t['hit'],t['miss'],t['n_decided'])==(w,l,w+l)
   sides[side]=dict(selected=len(rr),wins=w,losses=l,decided=w+l,hit_rate=w/(w+l)if w+l else None,push=t['push'],unresolved=t['unresolved'])
  combined=env['combine_tallies']([env['tally']([r['state']for r in rows if r['selected_side']==s])for s in ('over','under')])
  assert combined['hit']==sum(r['wins']for r in sides.values())and combined['miss']==sum(r['losses']for r in sides.values())
  # Exercise actual producer with no collection, model, or real player inputs.
  class MX:
   def factor(self,*args):return 1.,0
  ps=build['player_props'](dict(pos='RB'),None,[],2026,'BBB',MX())
  td=next(r for r in ps if r['key']=='anytime_td')
  outputs[ref]=dict(actual_function_fixtures=rows,fictional_side_counts=sides,fictional_combined=combined,
     null_projection_producer=dict(proj=td['proj'],td_chance=td['td_chance']),
     sparse_absence_note='PR1 inference of absent zero is explicitly a legacy sparse adapter assumption, not authenticated reported zero.')
  for f in ('build.py','grade.py','scoring.py'):bindings[ref+'/pull/'+f]=sha(root/'pull'/f)
 # Saved B originals: inspect already graded states and retained raw target cells.
 gradespath=a.b_private/'LOCAL_GRADED_ROWS.json.gz';sourcepath=a.b_private/'source-labels/stats.csv'
 rr=json.loads(gzip.decompress(gradespath.read_bytes()))['rows']
 rr=[r for r in rr if r.get('panel')=='ORIGINAL_PROVIDER_T90'and r.get('strategy')=='original']
 raw={(r['game_id'],r['player_id']):r for r in csv.DictReader(sourcepath.open())if(r['season'],r['week'],r['season_type'])==('2026','8','REG')}
 mapping=dict(pass_yd=['passing_yards'],pass_td=['passing_tds'],pass_cmp=['completions'],pass_att=['attempts'],pass_int=['passing_interceptions'],rush_yd=['rushing_yards'],rush_att=['carries'],rec=['receptions'],rec_yd=['receiving_yards'],rush_rec_yd=['rushing_yards','receiving_yards'])
 selected=[r for r in rr if r['selected_side']in('over','under')];decided=[r for r in selected if r['statistical_state']in('WIN','LOSS')]
 assert len(decided)==415 and len({(r['game_id'],r['player_id'],r['target'],str(r['line']))for r in decided})==415
 fields=collections.Counter();zero_outcomes=0
 for r in decided:
  s=raw[r['game_id'],r['player_id']];values=[]
  for f in mapping[r['target']]:
   assert f in s and s[f]not in('',None);v=Decimal(s[f]);assert v.is_finite();values.append(v);fields['required_cells']+=1;fields['explicit_zero_cells']+=v==0
  assert sum(values)==Decimal(str(r['actual']));zero_outcomes+=Decimal(str(r['actual']))==0
 states=collections.Counter((r['selected_side'],r['statistical_state'])for r in selected)
 assert states['over','WIN']==109 and states['over','LOSS']==128 and states['under','WIN']==96 and states['under','LOSS']==82
 # Verify one retained win/loss per selected-side bucket, deterministically.
 examples=[]
 for side in ('over','under'):
  for state in ('WIN','LOSS'):
   r=min((r for r in decided if r['selected_side']==side and r['statistical_state']==state),key=lambda r:(r['game_id'],r['player_id'],r['target']))
   win=Decimal(str(r['actual']))>Decimal(str(r['line']))if side=='over'else Decimal(str(r['actual']))<Decimal(str(r['line']))
   assert win==(state=='WIN');examples.append(dict(side=side,state=state,target=r['target'],record_sha256=hashlib.sha256(json.dumps(r,sort_keys=True,separators=(',',':')).encode()).hexdigest(),independent_decimal_boundary='PASS'))
 from nfl_v2 import empirical_benchmark,scoring as bs
 assert empirical_benchmark.target_value('rec',{'receptions':None})is None
 assert empirical_benchmark.target_value('rush_rec_yd',{'rushing_yards':55,'receiving_yards':None})is None
 assert empirical_benchmark.target_value('anytime_td',{'rushing_tds':0,'receiving_tds':None})is None
 assert bs.settle(None,4.5,'under',1.91)==('unresolved',None)
 result=dict(state='PASS_INDEPENDENT_CURRENT_MISSINGNESS_DEFECT_AND_B_SCOPE_REVIEW',website_source_bindings=bindings,
  website_fixtures=outputs,website_actual_historical_contamination_count=None,
  website_contamination_dependency='Original precompaction source statistics with key-presence/null/zero provenance for each affected historical player/game/statistic, bound to original offers and grade versions. Compacted absent fields alone cannot recover it.',
  B_saved_original_source_presence=dict(source_rows_total=len(rr),original_selected=len(selected),decided=len(decided),unknown_selected=len(selected)-len(decided),
     required_component_presence=dict(fields),zero_actuals_with_explicit_raw_components=zero_outcomes,original_wins=205,original_losses=210,original_hit_rate=205/415,
     over=dict(wins=109,losses=128,decided=237,hit_rate=109/237),under=dict(wins=96,losses=82,decided=178,hit_rate=96/178),
     always_under_same_pool=dict(wins=224,losses=191,decided=415,hit_rate=224/415),
     grade_source_sha256=sha(gradespath),raw_label_source_sha256=sha(sourcepath),representative_boundary_checks=examples,
     direct_website_compaction_contamination_demonstrated=False),
  B_path='tools/acquire_week8_grading_sources.py -> retained NFLverse CSV + ESPN finality -> tools/grade_saved_week8.py Labels.label -> tools/abc_b_local_saved_replay.py current final CSV refresh -> full_provider_prop_replay.grade -> saved rows',
  B_limits='Source/source-completeness and historical revisions remain distinct from explicit local cell presence. This check does not certify every source, identity, forecast model or season, and does not establish missing-stat zero semantics for unretained feeds.',
  source_ref_observation=json.loads((a.snapshots/'WEBSITE_CURRENT_REF_OBSERVATION.json').read_bytes()),
  fits=0,model_inference=0,new_NFL_grades=0,upstream_writes=0,synthetic_grades_are_not_NFL_accuracy=True)
 if a.output.exists():raise FileExistsError(a.output)
 a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(state=result['state'],B_decided=len(decided),sha256=sha(a.output))))
if __name__=='__main__':main()
