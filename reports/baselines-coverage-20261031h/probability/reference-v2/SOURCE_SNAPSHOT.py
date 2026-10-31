"""Frozen, earlier-only threshold references on retained G probability masks.

No model inference, fitting, source acquisition, directions or settlement reruns.
"""
from __future__ import annotations

import argparse
import bisect
import collections
import csv
import gzip
import hashlib
import json
import math
import re
import resource
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nfl_v2 import empirical_benchmark as empirical
from nfl_v2.paired_uncertainty import paired_losses
from nfl_v2.shared_subgroups import canonical, now, sha, write
from nfl_v2.week8_shadow import schedules
from tools.numerical_championship import csvwrite

VERSION = "v2-earlier-only-actual-threshold-probability-references-v1"
REGIONS = ("over", "under", "push")
BASELINES = ("B0_CONSTANT_HALF_NO_PUSH", "B1_EARLIER_SAME_POSITION_PREVALENCE")


def epoch(v):
    return datetime.fromisoformat(v.replace("Z", "+00:00")).timestamp()


def loss(pp, region):
    brier = .5 * math.fsum((pp[s] - int(region == s)) ** 2 for s in REGIONS)
    return brier, -math.log(pp[region]) if pp[region] > 0 else math.inf


def finite_json(value):
    if isinstance(value, float) and not math.isfinite(value):
        if math.isnan(value):
            raise ValueError("NaN must have an explicit missing-data reason")
        return "Infinity" if value > 0 else "-Infinity"
    if isinstance(value, dict):
        return {k:finite_json(v) for k,v in value.items()}
    if isinstance(value, (tuple,list)):
        return [finite_json(v) for v in value]
    return value


def reference(values, line):
    """Unsmoothed empirical region probabilities; caller supplies eligible values."""
    if not values:
        return dict(over=.5, under=.5, push=0.), "EMPTY_PREFIX_CONSTANT_HALF"
    n = len(values)
    lo, hi = bisect.bisect_left(values, line), bisect.bisect_right(values, line)
    return dict(over=(n-hi)/n, under=lo/n, push=(hi-lo)/n), "EARLIER_EMPIRICAL"


def auc(pairs):
    """Mann-Whitney AUC with exact midrank ties, only decisive actual outcomes."""
    if not pairs:
        return None
    positives = sum(y for _, y in pairs)
    negatives = len(pairs) - positives
    if not positives or not negatives:
        return None
    ranks = 0.
    ordered = sorted(pairs)
    i = 0
    while i < len(ordered):
        j = i + 1
        while j < len(ordered) and ordered[j][0] == ordered[i][0]:
            j += 1
        ranks += ((i+1+j)/2) * sum(y for _, y in ordered[i:j])
        i = j
    return (ranks - positives*(positives+1)/2)/(positives*negatives)


def diagnostics(rows, prefix):
    bins = collections.defaultdict(list)
    pairs = []
    for r in rows:
        pp = r[prefix+"_probabilities"]
        for s in REGIONS:
            bins[s, min(9, int(pp[s]*10))].append((pp[s], int(r["actual_region"] == s)))
        decisive_mass = pp["over"] + pp["under"]
        if r["actual_region"] != "push" and decisive_mass > 0:
            pairs.append((pp["over"]/decisive_mass, int(r["actual_region"] == "over")))
    histogram = []
    for (region, b), vals in sorted(bins.items()):
        mean_p = math.fsum(x[0] for x in vals)/len(vals)
        freq = math.fsum(x[1] for x in vals)/len(vals)
        histogram.append(dict(region=region, bin=b, lower=b/10, upper=(b+1)/10,
                              n=len(vals), mean_probability=mean_p, actual_frequency=freq,
                              signed_calibration_error=mean_p-freq))
    return dict(calibration_bins=histogram,
                calibration_rule="Fixed ten equal-width bins, last includes 1; descriptive, no calibration fitting",
                decisive_over_auc=auc(pairs), decisive_auc_n=len(pairs),
                decisive_auc_conditioning="Actual nonpush rows; predicted over/(over+under); separate from all-region proper score",
                decisive_auc_null_reason=None if auc(pairs) is not None else "SINGLE_ACTUAL_CLASS_OR_NO_DECISIVE_SUPPORT")


def paths(a, week, leaf):
    member = f"completion-20261031g-w{week}-" + ("complete-leaf-law-v1" if leaf else "rolling-method-comparison-v1")
    private = a.private_root/member
    public = a.root/"reports/completion-20261031g/roster"/(f"w{week}-complete-leaf-law-v1" if leaf else f"w{week}-rolling-method-comparison-v1")
    return private, public


