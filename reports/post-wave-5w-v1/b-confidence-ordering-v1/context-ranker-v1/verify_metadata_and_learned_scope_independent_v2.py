"""Append-only metadata and actual learned-output mask checks; no refits/rescores."""
import argparse,collections,gzip,hashlib,json
from datetime import datetime,timezone
from pathlib import Path
def load(p):
    b=p.read_bytes();return json.loads(gzip.decompress(b)if p.suffix=='.gz'else b)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(private,out):
    old=load(out/'SCORES_PRE_METADATA_QUALIFICATION_V1.json');new=load(out/'SCORES.json');q=load(out/'METADATA_QUALIFICATION_V2.json');prior=load(out/'INDEPENDENT_CONTEXT_RANKER_AUDIT_V1.json');rows=load(private/'MODELS_AND_SELECTION_ROWS.json.gz')['rows'];assert sha(out/'SCORES_PRE_METADATA_QUALIFICATION_V1.json')==prior['scores_sha256']==q['original_source_scores']['sha256']and sha(out/'SCORES.json')==q['current_scores']['sha256'];assert len(old)==804 and len(new)==816;learned=[];changed=collections.Counter()
    def pool(s,strict=False):
        arm=int(s['procedure_id'].split('::G')[1][0]);policy=s.get('parent_policy',s['strategy']);rr=[r for r in rows if r['target']==s['target']and r['method_key'].endswith('G'+str(arm))and r['selection_policy']==policy and(str(s['week'])=='ALL'or r['week']==int(s['week']))]
        if s['cohort_id']in('FITTED_RANKER_ORIGINS_INCLUDING_UNAVAILABLE_BASE','COMMON_LEARNED_RANKER_OUTPUT_ROWS'):rr=[r for r in rr if not r['ranker_identity_fallback']]
        if strict:rr=[r for r in rr if r['probabilities']is not None and r['rank_score']is not None]
        if '::MATCHED_'in s['procedure_id']:rr=[r for r in rr if r['selected_side']]
        return rr
    added={'score_version_state','source_score_sha256_before_metadata_qualification','cohort_scope_qualification'}
    for o,n in zip(old,new):
        assert o['record_id']==n['record_id']and n['evidence']=='NEW_EXPERIMENT';oo=dict(o);nn={k:v for k,v in n.items()if k not in added};oo['evidence']='NEW_EXPERIMENT'
        if o['cohort_id']=='COMMON_LEARNED_RANKER_ROWS':assert n['cohort_id']=='FITTED_RANKER_ORIGINS_INCLUDING_UNAVAILABLE_BASE';oo['cohort_id']=n['cohort_id'];changed['renamed_fitted_origin_views']+=1
        om=dict(oo['selection_metrics']);nm=dict(nn['selection_metrics']);rr=pool(n);unavailable=sum(r['probabilities']is None and r.get('fallback')in(None,'NOT_RETAINED')for r in rr);admitted=sum(r['probabilities']is not None and r.get('fallback')in(None,'NOT_RETAINED')for r in rr)
        assert nm['unavailable_base_with_unknown_fallback']==unavailable and nm['admitted_base_with_unknown_fallback']==admitted and nm['fallback_status_unknown']==unavailable+admitted
        assert nm['fallback_status_unknown_scope']=='WHOLE_THIS_VIEW_ELIGIBLE_POOL;NOT_KNOWN_NONFALLBACK_WHEN_BASE_MISSING';changed['fallback_count_corrected_views']+=int(om['fallback_status_unknown']!=nm['fallback_status_unknown'])
        om['fallback_status_unknown']=nm['fallback_status_unknown']
        for k in('unavailable_base_with_unknown_fallback','admitted_base_with_unknown_fallback','fallback_status_unknown_scope'):nm.pop(k)
        assert om==nm;oo['selection_metrics']=om;nn['selection_metrics']=nm;assert oo==nn
    for s in new[804:]:
        assert s['cohort_id']=='COMMON_LEARNED_RANKER_OUTPUT_ROWS'and s['evidence']=='NEW_EXPERIMENT_SAVED_ROW_QUALIFIED_COMMON_LEARNED_PROJECTION';rr=pool(s,strict=True);ss=[r for r in rr if r['selected_side']and(s['side']=='Combined'or r['selected_side']==s['side'])];c=collections.Counter(r['statistical_state']for r in ss);assert(s['forecast_rows'],s['n'],s['selection_metrics']['WIN'],s['selection_metrics']['LOSS'])==(len(ss),c['WIN']+c['LOSS'],c['WIN'],c['LOSS']);assert s['selection_metrics']['selection_pool_count']==len(rr)and s['selection_metrics']['technical_unavailable']==0
        assert s['evaluation_weeks']==sorted({r['week']for r in rr})
        if s['side']=='Combined':learned.append(dict(target=s['target'],arm=int(s['procedure_id'][-1]),eligible_output_rows=len(rr),selected=len(ss),wins=c['WIN'],losses=c['LOSS'],actual_positive_scored_weeks=sorted({r['week']for r in ss if r['statistical_state']in('WIN','LOSS','PUSH')}),membership_hash=hashlib.sha256(json.dumps(sorted(r['offer_id']for r in rr),separators=(',',':')).encode()).hexdigest()))
    for t in('rec','pass_td'):
        ll=[r for r in learned if r['target']==t];assert len(ll)==2 and ll[0]['membership_hash']==ll[1]['membership_hash'];assert all(len(r['actual_positive_scored_weeks'])==1 for r in ll)
    result=dict(state='PASS_METADATA_ONLY_CORRECTION_AND_TRUE_COMMON_LEARNED_MASK',at_utc=datetime.now(timezone.utc).isoformat(),verification_code_sha256=sha(Path(__file__)),metadata_qualification_sha256=sha(out/'METADATA_QUALIFICATION_V2.json'),preserved_original_scores_sha256=sha(out/'SCORES_PRE_METADATA_QUALIFICATION_V1.json'),current_scores_sha256=sha(out/'SCORES.json'),original804_numeric_choice_probability_and_status_fields_preserved=True,allowed_metadata_changes=dict(changed),new_saved_row_views_checked=12,true_common_learned=learned,refits=0,new_grades=0,new_NFL_observations=0,limits=['Renamed fitted-origin views may include unavailable base laws; strict learned-output views require both actual base probabilities and ranking outputs. These are separate scopes.','All whole-view unknown fallback counts now include missing None metadata; conditional constants remain on the original selected mask.','Learned-output evidence is one rec week and one PT week; it does not satisfy the exact-policy five-week floor.'])
    (out/'INDEPENDENT_METADATA_AND_LEARNED_SCOPE_V2.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('private',type=Path);p.add_argument('out',type=Path);a=p.parse_args();run(a.private,a.out)
