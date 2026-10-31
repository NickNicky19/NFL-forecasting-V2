"""Original bounded empirical-history diagnostic for supplied NFLverse CSVs.

Retrospective observed-stat-row cohort, current-vintage reconstruction. This is
not an ex-ante population, untouched confirmation, authentic historical issue,
strict-current-information cohort or operational adapter. No acquisition.
"""
from __future__ import annotations

import bisect
import collections
import csv
import gzip
import hashlib
import heapq
import json
import math
import re
import resource
import time
from datetime import datetime, timezone
from pathlib import Path
from statistics import fmean, stdev
from zoneinfo import ZoneInfo

VERSION = "v2-empirical-observed-participant-history-diagnostic-v1"
MAP = {"pass_yd":"passing_yards", "pass_td":"passing_tds", "pass_cmp":"completions",
       "pass_att":"attempts", "pass_int":"passing_interceptions", "rush_yd":"rushing_yards",
       "rush_att":"carries", "rec":"receptions", "rec_yd":"receiving_yards"}
COUNTS = {"pass_td", "pass_cmp", "pass_att", "pass_int", "rush_att", "rec"}
PHYSICAL_COUNTS = ("attempts", "completions", "carries", "targets", "receptions", "sacks_suffered",
                   "passing_tds", "rushing_tds", "receiving_tds", "passing_2pt_conversions",
                   "rushing_2pt_conversions", "receiving_2pt_conversions", "punt_returns", "kickoff_returns",
                   "def_tackles_solo", "def_tackles_with_assist", "def_tackle_assists", "def_sacks",
                   "def_interceptions", "fumble_recovery_own", "fumble_recovery_opp", "fg_att", "pt_att")
PHYSICAL_YARDS = ("passing_yards", "rushing_yards", "receiving_yards", "sack_yards_lost",
                  "punt_return_yards", "kickoff_return_yards", "def_interception_yards",
                  "fumble_recovery_yards_own", "fumble_recovery_yards_opp", "misc_yards")
ARMS = ("H-CURRENT", "H-RECENT", "H-MULTI")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dump(path, body):
    Path(path).write_text(json.dumps(body, sort_keys=True, indent=2, allow_nan=False) + "\n")


def numeric(text):
    if text is None or text == "":
        return None
    try:
        value = float(text)
    except (TypeError, ValueError):
        return None
    return value if math.isfinite(value) else None


def valid_count(value):
    return value is not None and value >= 0 and value == int(value)


def target_value(target, values):
    if target in MAP:
        value = values.get(MAP[target])
        return value if value is not None and (target not in COUNTS or valid_count(value)) else None
    if target == "rush_rec_yd":
        a, b = values.get("rushing_yards"), values.get("receiving_yards")
        return a+b if a is not None and b is not None else None
    if target == "anytime_td":
        a, b = values.get("rushing_tds"), values.get("receiving_tds")
        if any(v is not None and not valid_count(v) for v in (a, b)):
            return None
        if any(v is not None and v > 0 for v in (a, b)):
            return 1.
        return 0. if a == 0 and b == 0 else None
    raise ValueError("unregistered target")


class Series:
    """Earlier-availability prefix mean/lower-median, never target-game lookup."""
    def __init__(self, rows):
        rows = sorted(rows)
        self.times, self.sums, self.medians = [], [0.], []
        lower, upper = [], []
        for available, identity, value in rows:
            self.times.append(available)
            self.sums.append(self.sums[-1]+value)
            if not lower or value <= -lower[0]:
                heapq.heappush(lower, -value)
            else:
                heapq.heappush(upper, value)
            if len(lower) > len(upper)+1:
                heapq.heappush(upper, -heapq.heappop(lower))
            if len(upper) > len(lower):
                heapq.heappush(lower, -heapq.heappop(upper))
            self.medians.append(-lower[0])

    def at(self, cutoff):
        n = bisect.bisect_left(self.times, cutoff)
        return (n, self.sums[n]/n, self.medians[n-1], self.times[n-1]) if n else (0, None, None, None)


