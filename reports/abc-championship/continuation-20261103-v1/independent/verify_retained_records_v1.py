"""Separate arithmetic audit; accepts retained evidence paths, never invokes a scorer."""
import argparse, collections, gzip, hashlib, json, math
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path


def read(path):
    data=path.read_bytes()
    return json.loads(gzip.decompress(data) if path.suffix=='.gz' else data)


def grade(actual, line, side):
    actual,line=Decimal(str(actual)),Decimal(str(line))
    if actual==line:return 'PUSH'
    return 'WIN' if ((actual>line)==(side.lower()=='over')) else 'LOSS'


def summary(rows, sidekey='selected_side', statekey='status'):
    out={}
    for side in ('OVER','UNDER','COMBINED'):
        selected=[r for r in rows if str(r.get(sidekey)).upper() in (['OVER','UNDER'] if side=='COMBINED' else [side])]
        counts=collections.Counter(r[statekey] for r in selected)
        w,l=counts['WIN'],counts['LOSS']
        out[side]=dict(selected=len(selected),wins=w,losses=l,decided=w+l,hit_rate=w/(w+l) if w+l else None,states=dict(counts))
    assert all(out['COMBINED'][k]==out['OVER'][k]+out['UNDER'][k] for k in ('selected','wins','losses','decided'))
    return out


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def run(b_source, c_root, b_chunks, output, private):
    b=read(b_source)['rows']
    original=[r for r in b if r['panel']=='ORIGINAL_PROVIDER_T90' and r['strategy']=='original']
    selected=[r for r in original if r['selected_side'] in ('over','under')]
    decided=[r for r in selected if r['statistical_state'] in ('WIN','LOSS')]
    keys=[(r['game_id'],r['player_id'],r['target'],str(r['line'])) for r in selected]
    assert len(set(keys))==len(keys), 'Duplicate original selection'
    for r in decided:
        assert grade(r['actual'],r['line'],r['selected_side'])==r['statistical_state']
    assert len(selected)==427 and len(decided)==415
    by_category={}
    for category in sorted({r['target'] for r in selected}):
        rr=[r for r in selected if r['target']==category]
        old=summary(rr,statekey='statistical_state')
        under=[dict(r,selected_side='under',statistical_state=grade(r['actual'],r['line'],'under')) for r in rr if r['statistical_state'] in ('WIN','LOSS')]
        u=summary(under,statekey='statistical_state')
        by_category[category]=dict(original=old,always_under_on_same_decided_mask=u,unresolved=len(rr)-old['COMBINED']['decided'])
    all_o=summary(selected,statekey='statistical_state')
    all_u=summary([dict(r,selected_side='under',statistical_state=grade(r['actual'],r['line'],'under')) for r in decided],statekey='statistical_state')
    ow,ol=all_o['OVER']['wins'],all_o['OVER']['losses']
    uw,ul=all_o['UNDER']['wins'],all_o['UNDER']['losses']
    assert all_u['COMBINED']['wins']==ol+uw==224
    assert all_o['COMBINED']['wins']==ow+uw==205
    # Paired cluster-normal sensitivity independently calculated, one week cannot give week CI.
    diffs=collections.defaultdict(list)
    for r in decided:
        diffs[r['game_id']].append(int(grade(r['actual'],r['line'],'under')=='WIN')-int(r['statistical_state']=='WIN'))
    n=len(decided);delta=sum(map(sum,diffs.values()))/n;g=len(diffs)
    se=math.sqrt(g/(g-1)*sum((sum(v)-len(v)*delta)**2 for v in diffs.values()))/n
    paired=dict(n=n,unique_games=g,weeks=[8],extra_control_wins=19,win_rate_change=delta,game_cluster_normal95_sensitivity=[delta-1.96*se,delta+1.96*se],week_interval=None,week_interval_reason='ONE_WEEK;INSUFFICIENT_CLUSTERS',selection_limit='EXPOSED_DESCRIPTIVE_CONTROL_DIAGNOSTIC;NOT_MULTIPLICITY_ADJUSTED')
    # C: apply append-only corrections independently; preserve original selections.
    bindings=read(c_root/'reports/abc-championship/C_INPUT_BINDINGS.json')
    records={}; corrections=0; c_hashes=[]
    for d in bindings['datasets']:
        path=c_root/d['path'];assert digest(path)==d['SHA256'];c_hashes.append(dict(path=d['path'],sha256=d['SHA256']))
        for r in read(path)['rows']:
            if r['record_id'] in records:
                old=records[r['record_id']]
                assert r.get('supersedes_grade_id')==old['grade_id']
                for field in ('game_id','player_id','selected_side','line','decision_UTC','method_id','forecast_id'):
                    assert r.get(field)==old.get(field),field
                corrections+=1
            records[r['record_id']]=r
    first={}
    fields=('category','game_id','player_id','method_id','method_version','selector_id','policy_id','venue','product','line_tier','evidence_tier')
    for r in records.values():
        key=tuple(r[k] for k in fields);order=(r['decision_UTC'],r['scoring_snapshot_id'])
        if key not in first or order<first[key][0]:first[key]=(order,r)
    c=[v[1] for v in first.values() if v[1]['venue']=='pinnacle' and v[1]['season']==2026 and v[1]['week']<=8]
    checked=0
    for r in c:
        if r['status'] in ('WIN','LOSS','PUSH'):
            assert r['appearance']=='PLAYED' and r['comparator']=='STRICT_OVER_UNDER'
            assert grade(r['actual'],r['line'],r['selected_side'])==r['status']
            checked+=1
    expected=read(c_root/'reports/abc-championship/SCORES-v2-C-1.json');n_side=0
    for score in expected:
        rr=[r for r in c if r['category']==score['category'] and 'C::'+r['method_version']+'::'+r['method_id']+'::'+r['selector_id']==score['procedure_id'] and (score['week_view']=='ALL' or str(r['week'])==str(score['week_view']))]
        got=summary(rr)
        assert len(rr)==score['eligible']
        for side in ('OVER','UNDER','COMBINED'):
            for key in ('selected','decided'):assert got[side][key]==score[side][key]
            if got[side]['decided']:
                for key in ('wins','losses'):assert got[side][key]==score[side][key]
                assert abs(got[side]['hit_rate']-score[side]['rate'])<1e-14
            else:assert score[side]['rate'] is None
            n_side+=1
    # B retained D1/D2 forecast identity+cutoff+labels against C's primary offer board.
    offers={r['offer_id']:r for r in c if r['method_id']=='ALWAYS_OVER'}
    offered=collections.defaultdict(list)
    for r in offers.values():offered[(r['game_id'],r['player_id'],r['category'])].append(r)
    joins=0; label_mismatch=[];cutoff_mismatch=[];feature_bad=[];role_mismatch=[];matched_games=set();chunk_hashes=[]
    for path in sorted(b_chunks.glob('W0[23]-*.json.gz')):
        chunk_hashes.append(dict(file=path.name,sha256=digest(path)))
        for row in read(path)['rows']:
            for offer in offered.get((row['game_id'],row['player_id'],row['target']),[]):
                joins+=1;matched_games.add(row['game_id'])
                if row['actual'] is not None and offer['actual'] is not None and Decimal(str(row['actual']))!=Decimal(str(offer['actual'])):
                    label_mismatch.append(dict(chunk=path.name,game=row['game_id'],player=row['player_id'],category=row['target'],B=row['actual'],C=offer['actual']))
                if datetime.fromtimestamp(row['cutoff'],timezone.utc)!=datetime.fromisoformat(offer['decision_UTC']):cutoff_mismatch.append(path.name)
                if row.get('latest_feature_available') is not None and row['latest_feature_available']>row['cutoff']:feature_bad.append(path.name)
                if row['position']!=offer['position']:role_mismatch.append(dict(chunk=path.name,game=row['game_id'],player=row['player_id'],category=row['target'],B=row['position'],C=offer['position']))
    private.mkdir(parents=True,exist_ok=True)
    # Keep row-level examples and any identity/label exceptions private.
    examples={}
    for side in ('over','under'):
        for state in ('WIN','LOSS'):
            examples[side+'_'+state]=next(r for r in sorted(decided,key=lambda r:(r['game_id'],r['player_id'],r['target'])) if r['selected_side']==side and r['statistical_state']==state)
    (private/'INDEPENDENT_EXAMPLES_AND_JOIN_EXCEPTIONS.json').write_text(json.dumps(dict(examples=examples,label_mismatch=label_mismatch,cutoff_mismatch=cutoff_mismatch,role_mismatch=role_mismatch),indent=2))
    receipt=dict(verifier='independent separate-path verifier',at_utc=datetime.now(timezone.utc).isoformat(),scope='Read-only;no scorer invocation; no fits or inference; representative source and all published C side totals, not full source-vintage authentication.',B=dict(source_sha256=digest(b_source),original=all_o,always_under=all_u,per_category=by_category,paired=paired,unknown_selected=12),C=dict(ref='ac9cb1000bcb8f1197505b68ccfe246ea61bbafe',dataset_hashes=c_hashes,corrected_rows=corrections,primary_method_rows=len(c),direct_boundary_checks=checked,published_side_views_verified=n_side,unique_offers=len(offers),weeks=sorted({r['week'] for r in c}),evidence_tier='TIMING_UNVERIFIED_ACTUAL_LINE_DIAGNOSTIC'),B_C_join=dict(matched_forecast_offer_rows=joins,unique_games=len(matched_games),label_mismatches=len(label_mismatch),cutoff_mismatches=len(cutoff_mismatch),future_feature_availability_rows=len(feature_bad),role_mismatches=len(role_mismatch),chunk_hashes=chunk_hashes),status='PASS' if not(label_mismatch or cutoff_mismatch or feature_bad or role_mismatch) else 'PASS_ARITHMETIC_WITH_JOIN_EXCEPTIONS_REQUIRING_SCOPE_REVIEW')
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({k:v for k,v in receipt.items() if k not in ('B','C','B_C_join')}));print('B',all_o['COMBINED'],all_u['COMBINED'],paired);print('C rows/sideviews',len(c),n_side);print('B_C joins/exceptions',joins,len(label_mismatch),len(cutoff_mismatch),len(feature_bad),len(role_mismatch))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--b-source',type=Path,required=True);p.add_argument('--c-root',type=Path,required=True);p.add_argument('--b-chunks',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--private',type=Path,required=True);a=p.parse_args();run(a.b_source,a.c_root,a.b_chunks,a.output,a.private)
