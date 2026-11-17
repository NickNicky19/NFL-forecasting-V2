"""Readable actual-side tables and metadata supplement; retained grades only."""
import argparse,collections,csv,gzip,hashlib,json,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from nfl_v2 import prop_side_projection as p

def dump(path,value):
    with Path(path).open('x')as f:json.dump(value,f,sort_keys=True,indent=2);f.write('\n')
def csv_write(path,rows):
    with Path(path).open('x',newline='')as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def fmt(r):
    if r is None:return'Unavailable'
    m=r['selection_metrics'];c=m['status_counts'];n=r['n'];rate=m['hit_rate']
    return f"{r['forecast_rows']} selected; {c['WIN']}W/{c['LOSS']}L/{c['PUSH']}P; {n} decided; "+(f'{100*rate:.2f}%'if rate is not None else'N/A')+f"; {m['denominators']['unresolved']} unknown"

def main(root,private_root,refresh_readable_only=False):
    root,priv=Path(root),Path(private_root);start=time.monotonic();protocol=p.load(root/'FROZEN_PROTOCOL.json');receipt=p.load(root/'RUN_RECEIPT.json');scores=p.load(root/'SCORES.json');source_sha=p.sha(root/'SCORES.json')
    if source_sha!=receipt['score_sha256']:raise ValueError('canonical score bytes changed')
    m=p.load(priv/'INPUT_BINDINGS_PRIVATE.json');records=json.loads(gzip.decompress(Path(m['graded']).read_bytes()))['rows'];tag_packet=json.loads(gzip.decompress(Path(m['cohort_tags']).read_bytes()));tags=p.tag_rows(tag_packet)
    if p.sha(m['graded'])!=protocol['source_grade_sha256']or p.sha(m['cohort_tags'])!=protocol['cohort_tags_sha256']:raise ValueError('frozen source bytes changed')
    km=json.loads(gzip.decompress((priv/'FROZEN_K_MEMBERSHIPS.json.gz').read_bytes()))['rows'];kindex={(r['strategy'],r['target'],r['rank_scope'],r['K']):r['source_row_indices']for r in km};by=collections.defaultdict(dict)
    for r in records:by[r['strategy']][r['source_row_index']]=r
    def match(r):
        if r['K']is not None:rows=[by[r['strategy']][i]for i in kindex[r['strategy'],r['target'],r['rank_scope'],r['K']]]
        else:rows=[q for q in by[r['strategy']].values()if(r['target']=='ALL'or q['target']==r['target'])and p.in_cohort(q,r['cohort_id'],tags)]
        return[q for q in rows if q['selected_side']in('over','under')and(r['side']=='Combined'or q['selected_side']==r['side'])]
    def dimensions(r):return tuple(r[k]for k in('strategy','target','side','cohort_id','rank_scope','K'))
    weekly={dimensions(r):r for r in scores if r['time_panel_id']==p.PERIODS[0]};supp=[];flat=[]
    for r in scores:
        rr=match(r);hash_=hashlib.sha256(p.canonical(sorted(q['source_row_index']for q in rr))).hexdigest()
        if hash_!=r['query_membership_sha256']or len(rr)!=r['forecast_rows']:raise ValueError('frozen membership replay mismatch')
        decided=[q for q in rr if q['statistical_state']in('WIN','LOSS')]
        base=weekly[dimensions(r)];alias=base['record_id']if r['season_alias_of_week_view']else None
        if alias and(r['query_membership_sha256'],r['selection_metrics']['status_counts'])!=(base['query_membership_sha256'],base['selection_metrics']['status_counts']):raise ValueError('season alias is not exact same W7 source')
        s=dict(record_id=r['record_id'],source_record_id=r['record_id'],unique_players=len({q['player_id']for q in rr}),unique_player_games=len({(q['game_id'],q['player_id'])for q in rr}),
            unique_games=len({q['game_id']for q in rr}),decided_unique_players=len({q['player_id']for q in decided}),decided_unique_player_games=len({(q['game_id'],q['player_id'])for q in decided}),
            decided_unique_games=len({q['game_id']for q in decided}),registered_week_count=1,registered_weeks=[7],selected_week_count=int(bool(rr)),decided_week_count=int(bool(decided)),
            season_alias_of_week_view=r['season_alias_of_week_view'],alias_of_record_id=alias,statistic_period='full_game',season_type='REG',overtime=True,query_membership_sha256=hash_)
        supp.append(s);sm=r['selection_metrics'];c=sm['status_counts'];ci=sm['game_uncertainty']['game_interval']
        flat.append(dict(record_id=r['record_id'],strategy=r['strategy'],target=r['target'],actual_selected_side=r['side'],cohort=r['cohort_id'],time_panel=r['time_panel_id'],K=r['K'],rank_scope=r['rank_scope'],
            source_selected_rows=r['forecast_rows'],decided=r['n'],wins=c['WIN'],losses=c['LOSS'],pushes=c['PUSH'],unknown=c['UNKNOWN_PARTICIPATION'],missing_actual=c['MISSING_ACTUAL'],DNP=c['DNP'],pending=c['PENDING'],hit_rate=sm['hit_rate'],selection_loss_rate=r['selection_loss_rate'],
            unique_players=s['unique_players'],unique_player_games=s['unique_player_games'],unique_games=s['unique_games'],registered_weeks='[7]',decided_week_count=s['decided_week_count'],
            original_conditional_pool=sm['selection_pool_count'],full_forecast_feed_count=sm['full_forecast_feed_count'],provider_labelled_threshold_count=sm['provider_labelled_finite_threshold_count'],site_generated_threshold_count=sm['site_generated_threshold_count'],
            original_fullfeed_coverage=sm['original_fullfeed_coverage'],original_provider_threshold_coverage=sm['original_provider_threshold_coverage'],conditional_selection_coverage=sm['conditional_selection_coverage'],eligible_rank_pool=sm.get('eligible_rank_pool_n'),
            game_bootstrap95_low=None if ci is None else ci[0],game_bootstrap95_high=None if ci is None else ci[1],game_uncertainty_status=sm['game_uncertainty']['game_interval_status'],week_uncertainty_status=sm['game_uncertainty']['week_interval_status'],
            probability=None,decimal_price=None,Brier=None,log_loss=None,EV=None,ROI=None,drawdown=None,book_settlement='UNRESOLVED_CONTRACT',null_reason=r['null_reason'],
            alias_of_record_id=alias,source_score_artifact='SCORES.json',source_score_sha256=source_sha))
    if not refresh_readable_only:
        dump(root/'METADATA_SUPPLEMENT.json',dict(source_score_sha256=source_sha,source_protocol_sha256=p.sha(root/'FROZEN_PROTOCOL.json'),source_grade_sha256=protocol['source_grade_sha256'],rows=supp))
        csv_write(root/'ALL_ACTUAL_SIDE_VIEWS.csv',flat);csv_write(root/'TOPK_BY_CATEGORY.csv',[r for r in flat if r['K']is not None]);csv_write(root/'COHORT_BY_CATEGORY_SIDE.csv',[r for r in flat if r['K']is None and r['cohort']!='ALL'])
    index={r['record_id']:r for r in scores};metadata={r['record_id']:r for r in supp}
    def find(target,side,cohort='ALL',strategy='original',rank_scope=None,K=None):return next(r for r in scores if(r['strategy'],r['target'],r['side'],r['cohort_id'],r['rank_scope'],r['K'],r['time_panel_id'])==(strategy,target,side,cohort,rank_scope,K,p.PERIODS[0]))
    lines=['# Original selections: actual Over, Under and Combined\n',
        'These are statistical threshold results on the same original 285 preselected cases from thirteen Week 7 games. The original full forecast feed has 1,419 ordinary-stat rows: 462 provider-labelled finite thresholds (441 DK, 21 Sleeper) and 957 site-generated thresholds. Original selection coverage is 285/1,419=20.08%; within the provider-labelled threshold pool it is 285/462=61.69%. The four controls were evaluated only on the conditional 285-case pool, not all 1,419. Provider labels do not authenticate quote clocks, prices, jurisdiction or settlement.\n',
        'Every table groups the actual chosen side. Combined counts are the sum of Over and Under; percentages are calculated from summed wins/decided cases, never averaged across sides. Statistical pushes, unknown participation and missing labels remain separate. All book settlement is unresolved and all probabilities, Brier/log loss, EV, returns and ROI are unavailable. The saved-point control uses retained source precision; strict unrounded P1 is unavailable because the original producer rounded before retention.\n',
        '| Category | Actual Over: selected; W/L/P; decided; hit; unknown | Actual Under: selected; W/L/P; decided; hit; unknown | Combined |',
        '|---|---|---|---|']
    for target in('ALL',)+p.TARGETS:lines.append('|'+target+'|'+'|'.join(fmt(find(target,side))for side in p.SIDES)+'|')
    lines+=['|nick-chart-ppr-v1|Unavailable: no matching chart-threshold selection contract|Unavailable|Unavailable|','|anytime_td|Unavailable: no qualified event-offer/selection contract in numeric panel|Unavailable|Unavailable|','',
        'These ten categories are the supported source slice; the two unsupported targets have null counts/rates in [UNAVAILABLE_CELLS.json](UNAVAILABLE_CELLS.json), outside canonical scores. Supported empty sides, such as always-Under’s Over bucket, have zero selected cases and N/A rates. They are not an error-free forecast.','',
        '| Strategy | Actual Over | Actual Under | Combined |','|---|---|---|---|']
    for strategy in p.first.STRATEGIES:lines.append('|'+strategy+'|'+'|'.join(fmt(find('ALL',side,strategy=strategy))for side in p.SIDES)+'|')
    lines+=['','[Every method/category/actual-side/cohort/time view](ALL_ACTUAL_SIDE_VIEWS.csv) · [Cohort/category/side CSV](COHORT_BY_CATEGORY_SIDE.csv) · [All top-K views CSV](TOPK_BY_CATEGORY.csv) · [Unique-player/game and explicit time-alias supplement](METADATA_SUPPLEMENT.json).','',
        'The 285 original selections cover 136 unique players and 136 player-games across thirteen games in one week; 130 player-games have a qualified outcome and six remain appearance-unknown. Blank CSV metric/price cells represent null unavailable values, not zeros. The 2026 season view is an exact alias of this partial Week 7 slice, not a season-to-date or full-season evaluation. Each season-alias record explicitly points to its weekly record. Do not pool those aliases, strategies, overlapping cohorts or summary rows into additional NFL observations. The underlying population remains 285 player-game-target selections, including six unknown appearance cases; unique players and player-games differ from selection counts and are supplied for every view.','',
        'Previously saved Top flags remain original recorded subsets, with no replacements for the excluded earlier game. Reconstructed top-player/workload groups use earlier-availability profiles but were actually assembled after the games; they are diagnostic groups, not authentic original star lists. The ranking cutoff is later than the internal recorded capture clock, so it does not establish information available at that internal decision. Missing memberships remain an explicit cohort.','',
        'The new K 6/10/20 subsets are separately frozen per category, with Combined, Over-only and Under-only candidate pools. They rank absolute saved-point minus line gaps at retained precision with stable identity ties. Unknown outcomes, DNP and missing labels do not affect membership. They are NEW_RETRO_SUBSET within the already selected 285 cases, not original issued K, all offers, a full fourteen-game week or an evaluated live policy. No raw gaps are ranked across categories.','',
        'Game-cluster bootstrap intervals use 500 draws/seed 1703 when at least eight decided games contribute; otherwise they are unavailable. There is one supported week, so week intervals remain unavailable. These exposed descriptive sensitivity intervals are not adjusted for selection or multiplicity. Different selected-side pools do not establish a universal better side.','',
        'No outcomes were rejoined, no threshold was regraded and no model or forecast changed in this projection. All figures reuse the retained 1,140 strategy-grade rows. [Frozen protocol](FROZEN_PROTOCOL.json), [side-count reconciliation](ACTUAL_SIDE_RECONCILIATION.json) and [run receipt](RUN_RECEIPT.json) bind the sources and views.']
    (root/'README.md').write_text('\n'.join(lines)+'\n')
    lines=['# New retrospective per-category top-K subsets\n','Original strategy only is displayed below. All four strategies, three ranking scopes, three actual sides and both explicit time aliases are in [TOPK_BY_CATEGORY.csv](TOPK_BY_CATEGORY.csv). Membership never uses wins or labels. These lists are not original issued Top-K selections.\n','| Category | K | Ranking candidate pool | Actual Over | Actual Under | Combined | Selected picks | Unique players | Player-games |','|---|---:|---|---|---|---|---:|---:|---:|']
    for target in p.TARGETS:
        for k in p.K_VALUES:
            for scope in p.RANK_SCOPES:
                r=find(target,'Combined',cohort='NEW_RETRO_PICK_SUBSET',rank_scope=scope,K=k);s=metadata[r['record_id']]
                lines.append('|'+target+'|'+str(k)+'|'+scope+'|'+'|'.join(fmt(find(target,side,cohort='NEW_RETRO_PICK_SUBSET',rank_scope=scope,K=k))for side in p.SIDES)+f"|{r['forecast_rows']}|{s['unique_players']}|{s['unique_player_games']}|")
    (root/'TOPK_BY_CATEGORY.md').write_text('\n'.join(lines)+'\n')
    lines=['# Cohorts: picks, players and player-games\n','Original strategy, all ten supported categories combined. Category-specific actual sides and all controls are in [COHORT_BY_CATEGORY_SIDE.csv](COHORT_BY_CATEGORY_SIDE.csv). Reconstructed star/workload groups are diagnostics, separate from original saved Top flags.\n','| Cohort | Actual side | Selected picks | Unique players | Player-games | Statistical result |','|---|---|---:|---:|---:|---|']
    for cohort in receipt['cohort_names']:
        for side in p.SIDES:
            r=find('ALL',side,cohort=cohort);s=metadata[r['record_id']];lines.append(f"|{cohort}|{side}|{r['forecast_rows']}|{s['unique_players']}|{s['unique_player_games']}|{fmt(r)}|")
    (root/'COHORTS.md').write_text('\n'.join(lines)+'\n')
    dump(root/('READABLE_REPORT_REFRESH_RECEIPT.json' if refresh_readable_only else 'REPORT_RECEIPT.json'),dict(state='COMPLETE_RETAINED_VIEW_REPORT_AND_METADATA_ONLY',source_score_sha256=source_sha,score_views=len(scores),metadata_rows=len(supp),explicit_season_aliases=sum(bool(r['alias_of_record_id'])for r in supp),code_sha256=p.sha(__file__),new_threshold_grades=0,new_fits=0,new_forecasts=0,wall_seconds=time.monotonic()-start))
    print(json.dumps(dict(score_views=len(scores),metadata_rows=len(supp),source_score_sha256=source_sha,wall_seconds=time.monotonic()-start)))

if __name__=='__main__':
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('--root',required=True,type=Path);a.add_argument('--private-root',required=True,type=Path);a.add_argument('--refresh-readable-only',action='store_true');args=a.parse_args();main(args.root,args.private_root,args.refresh_readable_only)
