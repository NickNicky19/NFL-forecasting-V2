"""Independent source joins, decimal decisions and complete full-pool side audit.

No producer grader imports, fitting, collection or future outcomes. The lexical
scanner comes from the previously retained independent source-join checker.
"""
import argparse,collections,csv,datetime,gzip,hashlib,importlib.util,json,math,resource,time
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo
import numpy as np

TARGETS=('pass_yd','pass_td','pass_cmp','pass_att','pass_int','rush_yd','rush_att','rec','rec_yd','rush_rec_yd')
ADJ='SAVED_ADJUSTED_POINT_DIRECTION_RETAINED_PRECISION';RAW='SAVED_RAW_PROJECTION_DIRECTION_RETAINED_PRECISION'
STRATEGIES=('original',ADJ,RAW,'alwaysOver','alwaysUnder')
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def canon(x):return json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def read(p):return json.loads(Path(p).read_text())
def rows(p):return json.loads(gzip.decompress(Path(p).read_bytes()),parse_float=Decimal)['rows']
def clock(s):return datetime.datetime.fromisoformat(s.replace('Z','+00:00'))
def close(a,b):
    if a is None or b is None:assert a is b,(a,b)
    elif isinstance(a,list):
        assert len(a)==len(b)
        for x,y in zip(a,b):close(x,y)
    else:assert math.isclose(float(a),float(b),abs_tol=1e-12,rel_tol=1e-12),(a,b)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo-root',type=Path,required=True);ap.add_argument('--public-root',type=Path,required=True);ap.add_argument('--private-root',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();start=time.monotonic()
    p=read(a.public_root/'FROZEN_PROTOCOL.json');run=read(a.public_root/'RUN_RECEIPT.json');bindings=read(a.private_root/'INPUTS_PRIVATE.json')
    assert digest(a.public_root/'FROZEN_PROTOCOL.json')==run['protocol_sha256']
    assert digest(a.public_root/'SOURCE_SNAPSHOT.py')==p['code_sha256']==run['code_sha256']
    assert digest(a.public_root/'SCORES.json')==run['public_score_sha256']
    assert digest(a.private_root/'INPUTS_PRIVATE.json')==p['bindings_sha256']
    for k,v in p['input_sha256'].items():assert digest(bindings[k])==v,k
    old=a.repo_root/'reports/prop-grading-20261030e/check_panel_join_independent.py';spec=importlib.util.spec_from_file_location('previous_independent_scanner',old);scanner=importlib.util.module_from_spec(spec);spec.loader.exec_module(scanner)
    proof=clock(p['source_clock']);metadata=rows(bindings['metadata']);eligible=[]
    for r in metadata:
        line=r.get('line');finite=line is not None and not isinstance(line,bool)and Decimal(str(line)).is_finite()
        if r['category']in TARGETS and r.get('line_from')in('dk','sleeper')and finite and clock(r['kickoff'])-datetime.timedelta(minutes=90)>proof:eligible.append(r)
    frozen=rows(a.private_root/'FROZEN_FULL_POOL_METADATA.json.gz')
    assert digest(a.private_root/'FROZEN_FULL_POOL_METADATA.json.gz')==p['metadata_panel_sha256']
    assert len(eligible)==len(frozen)==462 and eligible==frozen
    assert collections.Counter(r['line_from']for r in eligible)==dict(dk=441,sleeper=21)
    assert sum(r.get('lean')in('over','under')for r in eligible)==285
    source_root=Path(bindings['source_root']);assert digest(source_root/'games.csv')==p['source_schedule_sha256'];assert digest(source_root/'roster-week8-identity-2026.csv.gz')==p['identity_bridge_sha256']
    bridge_sets=collections.defaultdict(set)
    with gzip.open(source_root/'roster-week8-identity-2026.csv.gz','rt')as f:
        for r in csv.DictReader(f):
            if r['season']=='2026'and int(r['week'])<=7 and r['sleeper_id']and r['gsis_id']:bridge_sets[r['sleeper_id']].add(r['gsis_id'])
    bridge={k:next(iter(v))for k,v in bridge_sets.items()if len(v)==1}
    with(source_root/'games.csv').open()as f:schedule={r['espn']:r for r in csv.DictReader(f)if(r['season'],r['game_type'],r['week'])==('2026','REG','7')}
    wanted={};key_by_index={}
    for r in eligible:
        g=schedule[str(r['game_id'])];key=(g['game_id'],bridge[str(r['player_id'])],r['category']);assert key not in wanted
        assert datetime.datetime.fromisoformat(g['gameday']+'T'+g['gametime']).replace(tzinfo=ZoneInfo('America/New_York')).timestamp()==clock(r['kickoff']).timestamp()
        wanted[key]=r;key_by_index[r['source_row_index']]=key
    reference=collections.defaultdict(list);decoded=0
    for i,raw in enumerate(scanner.raw_rows(gzip.decompress(Path(bindings['reference']).read_bytes()).decode())):
        key=tuple(scanner.identity_scalar(raw,k)for k in('game_id','player_id','target'))
        if key in wanted:reference[key].append((i,json.loads(raw,parse_float=Decimal)));decoded+=1
    indices={r['source_row_index']for r in eligible};original={i:json.loads(raw,parse_float=Decimal)for i,raw in enumerate(scanner.raw_rows(gzip.decompress(Path(bindings['forward']).read_bytes()).decode()))if i in indices}
    prior_members=json.loads(gzip.decompress(Path(bindings['memberships']).read_bytes()))
    member_map={tuple(r['key']):r for r in prior_members if str(r['key'][0]).startswith('2026_07_')}
    joined=rows(a.private_root/'JOINED_ROWS.json.gz');assert digest(a.private_root/'JOINED_ROWS.json.gz')==run['private_joined_sha256'];assert len(joined)==462
    expected_join={};joined_fields=0
    for j,m in zip(joined,eligible):
        i=m['source_row_index'];key=key_by_index[i];vv=reference[key];assert len(vv)==2
        assert {v['product_id']for _,v in vv}=={'website_point','provider_point'}
        states={v['status']for _,v in vv};assert len(states)==1
        positions={v['position']for _,v in vv};pops={v['population']for _,v in vv};actuals={v['actual']for _,v in vv};assert positions=={m['position']}and len(pops)==len(actuals)==1
        status=next(iter(states));y=next(iter(actuals));pop=next(iter(pops));raw=original[i]
        for field in('game_id','player_id','category','position','line','lean','line_from'):assert raw.get(field)==m.get(field)
        assert status in ('SUPPORTED','APPEARANCE_UNKNOWN')
        if status=='SUPPORTED':assert y is not None and y==int(y)
        else:assert y is None
        points={v['product_id']:v['prediction']for _,v in vv}
        assert points['website_point']==raw['adjusted_projection']and points['provider_point']==raw['raw_projection']
        member=member_map.get((*key,pop));qualified=bool(member and member.get('ranking_cutoff')is not None and member['ranking_cutoff']<=proof.timestamp()and(member.get('latest_available')is None or member['latest_available']<member['ranking_cutoff']))
        expected=dict(source_game_id=m['game_id'],source_player_id=m['player_id'],source_row_index=i,game_id=key[0],player_id=key[1],target=key[2],population=pop,position=m['position'],line=m['line'],line_from=m['line_from'],
            side=m.get('lean'),original_side=m.get('lean'),top_over=m.get('top_over'),top_under=m.get('top_under'),kickoff=m['kickoff'],season=2026,week=7,
            actual=int(y)if y is not None else None,label_state=status,participation='VERIFIED_PLAYED_POSITIVE_PHYSICAL'if status=='SUPPORTED'else'UNKNOWN',
            prediction=raw['adjusted_projection'],raw_prediction=raw['raw_projection'],source_cohorts=list(member['cohorts'])if qualified else[],
            cohort_state='MATCHED_RECONSTRUCTED_PRIOR_CLOCK'if qualified else'MEMBERSHIP_UNKNOWN',ranking_cutoff=member.get('ranking_cutoff')if qualified else None,
            price=None,probability=None,server_retained_by=p['source_clock'],recorded_capture=p['recorded_internal_capture'],retained_reference_indices=[i for i,_ in vv])
        assert j==expected,(i,[k for k in expected if j.get(k)!=expected[k]]);joined_fields+=len(expected);expected_join[i]=expected
    assert decoded==924
    expected=[];by=collections.defaultdict(list)
    for r in joined:
        for strategy in STRATEGIES:
            point=r['raw_prediction']if strategy==RAW else r['prediction'];line=Decimal(str(r['line']))
            if strategy=='original':side=r['side']
            elif strategy=='alwaysOver':side='over'
            elif strategy=='alwaysUnder':side='under'
            else:side=None if point is None or point==line else'over'if point>line else'under'
            y=r['actual'];state='ABSTAIN'if side is None else'UNKNOWN_PARTICIPATION'if r['participation']=='UNKNOWN'else'MISSING_ACTUAL'if y is None else'PUSH'if y==line else'WIN'if(y>line if side=='over'else y<line)else'LOSS'
            v=dict(r,strategy=strategy,selected_side=side,statistical_state=state,settlement_state='UNRESOLVED_CONTRACT'if side else'NOT_SELECTED',ranking_point=point,net_return=None);expected.append(v);by[strategy].append(v)
    graded=rows(a.private_root/'GRADED_ROWS.json.gz');assert digest(a.private_root/'GRADED_ROWS.json.gz')==run['private_grade_sha256'];assert graded==expected and len(graded)==2310
    def within(r,name):
        if name=='ALL':return True
        if name=='ORIGINAL_SELECTED':return r['original_side']in('over','under')
        if name=='ORIGINAL_ABSTAINED':return r['original_side']not in('over','under')
        if name.startswith('position:'):return r['position']==name.split(':',1)[1]
        if name.startswith('source:'):return r['line_from']==name.split(':',1)[1]
        if name=='original_top_over':return bool(r['top_over'])
        if name=='original_top_under':return bool(r['top_under'])
        if name=='cohort_unknown':return not r['source_cohorts']
        assert name.startswith('reconstructed:');return name.split(':',1)[1]in r['source_cohorts']
    kvals=rows(a.private_root/'FROZEN_K_MEMBERSHIPS.json.gz');freeze=read(a.public_root/'K_MEMBERSHIP_FREEZE_RECEIPT.json');assert digest(a.private_root/'FROZEN_K_MEMBERSHIPS.json.gz')==freeze['sha256'];assert len(kvals)==450
    kmap={}
    for k in kvals:
        pool=[r for r in by[k['strategy']]if r['target']==k['target']and r['selected_side']and r['ranking_point']is not None and(k['rank_scope']=='Combined'or r['selected_side']==k['rank_scope'])]
        order=sorted(pool,key=lambda r:(-abs(r['ranking_point']-Decimal(str(r['line']))),r['game_id']or'',r['player_id']or'',r['target'],str(r['line']),r['source_row_index']))
        assert k['eligible_pool_n']==len(pool)and k['source_row_indices']==[r['source_row_index']for r in order[:k['K']]]
        kmap[k['strategy'],k['target'],k['rank_scope'],k['K']]=k
    cache={};ci_count=0;view_checks=0;triads=collections.defaultdict(list)
    def interval(rr):
        g=collections.defaultdict(lambda:[0,0])
        for r in rr:
            if r['statistical_state']in('WIN','LOSS'):g[r['game_id']][0]+=r['statistical_state']=='WIN';g[r['game_id']][1]+=1
        values=tuple(tuple(g[k])for k in sorted(g));n=sum(v[1]for v in values);estimate=sum(v[0]for v in values)/n if n else None
        if len(g)<8:return estimate,None,len(g)
        if values not in cache:
            rng=np.random.Generator(np.random.PCG64(1703));draw=rng.integers(0,len(g),size=(500,len(g)));weights=np.stack([np.bincount(row,minlength=len(g))for row in draw]);z=np.asarray(values);rates=(weights@z[:,0])/(weights@z[:,1]);cache[values]=np.percentile(rates,[2.5,97.5],method='linear').tolist()
        return estimate,cache[values],len(g)
    scores=read(a.public_root/'SCORES.json')
    for view in scores:
        pool=[r for r in by[view['strategy']]if view['target']=='ALL'or r['target']==view['target']]
        if view['K']is None:pool=[r for r in pool if within(r,view['cohort_id'])];chosen=[r for r in pool if r['selected_side']]
        else:
            k=kmap[view['strategy'],view['target'],view['rank_scope'],view['K']];source={r['source_row_index']:r for r in pool};chosen=[source[i]for i in k['source_row_indices']]
        rr=[r for r in chosen if view['side']=='Combined'or r['selected_side']==view['side']];c=collections.Counter(r['statistical_state']for r in rr);m=view['selection_metrics'];w,l=c['WIN'],c['LOSS'];n=w+l
        assert view['forecast_rows']==len(rr)and view['n']==n and m['WIN']==w and m['LOSS']==l and m['PUSH']==c['PUSH']
        assert m['status_counts']=={s:c[s]for s in m['status_counts']}
        close(m['hit_rate'],w/n if n else None);close(view['selection_loss_rate'],l/n if n else None)
        assert m['selection_pool_count']==len(pool)and m['abstentions_outside_selected_partition']==sum(r['selected_side']is None for r in pool)
        eligible=len(pool)if view['K']is None else k['eligible_pool_n'];assert m['eligible_rank_pool_n']==eligible;close(m['selection_coverage'],len(rr)/eligible if eligible else None)
        assert view['query_membership_sha256']==hashlib.sha256(canon(sorted(r['source_row_index']for r in rr))).hexdigest()
        assert view['unique_games']==len({r['game_id']for r in rr})and view['unique_players']==len({r['player_id']for r in rr})and view['unique_player_games']==len({(r['game_id'],r['player_id'])for r in rr})
        estimate,limits,ngame=interval(rr);close(m['game_uncertainty']['estimate'],estimate);close(m['game_uncertainty']['game_interval'],limits);assert m['game_uncertainty']['game_clusters']==ngame;ci_count+=limits is not None
        assert m['game_uncertainty']['week_interval']is None and m['bookmaker_settlement_status_counts']=={'UNRESOLVED_CONTRACT':len(rr)}
        assert all(v is None for k,v in m['returns'].items()if k!='reason')and all(v is None for k,v in m['probability_scores'].items()if k!='reason')
        key=tuple(view[k]for k in('strategy','target','cohort_id','K','rank_scope'));triads[key].append(view);view_checks+=1
    assert len(scores)==run['canonical_score_views']==4980
    for vv in triads.values():
        sides={r['side']:r for r in vv};assert len(vv)==3 and set(sides)=={'over','under','Combined'}
        assert sides['Combined']['forecast_rows']==sides['over']['forecast_rows']+sides['under']['forecast_rows']
        assert sides['Combined']['n']==sides['over']['n']+sides['under']['n']
        for field in sides['Combined']['selection_metrics']['status_counts']:assert sides['Combined']['selection_metrics']['status_counts'][field]==sum(sides[x]['selection_metrics']['status_counts'][field]for x in('over','under'))
    original=[r for r in by['original']if r['selected_side']];assert collections.Counter(r['statistical_state']for r in original)==dict(WIN=183,LOSS=96,UNKNOWN_PARTICIPATION=6)
    summary=[]
    for strategy,rr in by.items():
        for side in('over','under','Combined'):
            ss=[r for r in rr if r['selected_side']and(side=='Combined'or r['selected_side']==side)];c=collections.Counter(r['statistical_state']for r in ss);n=c['WIN']+c['LOSS'];summary.append(dict(strategy=strategy,side=side,selected=len(ss),wins=c['WIN'],losses=c['LOSS'],n=n,hit_rate=c['WIN']/n if n else None,unknown=c['UNKNOWN_PARTICIPATION']))
    receipt=dict(state='PASS_INDEPENDENT_FULL_PROVIDER_POOL_JOINS_GRADES_AND_SIDES',checked_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        source_protocol_sha256=digest(a.public_root/'FROZEN_PROTOCOL.json'),score_sha256=digest(a.public_root/'SCORES.json'),grade_sha256=run['private_grade_sha256'],
        original_eligible_metadata_rows=462,provider_provenance=dict(dk=441,sleeper=21),retained_reference_product_views_decoded=decoded,independent_join_fields_checked=joined_fields,
        original_selections_preserved=285,original_abstentions_preserved=177,supported_existing_outcomes=446,unknown_appearances=16,strategy_grade_views=len(graded),canonical_score_views=view_checks,
        actual_side_triads=len(triads),frozen_per_category_K_lists=len(kvals),game_intervals_independently_checked=ci_count,independent_bootstrap_masks=len(cache),all_method_sides=summary,
        actual_push_void_count=0,fixture_push_void_evidence='Existingexact-coreindependentreceipt50cases;syntheticonly,norealvoidclaim.',
        limits=['Only2026W7thirteen-gameprovider-labelledthresholdpool;notcompleteNFLseasonoralltestedV2methods.',
            'Sourcequote/internalcapturevintagesunverified;notauthenticatedpricedexecutableoffers.',
            'Savedrawprojectionisfieldattributiononly;notauthenticatedexternalsupplieralgorithm.',
            'Cohorts/Kareexposedretrospectivechoices,notoriginalstar/Kissuance;oneweekuncertaintyinsufficient.'],
        new_fits=0,new_inference=0,new_forecasts=0,new_current2026_Week8_outcomes_read=0,
        resource=dict(wall_seconds=time.monotonic()-start,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024))
    with a.output.open('x')as f:json.dump(receipt,f,indent=2);f.write('\n')
    print(json.dumps({k:receipt[k]for k in('state','strategy_grade_views','canonical_score_views','actual_side_triads','game_intervals_independently_checked','resource')}))


if __name__=='__main__':main()