def prepare(a):
    if a.output.exists() or a.private_output.exists():
        raise ValueError("fresh H probability paths required")
    a.output.mkdir(parents=True)
    a.private_output.mkdir(parents=True)
    history = json.loads((a.root/"reports/continuation-20261029/history-diagnostic-v1/FROZEN_PROTOCOL.json").read_bytes())
    for src in history["source_ids"]:
        if sha(a.source_root/src["name"]) != src["sha256"]:
            raise ValueError("qualified history source changed")
    sources, roster = [], []
    for week in (6, 7):
        for leaf in (False, True):
            private, public = paths(a, week, leaf)
            plan_name = "FROZEN_LAW_DIRECTIONS_K.json.gz" if leaf else "FROZEN_SELECTIONS_AND_K.json.gz"
            grade_name = "GRADED_COMPLETE_LEAF_LAWS.json.gz" if leaf else "GRADED_METHOD_ROWS.json.gz"
            for path in (private/plan_name, private/grade_name, public/"SCORES.json"):
                sources.append(dict(member=path.name, source_id=private.name if path.parent == private else public.relative_to(a.root).as_posix(), sha256=sha(path)))
            plans = json.loads(gzip.decompress((private/plan_name).read_bytes()))["plans"]
            for tag, plan in plans.items():
                if not leaf and (plan["rule"] != "P2" or "ordered_leaf_cdf" in plan["recipe"][1] or "c02" in plan["recipe"][1]):
                    continue
                target, proc, arm = plan["recipe"][:3]
                roster.append(dict(week=week, target=target, procedure_id=proc, history_regime=arm,
                                   strict_current_information="strict" in proc, source_type="complete_leaf" if leaf else "full_parametric",
                                   method_id=tag, admitted_source_indices_sha256=hashlib.sha256(canonical(sorted(r["source_row_index"] for r in plan["rows"] if r["admitted"]))).hexdigest()))
    protocol = dict(version=VERSION, at=now(), state="FROZEN_BEFORE_H_BASELINE_NUMERICAL_EVALUATION",
        code_sha256=sha(__file__), empirical_helper_sha256=sha(empirical.__file__),
        uncertainty_helper_sha256=sha(a.root/"nfl_v2/paired_uncertainty.py"), source_members=sources,
        prior_source_ids=history["source_ids"], roster=roster, evaluation_season=2026, evaluation_weeks=[6,7],
        source_vintage="Current/revised football rows; inherited kickoff+7-day availability reconstruction, not authenticated historical publication",
        prior_baseline="Unsmoothed empirical Over/Under/Push frequencies at the exact offered line among same-position REG player-games with explicit target and positive physical appearance; each consumed kickoff+7d strictly before actual offer decision clock. No player-specific, role, odds, future ranking or current-outcome input.",
        history="H-CURRENT uses2026; H-RECENT2025–26; H-MULTI2022–26. Existing strict-current candidate gets2026-only reference. No pre2022 source. Strict reference has no older football features/priors/calibration/tuned parameters; query position comes from authenticated pregame context.",
        fallback="Empty earlier prefix uses explicitly named (.5,.5,0) categorical reference; no smoothing. No hidden old-season fallback. Population is historical same-position participants, which can differ from offered stars/current roles.",
        constant="B0 categorical per-threshold reference over=.5,under=.5,push=0; Brier .25 on decisive outcomes, .75 on pushes; push log-loss Infinity. It is not a single global CDF or a market reference.",
        products="Probability-only reference comparison, no new selection/settlement/K strategy. Half multiclass Brier and actual-region logloss, all eligible law/outcome rows including direction ties. Zero masses remain Infinity.",
        partitions="Exact competitor FULL/LEARNED/PRIOR masks; complete Leaf/C02 explicit law-origin marker is authoritative; parametric original fallback flag used only on that source. Baseline fallback contribution separately disclosed.",
        uncertainty="Existing paired_losses: game-cluster normal95 sensitivity with>=8games; whole-week CI requires>=8weeks, here insufficient; exposed/multiplicity-unadjusted. Weekly and cumulative underlying rows, no duplicate F fixed panel.",
        diagnostics="Fixed ten-bin per-region calibration and decisive-outcome midrank AUC reported separately; no calibrator or selector fit, no posthoc support pruning.",
        market_reference=dict(status="SOURCE_BLOCKED", reason="No authenticated same-contract side prices/quote status in retained G threshold sources; no -110 assumption or synthetic de-vig"),
        exposure="All evaluation seasons/outcomes previously exposed research. Baseline rule frozen before its new score calculation; not fresh holdout.",
        budget=dict(wall_seconds=300,max_RSS_bytes=1073741824,max_private_bytes=16777216,max_threads=2),
        new_fits=0,new_model_inference=0,new_captures=0,Week8_outcomes_read=0)
    write(a.output/"FROZEN_PROTOCOL.json", protocol)
    (a.output/"SOURCE_SNAPSHOT.py").write_bytes(Path(__file__).read_bytes())
    print(json.dumps(dict(state=protocol["state"],protocol_sha256=sha(a.output/"FROZEN_PROTOCOL.json"),weekly_law_recipes=len(roster))))


