"""Verify committed B saved-output handoff; no private offers, fits or grading."""
import gzip,hashlib,json,math,pathlib,subprocess,sys
from datetime import datetime,timezone
ROOT=pathlib.Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT))
from tools.query_targeted_qb_m2 import project
from nfl_v2.targeted_qb_m2 import restore_law

COMMIT='11db6280f8af4ae215f15ebbcc26c3a891db27f1'
BASE=ROOT/'reports/targeted-accuracy-checkpoint-closure-01/B/independent-M2'
SOURCE=ROOT/'reports/targeted-accuracy-w1w9-01/B'
PREFIX=f'https://raw.githubusercontent.com/NickNicky19/NFL-forecasting-V2/{COMMIT}/'
def sha(b):return hashlib.sha256(b).hexdigest()
def read(p):
    b=p.read_bytes();return json.loads(gzip.decompress(b)if p.suffix=='.gz'else b)
def immutable(path):return subprocess.check_output(['git','show',COMMIT+':'+path],cwd=ROOT)

def main():
    checks=0;problems=[];bindings=[]
    def check(value,reason):
        nonlocal checks
        checks+=1
        if not value:problems.append(reason)
    handoff_path='reports/targeted-accuracy-w1w9-01/B/OWNER_LOCAL_M2_HANDOFF_V1.json'
    h=read(ROOT/handoff_path);check(immutable(handoff_path)==(ROOT/handoff_path).read_bytes(),'handoff differs committed producer')
    manifest=read(SOURCE/'retention/final-v1/MANIFEST.json');members={r['path']:r for r in manifest['members']}
    methods=set(h['requested_new_cells']['products']);counts={};rows_by={};early={};model_kinds={};aliases=0
    for binding in h['prediction_files']:
        path=ROOT/binding['path'];raw=path.read_bytes();check(sha(raw)==binding['sha256'],'prediction hash '+path.name)
        check(len(raw)==binding['bytes'],'prediction size '+path.name);check(immutable(binding['path'])==raw,'prediction producer bytes '+path.name)
        check(members[binding['path']]['sha256']==binding['sha256'],'retention prediction contract '+path.name)
        body=json.loads(gzip.decompress(raw));w=body['week'];found={};ids={}
        for r in body['rows']:
            key=r['game_id'],r['player_id'],r['target'];full=(r['method'],)+key
            check(full not in rows_by,'duplicate forecast identity')
            rows_by[full]=r
            if r['target']=='pass_cmp':
                check(r['method']in methods,'unregistered CMP method');found[r['method']]=found.get(r['method'],0)+1
                ids.setdefault(r['method'],set()).add(key)
                check(math.isfinite(r['mean'])and math.isfinite(r['lower_median']),'finite typed points')
                model_kinds[r['law']['kind']]=model_kinds.get(r['law']['kind'],0)+1
                if r['method'].endswith('_BB'):
                    check(r['law']['version']=='B-TARGETED-QB-CONTEXT-BETA-BINOMIAL-v1','law version')
                    check(r['law']['tail_tol']==1e-10,'frozen tail tolerance')
            check(r['original_issuance']is False,'reconstruction typed original')
            check(r['fit_cutoff']<=r['feature_cutoff'],'fit/query ordering')
        check(set(found)==methods,'all seven CMP methods '+str(w))
        check(len({len(v)for v in ids.values()})==1,'same forecast identity counts '+str(w))
        first=next(iter(ids.values()));check(all(v==first for v in ids.values()),'same forecast query sets '+str(w))
        counts[str(w)]=found
        if w<=4:early[str(w)]={'queries_per_method':len(first),'owner_bound_offers':h['requested_new_cells']['owner_bound_existing_offers'][w-1],
            'new_grade_status':'OWNER_LOCAL_JOIN_REQUIRED_UNLESS_NEW_A_RECEIPT_OBTAINED'}
        for r in body['rows']:
            if r['method'].endswith('_BB'):
                parent=rows_by[(r['method'].replace('_BB','_BIN'),r['game_id'],r['player_id'],r['target'])]
                check(r['mean']==parent['mean'],'fixed parent mean')
                check(r['components']['attempt_law']==parent['components']['attempt_law'],'fixed attempt law')
                aliases+=1
        bindings.append(dict(binding,repository='NickNicky19/NFL-forecasting-V2',producer_commit=COMMIT,retrieval_url=PREFIX+binding['path']))
    exact_paths=[h['adapter']['path'],'nfl_v2/targeted_qb_m2.py','nfl_v2/player_context_matchup.py',
      'reports/targeted-accuracy-w1w9-01/B/wave-v1/FROZEN_PROTOCOL_V2.json',handoff_path]
    code=[]
    for path in exact_paths:
        raw=(ROOT/path).read_bytes();check(immutable(path)==raw,'immutable code/contract '+path)
        if path in members:check(members[path]['sha256']==sha(raw),'manifest code/contract '+path)
        if path==h['adapter']['path']:check(sha(raw)==h['adapter']['sha256'],'declared adapter hash')
        code.append(dict(path=path,sha256=sha(raw),bytes=len(raw),repository='NickNicky19/NFL-forecasting-V2',producer_commit=COMMIT,retrieval_url=PREFIX+path))
    fixture=[]
    for w in range(1,5):
        chosen=sorted([r for r in rows_by.values()if r['method']=='M2_P2_BB'and r['week']==w],key=lambda r:(r['game_id'],r['player_id']))
        for r in (chosen[0],chosen[-1]):
            key=r['game_id'],r['player_id'],r['target'];item=(r,{'artifact':'SOFTWARE_FIXTURE_ONLY'})
            q=dict(game_id=key[0],player_id=key[1],target=key[2],season=2026,week=w,line=r['mean'])
            point=project(q,item,'P1_MEAN');check(point['side']=='ABSTAIN','exact mean equality')
            q['line']=int(r['lower_median']);median=project(q,item,'P1_LOWER_MEDIAN');check(median['side']=='ABSTAIN','exact median equality')
            law=restore_law(r['law']);lawp=project(q,item,'P2_STATISTICAL_LAW')['probabilities']
            check(abs(sum(lawp.values())-1)<1e-10,'normalized crossing probabilities')
            check(abs(lawp['push']-law.pmf(q['line']))<1e-9,'integer push equality')
            check(point['probabilities']is None and median['probabilities']is None,'no point invented probability')
            check(project(q,None,'P1_MEAN')['side']is None,'missing not forced side')
            fixture.append(dict(case_sha256=sha(json.dumps(key).encode()),week=w,scope='INTERNAL_THRESHOLD_ADAPTER_FIXTURE_NOT_ACTUAL_OFFER_OR_GRADE'))
    bridge_path='reports/targeted-accuracy-w1w9-01/B/independent/OWNER_LOCAL_NATIVE_ORDINAL_BRIDGE_V2.json';bridge=read(ROOT/bridge_path)
    check(immutable(bridge_path)==(ROOT/bridge_path).read_bytes(),'ordinal bridge producer bytes')
    lookup=bridge['identity_hash_lookup'];check(len(lookup)==142,'bridge lookup count')
    check(len({z['identity_sha256']for z in lookup})==142,'unique lookup identities')
    check(sorted(z['original_filtered_index']for z in lookup)==list(range(142)),'original ordinal permutation')
    check(sorted(z['canonical_rank']for z in lookup)==list(range(142)),'canonical permutation')
    for rank,original in enumerate(bridge['canonical_to_original_filtered_index']):
        check(bridge['original_filtered_to_canonical_index'][original]==rank,'permutation inverse')
    receipt=dict(id='B_CHECKPOINT_FROZEN_M2_HANDOFF_AUTHENTICATION_v1',at_UTC=datetime.now(timezone.utc).isoformat(),
      state='PASS_FROZEN_PUBLIC_HANDOFF_AND_SOURCE_COMMITMENTS'if not problems else'FAIL',checks=checks,problems=problems,
      source_commit=COMMIT,source_repository='NickNicky19/NFL-forecasting-V2',prediction_bindings=bindings,adapter_and_contract_bindings=code,
      queries_per_week_and_method=counts,early84_join_cells=early,fixed_mean_attempt_pairs_checked=aliases,law_kinds=model_kinds,
      software_fixture_cases=fixture,ordinal_bridge=dict(path=bridge_path,producer_commit=COMMIT,sha256=sha((ROOT/bridge_path).read_bytes()),
        scope='Only original B0/B2 native142CMP W5–9 filtered-index commitments; it does not transfer old FTN grades or selection qualification to new M2 or M3.',
        actual_A_application='NOT_ESTABLISHED_BY_THIS_RECEIPT'),
      interpretation='Exact newM2 means/medians/laws are bound and available. OldB0/B2 early84grades cannot supply newM2 cells. This verifies code/row contracts only, not A private offers, quote clocks, historical source vintage, fit reproduction or new grading.',
      resource=dict(external_source_reads=0,new_fits=0,new_original_forecasts=0,new_actual_offer_grades=0,protected_rows_exported=0))
    BASE.mkdir(parents=True,exist_ok=True);(BASE/'FROZEN_HANDOFF_AUTHENTICATION_V1.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({'state':receipt['state'],'checks':checks,'problems':problems,'early_query_counts':early}))
    if problems:raise SystemExit(1)

if __name__=='__main__':main()
