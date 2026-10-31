"""Register bounded saved-row additions and their source-bound reporting metadata."""
import argparse,collections,csv,hashlib,json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):
 body=json.dumps(v,separators=(',',':'),allow_nan=False)+'\n'
 if p.exists()and p.read_text()!=body:raise ValueError('immutable metadata exists with different bytes '+str(p))
 p.write_text(body)
def pkey(r):return(r['target'],r['procedure_id'],r['history_regime'],bool(r.get('strict_current_information')),tuple(r['evaluation_weeks']),r['fallback_view'],'brier')
def baseline_comparisons(source):
 rows=read(source);pairsfile=source.with_name('PAIRED_REFERENCE_COMPARISONS.json')
 if not pairsfile.exists():pairsfile=source.with_name('PAIRED_COMPARISONS.json')
 pairs=read(pairsfile);lookup={pkey(p)+(p['comparator'],):p for p in pairs if p['metric']=='brier'};ann=[]
 for i,r in enumerate(rows):
  c=dict(status='UNESTABLISHED',reason='Not a supported reference comparison; inspect retained original selected-side comparison sources.')
  if r.get('reference_id')and r['n']:
   candidate=r['matched_candidate_procedure_id'];key=(r['target'],candidate,r['history_regime'],bool(r.get('strict_current_information')),tuple(r['evaluation_weeks']),r['fallback_view'],'brier');bname='B1'if r['reference_id']=='B1'else'B0';names=(bname,'B1_EARLIER_SAME_POSITION_PREVALENCE'if bname=='B1'else'B0_CONSTANT_HALF_NO_PUSH');pair=next(lookup[key+(n,)]for n in names if key+(n,)in lookup);reverse=r['reference_id']!='candidate';candidate_error=pair['comparator_error']if reverse else pair['candidate_error'];comp_error=pair['candidate_error']if reverse else pair['comparator_error']
   assert math.isclose(candidate_error,r['brier'],abs_tol=1e-12)and pair['n']==r['n']and pair['membership_sha256']==r['membership_sha256']
   uncertainty=dict(pair)
   if reverse:
    uncertainty['delta']=-pair['delta'];uncertainty['candidate_error'],uncertainty['comparator_error']=candidate_error,comp_error
    for k in('game_normal95_sensitivity','week_interval'):
     v=pair.get(k);uncertainty[k]=None if v is None else[-v[1],-v[0]]
    uncertainty['weekly_paired_sums_counts']={k:dict(v,loss_difference_sum=-v['loss_difference_sum'])for k,v in pair['weekly_paired_sums_counts'].items()};uncertainty['interpretation']='Sign reversal of retained exact candidate-minus-reference paired differences; not a new NFL scoring run.'
   comp_proc=candidate+':known-target-time-v1'if reverse else'B0_CONSTANT_HALF_NO_PUSH:matched-to:'+candidate
   c=dict(status='PAIRED_RETAINED_ROWS',metric='brier',paired_n=r['n'],candidate_error=candidate_error,comparator_error=comp_error,comparator_procedure_id=comp_proc,comparator_history_regime=r['history_regime'],comparator_product_id='actual_line_categorical_law',membership_sha256=pair['membership_sha256'],uncertainty=uncertainty,paired_source_artifact=pairsfile.relative_to(ROOT).as_posix(),paired_comparison_id=pair['comparison_id'])
  ann.append(dict(source_row_index=i,comparison=c))
 path=source.with_name('INDEX_REFERENCE_COMPARISON_ANNOTATIONS_V1.json');write(path,dict(source_score_sha256=sha(source),identity='source_row_index',semantics='Existing exact paired Brier comparisons; reference rows reverse candidate-minus-reference direction. Original scores/paired rows preserved.',rows=ann));return path

def coverage_rows(source):
 folder=source.parent;j=folder/'MASK_AND_OUTER_COVERAGE.json';c=folder/'MASK_AND_OUTER_COVERAGE.csv';records=read(j)if j.exists()else list(csv.DictReader(c.open()));scores=read(source);byid={r['record_id']:r for r in scores};full={}
 for r in records:
  s=byid[r['record_id']];key=(s['target'],s['matched_candidate_procedure_id'],s['history_regime'],bool(s['strict_current_information']),tuple(s['evaluation_weeks']));full[key]=r
 out=[]
 for i,r in enumerate(scores):
  if r['record_kind']!='prop_threshold_probability_evaluation':continue
  k=(r['target'],r['matched_candidate_procedure_id'],r['history_regime'],bool(r['strict_current_information']),tuple(r['evaluation_weeks']));v=full[k];outer=int(v['outer_source_offer_universe']);admitted=int(v['admitted_law_rows']);nfull=int(v.get('qualified_probability_and_outcome_mask',v.get('qualified_mask_n')));cov=dict(outer_offer_universe=outer,matched_candidate_admitted_law_rows=admitted,candidate_full_qualified_mask_n=nfull,qualified_mask_n=r['n'],mask_over_outer_offer_fraction=r['n']/outer if outer else None,candidate_origin_scope=r['fallback_view'],coverage_note='Availability counts describe the matched candidate law. B0/B1 evaluated on the identical mask; this is not an assertion that a constant reference could not predict outside it. FULL is full qualified law/outcome mask, not all offers.',source_coverage_artifact=(j if j.exists()else c).relative_to(ROOT).as_posix(),source_coverage_sha256=sha(j if j.exists()else c));out.append(dict(source_artifact=source.relative_to(ROOT).as_posix(),source_artifact_sha256=sha(source),source_row_index=i,record_id=r['record_id'],outer_offer_coverage=cov))
 return out

