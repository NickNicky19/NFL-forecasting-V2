"""Primitive Decimal threshold/mask/paired arithmetic; no project scorer imports."""
import argparse,collections,gzip,hashlib,json,math
from datetime import datetime,timezone
from decimal import Decimal
from pathlib import Path
MASK='cd315248b591579c11060d611ef4006a29e2848a811a30f526e3d9727f990d85'
def load(p):
    b=p.read_bytes();return json.loads(gzip.decompress(b)if p.suffix=='.gz'else b)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def utc(v):return float(v)if isinstance(v,(int,float))else datetime.fromisoformat(v.replace('Z','+00:00')).timestamp()
def decimal(v):return Decimal(str(v))
def close(a,b):return a==b or(a is not None and b is not None and abs(a-b)<1e-10)
def chosen(r):return None if r['prediction']is None or decimal(r['prediction'])==decimal(r['line'])else'over'if decimal(r['prediction'])>decimal(r['line'])else'under'
def grade(r,side=None):
    if r.get('prediction','NO_POINT_FIELD')is None:return'UNAVAILABLE_FORECAST'
    side=chosen(r)if side is None else side
    if side is None:return'ABSTAIN'
    if r.get('participation','VERIFIED_PLAYED_POSITIVE_PHYSICAL')!='VERIFIED_PLAYED_POSITIVE_PHYSICAL':return'UNKNOWN_PARTICIPATION'
    if r['actual']is None:return'MISSING_ACTUAL'
    y,l=decimal(r['actual']),decimal(r['line']);return'PUSH'if y==l else'WIN'if((y>l)==(side=='over'))else'LOSS'
