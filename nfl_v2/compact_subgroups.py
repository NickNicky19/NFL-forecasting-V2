"""Finite fixed-recipe subgroup corrections; retained points only, no fitting."""
from __future__ import annotations
import collections,csv,gzip,json,math,resource,time
from pathlib import Path
from . import shared_subgroups as base,paired_uncertainty
from .shared_subgroups import canonical,sha,load,write,digest,now,identity,metrics,loss,C02,CHART
VERSION='v2-fixed-recipe-compact-subgroups-v3'

def normal(raw,year,kind='season'):
 if int(raw.get('season',2026))!=year or not 1<=int(raw['week'])<=(7 if year==2026 else 18):return None
 r={k:raw[k]for k in('game_id','player_id','target','population','position','history_regime','fallback')};r.update(season=year,week=int(raw['week']),procedure_id=raw.get('procedure_id')or('empirical-player-history-control-v1'if kind=='empirical'else'hgb-direct-history-controls-v1:'+raw['objective']),product_id=raw.get('product_id')or raw.get('product')or raw.get('objective'),policy_id=raw.get('policy_id'),prediction=base.number(raw.get('prediction')),actual=base.number(raw.get('actual')),distribution_summary=None)
 return r

def alias(spec):
 s=dict(spec)
 if s['procedure_id'].startswith('hgb-direct-history-controls-v1:')and not s['procedure_id'].endswith((':common-feature-memory',':strict-current-inputs')):s['procedure_id']+=':common-feature-memory'
 if s['procedure_id'].endswith(':empirical'):s['procedure_id']='empirical-player-history-control-v1'
 if s['procedure_id']=='empirical-player-history-control-v1':s['product_id']={'empirical_mean':'mean','empirical_lower_median':'lower_median'}.get(s['product_id'],s['product_id'])
 return s

def select_fixed(leader_file,year):
 with Path(leader_file).open()as f:rows=list(csv.DictReader(f))
 result={}
 for r in rows:
  if r['ranking_product']!='display_point'or r['rank']!='1':continue
  s=dict(target=r['target'],procedure_id=r['procedure_id'],history_regime=r['history_regime'],product_id=r['product'],reference='fixed_2026_control')
  if year!=2026:s=alias(s)
  result.setdefault(r['target'],s)
 return result

def select_season(scores):
 rs=[r for r in scores if r['week']=='ALL'and r['position']=='ALL'and r['fallback_view']=='ALL'and r['population']=='primary'and not r['procedure_id'].startswith(C02)];out={}
 for t in sorted({r['target']for r in rs}):
  candidates=[r for r in rs if r['target']==t];n=max(r['n']for r in candidates);metric='brier'if t=='anytime_td'else'mae';r=min((r for r in candidates if r['n']==n and r.get(metric)is not None),key=lambda r:(r[metric],r['procedure_id'],r['history_regime'],r['product_id']))
  out[t]=dict(target=t,procedure_id=r['procedure_id'],history_regime=r['history_regime'],product_id=r['product_id'],reference='same_season_strongest_control')
 return out

def key(r):return(r['target'],r['procedure_id'],r['history_regime'],r['product_id'])
def compare(rows,reference,target):
 metric='brier'if target=='anytime_td'else'mae';c=base.paired(rows,reference,metric)
 if c['status']=='PAIRED_RETAINED_ROWS':
  pairs=[(r,reference[identity(r)])for r in rows if identity(r)in reference and loss(r,metric)is not None and loss(reference[identity(r)],metric)is not None];c['uncertainty']=paired_uncertainty.paired_losses([loss(a,metric)for a,b in pairs],[loss(b,metric)for a,b in pairs],[a['week']for a,b in pairs],[a['game_id']for a,b in pairs])
 return c

