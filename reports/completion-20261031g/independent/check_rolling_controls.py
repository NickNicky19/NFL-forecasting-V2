"""Read-only independent row/label/side/rolling-K verification of new controls."""
import argparse
from collections import Counter,defaultdict
from datetime import datetime,timezone
from decimal import Decimal
import csv,gzip,hashlib,importlib.util,json,math
from pathlib import Path

spec=importlib.util.spec_from_file_location('independent_method_checker',Path(__file__).with_name('check_w7_methods.py'));ind=importlib.util.module_from_spec(spec);spec.loader.exec_module(ind)
sha,canon=ind.sha,ind.canon
def read(p):return json.loads(p.read_bytes())
def gz(p):return json.loads(gzip.decompress(p.read_bytes()))['rows']
def close(a,b):
    if a is None or b is None:assert a is b
    else:assert math.isclose(a,b,abs_tol=1e-12,rel_tol=1e-12)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo-root',type=Path,required=True);ap.add_argument('--private-root',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();root=a.repo_root;reports=[]
    for week,suffix in((6,''),(7,'-w7')):
        public=root/'reports/completion-20261031g/source-expansion';public=public/'w7-rolling-v1'if week==7 else public;private=a.private_root/('completion-20261031g-source'+suffix);run=read(public/'RUN_RECEIPT.json');protocol_file=next(p for p in public.glob('FROZEN_GRADING_PROTOCOL*.json')if sha(p)==run['protocol_sha256']);p=read(protocol_file);freeze=read(public/'K_MEMBERSHIP_FREEZE_RECEIPT.json')
        assert sha(public/'SCORES.json')==run['score_sha256'];bindings=read(private/'GRADING_INPUT_BINDING_V2.json');assert sha(private/'GRADING_INPUT_BINDING_V2.json')==p['private_binding_sha256'];assert sha(Path(bindings['labels']))==p['label_source_sha256']
        joinedfile=private/'JOINED_ROWS.json.gz';gradefile=private/'GRADED_ROWS.json.gz';assert sha(joinedfile)==run['private_join_sha256']and sha(gradefile)==run['private_grades_sha256'];joined=gz(joinedfile);grades=gz(gradefile);jb={r['source_row_index']:r for r in joined};assert len(jb)==run['outer_rows']
        labels=defaultdict(list);wanted={(r['game_id'],r['player_id'],r['target'],r['position'])for r in joined}
        with gzip.open(bindings['labels'],'rt')as f:
            for r in csv.DictReader(f):
                if r['season']=='2026'and int(r['week'])==week:
                    key=tuple(r[k]for k in('game_id','player_id','target','position'))
                    if key in wanted:labels[key].append(r)
        for r in joined:
            vv=labels[r['game_id'],r['player_id'],r['target'],r['position']];parts={v['participation']for v in vv};values={float(v['actual'])for v in vv if v['actual']!=''};assert len(parts)<=1 and len(values)<=1;played=parts=={'played'};y=next(iter(values))if played and values else None;state='SUPPORTED'if y is not None else'MISSING_ACTUAL'if played else'APPEARANCE_UNKNOWN';assert r['actual']==y and r['label_state']==state;assert r['participation']==('VERIFIED_PLAYED_POSITIVE_PHYSICAL'if played else'UNKNOWN')
        by=defaultdict(list);grade_states=Counter()
        for r in grades:
            original=jb[r['source_row_index']];strategy=r['strategy'];point=original['raw_prediction']if strategy=='SAVED_RAW_PROJECTION_DIRECTION_RETAINED_PRECISION'else original['prediction'];line=Decimal(str(original['line']))
            if strategy=='original':side=original['original_side']
            elif strategy=='alwaysOver':side='over'
            elif strategy=='alwaysUnder':side='under'
            else:side=None if point is None else'over'if Decimal(str(point))>line else'under'if Decimal(str(point))<line else None
            y=original['actual'];state='ABSTAIN'if side is None else'UNKNOWN_PARTICIPATION'if original['participation']=='UNKNOWN'else'MISSING_ACTUAL'if y is None else'PUSH'if Decimal(str(y))==line else'WIN'if(Decimal(str(y))>line if side=='over'else Decimal(str(y))<line)else'LOSS';assert r['selected_side']==side and r['statistical_state']==state;by[strategy].append(r);grade_states[state]+=1
        kfile=private/'FROZEN_ROLLING_K_MEMBERSHIPS.json.gz';assert sha(kfile)==freeze['membership_sha256'];ks=gz(kfile);kmap={}
        for k in ks:
            pool=[r for r in by[k['strategy']]if r['target']==k['target']and r['selected_side']and(k['rank_scope']=='Combined'or r['selected_side']==k['rank_scope'])];chosen=[]
            for clock in sorted({r['source_server_clock']for r in pool}):
                batch=[r for r in pool if r['source_server_clock']==clock];batch.sort(key=lambda r:(-abs(Decimal(str(r['ranking_point']))-Decimal(str(r['line']))),r['game_id']or'',r['player_id']or'',r['target'],str(r['line']),r['source_row_index']));chosen.extend(batch[:max(0,k['K']-len(chosen))])
            assert k['eligible_pool_n']==len(pool)and k['source_row_indices']==[r['source_row_index']for r in chosen];assert len(set(k['source_row_indices']))==len(chosen);kmap[k['strategy'],k['target'],k['rank_scope'],k['K']]=k
        scores=read(public/'SCORES.json');triads=defaultdict(dict);summary=[]
        for r in scores:
            pool=[v for v in by[r['strategy']]if r['target']=='ALL'or v['target']==r['target']]
            if r['K']is None:pool=[v for v in pool if ind.member(v,r['cohort_id'])];selected=[v for v in pool if v['selected_side']]
            else:selected=[v for v in pool if v['source_row_index']in set(kmap[r['strategy'],r['target'],r['rank_scope'],r['K']]['source_row_indices'])]
            rr=[v for v in selected if r['side']=='Combined'or v['selected_side']==r['side']];c=Counter(v['statistical_state']for v in rr);m=r['selection_metrics'];n=c['WIN']+c['LOSS'];assert(r['forecast_rows'],r['n'],m['WIN'],m['LOSS'],m['PUSH'])==(len(rr),n,c['WIN'],c['LOSS'],c['PUSH']);close(m['hit_rate'],c['WIN']/n if n else None);close(r['selection_loss_rate'],c['LOSS']/n if n else None);assert m['status_counts']=={k:c[k]for k in m['status_counts']};assert r['query_membership_sha256']==hashlib.sha256(canon(sorted(v['source_row_index']for v in rr))).hexdigest()
            dims=(r['strategy'],r['target'],r['cohort_id'],r['K'],r['rank_scope']);triads[dims][r['side']]=[len(rr),n]+[c[k]for k in('WIN','LOSS','PUSH','UNKNOWN_PARTICIPATION','MISSING_ACTUAL','VOID','PENDING')]
            if r['target']=='ALL'and r['cohort_id']=='ALL'and r['K']is None:summary.append(dict(strategy=r['strategy'],side=r['side'],selected=len(rr),wins=c['WIN'],losses=c['LOSS'],decided=n,hit_rate=m['hit_rate'],unknown=c['UNKNOWN_PARTICIPATION']))
        for group in triads.values():assert set(group)=={'over','under','Combined'}and group['Combined']==[x+y for x,y in zip(group['over'],group['under'])]
        assert len(ks)==450 and len(scores)==3330 and len(grades)==5*len(joined)
        reports.append(dict(week=week,protocol_sha256=run['protocol_sha256'],score_sha256=run['score_sha256'],offer_rows=len(joined),label_states=dict(Counter(r['label_state']for r in joined)),grade_views=len(grades),score_views=len(scores),side_triplets=len(triads),rolling_K_lists=len(ks),grade_states=dict(grade_states),all_methods_sides=summary))
    report=dict(state='PASS_INDEPENDENT_W6_W7_ROLLING_CONTROL_LABEL_JOINS_GRADES_SIDES_AND_K',at=datetime.now(timezone.utc).isoformat(),weeks=reports,new_fits=0,new_inference=0,new_forecasts=0,new_grades=0,new_NFL_observations=0,scope='New14game W6 and14game W7 rolling provider-labelled threshold panels; F Friday13game panel remains separately frozen. No prices/booksettlement/ROI. Cohort-v3 corrections are separate from these original completed views.')
    with a.output.open('x')as f:json.dump(report,f,indent=2);f.write('\n')
    print(json.dumps(dict(state=report['state'],weeks=[(r['week'],r['offer_rows'],r['score_views'])for r in reports])))


if __name__=='__main__':main()
