"""Public-safe 60-request status projection; no fitting or source acquisition."""
import argparse
import collections
import csv
import hashlib
import json
import re
from pathlib import Path
from datetime import datetime, timezone


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def dump(path, value):
    with Path(path).open('x') as handle:
        json.dump(value, handle, sort_keys=True, indent=2, allow_nan=False)
        handle.write('\n')


BASE = 'reports/continuation-20261030/distribution-wave-v2/'
CHART = 'reports/continuation-20261030/chart-wave-v1/'
C02 = 'reports/continuation-20261030b/ordered-information-ablation-v1/'
DEFENSE = 'reports/continuation-20261030c/qualified-defense-information-v1/'
HGB = 'reports/continuation-20261029/hgb-history-v1/'
LEGACY = 'reports/inventory/ALL_METHOD_SCORES.json'

# Explicit mechanism mapping, not label-based automatic equivalence. A completed
# related control does not complete an unimplemented requested information path.
MAPPING = {
 'PY1':('PARTIAL_EXECUTED', 'Direct Leaf/GLM/HGB and matched D1/D2 opponent additions; C02 own lag-block ablation', 'Qualified QB/receiver availability information and its unchanged-learner ablation', 'SOURCE_CONTEXT', 'direct'),
 'PY2':('QUEUED_DISTINCT', 'Direct marginal controls; original workload procedures retained', 'Joint uncertain attempts/completions/signed gains with volume-vs-gain ablations', 'OOF_EXPOSURE_JOINT', 'structured'),
 'PY3':('COMPLETED_SUPPORTED_CONTROL', 'Conditional signed Leaf-CDF law and regularized signed law on identical own inputs', 'Richer support-sensitive learner may be a new contender; this is not permanent optimality', 'NONE_FOR_RETAINED_CONTROL', 'direct'),
 'PY4':('BLOCKED_QUALIFICATION', 'Original simple analog/ordered controls retained', 'TabICLv2 license/version/pretraining/runtime and chronological learned retrieval', 'PRETRAINING_LICENSE_RUNTIME', 'retrieval'),
 'PY5':('BLOCKED_MARKET_SOURCE', 'Reported market/provider/website references retained separately', 'Authenticated same-time market-only law and small football correction', 'AUTHENTICATED_QUOTES', 'market'),
 'PA1':('PARTIAL_EXECUTED', 'Direct count Leaf/GLM/HGB/Poisson-point controls with ordered own history', 'Separately qualified QB playing-time/role group', 'SOURCE_CONTEXT', 'direct'),
 'PA2':('QUEUED_DISTINCT', 'Original workload/count controls reported', 'Team opportunities/dropbacks/attempts/sacks/scrambles law with uncertain QB shares', 'OOF_EXPOSURE_JOINT', 'structured'),
 'PA3':('PARTIAL_EXECUTED', 'Partially pooled position-prior regularized count law; D1/D2 prior opponent group', 'Dynamic team/QB passing tendency and forecast conditions; no actual game script', 'STATE_CONTEXT', 'state'),
 'PA4':('BLOCKED_QUALIFICATION', 'Original analog/history-weighting evidence retained', 'Qualified TabICLv2 or learned historical-role retrieval on matched inputs', 'PRETRAINING_LICENSE_RUNTIME', 'retrieval'),
 'PA5':('BLOCKED_MARKET_SOURCE', 'Original offered-line heuristic/market references reported', 'Compatible same-time count market/football correction on retained real offers', 'AUTHENTICATED_QUOTES', 'market'),
 'PC1':('PARTIAL_EXECUTED', 'Direct completion Leaf/GLM/HGB/Poisson-point controls; D1/D2 separate learner-fixed addition', 'Qualified catch-quality/receiver availability group', 'SOURCE_CONTEXT', 'direct'),
 'PC2':('QUEUED_DISTINCT', 'Original held-volume/workload conversion results retained', 'Completion conversion law integrated over predicted attempts; hold each factor fixed in ablation', 'OOF_EXPOSURE_JOINT', 'structured'),
 'PC3':('BLOCKED_FEATURE_SOURCE', 'Original NGS/FTN additions and adverse results retained', 'Timestamp-qualified throw difficulty/type plus shrunk QB execution without double count', 'NGS_FTN_ASOF', 'tracking'),
 'PC4':('QUEUED_DISTINCT', 'Direct completion marginal laws scored', 'Coherent joint passing outcomes versus same-information direct marginals', 'OOF_EXPOSURE_JOINT', 'structured'),
 'PC5':('BLOCKED_MARKET_SOURCE', 'Original calibration/market/blend evidence retained', 'Qualified completion market CDF and earlier-OOF conservative football law blend', 'AUTHENTICATED_QUOTES_AND_OOF', 'market'),
 'PT1':('PARTIAL_EXECUTED', 'Direct count Leaf/GLM/Poisson-point controls with explicit zero mass; D1/D2 scored', 'Qualified current scoring-role information', 'SOURCE_CONTEXT', 'direct'),
 'PT2':('QUEUED_DISTINCT', 'Legacy scoring/workload mechanisms remain reported evidence', 'Field-position opportunity law including explosive scores and pass/rush/other choice', 'OOF_OPPORTUNITY_PROCESS', 'structured'),
 'PT3':('QUEUED_DISTINCT', 'Direct TD/count and legacy pooled workload controls retained', 'Heavily pooled TD conversion conditional on forecast completions/throw-location mixture', 'OOF_EXPOSURE_JOINT', 'structured'),
 'PT4':('BLOCKED_FEATURE_SOURCE', 'Own-history/position features scored, not an availability scenario model', 'Qualified receiver/QB full-limited-substitution information added to fixed learner first', 'SOURCE_CONTEXT', 'roles'),
 'PT5':('BLOCKED_MARKET_SOURCE', 'Original count-market/O-U results reported without V2 offer admission', 'Compatible probabilities across several passing-TD thresholds and small correction', 'AUTHENTICATED_QUOTES', 'market'),
 'PI1':('PARTIAL_EXECUTED', 'Direct count/GLM/Poisson-point/pooled controls; zero mass and adverse count results retained', 'Accurate predicted attempt exposure and qualified current QB-role group', 'OOF_EXPOSURE_CONTEXT', 'direct'),
 'PI2':('QUEUED_DISTINCT', 'Regularized direct count and narrow D2 exposure-rate information scored', 'Conditional risk under forecast attempts/depth/pressure with pooled QB/opponent effects', 'OOF_EXPOSURE_AND_CONTEXT', 'structured'),
 'PI3':('REUSE_REPORTED_ADVERSE_ATTEMPTS', 'Prior FTN/risk/hierarchical losses retained; no unchanged retry', 'A precise new timing/exposure/feature mechanism must address prior failure before new run', 'NGS_FTN_ASOF_AND_NEW_HYPOTHESIS', 'tracking'),
 'PI4':('QUEUED_DISTINCT', 'Direct risk marginal law scored', 'Joint passing reconciliation with risk marginal held fixed', 'OOF_EXPOSURE_JOINT', 'structured'),
 'PI5':('BLOCKED_MARKET_SOURCE', 'Reported market risk controls retained', 'Qualified zero/one/multiple-pick market probabilities and conservative correction', 'AUTHENTICATED_QUOTES', 'market'),
 'RA1':('PARTIAL_EXECUTED', 'Ordered Leaf/C02, HGB role-specialization repair, Poisson-point; stronger controls and WR/TE losses scored', 'Qualified full/limited/replacement and teammate information separately isolated', 'SOURCE_CONTEXT', 'direct'),
 'RA2':('QUEUED_DISTINCT', 'Original dynamic backfield/workload studies retained at reported evidence level', 'Finite team designed-run volume and uncertain backfield allocation with other-player bucket', 'OOF_TEAM_ALLOCATION', 'structured'),
 'RA3':('QUEUED_DISTINCT', 'Own recency and ordered histories scored', 'Forward-filtered role/changepoint model for promotions/returns/restrictions versus recency', 'STATE_CONTEXT', 'state'),
 'RA4':('PARTIAL_EXECUTED', 'Earlier carries/count support available; no snap or route denominator admitted', 'Exposure-first permitted participation or accurately named team carry share; separate QB run types', 'PARTICIPATION_OR_DESIGNED_RUN_SOURCE', 'workload'),
 'RA5':('BLOCKED_QUALIFICATION', 'Original fixed analog/weighting controls reported', 'Learned role retrieval or capped relevance-weighted learning on matched cases', 'RETRIEVAL_CHRONOLOGY_RUNTIME', 'retrieval'),
 'RY1':('PARTIAL_EXECUTED', 'Direct signed Leaf/HGB/GLM/C02 and learner-fixed D1/D2 scored', 'Same qualified current role/carry information required by structured alternative', 'SOURCE_CONTEXT', 'direct'),
 'RY2':('QUEUED_DISTINCT', 'Legacy workload/compound/component results retained', 'Uncertain carries compounded with signed loss/zero/ordinary/explosive gains; factor ablations', 'OOF_EXPOSURE_JOINT', 'structured'),
 'RY3':('BLOCKED_FEATURE_SOURCE', 'Narrow qualified opponent-rate information scored; original NGS evidence retained', 'Earlier NGS opportunity quality plus shrunk execution/personnel effects', 'NGS_FTN_ASOF', 'tracking'),
 'RY4':('BLOCKED_QUALIFICATION', 'Original analog controls and current sparse-role fallbacks retained', 'Qualified TabICLv2 median and bounded learned role retrieval', 'PRETRAINING_LICENSE_RUNTIME', 'retrieval'),
 'RY5':('BLOCKED_MARKET_SOURCE', 'Reported market/provider references retained', 'Qualified market curve/point correction versus strongest same-time football/market controls', 'AUTHENTICATED_QUOTES', 'market'),
 'R1':('PARTIAL_EXECUTED', 'Ordered count Leaf/GLM/Poisson-point, C02 and D1/D2 scored', 'Qualified current target competition/QB/teammate information; original target-CDF continuation stays with owner', 'SOURCE_CONTEXT_AND_OWNER_COORDINATION', 'direct'),
 'R2':('QUEUED_DISTINCT', 'Original receiving-target/CDF continuation remains original owner; existing target-share/workload evidence reported', 'Targetable volume to finite targets to uncertain catches with no-credited-target bucket', 'OOF_TEAM_ALLOCATION_AND_OWNER_COORDINATION', 'structured'),
 'R3':('BLOCKED_ROUTE_SOURCE', 'Targets/carry/share controls do not supply all-player routes', 'Genuine live/as-of route participation denominator and matched snaps/target-share comparison', 'ALL_PLAYER_ROUTE_RIGHTS_TIMING', 'routes'),
 'R4':('BLOCKED_FEATURE_SOURCE', 'Original FTN catch/drop/throw-type experiments retained', 'Qualified lagged conversion information with fixed target law before allocation change', 'NGS_FTN_ASOF_AND_OOF_TARGETS', 'tracking'),
 'R5':('BLOCKED_QUALIFICATION', 'Leaf/GLM/count controls and original analog/calibration/stack results retained', 'Qualified TabICLv2/chronological retrieval OR separately registered restrained distribution stack', 'PRETRAINING_OR_EARLIER_OOF', 'retrieval'),
 'REY1':('PARTIAL_EXECUTED', 'Direct signed Leaf/HGB/GLM/C02 and D1/D2 opponent group scored', 'Qualified current role/QB/teammate context addition', 'SOURCE_CONTEXT', 'direct'),
 'REY2':('QUEUED_DISTINCT', 'Original target/workload/component procedures reported', 'Predicted target type/catch/signed gain joint process with shared uncertainty', 'OOF_EXPOSURE_JOINT_AND_OWNER_COORDINATION', 'structured'),
 'REY3':('BLOCKED_FEATURE_SOURCE', 'Original NGS/FTN/air-gain/YAC studies and losses retained', 'Compatible earlier air-gain/YAC opportunity and pooled residual execution', 'NGS_FTN_ASOF', 'tracking'),
 'REY4':('BLOCKED_QUALIFICATION', 'Direct HGB and original categorical/analog controls reported', 'Qualified TabICLv2 or learned role retrieval; distinct genuine categorical learner admissible separately', 'PRETRAINING_LICENSE_RUNTIME', 'retrieval'),
 'REY5':('BLOCKED_MARKET_SOURCE', 'Original market/line studies remain reported', 'Authenticated alternate-line law or small point correction; quote-path test beyond same-cutoff static market', 'AUTHENTICATED_QUOTES', 'market'),
 'RR1':('PARTIAL_EXECUTED', 'Strong direct total Leaf/HGB/GLM/C02 and D1/D2 scored, including QB/TE extended roles', 'Qualified current role information held common to direct and joint competitors', 'SOURCE_CONTEXT', 'direct'),
 'RR2':('QUEUED_DISTINCT', 'Original component/shared-workload recipes reported', 'Shared role/game-state scenarios for carries and targets with total from common joint draws', 'OOF_EXPOSURE_JOINT', 'structured'),
 'RR3':('QUEUED_DISTINCT', 'Direct total law available as strong comparator', 'Multivariate conditional rush/receive production law on identical rows', 'JOINT_LAW_AND_OOF', 'structured'),
 'RR4':('REUSE_REPORTED_ADVERSE_ATTEMPTS', 'Prior independent-sum/copula/reconciliation losses preserved', 'Specific new regularized reconciliation/dependence mechanism with fixed marginal ablation', 'NEW_HYPOTHESIS_AND_JOINT_LAW', 'joint'),
 'RR5':('QUEUED_DISTINCT', 'Original ensemble/market evidence retained; no law mixture inferred from point average', 'Conservative direct/derived law mixture trained earlier; market version separately source-blocked', 'EARLIER_OOF_AND_JOINT_LAW', 'stack'),
 'AT1':('PARTIAL_EXECUTED', 'Direct HGB/logistic/Leaf probability controls; D1/D2 Brier, reliability, prevalence retained', 'Qualified goal-line/end-zone role information at unchanged learner', 'SOURCE_CONTEXT', 'direct'),
 'AT2':('QUEUED_DISTINCT', 'Original workload/scoring-role procedures reported', 'Team offensive TD opportunities allocated by field position and eligible players incl explosive scores', 'OOF_OPPORTUNITY_ALLOCATION', 'structured'),
 'AT3':('QUEUED_DISTINCT', 'Position-prior fallback does not establish a full/limited role mixture', 'Nonlinear full/limited/replacement scenarios preserving 1-E[exp(-Lambda)]', 'ROLE_SCENARIOS_AND_JOINT_LAW', 'roles'),
 'AT4':('QUEUED_DISTINCT', 'Direct binary/count-rate controls and original workload results retained', 'Uncertain carries/targets integrated with strongly pooled scoring conversion', 'OOF_EXPOSURE_JOINT', 'structured'),
 'AT5':('BLOCKED_MARKET_SOURCE', 'Original Yes/No market evidence retains contract/clock limitations', 'Same-event same-book Yes/No reference with constrained earlier calibration/small correction', 'AUTHENTICATED_QUOTES', 'market'),
 'PPR1':('COMPLETED_SUPPORTED_CONTROL', 'Exact-qualified-partial-chart Leaf law/median and empirical control scored2022-2026', 'Remaining35 current labels/rare-credit attribution limit full-chart coverage, not fabricated zero', 'RARE_COMPONENT_SOURCE_FOR_EXTENDED_COVERAGE', 'chart'),
 'PPR2':('QUEUED_DISTINCT', 'Football HGB is not a scored same-chart HGB; original chart procedures reported', 'Small exact-chart absolute-loss/quantile HGB/CatBoost/LightGBM/XGBoost library under new bounded IDs', 'RETENTION_AND_DECLARED_LIBRARY', 'chart'),
 'PPR3':('PARTIAL_EXECUTED', 'Proper signed exact-grid Leaf/regularized law scored with genuine mean/median separate', 'TabICLv2 extension requires qualification; no pretrained/current-only claim', 'PRETRAINING_LICENSE_RUNTIME_FOR_TABICL', 'chart'),
 'PPR4':('QUEUED_DISTINCT', 'Exact weighted chart LABEL reconstructed; that is not a component forecast or predictive gain', 'Coherent joint component-outcome chart law plus separately weighted component means', 'JOINT_COMPONENT_FORECASTS_AND_RARE_SOURCE', 'joint'),
 'PPR5':('QUEUED_DISTINCT', 'Original chart/component/ensemble losses retained', 'Earlier-OOF conservative direct/component-law combination with shrunk role weights if supported', 'EARLIER_OOF_AND_JOINT_LAW', 'stack'),
}