def evaluate(candidates,references,members,p):
 # references[group,target,name][identity] is the exact retained comparator row.
 groups=collections.defaultdict(list);seen=set()
 for group,r in candidates:
  i=identity(r);k=group,i
  if k in seen or i not in members:raise ValueError('duplicate/outside frozen candidate query')
  seen.add(k);refs=[v for(g,t,name),v in references.items()if(g,t)==(group,r['target'])]
  if not refs:raise ValueError('missing registered reference')
  for lookup in refs:
   other=lookup.get(i)
   if other is None or(other['actual'],other['position'])!=(r['actual'],r['position']):raise ValueError('reference exact query/label/position mismatch')
  views=['full_system','own_learned_only'if r['fallback']=='none'else'fallback_only']
  if r['fallback']=='none'and r['prediction']is not None and r['actual']is not None and all(x[i]['fallback']=='none'and x[i]['prediction']is not None for x in refs):views.append('selected_candidate_and_controls_common_learned_overlap')
  for cohort in members[i]['cohorts']:
   for view in views:groups[group,r['target'],r['population'],cohort,view].append(r)
 scores=[];pairs=[];dates=[]
 for dims,rows in sorted(groups.items()):
  group,target,pop,cohort,view=dims;r=rows[0];rid='COMPACT-'+digest([VERSION,p['evaluation_season'],dims,r['procedure_id'],r['history_regime'],r['product_id']])[:24];scored=[r for r in rows if r['prediction']is not None and r['actual']is not None];cs=[]
  for(g,t,name),lookup in references.items():
   if(g,t)!=(group,target):continue
   c=compare(rows,lookup,target);pairs.append(dict(source_record_id=rid,reference_view=name,**c));cs.append((name,c))
  primary=next((c for name,c in cs if name in('same_season_strongest_control','fixed_strong_control')),cs[0][1]);m=metrics(rows,target,r['product_id'])
  scores.append(dict(record_id=rid,procedure_id=r['procedure_id'],procedure_family_id='ordered_leaf_cdf',recipe_group=group,target=target,population=pop,history_regime=r['history_regime'],policy_id=r.get('policy_id'),product_id=r['product_id'],cohort_id=cohort,fallback_view=view,season=p['evaluation_season'],week='ALL',position='ALL',evaluation_seasons=[p['evaluation_season']],evaluation_weeks=sorted({r['week']for r in scored}),evaluation_panel_id=VERSION+':'+p['mode']+':'+str(p['evaluation_season']),record_kind='NEW_EXPERIMENT_CURRENT_VINTAGE_PARTICIPANT_DIAGNOSTIC',evidence='NEW_EXPERIMENT',source_vintage='current_vintage_reconstruction',cohort_limit=p['cohort_limit'],cohort_protocol_sha256=p['protocol_sha256'],cohort_membership_sha256=digest(sorted(identity(r)for r in rows)),scored_membership_sha256=digest(sorted(identity(r)for r in scored)),comparison=primary,distribution_score_status='POINT_VIEW_REPLAY; properlaw/meanproductsremaininseparatelyregisteredfullmethodscoreartifact',**m))
  dates.append(dict(source_row_index=len(scores)-1,evaluation_seasons=[p['evaluation_season']],evaluation_weeks=scores[-1]['evaluation_weeks'],actual_scored_weeks=scores[-1]['evaluation_weeks'],forecast_query_weeks=sorted({r['week']for r in rows})))
 return scores,pairs,dates