def prior_rows(a):
    games = schedules(a.source_root/"games.csv")
    needed = set(empirical.MAP.values()) | set(empirical.PHYSICAL_COUNTS) | set(empirical.PHYSICAL_YARDS)
    groups = collections.defaultdict(list)
    seen, counts = set(), collections.Counter()
    for year in range(2022,2027):
        with (a.source_root/f"stats_player_week_{year}.csv").open() as f:
            for r in csv.DictReader(f):
                if r["season_type"] != "REG" or (year == 2026 and int(r["week"]) > 7):
                    continue
                if r["position"] not in ("QB","RB","WR","TE") or not re.fullmatch(r"00-\d{7}",r["player_id"]):
                    continue
                game = games.get(r["game_id"])
                if not game or game["season"] != year or game["week"] != int(r["week"]):
                    raise ValueError("prior source schedule mismatch")
                if (r["team"],r["opponent_team"]) not in ((game["home"],game["away"]),(game["away"],game["home"])):
                    raise ValueError("prior source team mismatch")
                key = (r["game_id"],r["player_id"])
                if key in seen: raise ValueError("duplicate prior player-game")
                seen.add(key)
                vals = {k:empirical.numeric(r[k]) for k in needed}
                played = any(empirical.valid_count(vals[k]) and vals[k]>0 for k in empirical.PHYSICAL_COUNTS) or any(vals[k] is not None and vals[k]!=0 for k in empirical.PHYSICAL_YARDS)
                counts["verified_played" if played else "participation_unknown"] += 1
                if not played: continue
                for target in (*empirical.MAP,"rush_rec_yd"):
                    if target.startswith("pass_") and r["position"] != "QB": continue
                    value = empirical.target_value(target,vals)
                    if value is not None:
                        groups[target,r["position"]].append((year,game["kickoff"]+7*86400,value,key))
    return groups, dict(counts)


