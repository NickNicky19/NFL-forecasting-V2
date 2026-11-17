#!/usr/bin/env python3
"""Grade original retained forecasts against separately reconstructed later labels.

Never replaces original scorecards, implies complete zeros, or creates forecasts.
"""
import argparse,collections,csv,gzip,hashlib,json,pathlib,sys,time
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from nfl_v2.scoring import point_metrics,finite,valid_actual
from tools.replay_retained import role,dt,csvwrite
PANEL='2026-W7-original-forecasts-later-explicit-label-subset-v1'
def main():
 p=argparse.ArgumentParser();p.add_argument('--private-dir',type=pathlib.Path,required=True);p.add_argument('--output',type=pathlib.Path,required=True);a=p.parse_args()
 if a.output.exists():raise SystemExit('immutable output: use a new directory')
 started=time.monotonic();cpu=time.process_time()
 fb=(a.private_dir/'forecast.json.gz').read_bytes();lb=(a.private_dir/'outcomes-week7-later-explicit.json').read_bytes()
 f=json.loads(gzip.decompress(fb))['rows'];labels=json.loads(lb)
 if isinstance(labels,dict):labels=labels['rows']
 key=lambda r:(r['game_id'],r['player_id'],r['target'])
 lookup={key(o):o for o in labels};assert len(lookup)==len(labels)
 groups=collections.defaultdict(list);coverage=collections.defaultdict(collections.Counter);scored=[];seen=set()
 for r in f:
  k=key(r);fk=(r['model_id'],)+k;assert fk not in seen;seen.add(fk)
  o=lookup.get(k);state='missing_label' if o is None else o.get('participation_state','unknown')
  ok=dt(r['feature_cutoff_utc'])<=dt(r['issued_at'])<dt(r['kickoff_utc'])
  reason='scored' if state=='played' and valid_actual(r['target'],o.get('actual')) and finite(r.get('mean')) and ok else ('invalid_chronology' if not ok else 'missing_actual' if state=='played' else state)
  for pop in ['all_offered','primary_roles']:
   if pop=='primary_roles' and not role(r['target'],r['position']):continue
   g=(r['model_id'],r['target'],pop);coverage[g]['forecast_rows']+=1;coverage[g][reason]+=1;coverage[g]['fallback_rows']+=bool(r.get('fallback'))
   if reason=='scored':groups[g].append((r,o));coverage[g]['scored_fallback_rows']+=bool(r.get('fallback'))
  if reason=='scored':scored.append(dict(procedure_id=r['model_id'],**{x:r[x] for x in ['game_id','player_id','target','season','week','position']},prediction=r['mean'],actual=o['actual'],error=r['mean']-o['actual'],fallback=r.get('fallback')))
 results=[]
 for g,c in sorted(coverage.items()):
  pairs=groups[g];m=point_metrics([r['mean'] for r,o in pairs],[o['actual'] for r,o in pairs],g[1]);loss='brier' if g[1]=='anytime_td' else 'mae'
  results.append(dict(procedure_id=g[0],target=g[1],population=g[2],product_id='event_probability' if g[1]=='anytime_td' else 'conditional_played_mean',evaluation_panel_id=PANEL,evidence='NEW_LABEL_RECONSTRUCTION_SCORED',season=2026,week=7,unique_games=len({r['game_id'] for r,o in pairs}),unique_players=len({r['player_id'] for r,o in pairs}),**m,**c,primary_metric=loss,primary_loss=m.get(loss),limits='Later same-provider normalized snapshot; omitted zeros/identity-unverified rows unresolved; not representative fullpopulationskill',uncertainty='one_week_insufficient_clusters; no generalization interval claimed'))
 paired=[]
 for t in sorted({r['target'] for r in f}):
  for pop in ['all_offered','primary_roles']:
   maps=[{key(r):(r,o) for r,o in groups[(model,t,pop)]} for model in ['lab-v1.1-recent','lab-v1.1-pooled']];common=sorted(maps[0].keys()&maps[1].keys());diff=[];learned=[]
   for k in common:
    r,o=maps[0][k];s,q=maps[1][k];assert o['actual']==q['actual'];power=2 if t=='anytime_td' else 1
    d=abs(s['mean']-o['actual'])**power-abs(r['mean']-o['actual'])**power;diff.append(d)
    if not r.get('fallback') and not s.get('fallback'):learned.append(d)
   paired.append(dict(target=t,population=pop,n=len(common),games=len({k[0] for k in common}),metric='brier' if t=='anytime_td' else 'mae',delta_pooled_minus_recent=sum(diff)/len(diff) if diff else None,learned_only_n=len(learned),learned_only_delta=sum(learned)/len(learned) if learned else None,limits='Legacyrecipes not isolated fitwindowhistory; selected explicitvalue subset; insufficientweekclusters'))
 a.output.mkdir(parents=True);dump=lambda name,x:(a.output/name).write_text(json.dumps(x,indent=2,allow_nan=False)+'\n')
 dump('SCORES.json',results);csvwrite(a.output/'SCORES.csv',results);csvwrite(a.output/'PAIRED.csv',paired);csvwrite(a.private_dir/'later-label-scored-player-games.csv',scored)
 supported=[o for o in labels if o.get('participation_state')=='played' and valid_actual(o['target'],o.get('actual'))]
 receipt=dict(run_id='v2-week7-later-explicit-label-grading-v1',evaluation_panel_id=PANEL,forecast_sha256=hashlib.sha256(fb).hexdigest(),labels_sha256=hashlib.sha256(lb).hexdigest(),forecast_rows=len(f),forecast_games=len({r['game_id'] for r in f}),label_opportunities=len(labels),explicit_supported_target_outcomes=len(supported),supported_player_games=len({(o['game_id'],o['player_id']) for o in supported}),supported_games=len({o['game_id'] for o in supported}),scored_method_rows=len(scored),summary_cells=len(results),new_fits=0,new_forecasts=0,wall_seconds=time.monotonic()-started,cpu_seconds=time.process_time()-cpu,evidence_tier='originalrecordedforecasts; latercurrentvintageexplicitlabels, incompletezerosemantics; no newissuance',source_truth='sameprovider normalizedlabels, independentlymapped but not independentlyofficiallyauthenticated')
 dump('RECEIPT.json',receipt);print(json.dumps(receipt))
if __name__=='__main__':main()