def main(repo, output):
    repo, output = Path(repo), Path(output)
    if output.exists(): raise ValueError('fresh output directory required')
    request_path = repo/'registries/REQUEST_METHOD_CROSSWALK.csv'
    requests = [r for r in csv.DictReader(request_path.open()) if re.fullmatch(r'(?:PY|PA|PC|PT|PI|RA|RY|R|REY|RR|AT|PPR)[1-5]', r['request_id'])]
    if len(requests)!=60 or {r['request_id'] for r in requests}!=set(MAPPING): raise ValueError('exact60-request mapping required')
    output.mkdir(parents=True)
    rows=[]
    for r in requests:
        status, completed, remaining, blocker, group=MAPPING[r['request_id']]
        evidence=[LEGACY, 'reports/continuation-20261030/distribution-wave-v1/LEGACY_MECHANISM_RECONCILIATION.json']
        if group=='direct': evidence += [BASE+'SCORES.json',HGB+'SCORES.json',C02+'SCORES.json',DEFENSE+'SCORES.json']
        if group=='chart': evidence += [CHART+'SCORES.json',CHART+'EMPIRICAL_SCORES.json']
        if group in ('tracking','joint','stack','structured','state','retrieval','roles','workload','routes','market'): evidence += ['reports/INVENTORY_COMPLETENESS.md', 'reports/continuation-20261030c/UPSTREAM_RECEIPT_RECONCILIATION.json']
        owner='original upstream owner: receiving-target/CDF continuation; V2 coordinated only' if r['request_id'] in ('R1','R2','REY2') else 'V2 research executor, coordinated with retained production owner'
        rows.append(dict(pathway_id=r['request_id'],target=r['target'],requested_mechanism=r['requested_mechanism'],
            delivery=r['delivery'],status=status,located_completed_or_reported_work=completed,
            exact_remaining_mechanism=remaining,additional_prerequisites=blocker,
            new_fit_state='NO_NEW_FIT_REQUESTED_FOR_RETAINED_CONTROL' if status=='COMPLETED_SUPPORTED_CONTROL' else 'BLOCKED_DURABLE_RETENTION_CAPACITY_AND_LISTED_PREREQUISITES',
            failed_or_adverse_state='REPORTED_ADVERSE_ATTEMPTS_PRESERVED_NOT_RETRIED' if status=='REUSE_REPORTED_ADVERSE_ATTEMPTS' else 'LOCATED_LOSSES_RETAINED; NOT_A_LIFETIME_ATTEMPT_CENSUS',
            evidence_scope='NEW_V2_EXECUTED_WHERE_CITED; legacyREPORTED_NOT_REPRODUCED; exact new recipe not inherited by label',
            core_history_scope='V2newdirectcontrols core3+strict current2026, rolling2022-25;2022RECENT2021component unsupported',
            owner=owner,reference_artifacts=evidence,new_fits=0,new_forecasts=0))
    dump(output/'PATHWAY_STATUS_60.json',rows)
    with (output/'PATHWAY_STATUS_60.csv').open('x',newline='') as handle:
        writer=csv.DictWriter(handle,fieldnames=list(rows[0]));writer.writeheader()
        for r in rows:writer.writerow({k:json.dumps(v,separators=(',',':')) if isinstance(v,(list,dict)) else v for k,v in r.items()})
    original_path=repo/'reports/continuation-20261030c/UPSTREAM_RECEIPT_RECONCILIATION.json'
    original=json.loads(original_path.read_bytes());groups=collections.defaultdict(list)
    for r in original['results']:
        metric=r['scores'].get('MAE',{})
        if metric.get('state')!='FINITE':continue
        c=r['comparison'];k=(c['comparison_set_id'],c['target'],c['season'],tuple(c['weeks']))
        groups[k].append(r)
    best=[]
    for dims,rr in sorted(groups.items()):
        r=min(rr,key=lambda x:(x['scores']['MAE']['value'],x['method_id'],x['output_id']))
        best.append(dict(comparison_set_id=dims[0],target=dims[1],season=dims[2],weeks=list(dims[3]),
            method_id=r['method_id'],output_id=r['output_id'],mae=r['scores']['MAE']['value'],
            run_id=r['run_id'],source_record=r['source_record'],evidence='REPORTED_NOT_REPRODUCED',
            v2_reuse='INCOMPATIBLE2019_MEMORY_ORIGINAL_PRIVATE_ROWS/QUERY_CONTRACT; not common2026W1-W7 champion',
            tied_minima=sum(x['scores']['MAE']['value']==r['scores']['MAE']['value'] for x in rr)))
    old_path=repo/'reports/inventory/REPORTED_TOP5_2026_W1_W6.json'
    old_min=[r for r in json.loads(old_path.read_bytes()) if r.get('rank')==1]
    dump(output/'STRONGEST_LOCATED_LEGACY_REFERENCES.json',dict(
        inherited_2026W1W6_rank1_references=old_min,
        original_413ed_exact_panel_best_observed_MAE=best,
        interpretation='Different panels, populations,2019memory,contracts/horizons; no pooled cross-panel league table. Point output minima are not independent learners. Source scores reported, not reproduced. Original target-CDF continuation remains original owner.'))
    refs=sorted({x for r in rows for x in r['reference_artifacts']}|{
        'registries/REQUEST_METHOD_CROSSWALK.csv','reports/inventory/REPORTED_TOP5_2026_W1_W6.json'})
    receipts=[dict(artifact_id=r,sha256=sha(repo/r))for r in refs]
    dump(output/'RECONCILIATION_RECEIPT.json',dict(state='COMPLETE_SCOPED_60_DELIVERED_PATHWAY_PROJECTION',
        generated_at_utc=datetime.now(timezone.utc).isoformat(),code_sha256=sha(__file__),request_source_sha256=sha(request_path),
        source_bindings=receipts,status_counts=dict(collections.Counter(r['status']for r in rows)),
        unique_delivered_pathways=60,new_methods_claimed=0,new_fits=0,new_forecasts=0,week8_outcomes_read=0,
        original_owner_commit=original['inspected_commit'],original_method_records=original['method_records'],
        original_result_views=original['result_views'],original_source_receipt_sha256=sha(original_path),
        completeness='Only directly delivered60paths with located public-safe evidence. Private1172ledger/unarchived instructions and missing model/query originals remain inaccessible; no every-attempt claim.',
        owner_receiving_target_cdf='https://github.com/NickNicky19/NFL-forecasting/pull/1#issuecomment-6527892507'))
    lines=['# Sixty requested pathways: scoped status\n',
      'This is a request-to-evidence projection, not sixty completed procedures. The two `COMPLETED_SUPPORTED_CONTROL` entries complete a bounded mathematical control under the retained qualified source/label contract; they do not complete all variants, targets, source additions, release readiness or the overall tournament. Every proposed new fit remains blocked by durable retention capacity and its listed prerequisites. Existing numerical gains and losses remain unchanged.\n',
      'Original receiving-target/CDF continuation remains with the original owner. The latest original receipt contains29methodrecords/86resultviews; it uses different 2019memory or original source/query contracts and cannot silently fill V2 W1–7 cells. Its72,646 reported O/U decisions do not authenticate same-time prices, live profitability or V2 offers. The source-linked legacy minima are retained separately in `STRONGEST_LOCATED_LEGACY_REFERENCES.json`.\n',
      '| Path | Target | State | Executed or reported evidence | Remaining exact work |',
      '|---|---|---|---|---|']
    for r in rows:lines.append(f"|{r['pathway_id']}|{r['target']}|{r['status']}|{r['located_completed_or_reported_work']}|{r['exact_remaining_mechanism']}|")
    lines += ['', 'Statuses separate mathematical mechanisms from source additions: direct models do not fill joint exposure/allocation, current-role/availability, routes, qualified NGS/FTN, pretrained retrieval, market or stacking cells. A Poisson fitting objective alone does not create a forecast distribution. Exact chart labels alone do not create a component-derived joint forecast. No new seeds or mean/median views inflate family counts.',
      '', 'Next supported sequence: resolve durable retention; independently review the scheduled-game defense alternative; finish original strict-HGB and qualified chart direct controls under distinct IDs; then admit one narrowly qualified role/context or exposure mechanism at a time. The original owner retains its target/CDF study. Route and market paths await actual permitted sources; no alternative mirror, secret extraction or second collector is authorized.',
      '', 'The inaccessible original private attempt ledger and unarchived instructions remain a separate limitation. This file reconciles sixty demonstrably delivered pathways against accessible evidence; it makes no lifetime-completeness percentage.']
    (output/'PATHWAY_STATUS_60.md').write_text('\n'.join(lines)+'\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--repo-root',required=True,type=Path);parser.add_argument('--output',required=True,type=Path)
    a=parser.parse_args();main(a.repo_root,a.output)