def run(*,public_root,private_root):
 root,priv=Path(public_root),Path(private_root);p=load(root/'FROZEN_PROTOCOL.json');start=time.monotonic()
 if p['code_sha256']!=sha(__file__)or p['paired_helper_sha256']!=sha(paired_uncertainty.__file__)or p['base_helper_sha256']!=sha(base.__file__):raise ValueError('sealed compact code changed')
 for name,h in p['metric_helpers'].items():
  if sha(Path(__file__).with_name(name))!=h:raise ValueError('metric helper changed')
 for s in p['bindings']:
  if sha(priv/s['private_member'])!=s['sha256']:raise ValueError('source bytes changed')
 if load(root/'SOFTWARE_CHECKS.json')['code_sha256']!=sha(__file__):raise ValueError('exact code tests required')
 year=p['evaluation_season'];members={}
 for name in p['memberships']:
  for m in json.loads(gzip.decompress((priv/name).read_bytes())):
   k=tuple(m['key'])
   if k in members:raise ValueError('duplicate cohort identity')
   members[k]={k:v for k,v in m.items()if k!='key'}
 write(root/'EXECUTION_REGISTRATION.json',dict(version=VERSION,actual_started_at_utc=now(),protocol_sha256=sha(root/'FROZEN_PROTOCOL.json'),new_fits=0,new_forecasts=0,current2026_week8_outcomes_read=0))
 p['protocol_sha256']=sha(root/'FROZEN_PROTOCOL.json');choices=p['choices'];wanted={key(c):c['group']for c in choices};refspec=p['reference_specs'];need={key(s)for s in refspec};candidates=[];index=collections.defaultdict(dict)
 def admit(raw,kind='season'):
  if p['mode']=='season'and p.get('role_overlay')and kind=='season_base'and'qb-rb-specialization'in raw['procedure_id']:return
  if int(raw.get('season',2026))!=year or int(raw['week'])>(7 if year==2026 else 18):return
  rawproc=raw.get('procedure_id')or('empirical-player-history-control-v1'if kind=='empirical'else'hgb-direct-history-controls-v1:'+raw['objective']);rawproduct=raw.get('product_id')or raw.get('product')or raw.get('objective')
  rawkey=(raw['target'],rawproc,raw['history_regime'],rawproduct)
  if rawkey not in wanted and rawkey not in need:return
  r=normal(raw,year,kind)
  if r is None:return
  k=key(r);i=identity(r)
  if k in wanted:candidates.append((wanted[k],r))
  if k in need:
   if i in index[k]:raise ValueError('duplicate comparator row')
   index[k][i]=r
  if p['mode']=='defense'and k in wanted:
   old=dict(r,procedure_id=raw['control_procedure_id'],prediction=raw['control_prediction'],fallback=raw['control_fallback']);index[wanted[k],r['target'],'same_leaf_control'][i]=old
 def guard():
  if time.monotonic()-start>p['budget']['wall_seconds']or resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024>p['budget']['max_peak_memory_bytes']:raise RuntimeError('COMPACT_REPLAY_BUDGET')
 for source in p['prediction_sources']:
  path=priv/source['private_member'];kind=source['kind']
  if source['format']=='csv':
   with gzip.open(path,'rt',newline='')as f:
    for raw in csv.DictReader(f):admit(raw,kind)
  else:
   for raw in base.packet_rows(path):admit(raw,kind)
  guard()
 references={}
 for s in refspec:
  references[s['group'],s['target'],s['reference']]=index.get(key(s),{})
 if p['mode']=='defense':
  for c in choices:references[c['group'],c['target'],'same_leaf_control']=index[c['group'],c['target'],'same_leaf_control']
 scores,pairs,dates=evaluate(candidates,references,members,p);guard()
 if len(scores)>p['budget']['max_score_views']:raise RuntimeError('COMPACT_SCORE_BUDGET')
 write(root/'SCORES.json',scores);write(root/'PAIRED_COMPARISONS.json',dict(source_score_sha256=sha(root/'SCORES.json'),rows=pairs));write(root/'SCORE_DATE_PROJECTION.json',dict(source_score_sha256=sha(root/'SCORES.json'),rows=dates))
 receipt=dict(version=VERSION,state='COMPLETE_FIXED_RECIPE_COMPACT_SUBGROUP_REPLAY',mode=p['mode'],evaluation_season=year,completed_at_utc=now(),protocol_sha256=sha(root/'FROZEN_PROTOCOL.json'),query_cells=len(members),candidate_retained_views=len(candidates),unique_games=len({r['game_id']for _,r in candidates}),unique_player_games=len({(r['game_id'],r['player_id'])for _,r in candidates}),score_views=len(scores),paired_comparison_views=len(pairs),score_sha256=sha(root/'SCORES.json'),comparison_sha256=sha(root/'PAIRED_COMPARISONS.json'),resource=dict(wall_seconds=time.monotonic()-start,peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,max_threads=1),new_fits=0,new_forecasts=0,current2026_week8_outcomes_read=0)
 write(root/'RUN_RECEIPT.json',receipt);return receipt
