"""Saved-row paired D2-minus-D1 tests; no refits or new univariate views."""
import argparse,collections,csv,gzip,hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from nfl_v2.shared_subgroups import paired,identity,sha,write,digest,now

def run(public_root,private_root):
 public_root,private_root=map(Path,(public_root,private_root));panels=collections.defaultdict(lambda:collections.defaultdict(dict));sources=[]
 for path in sorted(public_root.glob('W0[1-7]-*-FORECAST.json')):
  receipt=json.loads(path.read_bytes());p=receipt['packet'];file=private_root/p['bundle_name']
  if sha(file)!=p['sha256']:raise ValueError('retained chunk changed')
  sources.append(dict(receipt_artifact=path.name,receipt_sha256=sha(path),prediction_sha256=p['sha256']))
  for raw in json.loads(gzip.decompress(file.read_bytes()))['rows']:
   if int(raw['season'])!=2026 or not 1<=int(raw['week'])<=7:raise ValueError('only frozen historical panel permitted')
   r={k:raw[k]for k in('game_id','player_id','target','population','position','week','procedure_id','history_regime','policy_id','product_id','prediction','actual','fallback')};r['distribution_summary']=raw['distribution_summary']if raw['product_id']in('mean','event_probability')else None
   group=raw['information_group'];k=tuple(raw[f]for f in('target','population','product_id','policy_id'));i=identity(raw)
   if i in panels[k][group]:raise ValueError('duplicate retained group prediction')
   panels[k][group][i]=r
 output=[]
 for dims,groups in sorted(panels.items()):
  if set(groups)!={'D1','D2'}or set(groups['D1'])!=set(groups['D2']):raise ValueError('information groups differ in fixed query IDs')
  if any(groups['D1'][k]['actual']!=groups['D2'][k]['actual']for k in groups['D1']):raise ValueError('information group labels changed')
  target,pop,product,policy=dims;common={k for k in groups['D1']if all(groups[g][k]['fallback']=='none'for g in groups)}
  for view,keys in [('full_system',set(groups['D1'])),('paired_learned_overlap',common)]:
   rows=[groups['D2'][k]for k in sorted(keys)];metrics=['brier'if target=='anytime_td'else'mae']
   if target!='anytime_td'and product=='mean':metrics+=['crps','mse']
   for metric in metrics:
    c=paired(rows,groups['D1'],metric);c['cutoff_policy']='Identical ownfeatures/trainingmembers/fitwindow/featurememory/weeklyfits/pergamecutoffs/priors/fallback; D2addscompatible-exposurerategroup afterD1rawmean/coverage. Fixedforestrecipe; featurecompetition changes.'
    output.append(dict(record_id='DEFENSE-INFO-'+digest([dims,view,metric])[:24],target=target,population=pop,product_id=product,policy_id=policy,view=view,candidate_information_group='D2',comparator_information_group='D1',forecast_query_n=len(keys),**c))
 write(public_root/'INFORMATION_GROUP_PAIRED.json',dict(version='v2-qualified-defense-D2-versus-D1-paired-contrasts-v1',source_score_sha256=sha(public_root/'SCORES.json'),source_protocol_sha256=sha(public_root/'FROZEN_PROTOCOL.json'),code_sha256=sha(__file__),paired_helper_sha256=sha(Path(__file__).resolve().parents[1]/'nfl_v2/shared_subgroups.py'),source_chunks=sources,rows=output,artifact_kind='pairedcontrasts_only_notnewunivariate_scoreboard',new_fits=0,new_forecasts=0,week8_outcomes_read=0,completed_at_utc=now()))
 with(public_root/'INFORMATION_GROUP_PAIRED.csv').open('x',newline='')as f:
  fields=list(dict.fromkeys(k for r in output for k in r));w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows({k:json.dumps(v,sort_keys=True)if isinstance(v,(dict,list))else v for k,v in r.items()}for r in output)
 return dict(paired_contrasts=len(output),new_univariate_views=0,new_fits=0,new_forecasts=0)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--public-root',type=Path,required=True);p.add_argument('--private-root',type=Path,required=True);print(json.dumps(run(**vars(p.parse_args()))))