def view(rr,w):return[r for r in rr if str(w)=='ALL'or r['week']==int(w)]
def run(private,csnapshot,maskpath,out):
    protocol=load(out/'FROZEN_PACKAGE.json');receipt=load(out/'RUN_RECEIPT.json');assert sha(out/'FROZEN_PACKAGE.json')==receipt['source_protocol_sha256'];assert sha(maskpath)==protocol['source_public_mask_sha256'];mask=next(r for r in load(maskpath)if r['mask_id']==MASK);ids=set(mask['offer_ids']);assert len(ids)==len(mask['offer_ids'])==111 and hashlib.sha256(json.dumps(sorted(ids),separators=(',',':')).encode()).hexdigest()==MASK and mask['category']=='rush_yd'
    groups=collections.defaultdict(list);sourcehashes={}
    for n,b in zip(['B_OWNER_LOCAL_C_MATCHED_ROWS_V2.json.gz','B_OWNER_LOCAL_C_ADDITIONAL_ROWS_V3.json.gz'],protocol['source_rows']):
        p=private/n;assert sha(p)==b['sha256'];sourcehashes[b['safe_id']]=sha(p)
        for r in load(p)['rows']:
            if r['target']=='rush_yd':groups[r['method_key']].append(r)
    assert len(groups)==52 and all(len(rr)==181 and len({r['offer_id']for r in rr})==181 for rr in groups.values())
    cc=collections.defaultdict(dict);csourcehashes={}
    for n in ['reports/propline-v7/GRADED_ROWS.json','reports/propline-v7/CORRECTIONS_GRADED_ROWS_V7_1.json','artifacts/reliability-v8/PREVALENCE_GRADED_ROWS.json.gz']:
        p=csnapshot/n;csourcehashes[n]=sha(p)
        for r in load(p)['rows']:
            if r['offer_id']not in ids:continue
            assert r['position']=='RB'and r['category']=='rush_yd'and r['venue']=='pinnacle'and r['selected_side']in('OVER','UNDER');assert r['offer_id']not in cc[r['method_id']];cc[r['method_id']][r['offer_id']]=r
    assert set(cc)==set(mask['C_controls'])and all(set(rr)==ids for rr in cc.values())
    for name,rr in cc.items():
        counts={s:collections.Counter()for s in('OVER','UNDER','COMBINED')}
        for r in rr.values():
            state=grade(r,r['selected_side'].lower());assert state==r['status'];counts[r['selected_side']][state]+=1;counts['COMBINED'][state]+=1
            if name=='EARLIER_PREVALENCE_V8'and r.get('latest_training_available')is not None:assert utc(r['latest_training_available'])<utc(r['fit_origin_UTC'])<=utc(r['decision_UTC'])
        for side,c in counts.items():
            s=mask['C_controls'][name][side];n=c['WIN']+c['LOSS'];assert s['decided']==n and s['wins']==(c['WIN']if n else None)and s['losses']==(c['LOSS']if n else None)and close(s['rate'],c['WIN']/n if n else None)
    base=cc['P3_DIRECT'];clockchecks=0;identitychecks=0;owncoverage=collections.Counter()
    for method,rr in groups.items():
        owncoverage[len(rr),sum(r['prediction']is not None for r in rr),sum(r['prediction']is None for r in rr)]+=1
        common=[r for r in rr if r['offer_id']in ids];assert len(common)==111
        for r in common:
            c=base[r['offer_id']];assert r['position']=='RB'and (r['game_id'],r['player_id'],r['week'],r['target'],decimal(r['line']),decimal(r['actual']))==(c['game_id'],c['player_id'],c['week'],c['category'],decimal(c['line']),decimal(c['actual']));identitychecks+=1
            assert r['selected_side']==chosen(r)and r['statistical_state']==grade(r);assert utc(r['decision_time'])==utc(c['decision_UTC'])and utc(r['kickoff'])==utc(c['kickoff_UTC'])and r['forecast_cutoff']<=utc(r['decision_time']);assert r['latest_feature_available']is None or r['latest_feature_available']<r['forecast_cutoff'];assert r['prediction']is not None;clockchecks+=1
    scores=load(out/'SCORES.json');triads=collections.defaultdict(dict)
    for s in scores:
        pool=view([r for r in groups[s['procedure_id']]if r['offer_id']in ids],s['week']);ss=[r for r in pool if chosen(r)and(s['side']=='Combined'or chosen(r)==s['side'])];c=collections.Counter(grade(r)for r in ss);m=s['selection_metrics'];n=c['WIN']+c['LOSS'];assert(s['forecast_rows'],s['n'],m['WIN'],m['LOSS'],m['PUSH'])==(len(ss),n,c['WIN'],c['LOSS'],c['PUSH']);assert m['selection_pool_count']==len(pool)and m['hit_rate']==(c['WIN']/n if n else None)
        for k,v in m['status_counts'].items():assert v==c[k]
        assert m['technical_unavailable']==sum(r['prediction']is None for r in pool)and m['admitted_rule_abstentions']==sum(r['prediction']is not None and chosen(r)is None for r in pool);assert m['fallback_issued']==sum(r['fallback']not in('none',None,False,'NOT_RETAINED')for r in pool)and m['fallback_status_unknown']==sum(r['fallback']in(None,'NOT_RETAINED')for r in pool)
        for label,match in [('learned_only_contribution',lambda r:r['fallback']in('none',False)),('fallback_only_contribution',lambda r:r['fallback']not in('none',None,False,'NOT_RETAINED'))]:
            eligible=[r for r in pool if match(r)];selected=[r for r in ss if match(r)];counts=collections.Counter(grade(r)for r in selected);z=m[label];assert(z['eligible'],z['selected'],z['wins'],z['losses'],z['decided'])==(len(eligible),len(selected),counts['WIN'],counts['LOSS'],counts['WIN']+counts['LOSS']);assert close(z['hit_rate'],counts['WIN']/(counts['WIN']+counts['LOSS'])if counts['WIN']+counts['LOSS']else None)
        errors=[r['prediction']-r['actual']for r in ss if grade(r)in('WIN','LOSS','PUSH')];assert close(math.fsum(map(abs,errors))/len(errors)if errors else None,s['mae'])and close(math.fsum(errors)/len(errors)if errors else None,s['bias']);assert s['default_rank_eligible']is False and s['mask_id']==MASK and s['role_scope']=='RB_ONLY';triads[s['procedure_id'],str(s['week'])][s['side']]=s
    assert len(scores)==468 and len(triads)==156
    for v in triads.values():
        assert set(v)=={'over','under','Combined'}
        for key in('WIN','LOSS','PUSH'):assert v['Combined']['selection_metrics'][key]==sum(v[side]['selection_metrics'][key]for side in('over','under'))
        for key in('n','forecast_rows'):assert v['Combined'][key]==sum(v[side][key]for side in('over','under'))
    paired=load(out/'PAIRED_CONTROLS.json');maximumdiff=[]
    for p in paired:
        rr=view([r for r in groups[p['procedure_id']]if r['offer_id']in ids],p['week_view']);cr=cc[p['control_id']];common=[(r,cr[r['offer_id']])for r in rr if grade(r)in('WIN','LOSS')and grade(cr[r['offer_id']],cr[r['offer_id']]['selected_side'].lower())in('WIN','LOSS')];aw=sum(grade(r)=='WIN'for r,c in common);bw=sum(grade(c,c['selected_side'].lower())=='WIN'for r,c in common);assert(len(common),aw,bw,aw-bw)==(p['common_decided'],p['candidate_wins'],p['control_wins'],p['win_difference']);assert p['disagreements']==sum(chosen(r)!=c['selected_side'].lower()for r,c in common);game=collections.defaultdict(list)
        for r,c in common:game[r['game_id']].append(int(grade(r)=='LOSS')-int(grade(c,c['selected_side'].lower())=='LOSS'))
        delta=(bw-aw)/len(common);u=p['uncertainty'];assert close(delta,u['delta'])and u['week_interval']is None
        if len(game)>=8:
            se=math.sqrt(len(game)/(len(game)-1)*math.fsum((sum(v)-len(v)*delta)**2 for v in game.values()))/len(common);assert close(se,u['game_cluster_sensitivity_se'])and all(close(a,b)for a,b in zip([delta-1.96*se,delta+1.96*se],u['game_normal95_sensitivity']))
        if str(p['week_view'])=='ALL'and aw==65:maximumdiff.append(dict(method=p['procedure_id'],control=p['control_id'],wins=aw,control_wins=bw,win_difference=aw-bw,hit_change=(aw-bw)/111,game95_hit_change=[-v for v in reversed(u['game_normal95_sensitivity'])]))
    assert len(paired)==468
    membership=load(out/'PUBLIC_C_MASK_MEMBERSHIP_BINDINGS.json');assert len(membership)==156
    for m in membership:
        rr=view([r for r in groups[m['procedure_id']]if r['offer_id']in ids],m['week']);assert m['offer_ids']==sorted(r['offer_id']for r in rr)and m['decided_offer_ids']==sorted(r['offer_id']for r in rr if grade(r)in('WIN','LOSS'))
    cumulative=load(out/'CUMULATIVE_ALL_METHODS.json');assert len(cumulative)==52;maximum=max(r['wins']for r in cumulative);leaders=[r for r in cumulative if r['wins']==maximum];assert maximum==65 and len(leaders)==4 and all(r['decided']==111 and r['fallback']==55 for r in leaders)
    for r in cumulative:
        s=triads[r['procedure_id'],'ALL']['Combined'];assert(r['wins'],r['losses'],r['decided'],r['eligible'],r['selected'],r['fallback'],r['games'])==(s['selection_metrics']['WIN'],s['selection_metrics']['LOSS'],s['n'],s['selection_metrics']['selection_pool_count'],s['forecast_rows'],s['selection_metrics']['fallback_issued'],s['unique_games']);assert close(r['MAE'],s['mae'])and close(r['bias'],s['bias'])
    failures=[]
    for version,name,snapshot in [('v1','FAILURE_RECEIPT_V1.json','SOURCE_BEFORE_METADATA_ADAPTER_FIX_V1.py'),('v2','FAILURE_RECEIPT_V2.json','SOURCE_BEFORE_METADATA_STATUS_FIX_V2.py')]:
        p=out.parent/('B-111-RB-common-mask-'+version);f=load(p/name);assert f['new_fits']==0 and f.get('score_views_published',f.get('published_score_views'))==0 and not(p/'SCORES.json').exists();failures.append(dict(version=version,receipt_sha256=sha(p/name),source_snapshot_sha256=sha(p/snapshot),error=f['error']))
    result=dict(state='PASS_INDEPENDENT_111_RB_PRIMITIVE_MASK_COUNTS_AND_PAIRS',at_utc=datetime.now(timezone.utc).isoformat(),verification_code_sha256=sha(Path(__file__)),scores_sha256=sha(out/'SCORES.json'),protocol_sha256=sha(out/'FROZEN_PACKAGE.json'),mask_source_sha256=sha(maskpath),exact_mask_id=MASK,B_existing_source_hashes=sourcehashes,C_existing_control_source_hashes=csourcehashes,method_history_point_output_configurations=52,not_learner_family_count=True,own_full_board_availability_histogram=[dict(source_rows=k[0],point_available=k[1],point_unavailable=k[2],configurations=v)for k,v in sorted(owncoverage.items())],exact_RB_mask_rows=111,actual_weeks=[2,3],unique_games=32,identity_and_role_checks=identitychecks,cutoff_and_feature_availability_checks=clockchecks,C_controls_verified=7,side_views_verified=468,side_triads_verified=156,paired_control_views_verified=468,public_membership_bindings_verified=156,observed_leaders=leaders,leader_paired_control_changes=maximumdiff,preserved_adapter_failures=failures,new_fits=0,new_inference=0,new_private_bytes=0,new_NFL_observations=0,five_week_floor_met=False,limits=['Same frozen111RBparticipant/offer subset is conditional;181sourceoffers and fullboard availability remain separate. Roles are as retained/corrected C crosswalk, not independently authenticated pregame roster vintages.','Four strict-current median procedures tie65/111 with55fallback rows; this is not four independent validations, new NFL games or five-week qualification. Own learned/fallback contributions are not a universal common-learned comparison.','Allcutoff metadata and source identity/label values match retainedCrows; neither football source publication vintage nor quote executability/settlement is authenticated here.','Largest observed gain is exposed descriptive and uncertainty/multiplicity limited; no inverted/router/production policy was constructed. C intake/admission remains separate.'])
    (out/'INDEPENDENT_111_RB_MASK_AUDIT_V1.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('private',type=Path);p.add_argument('csnapshot',type=Path);p.add_argument('maskpath',type=Path);p.add_argument('out',type=Path);a=p.parse_args();run(a.private,a.csnapshot,a.maskpath,a.out)
