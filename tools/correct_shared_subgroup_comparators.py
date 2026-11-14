"""Append a pre-C02 comparator correction; preserve every v1 score/source byte."""
import argparse,csv,gzip,json,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from nfl_v2 import shared_subgroups as s
VERSION='v2-shared-subgroup-pre-c02-comparator-correction-v1'

def prepare(private_root,original_public,public_root,leader_file):
 private_root,original_public,public_root,leader_file=map(Path,(private_root,original_public,public_root,leader_file))
 if public_root.exists():raise ValueError('fresh output required')
 old=s.load(original_public/'FROZEN_PROTOCOL.json')
 if old['code_sha256']!=s.sha(s.__file__):raise ValueError('original scorer changed')
 specs=s.selected_specs(leader_file)
 if any(x['procedure_id'].startswith(s.C02)for x in specs):raise ValueError('pre-C02 controls must exclude candidate')
 public_root.mkdir(parents=True)
 p=dict(version=VERSION,registered_at_utc=s.now(),code_sha256=s.sha(__file__),original_scorer_sha256=s.sha(s.__file__),source_protocol_sha256=s.sha(original_public/'FROZEN_PROTOCOL.json'),source_score_sha256=s.sha(original_public/'SCORES.json'),old_comparison_sha256=s.sha(original_public/'PAIRED_COMPARISONS.json'),leader_artifact=leader_file.as_posix(),leader_sha256=s.sha(leader_file),comparators=specs,correction_reason='30bTOP5 containsC02itself; originalv1sidecarunestablishedselfreferences. ReplacecomparatorselectionswithfrozenpreC0230TOP5; neverinterpretmissingaswin. Recomputeallunivariatesandmasks, requireexactequalitybeforeoldviewsreused.',budget=old['budget'],new_fits=0,new_forecasts=0,week8_outcomes_read=0)
 s.write(public_root/'FROZEN_PROTOCOL.json',p);return p

def run(private_root,original_public,public_root):
 private_root,original_public,public_root=map(Path,(private_root,original_public,public_root));start=time.monotonic();p=s.load(public_root/'FROZEN_PROTOCOL.json');old=s.load(original_public/'FROZEN_PROTOCOL.json')
 for k,path in [('code_sha256',__file__),('original_scorer_sha256',s.__file__),('source_protocol_sha256',original_public/'FROZEN_PROTOCOL.json'),('source_score_sha256',original_public/'SCORES.json'),('old_comparison_sha256',original_public/'PAIRED_COMPARISONS.json'),('leader_sha256',p['leader_artifact'])]:
  if s.sha(path)!=p[k]:raise ValueError('registered correction source changed')
 for b in old['source_bindings']:
  if s.sha(private_root/s.FILES[b['artifact_id']][0])!=b['sha256']:raise ValueError('original bytes changed')
 s.write(public_root/'EXECUTION_REGISTRATION.json',dict(version=VERSION,actual_started_at_utc=s.now(),protocol_sha256=s.sha(public_root/'FROZEN_PROTOCOL.json'),new_fits=0,new_forecasts=0,week8_outcomes_read=0))
 member={}
 for aid in('football_membership','chart_membership'):
  for m in json.loads(gzip.decompress((private_root/s.FILES[aid][0]).read_bytes())):member[tuple(m['key'])]={k:v for k,v in m.items()if k!='key'}
 candidates=[r for x in s.packet_rows(private_root/s.FILES['candidate'][0])if(r:=s.normalize(x,'candidate'))is not None]
 need={(r['procedure_id'],r['history_regime'],r['product_id'])for r in p['comparators']};controls=[]
 for aid in('football_laws','chart_controls','empirical','count_role'):
  with gzip.open(private_root/s.FILES[aid][0],'rt',newline='')as f:
   for raw in csv.DictReader(f):
    if int(raw.get('season',2026))!=2026 or not 1<=int(raw['week'])<=7:continue
    r=s.normalize(raw,aid)
    if s.modelkey(r)in need or 'ordered_leaf_cdf:'in r['procedure_id']:controls.append(r)
 for b in old['hgb_chunk_bindings']:
  path=private_root/'hgb-history-v1/prediction-chunks'/b['artifact_id']
  if s.sha(path)!=b['sha256']:raise ValueError('original HGB changed')
  for raw in s.packet_rows(path):
   r=s.normalize(raw,'hgb')
   if r is not None and s.modelkey(r)in need:controls.append(r)
 if len(candidates)+len(controls)>p['budget']['max_prediction_rows']:raise RuntimeError('ROW_BUDGET')
 scores,comp,dates,overlap=s.evaluate(candidates,controls,member,s.sha(original_public/'FROZEN_PROTOCOL.json'),p['comparators'])
 original=s.load(original_public/'SCORES.json')
 if scores!=original:
  changes=[dict(source_record_id=a['record_id'],changed_fields=[k for k in set(a)|set(b)if a.get(k)!=b.get(k)])for a,b in zip(original,scores)if a!=b]
  s.write(public_root/'UNIVARIATE_MASK_DIFFERENCES.json',dict(old_n=len(original),new_n=len(scores),changes=changes));raise ValueError('mask or metric changed; old views cannot silently reused')
 if time.monotonic()-start>p['budget']['wall_seconds']or len(comp)>p['budget']['max_comparison_rows']:raise RuntimeError('CORRECTION_BUDGET')
 s.write(public_root/'PAIRED_COMPARISONS.json',dict(source_score_artifact=(original_public/'SCORES.json').as_posix(),source_score_sha256=p['source_score_sha256'],supersedes_comparison_sha256=p['old_comparison_sha256'],rows=comp))
 s.write(public_root/'UNIVARIATE_REUSE_VERIFICATION.json',dict(status='EXACT_REPRODUCTION',source_score_sha256=p['source_score_sha256'],score_views=len(scores),all_values_masks_primary_comparisons_equal=True,source_protocol_sha256=p['source_protocol_sha256'],new_univariate_views=0,shared_learned_query_counts=overlap))
 result=dict(version=VERSION,state='COMPLETE_COMPARATOR_CORRECTION',actual_completed_at_utc=s.now(),reused_score_views=len(scores),new_univariate_score_views=0,paired_comparison_views=len(comp),candidate_views=len(candidates),control_reference_views=len(controls),score_sha256=p['source_score_sha256'],comparison_sha256=s.sha(public_root/'PAIRED_COMPARISONS.json'),protocol_sha256=s.sha(public_root/'FROZEN_PROTOCOL.json'),wall_seconds=time.monotonic()-start,new_fits=0,new_forecasts=0,week8_outcomes_read=0)
 s.write(public_root/'RUN_RECEIPT.json',result);return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=('prepare','run'));p.add_argument('--private-root',type=Path,required=True);p.add_argument('--original-public',type=Path,required=True);p.add_argument('--public-root',type=Path,required=True);p.add_argument('--leader-file',type=Path)
 a=vars(p.parse_args());action=a.pop('action')
 if action=='run':a.pop('leader_file')
 print(json.dumps((prepare if action=='prepare'else run)(**a)))
