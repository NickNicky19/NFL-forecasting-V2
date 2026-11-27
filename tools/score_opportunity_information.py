"""Target-aware opportunity exports into the unchanged pinned M2/C evaluator.

No fitting, acquisition or new grader. Restricted offers stay in memory;
only aggregate results, source commitments and hashes are written.
"""
from __future__ import annotations
import argparse, ast, collections, copy, math, pathlib, resource, sys, time
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools import score_qb_pass_mix_information as inherited

BASE = ROOT/'reports/information-skill-follow-through-01/B/opportunity-v1'
METHODS = ('OPP_BASE', 'OPP_MEAN', 'OPP_JOINT', 'DIRECT_ATT')
TARGETS = ('pass_att', 'pass_cmp')
CONTRASTS = (('OPP_MEAN', 'OPP_BASE'), ('OPP_JOINT', 'OPP_MEAN'),
             ('OPP_JOINT', 'OPP_BASE'), ('DIRECT_ATT', 'OPP_BASE'))
TIER = inherited.TIER


def windows(rows):
    return [('ALL', rows)]+[(str(w), [r for r in rows if r['week']==w]) for w in range(5,10)]


def inherited_pairer(ev, paired_losses, target):
    """Reuse the trusted comparison function; change only result target label."""
    tree = ast.parse(pathlib.Path(inherited.__file__).read_text())
    main = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name=='main')
    node = next(n for n in main.body if isinstance(n, ast.FunctionDef) and n.name=='paired')
    namespace = dict(ev=ev, paired_losses=paired_losses, math=math)
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(inherited.__file__), 'exec'), namespace)
    def paired(*args, **kwargs):
        result = namespace['paired'](*args, **kwargs)
        result['target'] = target
        return result
    return paired


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('sources','scorer-source','interval-source'):
        parser.add_argument('--'+name,type=pathlib.Path,required=True)
    parser.add_argument('--predictions',type=pathlib.Path,default=BASE/'wave-v1/predictions')
    parser.add_argument('--existing-att-grades',type=pathlib.Path)
    parser.add_argument('--existing-cmp-grades',type=pathlib.Path)
    parser.add_argument('--out',type=pathlib.Path,default=BASE/'evaluation-v1')
    args=parser.parse_args()
    if args.out.exists():raise FileExistsError('Versioned outputs only; no overwrite or implicit retry.')
    if not args.out.resolve().is_relative_to(BASE.resolve()):raise ValueError('Owned opportunity subtree only.')
    ev,_=inherited.load_evaluator()
    from nfl_v2 import player_context_matchup as ctx, opportunity_information as oi
    from nfl_v2.paired_uncertainty import paired_losses
    design=ev.read(BASE/'FROZEN_DESIGN_V1.json')
    qualified=design['qualified_source']
    for field,digest_field in [('opportunity','sha256'),('context','context_sha256')]:
        if ev.sha(ROOT/qualified[field])!=qualified[digest_field]:raise ValueError('Frozen opportunity input hash changed.')
    started,cpu=time.monotonic(),time.process_time()
    def check():
        if time.process_time()-cpu>180 or time.monotonic()-started>600:raise RuntimeError('Frozen evaluation CPU180/wall600 cap; preserve state.')
        if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024>1073741824:raise RuntimeError('Evaluation RSS1GiB cap.')
    adapter=ev.module(ROOT/'reports/w1w9-comparison-closure-01/B/common-intake/COMMON_SCORER_PARITY_ADAPTER_V1.py','OPP_PINNED_C_ADAPTER')
    status,summary,_=adapter.load_common_functions(args.scorer_source,args.interval_source)
    fixtures=adapter.boundary_fixtures(status)
    inventory=ev.module(ROOT/'reports/player-context-matchup-01/B/independent/inventory_retained_qb_offers_v1.py','OPP_EXISTING_OFFER_ITERATOR')
    sources={int(w):pathlib.Path(p) for w,p in ev.read(args.sources).items()}
    if set(sources)!=set(range(5,10)):raise ValueError('Exact frozen native W5–9 sources required.')
    prior=ev.read(inherited.M2_PATH.parent/'EXECUTION_INPUT_BINDINGS_V1.json')
    for row in prior['source_files']:
        if ev.sha(sources[row['week']])!=row['sha256']:raise ValueError('Native source differs from inherited panel.')
    for name,key in [('scorer_source','C_scorer_sha256'),('interval_source','C_interval_sha256')]:
        if ev.sha(getattr(args,name))!=prior[key]:raise ValueError('Pinned C implementation hash mismatch.')
    offers_all=[r for w,p in sorted(sources.items()) for r in inventory.iter_offers(p,w) if r['target'] in TARGETS]
    offers={t:[r for r in offers_all if r['target']==t] for t in TARGETS}
    for target,rr in offers.items():
        if len(rr)!=142 or len({ev.key(r) for r in rr})!=142:raise ValueError('Expected identical142 '+target+' offers.')
        if collections.Counter(r['week']for r in rr)!={5:28,6:28,7:28,8:28,9:30}:raise ValueError('Weekly native mask changed.')
        if any(r['actual']is None or r['label_state']!='SUPPORTED' or r['participation']!='VERIFIED_PLAYED_POSITIVE_PHYSICAL' or float(r['line'])%1!=.5 for r in rr):raise ValueError('Qualified explicit counts/halfpoint source contract changed.')
    prediction_files=sorted(args.predictions.glob('2026-W*.json.gz'))
    if len(prediction_files)!=9:raise ValueError('Nine frozen numerical origin files required.')
    predictions=[r for p in prediction_files for r in ev.read(p)['rows'] if r['method']in METHODS and r['target']in TARGETS]
    predmap={(r['method'],ev.key(r)):r for r in predictions}
    if len(predmap)!=len(predictions):raise ValueError('Duplicate exact forecast identity.')
    queries=ctx.load_inputs(ROOT/qualified['context']);querymap={(r['game_id'],r['player_id']):r for r in queries}
    for target in TARGETS:
        expected={(r['game_id'],r['player_id'],target)for r in queries if r['season']==2026}
        for method in METHODS:
            if {ev.key(r)for r in predictions if r['method']==method and r['target']==target}!=expected:raise ValueError('Different315 numerical query population '+method+'/'+target)
    origins={w:min(ev.dt(r['fit_cutoff'])for r in predictions if r['week']==w)for w in range(1,10)}
    for row in predictions:
        if ev.dt(row['fit_cutoff'])>ev.dt(row['kickoff']) or ev.dt(row['feature_cutoff'])!=ev.dt(row['kickoff']):raise ValueError('Forecast fit/query chronology mismatch.')
        if not math.isfinite(row['mean']) or row['mean']<0:raise ValueError('Invalid typed count mean.')
        key=ev.key(row);base=predmap['OPP_BASE',(key[0],key[1],row['target'])]
        conversion=row['components']['conversion_fixed']
        if (not math.isfinite(conversion)or not 0<=conversion<=1 or
                conversion!=base['components']['conversion_fixed']):raise ValueError('Frozen conversion probability changed across opportunity arms.')
        att=predmap[row['method'],(key[0],key[1],'pass_att')]
        cmp=predmap[row['method'],(key[0],key[1],'pass_cmp')]
        if abs(cmp['mean']-att['mean']*conversion)>1e-8:raise ValueError('ATT/CMP means violate fixed-conversion thinning.')
        parent=base['components']['parent_attempt_law']
        if row['method']=='OPP_BASE'and row['target']=='pass_att':
            if row['law'].get('kind')!='gamma_poisson_count'or row['law']['shape']!=parent['shape']or row['mean']!=parent['mean']:raise ValueError('OPP_BASE changed the unchanged parent attempt law.')
        if row['method']=='OPP_MEAN'and row['target']=='pass_att':
            joint=predmap['OPP_JOINT',(key[0],key[1],'pass_att')]
            if row['law'].get('kind')!='gamma_poisson_count'or row['law']['shape']!=parent['shape']or abs(row['mean']-joint['mean'])>1e-8:raise ValueError('Mean-isolation product changed parent shape or joint mean.')
    law_cache={}
    def common_row(offer,selected_side,*,appearance,status):
        # The inherited adapter intentionally admits completions only. Supply
        # an explicit separate official-QB-attempt contract, never mislabel an
        # attempt as a completion to evade its target guard. C's status and
        # summary functions remain byte-identical for both admitted contracts.
        if offer['target']=='pass_cmp':return adapter.common_row(offer,selected_side,appearance=appearance,status=status)
        if offer['target']!='pass_att'or offer['position']!='QB':raise ValueError('Unsupported explicit opportunity role/target')
        return dict(game_id=offer['game_id'],player_id=offer['player_id'],category='pass_att',position='QB',season=offer['season'],week=offer['week'],selected_side=selected_side,actual=offer['actual'],appearance=appearance,status=status,line=offer['line'],comparator='STRICT_OVER_UNDER',period='FULL_GAME_INCLUDING_OT',scoring_contract_id='OFFICIAL_FULL_GAME_PASS_ATTEMPTS',record_kind='ACTUAL_OFFER',evidence_tier='TIMING_UNVERIFIED_ACTUAL_LINE_DIAGNOSTIC',source_scope='Existing B qualified native W5-9 ATT diagnostic; attempts exclude sacks; no new quote admission')
    def law_for(row):
        key=row['method'],ev.key(row)
        if key not in law_cache:law_cache[key]=oi.restore_law(row['law'])
        return law_cache[key]
    def forecast_row(offer,method,policy,prediction):
        row=common_row(offer,None,appearance='PLAYED',status='UNAVAILABLE_FORECAST')
        row.update(target=offer['target'],category=offer['target'],kickoff=offer['kickoff'],line_from=offer['line_from'],method=method,component_policy=policy,procedure_id=method,point=None,probs=None,available=prediction is not None,unavailable_reason=None if prediction else'MISSING_EXACT_SAVED_FORECAST',fallback=None,parent_fallback=False,attribution='unavailable',original_issuance=False)
        if prediction is not None:
            if prediction.get('actual')is not None and prediction['actual']!=offer['actual']:raise ValueError('Frozen forecast and qualified actual differ.')
            law=law_for(prediction);probs=ctx.exact_probabilities(law,offer['line'])
            if any(not math.isfinite(v)or not 0<=v<=1 for v in probs.values())or abs(sum(probs.values())-1)>1e-9:raise ValueError('Invalid exactline masses.')
            if abs(law.mean-prediction['mean'])>1e-7:raise ValueError('Wrong typed expected count.')
            point=prediction['mean'if policy=='MEAN'else'lower_median']if policy!='LAW'else None
            if point is not None and not math.isfinite(point):raise ValueError('Nonfinite typed point.')
            side=ev.lawside(probs)if policy=='LAW'else'OVER'if point>offer['line']else'UNDER'if point<offer['line']else'ABSTAIN'
            fallback=prediction.get('fallback')
            row.update(procedure_id=prediction['procedure_id'],point=point,probs=probs,selected_side=side,status='ABSTAIN'if side=='ABSTAIN'else'READY',fallback=fallback,parent_fallback=ev.fallback(fallback),attribution='fallback'if ev.fallback(fallback)else'learned')
        row['status']=status(row)
        return row
    tables=[];selective=[];proper=[];broad=[];pairs=[];ownlists=[];commitments=[];calibration=[];imported=[]
    for target in TARGETS:
        check();rr=offers[target]
        raw={(m,p):[forecast_row(o,m,p,predmap.get((m,ev.key(o))))for o in rr]for m in METHODS for p in ('MEAN','MEDIAN','LAW')}
        for method,side in [('ALWAYS_OVER','OVER'),('ALWAYS_UNDER','UNDER')]:
            frame=[]
            for offer in rr:
                row=forecast_row(offer,method,'REGISTERED_DIRECTION',None);row.update(available=True,unavailable_reason=None,selected_side=side,status='READY',attribution='reference');row['status']=status(row);frame.append(row)
            raw[method,'REGISTERED_DIRECTION']=frame
        source_path=args.existing_att_grades if target=='pass_att'else args.existing_cmp_grades
        if source_path:
            digest_key='existing_ATT_grade_sha256'if target=='pass_att'else'existing_CMP_grade_sha256'
            if ev.sha(source_path)!=prior[digest_key]:raise ValueError('Retained rowcontrol source hash mismatch '+target)
            body=ev.read(source_path);existing=body['rows']if isinstance(body,dict)else body
            # Whitelisted source-native controls only. Inaccessible/different-horizon
            # C02/known-target-time laws are not silently imported as main controls.
            allowed={'B0','B2','SAVED_ADJUSTED','SAVED_RAW','EARLIER_LINE_PREVALENCE','ADJUSTED','RAW','COMMON_EXPOSURE'}
            policy_map={'P1_MEAN':'MEAN','P1_LOWER_MEDIAN':'MEDIAN','P2_STATISTICAL_LAW':'LAW',
                        'REGISTERED_DIRECTION':'REGISTERED_DIRECTION','MEAN':'MEAN','MEDIAN':'MEDIAN','LAW':'LAW',
                        'SAVED_ADJUSTED':'SAVED_ADJUSTED','SAVED_RAW':'SAVED_RAW',
                        'EARLIER_LINE_PREVALENCE':'EARLIER_LINE_PREVALENCE','P90':'P90'}
            groups=collections.defaultdict(list)
            for row in existing:
                name=str(row.get('model_key',row.get('method',''))).upper()
                category=row.get('category',row.get('target'))
                if category==target and name in allowed and row.get('policy')in policy_map:groups[name,policy_map[row['policy']]].append(row)
            for (name,policy),source_rows in groups.items():
                lookup={ev.key(r):r for r in source_rows}
                if len(lookup)!=len(source_rows):raise ValueError('Duplicate imported control key.')
                method='RETAINED_'+name;frame=[]
                for offer in rr:
                    old=lookup.get(ev.key(offer));row=forecast_row(offer,method,policy,None)
                    if old is not None:
                        if old['actual']!=offer['actual']or old['line']!=offer['line']or old.get('line_from')!=offer['line_from']:raise ValueError('Control source/line/outcome mismatch.')
                        row.update({k:old.get(k)for k in ('point','probs','fallback','procedure_id','unavailable_reason')});row.update(selected_side=old.get('selected_side'),available=old.get('available',True),attribution=old.get('attribution','reference'),parent_fallback=ev.fallback(old.get('fallback')));row['status']=status(row)
                    frame.append(row)
                raw[method,policy]=frame;imported.append(dict(target=target,method=method,policy=policy,source_rows=len(source_rows)))
        inherited_report=inherited.inherited_table(ev,summary,raw)
        def table(method,policy,window,frame,mode='RAW'):
            result=inherited_report(method,policy,window,frame,mode=mode)
            result.update(record_id='B-OPP-EVAL-'+ev.digest([target,method,policy,window,mode])[:24],category=target,target=target,evaluation_panel_id='B-OPP-2026-NATIVE-QB142-'+target,canonical_source_view=method in METHODS,reused_forecasts=method not in METHODS)
            return result
        for (method,policy),frame in raw.items():
            tables.extend(table(method,policy,w,x)for w,x in windows(frame))
            if method in METHODS:
                for w,x in [('DK_ONLY',[r for r in frame if r['line_from']=='dk']),('SLEEPER_ONLY',[r for r in frame if r['line_from']=='sleeper']),('LEARNED_ONLY',[r for r in frame if r['attribution']=='learned']),('FALLBACK_ONLY',[r for r in frame if r['attribution']=='fallback'])]:tables.append(table(method,policy,w,x))
        selective_methods=list(METHODS)+[m for m in ('RETAINED_B0','RETAINED_B2')if(m,'LAW')in raw and any(r.get('probs')is not None for r in raw[m,'LAW'])]
        selected_frames={}
        for method in selective_methods:
            frame=raw[method,'LAW'];cal=[]
            for w in range(5,10):
                subset=[r for r in ev.calibrated(frame,origins[w])if r['week']==w];cal.extend(subset)
                calibration.append(dict(target=target,method=method,week=w,origin=origins[w].isoformat(),n_min=min(r['calibration_n']for r in subset),n_max=max(r['calibration_n']for r in subset)))
            for n,d,name in [(1,1,'COVERAGE_100'),(1,2,'COVERAGE_50'),(1,4,'COVERAGE_25'),(1,10,'COVERAGE_10')]:
                chosen=set().union(*(ev.choose_fraction([r for r in frame if r['week']==w],n,d)for w in range(5,10)));selected_frames[method,name]=ev.apply_selection(frame,chosen)
            for k in (6,10,20):
                for pool in ('Combined','OVER','UNDER'):
                    chosen=set().union(*(ev.choose_top([r for r in frame if r['week']==w],k,pool)for w in range(5,10)));selected_frames[method,f'TOP_{k}_{pool}']=ev.apply_selection(frame,chosen)
            for threshold in (.75,.8,.9):
                for mode,values in [('RAW',frame),('CALIBRATED_RELIABILITY',cal)]:
                    chosen={ev.key(r)for r in values if r['available']and r['selected_side']in('OVER','UNDER')and(r['calibrated_selected_confidence']if mode!='RAW'else r['probs'][r['selected_side'].lower()])>=threshold}
                    selected_frames[method,f'THRESHOLD_{int(threshold*100)}_{mode}']=ev.apply_selection(values,chosen)
            if sum(m==method for m,p in selected_frames)!=19:raise AssertionError('Changed frozen19 selection policies.')
            for (m,policy),values in selected_frames.items():
                if m==method:
                    mode='CALIBRATED_RELIABILITY'if policy.endswith('CALIBRATED_RELIABILITY')else'RAW';selective.extend(table(m,policy,w,x,mode)for w,x in windows(values))
            for mode,values in [('RAW',frame),('CALIBRATED_RELIABILITY',cal)]:
                for w,x in windows(values):
                    q=ev.probstats(x,'probs'if mode=='RAW'else'calibrated_probs')
                    proper.append(dict(record_id='B-OPP-PROB-'+ev.digest([target,method,mode,w])[:24],record_kind='prop_threshold_probability_evaluation',method=method,procedure_id=frame[0]['procedure_id'],category=target,target=target,season=2026,actual_weeks=sorted({r['week']for r in x}),window=w,week_view=w,policy='RAW_EXACT_LINE_LAW'if mode=='RAW'else'CALIBRATED_RAW_SIDE_CORRECTNESS_BERNOULLI',n=q['events'],probability_events=q['events'],brier=q['half_three_state_Brier'],strict_binary_Over_Brier=q['strict_binary_Over_Brier'],log_loss=q['log_loss'],reliability=q,eligible=len(x),available=sum(r['available']for r in x),unavailable=sum(not r['available']for r in x),points=None,games=len({r['game_id']for r in x}),evidence_tier=TIER,primary_admission='LOCAL_NOT_C_ADMITTED',probability_score_contract='HALF_MULTICLASS_BRIER_OVER_UNDER_PUSH_V1',probability_conditioning='MODELED_APPEARANCE',history_regime='H-RECENT',population='FULL_DECLARED_NATIVE_QB_OFFER_BOARD;CONDITIONAL_QUALIFIED_PLAYED_LABELS',evaluation_panel_id='B-OPP-2026-NATIVE-QB142-'+target,membership_SHA256=ev.digest(sorted(ev.key(r)for r in x)),calibration_mode=mode,canonical_source_view=method in METHODS,joint_scope='SELECTED_SIDE_BERNOULLI_NOT_COUNT_CDF'if mode!='RAW'else'RAW_COUNT_LAW'))
        paired=inherited_pairer(ev,paired_losses,target)
        for candidate,control in CONTRASTS:
            for policy in ('MEAN','MEDIAN','LAW'):pairs.append(paired(candidate,policy,raw[candidate,policy],control,policy,raw[control,policy],'MATCHED_COMPLETE_PIPELINE'))
            for metric in ('STRICT_BINARY_OVER_BRIER','EXACT_LINE_LOG_LOSS'):pairs.append(paired(candidate,'LAW',raw[candidate,'LAW'],control,'LAW',raw[control,'LAW'],'MATCHED_COMPLETE_PIPELINE_PROBABILITY',metric))
            for policy in ('MEAN','MEDIAN'):pairs.append(paired(candidate,policy,raw[candidate,policy],control,policy,raw[control,policy],'MATCHED_OFFERED_NUMERICAL','ABSOLUTE_NUMERICAL_ERROR'))
        controls=[(m,p)for m,p in raw if m not in METHODS]
        target_selective={(r['method'],r['policy']):r for r in selective if r['target']==target and r['window']=='ALL'}
        for method in METHODS:
            for policy in ('MEAN','MEDIAN','LAW'):
                for control,cp in controls:pairs.append(paired(method,policy,raw[method,policy],control,cp,raw[control,cp],'MATCHED_FULL_BOARD'))
            for (m,policy),frame in selected_frames.items():
                if m!=method:continue
                commitments.append(dict(target=target,method=m,policy=policy,selected=sum(r['selected_side']in('OVER','UNDER')for r in frame),selected_keys_sha256=ev.digest(sorted(ev.key(r)for r in frame if r['selected_side']in('OVER','UNDER')))))
                for control,cp in controls:pairs.append(paired(method,policy,frame,control,cp,raw[control,cp],'CANDIDATE_OWN_SELECTED_CASES_CONTROL_BROAD_SIDES'))
                candidate_keys={ev.key(r)for r in frame if r['selected_side']in('OVER','UNDER')}
                for control in selective_methods:
                    if control==method:continue
                    reference=selected_frames[control,policy];control_keys={ev.key(r)for r in reference if r['selected_side']in('OVER','UNDER')};left=target_selective[method,policy];right=target_selective[control,policy]
                    fields=('record_id','OVER','UNDER','COMBINED','eligible','available','selected','unknown','fallback_selected','selected_by_week','zero_selection_weeks','selected_membership_SHA256','actual_weeks','distinct_scored_weeks')
                    lr,rrate=left['COMBINED']['rate'],right['COMBINED']['rate']
                    ownlists.append(dict(target=target,candidate=method,control=control,policy=policy,comparison_kind='OWN_LIST',status='DESCRIPTIVE_UNPAIRED_OWN_SELECTED_POPULATIONS',candidate_own_list={k:left[k]for k in fields},control_own_list={k:right[k]for k in fields},selected_overlap=len(candidate_keys&control_keys),candidate_only=len(candidate_keys-control_keys),control_only=len(control_keys-candidate_keys),observed_own_list_rate_difference=lr-rrate if lr is not None and rrate is not None else None,uncertainty='No paired interval for different own lists; matched-case paired contrasts separate.',same_selected_case_reference='PAIRS.json.gz',weekly_own_list_reference='SELECTIVE_TABLES_V1.json.gz',evidence_tier=TIER))
        for method in METHODS:
            group=[r for r in predictions if r['method']==method and r['target']==target]
            for output in ('mean','lower_median'):
                for window,subset in [('ALL',group)]+[(str(w),[r for r in group if r['week']==w])for w in range(1,10)]:
                    nr=[];unknown=0;losses=[];infinite=0
                    for row in subset:
                        q=querymap.get((row['game_id'],row['player_id']));actual=q.get('official_attempts'if target=='pass_att'else'official_completions')if q else None
                        if q is None or not q.get('physical_participation')or not q.get('target_parity')or actual is None:unknown+=1;continue
                        nr.append(dict(point=row[output],actual=actual));law=law_for(row);lp=law.logpmf(actual)if hasattr(law,'logpmf')else math.log(law.pmf(actual))if law.pmf(actual)>0 else-math.inf
                        if math.isfinite(lp):losses.append(-lp)
                        else:infinite+=1
                    broad.append(dict(record_id='B-OPP-NUMERIC-'+ev.digest([target,method,output,window])[:24],record_kind='forecast_evaluation_view',method=method,procedure_id=group[0]['procedure_id'],target=target,category=target,season=2026,window=window,week_view=window,actual_weeks=sorted({r['week']for r in subset}),output=output,eligible=len(subset),available=len(subset),unknown=unknown,games=len({r['game_id']for r in subset}),numerical=ev.numeric(nr),count_log_loss='Infinity'if infinite else sum(losses)/len(losses)if losses else None,law_events=len(losses)+infinite,infinite_count_logloss_cases=infinite,fallback_states=dict(collections.Counter(str(r.get('fallback'))for r in subset)),evidence_tier='CURRENT_VINTAGE_7DAY_CHRONOLOGICAL_RECONSTRUCTION;STAT_ROW_CONDITIONAL_QUERY_UNIVERSE;NO_OFFER_REQUIRED',primary_admission='LOCAL_NOT_C_ADMITTED',history_regime='H-RECENT',evaluation_panel_id='B-OPP-2026-QB-STAT-ROW-NUMERICAL-'+target,canonical_source_view=True))
        # Reuse inherited guards: future labels cannot change earlier calibration;
        # chronological capacity membership cannot change an earlier decision batch.
        fixture=raw['OPP_BASE','LAW'];changed=copy.deepcopy(fixture)
        for row in changed:
            if row['week']==9:row['actual']+=1000;row['status']='LOSS'if row['status']=='WIN'else'WIN'
        before,after=ev.calibrated(fixture,origins[7]),ev.calibrated(changed,origins[7])
        if [r.get('calibrated_probs')for r in before if r['week']<=7]!=[r.get('calibrated_probs')for r in after if r['week']<=7]:raise AssertionError('Future calibration mutation failed.')
        for den in (1,2,4,10):
            for week in range(5,10):
                frame=[r for r in fixture if r['week']==week];chosen=ev.choose_fraction(frame,1,den)
                for kickoff in sorted({r['kickoff']for r in frame},key=ev.dt):
                    prefix=[r for r in frame if ev.dt(r['kickoff'])<=ev.dt(kickoff)]
                    if ev.choose_fraction(prefix,1,den)!={ev.key(r)for r in prefix if ev.key(r)in chosen}:raise AssertionError('Earlier batch membership changed.')
        check()
    canonical=[r for r in tables+selective+proper+broad if r['method']in METHODS]
    if len({r['record_id']for r in canonical})!=len(canonical):raise ValueError('Canonical target-aware record IDs collide.')
    bindings=dict(design_sha256=ev.sha(BASE/'FROZEN_DESIGN_V1.json'),code_sha256=ev.sha(__file__),inherited_reporting_sha256=ev.sha(inherited.__file__),inherited_evaluator_sha256=ev.sha(inherited.M2_PATH),C_scorer_sha256=ev.sha(args.scorer_source),C_interval_sha256=ev.sha(args.interval_source),prediction_files=[dict(file=p.name,sha256=ev.sha(p))for p in prediction_files],existing_ATT_grade_sha256=ev.sha(args.existing_att_grades)if args.existing_att_grades else None,existing_CMP_grade_sha256=ev.sha(args.existing_cmp_grades)if args.existing_cmp_grades else None,source_files=[dict(week=w,sha256=ev.sha(p))for w,p in sorted(sources.items())])
    outputs={'EXECUTION_INPUT_BINDINGS_V1.json':bindings,'MAIN_TABLES_V1.json.gz':tables,'SELECTIVE_TABLES_V1.json.gz':selective,'PROBABILITY_TABLES_V1.json.gz':proper,'BROAD_NUMERICAL_TABLES_V1.json.gz':broad,'PAIRS.json.gz':pairs,'OWN_LIST_COMPARISONS_V1.json.gz':ownlists,'CALIBRATION_SUPPORT_TRACE_V1.json':calibration,'SCORES.json':canonical,'MEMBERSHIP_COMMITMENTS_V1.json':commitments,'PUBLIC_RETAINED_CONTROL_REFERENCES_V1.json':dict(imported_row_controls=imported,known_horizon_incompatible='Strict-currentC02 partial80/84 and unavailablelawchunks are not silently scored as same142board contenders.',scope='Imported controls retain row-bound side/output policies; not re-registered as new canonical scientific results.')}
    check()
    for name,body in outputs.items():ev.write(args.out/name,body)
    public_bytes=sum(p.stat().st_size for p in args.out.iterdir()if p.is_file())
    if public_bytes>25165824:raise RuntimeError('Aggregate24MiB cap exceeded; preserve output, no automatic retry.')
    receipt=dict(state='EXECUTED_OPPORTUNITY_LOCAL_NOT_C_ADMITTED',UTC=datetime.now(timezone.utc).isoformat(),methods=list(METHODS),targets=list(TARGETS),offers_per_target=142,unique_player_games=142,native_games=71,actual_offer_weeks=list(range(5,10)),missing_offer_weeks=[1,2,3,4],numerical_weeks=list(range(1,10)),canonical_views=len(canonical),main_views=len(tables),selective_views=len(selective),probability_views=len(proper),broad_views=len(broad),paired_views=len(pairs),own_list_views=len(ownlists),frozen_selection_policies=19,imported_control_views=imported,grader_boundary_fixtures=fixtures,future_calibration_mutation='PASS',decision_batch_prefix='PASS',new_fits=0,new_network_reads=0,new_NFL_games=0,original_pregame_selections=0,raw_protected_rows_written=0,public_bytes=public_bytes,CPU_seconds=time.process_time()-cpu,wall_seconds=time.monotonic()-started,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,code_sha256=ev.sha(__file__),current_feed_or_primary_activation=False)
    ev.write(args.out/'RUN_RECEIPT_V1.json',receipt)
    print(ev.json.dumps({k:receipt[k]for k in ('state','canonical_views','paired_views','CPU_seconds','public_bytes')}))


if __name__=='__main__':
    from threadpoolctl import threadpool_limits
    with threadpool_limits(limits=2):main()