def run(a):
    start, cpu = time.monotonic(),time.process_time()
    p = json.loads((a.output/"FROZEN_PROTOCOL.json").read_bytes())
    if sha(__file__) != p["code_sha256"]: raise ValueError("frozen executor changed")
    if any(sha(a.source_root/s["name"])!=s["sha256"] for s in p["prior_source_ids"]): raise ValueError("prior source changed")
    def guard():
        if time.monotonic()-start>300 or resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024>1073741824: raise RuntimeError("bounded H probability wave")
    prior, prior_counts = prior_rows(a)
    data = collections.defaultdict(dict)
    bindings, origins = {}, {}
    for week in (6,7):
        for leaf in (False,True):
            private, public = paths(a,week,leaf)
            plan_name = "FROZEN_LAW_DIRECTIONS_K.json.gz" if leaf else "FROZEN_SELECTIONS_AND_K.json.gz"
            grade_name = "GRADED_COMPLETE_LEAF_LAWS.json.gz" if leaf else "GRADED_METHOD_ROWS.json.gz"
            for file in (private/plan_name, private/grade_name, public/"SCORES.json"):
                sid=private.name if file.parent==private else public.relative_to(a.root).as_posix()
                want=next(s["sha256"] for s in p["source_members"] if s["member"]==file.name and s["source_id"]==sid)
                if sha(file)!=want: raise ValueError("saved probability source changed")
            plans=json.loads(gzip.decompress((private/plan_name).read_bytes()))["plans"]
            grades=json.loads(gzip.decompress((private/grade_name).read_bytes()))
            publicrows=json.loads((public/"SCORES.json").read_bytes())
            pub={r["record_id"]:(i,r) for i,r in enumerate(publicrows)}
            selected={r["method_id"]:r for r in p["roster"] if r["week"]==week and r["source_type"]==("complete_leaf" if leaf else "full_parametric")}
            losses=collections.defaultdict(dict)
            for r in grades["proper_losses" if leaf else "probability_rows"]:
                if r["method_id"] in selected: losses[r["method_id"]][r["source_row_index"]]=r
            for tag, spec in selected.items():
                target,proc,arm=plans[tag]["recipe"][:3]
                key=(target,proc,arm)
                ii,pr=pub[("LEAF-PROB-" if leaf else "METHOD-PROB-")+tag]
                bindings[week,key]=dict(source_artifact=(public/"SCORES.json").relative_to(a.root).as_posix(),source_artifact_sha256=sha(public/"SCORES.json"),source_row_index=ii,record_id=pr["record_id"])
                source_rows={r["source_row_index"]:r for r in grades["graded"][tag]}
                for idx,l in losses[tag].items():
                    r=source_rows[idx]
                    region="over" if r["actual"]>float(r["line"]) else "under" if r["actual"]<float(r["line"]) else "push"
                    origin=("PRIOR" if r["source"]=="REUSED_ELIGIBLE_FALLBACK_LAW" else "LEARNED") if leaf else ("LEARNED" if r.get("fallback") in (None,"none") else "PRIOR")
                    ll=l.get("log_loss",l.get("categorical_log_loss"))
                    data[key][week,idx]=dict(week=week,source_row_index=idx,game=r["game_id"],player=r["player_id"],target=target,position=r["position"],line=float(r["line"]),actual=r["actual"],actual_region=region,decision_time=r.get("source_server_clock",r.get("server_retained_by")),origin=origin,candidate_probabilities=r["probabilities"],candidate_brier=l.get("brier",l.get("half3class_brier")),candidate_log_loss=math.inf if ll=="Infinity" else ll)
                if len(losses[tag])!=pr["n"]: raise ValueError("cached mask differs from proper source")
            guard()
    cache={}; private_rows=[]; scores=[]; contrasts=[]; diag=[]
    for key,dd in sorted(data.items()):
        target,proc,arm=key
        strict="strict" in proc
        floor=2026 if strict or arm=="H-CURRENT" else 2025 if arm=="H-RECENT" else 2022
        for r in dd.values():
            ck=(target,r["position"],r["line"],r["decision_time"],floor)
            if ck not in cache:
                cutoff=epoch(r["decision_time"])
                eligible=[x for x in prior[target,r["position"]] if x[0]>=floor and x[1]<cutoff]
                vv=sorted(x[2] for x in eligible)
                pp,status=reference(vv,r["line"])
                cache[ck]=dict(probabilities=pp,status=status,n=len(vv),earliest_available=min((x[1] for x in eligible),default=None),latest_available=max((x[1] for x in eligible),default=None),membership_sha256=hashlib.sha256(canonical(sorted(x[3] for x in eligible))).hexdigest())
            b=cache[ck]
            r.update(B0_probabilities=dict(over=.5,under=.5,push=0.),B1_probabilities=b["probabilities"],baseline_prior_n=b["n"],baseline_prior_earliest=b["earliest_available"],baseline_prior_latest=b["latest_available"],baseline_prior_membership_sha256=b["membership_sha256"],baseline_origin=b["status"])
            for ref in ("B0","B1"):
                r[ref+"_brier"],r[ref+"_log_loss"]=loss(r[ref+"_probabilities"],r["actual_region"])
            private_rows.append(dict(procedure_id=proc,history_regime=arm,strict_current_information=strict,**r))
        for weeks in ((6,),(7,),(6,7)):
            full=[r for q,r in sorted(dd.items()) if q[0] in weeks]
            for partition in ("FULL","LEARNED","PRIOR"):
                rr=[r for r in full if partition=="FULL" or r["origin"]==partition]
                mask=hashlib.sha256(canonical([[r["week"],r["source_row_index"],r["game"],r["player"],r["target"],r["line"],r["actual"]] for r in rr])).hexdigest()
                source=[bindings[w,key] for w in weeks if (w,key) in bindings]
                for ref in ("candidate","B0","B1"):
                    n=len(rr); ll=[r[ref+"_log_loss"] for r in rr]; inf=sum(math.isinf(v) for v in ll)
                    rid="H-PROB-"+hashlib.sha256(canonical([key,weeks,partition,ref])).hexdigest()[:24]
                    row=dict(record_id=rid,record_kind="prop_threshold_probability_evaluation",procedure_id=proc+":known-target-time-v1" if ref=="candidate" else BASELINES[int(ref[-1])]+":matched-to:"+proc,reference_id=ref,matched_candidate_procedure_id=proc,history_regime=arm,strict_current_information=strict,product_id="actual_line_categorical_law",target=target,population="original_full_provider_labelled_offer_pool_on_exact_saved_candidate_probability_mask",season=2026,week=weeks[0] if len(weeks)==1 else "ALL",evaluation_seasons=[2026],evaluation_weeks=list(weeks),evaluation_panel_id=VERSION,fallback_view=partition,n=n,forecast_rows=len(full),brier=math.fsum(r[ref+"_brier"] for r in rr)/n if n else None,log_loss="Infinity" if inf else math.fsum(ll)/n if n else None,infinite_log_losses=inf,mae=None,mse=None,probability_conditioning="MODELED_APPEARANCE",probability_score_contract="HALF_MULTICLASS_BRIER_OVER_UNDER_PUSH_V1",bookmaker_nonvoid_conditioning="UNESTABLISHED",membership_sha256=mask,source_records=source,candidate_prior_rows=sum(r["origin"]=="PRIOR" for r in rr),baseline_empty_prefix_rows=sum(r["baseline_origin"]=="EMPTY_PREFIX_CONSTANT_HALF" for r in rr),baseline_prior_n_min=min((r["baseline_prior_n"] for r in rr),default=None),baseline_prior_n_max=max((r["baseline_prior_n"] for r in rr),default=None),unique_games=len({r["game"] for r in rr}),unique_weeks=len({r["week"] for r in rr}),statistical_pushes=sum(r["actual_region"]=="push" for r in rr),null_reason=None if n else "NO_ROWS_IN_FROZEN_CANDIDATE_ORIGIN_PARTITION",evidence="NEW_SAVED_ROW_PROBABILITY_REFERENCE_EVALUATION",selection_policy=None,selection_policy_reason="PROBABILITY_ONLY_NO_NEW_DIRECTION_RULE",new_NFL_observations=0)
                    scores.append(row)
                    diag.append(dict(record_id=rid,**diagnostics(rr,ref)))
                for ref in ("B0","B1"):
                    for metric in ("brier","log_loss"):
                        u=paired_losses([r["candidate_"+metric] for r in rr],[r[ref+"_"+metric] for r in rr],[r["week"] for r in rr],[r["game"] for r in rr])
                        contrasts.append(dict(comparison_id="H-PAIR-"+hashlib.sha256(canonical([key,weeks,partition,ref,metric])).hexdigest()[:24],target=target,procedure_id=proc,history_regime=arm,strict_current_information=strict,evaluation_weeks=list(weeks),fallback_view=partition,comparator=BASELINES[int(ref[-1])],metric=metric,membership_sha256=mask,source_records=source,**u))
        guard()
    blob=gzip.compress(canonical(finite_json(private_rows)),mtime=0)
    if len(blob)>16777216: raise RuntimeError("private derivative retention cap")
    with (a.private_output/"BASELINE_AND_CACHED_LAW_ROWS.json.gz").open("xb") as f:f.write(blob)
    write(a.output/"SCORES.json",scores)
    csvwrite(a.output/"PROBABILITY_REFERENCE_SCORES.csv",scores)
    write(a.output/"PAIRED_REFERENCE_COMPARISONS.json",contrasts)
    csvwrite(a.output/"PAIRED_REFERENCE_COMPARISONS.csv",contrasts)
    write(a.output/"CALIBRATION_AND_DISCRIMINATION.json",diag)
    write(a.output/"RUN_RECEIPT.json",dict(state="COMPLETE_FROZEN_EARLIER_ONLY_PROBABILITY_REFERENCE_COMPARISON",at=now(),protocol_sha256=sha(a.output/"FROZEN_PROTOCOL.json"),score_sha256=sha(a.output/"SCORES.json"),scored_views=len(scores),paired_contrasts=len(contrasts),cached_recipe_offer_rows=len(private_rows),distinct_target_offer_keys=len({(r["week"],r["source_row_index"]) for r in private_rows}),prior_source_qualification=prior_counts,private_rows_sha256=hashlib.sha256(blob).hexdigest(),private_bytes=len(blob),new_fits=0,new_model_inference=0,new_directions=0,new_captures=0,new_NFL_observations=0,Week8_outcomes_read=0,resources=dict(wall_seconds=time.monotonic()-start,cpu_seconds=time.process_time()-cpu,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)))
    print(json.dumps(dict(scores=len(scores),comparisons=len(contrasts),private_bytes=len(blob),wall_seconds=time.monotonic()-start)))


if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("action",choices=("prepare","run"))
    ap.add_argument("--root",type=Path,default=Path(__file__).resolve().parents[1])
    ap.add_argument("--private-root",type=Path,required=True)
    ap.add_argument("--source-root",type=Path,required=True)
    ap.add_argument("--output",type=Path,required=True)
    ap.add_argument("--private-output",type=Path,required=True)
    args=ap.parse_args()
    prepare(args) if args.action=="prepare" else run(args)