def main(folder):
 groups=collections.defaultdict(dict);inputs=[];paths=sorted(folder.glob('actual-method-w5/method-comparison-v1/metadata-and-control-k-v1/*ANNOTATIONS.json'))+[folder/'actual-method-w5/COMPLETE_LEAF_LAW_ORIGIN_ANNOTATIONS.json'];digests={}
 for p in paths:
  data=read(p);inputs.append(dict(path=p.relative_to(ROOT).as_posix(),sha256=sha(p),rows=len(data)))
  for r in data:
   source=r['source_artifact'];i=r['source_row_index'];g=groups[source].setdefault(i,dict(source_row_index=i,record_id=r['record_id']));assert g['record_id']==r['record_id'];digests.setdefault(source,sha(ROOT/source));assert digests[source]==r['source_artifact_sha256']
   for k in('precision_counts','probability_scores'):
    if k in r:g[k]=r[k]
   if 'actual_source_fallback_count'in r:g['law_origin_counts']={k:v for k,v in r.items()if k not in('source_artifact','source_artifact_sha256','source_row_index','record_id')}
   if 'admitted_rule_abstentions'in r:g['denominators']={k:v for k,v in r.items()if k not in('source_artifact','source_artifact_sha256','source_row_index','record_id')}
 scores=sorted(folder.rglob('*SCORES.json'));comparisons={}
 for p in scores:
  if p.parent.parent.name=='probability':
   comparisons[p.relative_to(ROOT).as_posix()]=baseline_comparisons(p).relative_to(ROOT).as_posix()
   for r in coverage_rows(p):groups[r['source_artifact']].setdefault(r['source_row_index'],dict(source_row_index=r['source_row_index'],record_id=r['record_id']))['outer_offer_coverage']=r['outer_offer_coverage']
 projections={};bindings=[]
 for source,data in sorted(groups.items()):
  p=(ROOT/source).with_name('CURRENT_REPORTING_ANNOTATIONS_H_V1.json');write(p,dict(source_score_sha256=sha(ROOT/source),semantics='Source-bound denominator/precision/selected-probability/origin/outer-mask metadata; no prediction or loss changes.',rows=[data[i]for i in sorted(data)]));projections[source]=p.relative_to(ROOT).as_posix();bindings.append(dict(source_artifact=source,projection=projections[source],sha256=sha(p),rows=len(data)))
 write(folder/'REPORTING_ANNOTATION_MANIFEST.json',dict(state='SOURCE_BOUND_METADATA_NO_NEW_SCORES',inputs=inputs,bindings=bindings))
 registry=ROOT/'registries/RESULT_ARTIFACTS.json';items=read(registry);known={r['artifact']for r in items};manifest=[];counts=collections.Counter();scopefix=0
 for p in scores:
  rel=p.relative_to(ROOT).as_posix();data=read(p);assert data and len({r['record_id']for r in data})==len(data);manifest.append(dict(path=rel,sha256=sha(p),rows=len(data)));counts.update(r['record_kind']for r in data)
  if rel in known:continue
  item=dict(artifact=rel,state='SCORED',kind='new_qualified_week_or_same_mask_reference_comparison',version_note='NewW5scope or earlier-only probability references/cached cumulative views. B0/B1 are two mechanisms; matched-to IDs are masks. FULL probability view is the qualified comparison mask, with outer offers explicit. No new fits or issuance.')
  if rel in projections:item['reporting_annotations']=projections[rel]
  for field,name in [('selection_metadata_projection','METADATA_SUPPLEMENT.json'),('comparison_annotations','COMPARISON_ANNOTATIONS.json')]:
   q=p.with_name(name)
   if q.exists():item[field]=q.relative_to(ROOT).as_posix()
  if rel in comparisons:item['comparison_annotations']=comparisons[rel]
  if item.get('comparison_annotations'):
   q=ROOT/item['comparison_annotations'];ann=read(q);assert ann['source_score_sha256']==sha(p);byid={r['record_id']:r for r in data};fixed=0
   for a in ann['rows']:
    c=a['comparison']
    if c.get('status')!='PAIRED_RETAINED_ROWS':continue
    r=data[a['source_row_index']]if'source_row_index'in a else byid[a['source_record_id']];loss=r.get(c['metric']);same=c['paired_n']==r['n']and loss is not None and math.isclose(c['candidate_error'],loss,abs_tol=1e-10,rel_tol=1e-10)
    if not same:
     assert 0<c['paired_n']<=r['n'];c.update(status='PAIRED_SUBSET_RETAINED_ROWS',complete_scored_view_n=r['n'],comparison_scope='Exact paired common subset; not the complete selected view. Preserve both scored and paired denominators.');fixed+=1
   if fixed:
    dest=q.with_name('INDEX_COMPARISON_SCOPE_CORRECTION_V1.json');ann['previous_annotation_sha256']=sha(q);write(dest,ann);item['comparison_annotations']=dest.relative_to(ROOT).as_posix();scopefix+=fixed
  items.append(item)
 registry.write_text(json.dumps(items,indent=2)+'\n');write(folder/'NEW_CANONICAL_SCORE_MANIFEST.json',dict(state='REGISTERED_APPEND_ONLY',sources=manifest,views=sum(r['rows']for r in manifest),by_kind=dict(counts),comparison_scope_disclosures=scopefix,new_fits=0,new_issued_forecasts=0));print(json.dumps(dict(sources=len(manifest),views=sum(r['rows']for r in manifest),scope_disclosures=scopefix)))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True);main(p.parse_args().directory.resolve())