class Metrics:
    def __init__(self):
        self.errors, self.actuals = [], []
        self.n_queries = self.n_fallback = self.n_zero = 0
        self.log_losses = []
        self.infinite_log = 0

    def add(self, prediction, actual, fallback, target):
        self.n_queries += 1
        self.n_fallback += fallback != "none"
        self.n_zero += fallback == "constant_zero"
        if actual is None:
            return
        self.errors.append(prediction-actual)
        if target == "anytime_td":
            self.actuals.append(actual)
            event_mass = prediction if actual else 1-prediction
            if event_mass <= 0:
                self.infinite_log += 1
            else:
                self.log_losses.append(-math.log(event_mass))

    def result(self):
        errors = self.errors
        out = {"forecast_queries":self.n_queries, "scored_n":len(errors),
               "missing_actual_n":self.n_queries-len(errors), "fallback_n":self.n_fallback,
               "fallback_rate":self.n_fallback/self.n_queries if self.n_queries else None,
               "constant_zero_n":self.n_zero}
        if not errors:
            return dict(out, mae=None, mse=None, rmse=None, bias=None)
        absolute = sorted(abs(v) for v in errors)
        def quantile(p):
            x = (len(absolute)-1)*p
            i, j = math.floor(x), math.ceil(x)
            return absolute[i]+(absolute[j]-absolute[i])*(x-i)
        mse = fmean(v*v for v in errors)
        out.update(mae=fmean(absolute), mse=mse, rmse=math.sqrt(mse), bias=fmean(errors),
                   p90_abs=quantile(.9), p95_abs=quantile(.95), max_abs=absolute[-1],
                   exact_rate=sum(v == 0 for v in errors)/len(errors))
        for tol in (1, 5, 10):
            out[f"abs_lt_{tol}"] = sum(v < tol for v in absolute)/len(absolute)
            out[f"abs_le_{tol}"] = sum(v <= tol for v in absolute)/len(absolute)
        if self.actuals:
            prevalence = fmean(self.actuals)
            out.update(brier=mse, prevalence=prevalence, prevalence_reference_brier=prevalence*(1-prevalence),
                       log_loss=None if self.infinite_log else fmean(self.log_losses),
                       infinite_log_losses=self.infinite_log)
        return out


def write_csv(path, rows):
    rows = list(rows)
    fields = list(dict.fromkeys(k for row in rows for k in row))
    with Path(path).open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def run(source_root, protocol_path, public_root, private_root):
    start, cpu = time.monotonic(), time.process_time()
    source_root, public_root, private_root = map(Path, (source_root, public_root, private_root))
    protocol = json.loads(Path(protocol_path).read_text())
    if protocol["version"] != VERSION or protocol["state"] != "REGISTERED_BEFORE_TARGET_VALUE_INSPECTION":
        raise ValueError("frozen diagnostic protocol required")
    if (public_root/"RUN_RECEIPT.json").exists() or (private_root/"predictions.csv.gz").exists():
        raise ValueError("immutable run already exists")
    for item in protocol["source_ids"]:
        path = source_root/item["name"]
        if path.stat().st_size != item["bytes"] or sha(path) != item["sha256"]:
            raise ValueError("frozen source bytes changed")
    if sum(x["bytes"] for x in protocol["source_ids"]) > protocol["budget"]["max_source_bytes"]:
        raise ValueError("source byte budget")
    code_hash = sha(__file__)
    registration = dict(procedure_version=VERSION, protocol_sha256=sha(protocol_path),
                        code_sha256=code_hash, registered_before_numeric_decode=datetime.now(timezone.utc).isoformat(),
                        source_ids=protocol["source_ids"], budget=protocol["budget"])
    public_root.mkdir(parents=True, exist_ok=True)
    private_root.mkdir(parents=True, exist_ok=True)
    if (public_root/"EXECUTION_REGISTRATION.json").exists():
        raise ValueError("execution registration already exists")
    dump(public_root/"EXECUTION_REGISTRATION.json", registration)
    def budget():
        if time.monotonic()-start > protocol["budget"]["wall_seconds"]:
            raise RuntimeError("wall budget exceeded")
        if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024 > protocol["budget"]["max_peak_memory_bytes"]:
            raise RuntimeError("memory budget exceeded")
    # Only these schedule fields are consumed; scores/odds/weather are never numeric predictors.
    schedules = {}
    with (source_root/"games.csv").open() as f:
        for r in csv.DictReader(f):
            if r["season"] not in {str(y) for y in range(2022, 2027)} or r["game_type"] != "REG":
                continue
            if r["season"] == "2026" and int(r["week"]) > 7:
                continue
            gid = r["game_id"]
            if gid in schedules:
                raise ValueError("duplicate game identity")
            if not r["gametime"] or not r["gameday"]:
                raise ValueError("unknown game kickoff")
            dt = datetime.fromisoformat(r["gameday"]+"T"+r["gametime"]).replace(tzinfo=ZoneInfo("America/New_York"))
            schedules[gid] = dict(season=int(r["season"]), week=int(r["week"]),
                                  kickoff=int(dt.timestamp()), home=r["home_team"], away=r["away_team"])
    source_counts = collections.Counter()
    qualified = []
    identity_seen = set()
    needed = set(MAP.values()) | set(PHYSICAL_COUNTS) | set(PHYSICAL_YARDS) | {"rushing_tds", "receiving_tds"}
    for year in range(2022, 2027):
        with (source_root/f"stats_player_week_{year}.csv").open() as f:
            reader = csv.DictReader(f)
            required = {"player_id", "position", "season", "week", "season_type", "game_id", "team", "opponent_team"} | needed
            if not required <= set(reader.fieldnames):
                raise ValueError("wrong/incomplete source schema")
            for r in reader:
                source_counts["raw_rows"] += 1
                if source_counts["raw_rows"] > protocol["budget"]["max_source_rows"]:
                    raise ValueError("source row budget")
                if r["season_type"] != "REG" or int(r["season"]) != year or (year == 2026 and int(r["week"]) > 7):
                    source_counts["outside_panel_before_numeric_decode"] += 1
                    continue
                if r["position"] not in {"QB", "RB", "WR", "TE"}:
                    source_counts["outside_registered_positions"] += 1
                    continue
                if not re.fullmatch(r"00-\d{7}", r["player_id"]):
                    source_counts["unqualified_exact_identity"] += 1
                    continue
                game = schedules.get(r["game_id"])
                if not game or game["season"] != year or game["week"] != int(r["week"]):
                    raise ValueError("stats/schedule identity mismatch")
                if (r["team"], r["opponent_team"]) not in ((game["home"], game["away"]), (game["away"], game["home"])):
                    raise ValueError("stats/schedule team mismatch")
                key = (r["game_id"], r["player_id"])
                if key in identity_seen:
                    raise ValueError("duplicate player-game; do not select convenient revision")
                identity_seen.add(key)
                vals = {k:numeric(r[k]) for k in needed}
                played = (any(valid_count(vals[k]) and vals[k] > 0 for k in PHYSICAL_COUNTS)
                          or any(vals[k] is not None and vals[k] != 0 for k in PHYSICAL_YARDS))
                source_counts["physical_played" if played else "participation_unknown"] += 1
                qualified.append(dict(player_id=r["player_id"], game_id=r["game_id"], position=r["position"],
                                      team=r["team"], opponent=r["opponent_team"], season=year,
                                      week=int(r["week"]), kickoff=game["kickoff"],
                                      available=game["kickoff"]+7*86400, played=played,
                                      values={t:target_value(t, vals) if played else None for t in protocol["targets"]}))
                budget()
    queries, observations = [], []
    target_source = {}
    for row in qualified:
        for target in protocol["targets"]:
            view = ("primary" if row["position"] in protocol["primary_roles"][target] else
                    "extended" if row["position"] in protocol["extended_roles"].get(target, []) else None)
            if view is None:
                continue
            value = row["values"][target]
            q = {k:row[k] for k in ("player_id", "game_id", "position", "season", "week", "kickoff", "available")}
            q.update(target=target, actual=value, population=view, participation="played" if row["played"] else "unknown")
            queries.append(q)
            state = "missing_or_unsupported" if value is None else "explicit_zero" if value == 0 else "explicit_nonzero"
            target_source.setdefault(target, collections.Counter())[state] += 1
            if value is not None:
                observations.append(q)
    if len(queries) > protocol["budget"]["max_query_cells"]:
        raise ValueError("query budget")
    membership = hashlib.sha256(json.dumps([{k:q[k] for k in ("player_id", "game_id", "target", "population", "position", "season", "week")} for q in queries], sort_keys=True).encode()).hexdigest()
    dump(public_root/"SOURCE_QUALIFICATION.json", dict(version=VERSION, source_tier="CURRENT_VINTAGE_RECONSTRUCTION",
         numerical_source_rows=dict(source_counts), target_explicitness={k:dict(v) for k,v in target_source.items()},
         source_ids=protocol["source_ids"], query_membership_sha256=membership, query_cells=len(queries),
         unique_player_games=len(qualified), unique_games=len({q["game_id"] for q in qualified}),
         zero_policy="Only explicit numeric0 after positive official physical-event proof; blanks never0",
         cohort="Retrospective statistical-row/observed-participation diagnostic; not full exante forecast population",
         cutoff="pergame kickoff leftlimit; earlier kickoff+7day strictly before cutoff; reconstruction assumption",
         feature_memory="none; rowposition/observedcohort is retrospective so no full strictcurrent claim",
         unused_columns="EPA/CPOE/NGS/weather/odds/fantasy totals/currentrosters/PFRsnaps not consumed",
         chart="BLOCKED_EXACT_RARE_PRIMITIVE_ZERO_ATTRIBUTION_CONTRACT",
         source_license="Owner-restored official NFLverse basic-stat family; no raw redistribution; full license receipt review external"))
    # Aggregation keys: season/week, pooled, position and fallback contributions.
    metrics = collections.defaultdict(Metrics)
    paired = collections.defaultdict(list)
    n_forecasts = summary_series = summary_observations = 0
    private_file = private_root/"predictions.csv.gz"
    fields = ["run_id", "season", "week", "game_id", "player_id", "position", "target", "population", "history_regime", "product", "prediction", "actual", "participation", "fallback", "own_n", "used_n", "cutoff_epoch_utc", "latest_training_available_epoch_utc", "fit_floor", "fit_ceiling", "evidence_tier"]
    with gzip.open(private_file, "wt", newline="", compresslevel=6) as out:
        writer = csv.DictWriter(out, fieldnames=fields)
        writer.writeheader()
        for season in range(2022, 2027):
            season_queries = [q for q in queries if q["season"] == season]
            for arm in ARMS:
                floor = season if arm == "H-CURRENT" else max(2022, season-1) if arm == "H-RECENT" else 2022
                group = collections.defaultdict(list)
                for obs in observations:
                    if floor <= obs["season"] <= season:
                        item = (obs["available"], (obs["game_id"], obs["player_id"]), obs["actual"])
                        group[(obs["target"], obs["position"], obs["player_id"])].append(item)
                        group[(obs["target"], obs["position"], None)].append(item)
                index = {key:Series(rows) for key,rows in group.items()}
                summary_series += len(index)
                summary_observations += sum(len(v) for v in group.values())
                for q in season_queries:
                    own = index.get((q["target"], q["position"], q["player_id"]))
                    own_values = own.at(q["kickoff"]) if own else (0,None,None,None)
                    values = own_values
                    fallback = "none"
                    if not own_values[0]:
                        position = index.get((q["target"], q["position"], None))
                        values = position.at(q["kickoff"]) if position else (0,None,None,None)
                        fallback = "position_empirical" if values[0] else "constant_zero"
                    products = [("event_probability", values[1])] if q["target"] == "anytime_td" else [("empirical_mean",values[1]),("lower_median",values[2])]
                    for product, prediction in products:
                        prediction = prediction if values[0] else 0.
                        if values[3] is not None and values[3] >= q["kickoff"]:
                            raise AssertionError("training chronology failure")
                        record = dict(run_id=VERSION, season=season, week=q["week"], game_id=q["game_id"], player_id=q["player_id"], position=q["position"], target=q["target"], population=q["population"], history_regime=arm, product=product, prediction=prediction, actual=q["actual"], participation=q["participation"], fallback=fallback, own_n=own_values[0], used_n=values[0], cutoff_epoch_utc=q["kickoff"], latest_training_available_epoch_utc=values[3], fit_floor=floor, fit_ceiling=season, evidence_tier="current_vintage_reconstruction")
                        writer.writerow(record)
                        n_forecasts += 1
                        if n_forecasts > protocol["budget"]["max_forecast_rows"]:
                            raise ValueError("forecast row budget")
                        base = (q["target"], q["population"], arm, product)
                        for ending in ((str(season),"ALL","ALL","ALL"), (str(season),str(q["week"]),"ALL","ALL"),
                                       ("POOLED_2022_2026","ALL","ALL","ALL"), (str(season),"ALL",q["position"],"ALL"),
                                       (str(season),"ALL","ALL",fallback)):
                            metrics[base+ending].add(prediction,q["actual"],fallback,q["target"])
                        if season == 2026 and q["actual"] is not None and q["population"] == "primary":
                            loss = (prediction-q["actual"])**2 if q["target"] == "anytime_td" else abs(prediction-q["actual"])
                            paired[(q["target"],product,q["week"],q["game_id"],q["player_id"])].append((arm,loss,fallback))
                    budget()
                del index, group
    if private_file.stat().st_size > protocol["budget"]["max_private_output_bytes"]:
        raise ValueError("private retained byte budget")
    score_rows = []
    for key,m in sorted(metrics.items()):
        target,pop,arm,product,season,week,position,fallback = key
        score_rows.append(dict(target=target,population=pop,history_regime=arm,product=product,season=season,week=week,position=position,fallback_view=fallback,**m.result()))
    write_csv(public_root/"SEASON_RESULTS_2022_2026.csv",score_rows)
    a_rows = [r for r in score_rows if r["season"] == "2026" and r["week"] == "ALL" and r["position"] == "ALL" and r["fallback_view"] == "ALL"]
    write_csv(public_root/"HISTORY_COMPARISON_2026_W1_W7.csv",a_rows)
    # Explicitly equal-season metric summary, separate from pooled micro rows.
    balanced=[]
    for target in protocol["targets"]:
        for pop in ("primary","extended"):
            for arm in ARMS:
                for product in ("event_probability",) if target == "anytime_td" else ("empirical_mean","lower_median"):
                    selected=[r for r in score_rows if (r["target"],r["population"],r["history_regime"],r["product"])==(target,pop,arm,product) and r["season"].isdigit() and r["week"]=="ALL" and r["position"]=="ALL" and r["fallback_view"]=="ALL" and r.get("mae") is not None]
                    if selected:
                        balanced.append(dict(target=target,population=pop,history_regime=arm,product=product,seasons=len(selected),definition="equalweight_mean_of_each_season_metric;2026W1-7otherseasonsfullREG",mae=fmean(r["mae"] for r in selected),mse=fmean(r["mse"] for r in selected),bias=fmean(r["bias"] for r in selected)))
    write_csv(public_root/"SEASON_BALANCED_RESULTS.csv",balanced)
    comparisons=[]
    for target in protocol["targets"]:
        for product in (("event_probability",) if target=="anytime_td" else ("empirical_mean","lower_median")):
            for other in ("H-RECENT","H-MULTI"):
                all_diffs,week_diffs,learned=[] ,collections.defaultdict(list),[]
                for key,values in paired.items():
                    if key[:2] != (target,product):continue
                    arms={arm:(loss,fb) for arm,loss,fb in values}
                    if "H-CURRENT" not in arms or other not in arms:raise AssertionError("unpaired histories")
                    d=arms[other][0]-arms["H-CURRENT"][0];all_diffs.append(d);week_diffs[key[2]].append(d)
                    if arms[other][1]==arms["H-CURRENT"][1]=="none":learned.append(d)
                if all_diffs:
                    wm=[fmean(v) for _,v in sorted(week_diffs.items())];estimate=fmean(wm)
                    half=2.447*stdev(wm)/math.sqrt(len(wm)) if len(wm)==7 else None
                    comparisons.append(dict(target=target,product=product,comparison=other+"_minus_H-CURRENT",primary_loss="Brier" if target=="anytime_td" else "absolute_error",paired_n=len(all_diffs),paired_weeks=len(wm),pooled_mean_loss_difference=fmean(all_diffs),week_balanced_mean_loss_difference=estimate,week_t95_low=estimate-half if half is not None else None,week_t95_high=estimate+half if half is not None else None,learned_only_paired_n=len(learned),learned_only_mean_loss_difference=fmean(learned) if learned else None,uncertainty_limit="7weekclusters_insufficient_for_strong_claim;exploratorytinterval;no_selectioncorrection;sharedgame/playerdependence"))
    write_csv(public_root/"PAIRED_HISTORY_DIFFERENCES.csv",comparisons)
    receipt=dict(version=VERSION,status="NEW_EXPERIMENT_DIAGNOSTIC_COMPLETE_NOT_OPERATIONALLY_ADMITTED",protocol_sha256=sha(protocol_path),code_sha256=code_hash,query_membership_sha256=membership,original_optimization_fits=0,forecast_rows=n_forecasts,unique_query_cells=len(queries),unique_player_games=len(qualified),unique_games=len({q["game_id"] for q in qualified}),season_week_coverage={str(y):sorted({q['week'] for q in queries if q['season']==y}) for y in range(2022,2027)},empirical_series_constructed=summary_series,series_observations_including_shared_position_summaries=summary_observations,accuracy_metric_rows=len(score_rows),source_counts=dict(source_counts),private_prediction_sha256=sha(private_file),private_prediction_bytes=private_file.stat().st_size,private_storage="LOCAL_ONLY;approved_private_companion_not_bound;source_and_code_hashes_do_not_establish_private_durability",resource=dict(wall_seconds=time.monotonic()-start,cpu_seconds=time.process_time()-cpu,peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,threads_used=1),actual_completed_at=datetime.now(timezone.utc).isoformat(),source_tier="CURRENT_VINTAGE_RECONSTRUCTION",cohort="RETROSPECTIVE_OBSERVED_STAT_ROW_PARTICIPATION_DIAGNOSTIC;noexante/fullsystem/purecurrentclaim",chart_state="BLOCKED_EXACT_LABEL_CONTRACT",no_new_prospective_forecasts=True)
    receipt['public_outputs']={p.name:sha(p) for p in public_root.glob('*.csv')}
    dump(public_root/"RUN_RECEIPT.json",receipt)
    return receipt
