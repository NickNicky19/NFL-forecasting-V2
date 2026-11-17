"""Independent frozen-row statistical crossings and public aggregate checks.

No C grader/status, author law class, fitting or source collection is called.
Approved reference grade rows remain in memory; only safe hashes/counts leave.
"""
from __future__ import annotations

import argparse
import collections
import gzip
import hashlib
import json
import math
import resource
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy import special, stats

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT/"reports/information-skill-follow-through-01/B/opportunity-v1"
METHODS = ("OPP_BASE", "OPP_MEAN", "OPP_JOINT", "DIRECT_ATT")
TARGETS = ("pass_att", "pass_cmp")


def read(path):
    path = Path(path); body = path.read_bytes()
    return json.loads(gzip.decompress(body) if path.suffix == ".gz" else body)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def key(row):
    return row["game_id"], row["player_id"], row.get("target", row.get("category"))


def compact_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


class Verify:
    def __init__(self):
        self.start, self.wall = time.process_time(), time.monotonic()
        self.checks, self.problems = 0, []

    def check(self, valid, label):
        self.checks += 1
        if not valid:
            self.problems.append(label)
        if time.process_time()-self.start > 24:
            raise RuntimeError("INDEPENDENT_GRADE_CPU24_OF25_COMPLETION_GUARD")

    def close(self, left, right, label, tolerance=2e-10):
        self.check((left is None and right is None) or
                   (left is not None and right is not None and math.isclose(
                       left, right, rel_tol=1e-10, abs_tol=tolerance)), label)


def independent_mean(payload, thinning=1.):
    kind = payload["kind"]
    if kind in ("gamma_poisson_count", "poisson"):
        return float(payload["mean"])*thinning
    if kind == "zero":
        return 0.
    if kind == "geometric":
        q = float(payload["q"])
        return q/(1-q)*thinning
    if kind == "exact_binomial_thinned_leaf_v1":
        return independent_mean(payload["source"], thinning*payload["conversion"])
    if kind == "leaf_mixture":
        b = float(payload["mixture"])
        return ((1-b)*float(np.dot(payload["support"], payload["weights"]))
                + b*independent_mean(payload["prior"]))*thinning
    if kind == "opportunity_team_binomial_mixture_v1":
        t, weights, probability = independent_team_grid(payload, thinning)
        return float(np.dot(weights, t*probability))
    raise ValueError("Unsupported trusted law kind: "+kind)


def independent_team_grid(payload, thinning):
    mean, shape = float(payload["team_mean"]), float(payload["team_shape"])
    t = np.arange(int(payload["grid_max"])+1)
    weights = stats.nbinom.pmf(t, shape, shape/(shape+mean)) if mean else np.array([1.])
    ratio = np.zeros(len(t)); positive = t > 0
    ratio[positive] = np.log(t[positive]/float(payload["T_reference"]))
    probability = special.expit(float(payload["share_base_logit"])+float(payload["volume_slope"])*ratio)
    probability *= float(payload["conversion"])*thinning
    return t, weights, probability


def independent_cdf(payload, value, thinning=1.):
    """Explicit count-law integration, independent of author restore/CDF code."""
    k = math.floor(value)
    if k < 0:
        return 0.
    kind = payload["kind"]
    if kind == "zero":
        return 1.
    if kind == "gamma_poisson_count":
        mean, shape = float(payload["mean"])*thinning, float(payload["shape"])
        return 1. if not mean else float(stats.nbinom.cdf(k, shape, shape/(shape+mean)))
    if kind == "poisson":
        return float(stats.poisson.cdf(k, float(payload["mean"])*thinning))
    if kind == "geometric":
        q = float(payload["q"]); mean = q/(1-q)*thinning
        return 1.-(mean/(1+mean))**(k+1)
    if kind == "exact_binomial_thinned_leaf_v1":
        return independent_cdf(payload["source"], k, thinning*float(payload["conversion"]))
    if kind == "leaf_mixture":
        support, weights = np.asarray(payload["support"]), np.asarray(payload["weights"])
        empirical = float(np.dot(weights, support <= k)) if thinning == 1. else float(np.dot(weights, stats.binom.cdf(k, support, thinning)))
        b = float(payload["mixture"])
        return (1-b)*empirical+b*independent_cdf(payload["prior"], k, thinning)
    if kind == "opportunity_team_binomial_mixture_v1":
        t, weights, probability = independent_team_grid(payload, thinning)
        return float(np.dot(weights, stats.binom.cdf(k, t, probability)))
    raise ValueError("Unsupported trusted law kind: "+kind)


def independent_median(payload):
    low, high = -1, 1
    while independent_cdf(payload, high) < .5:
        high = 2*high+1
        if high > 10000:
            raise ValueError("Bounded median verification grid exceeded")
    while high-low > 1:
        middle = (low+high)//2
        if independent_cdf(payload, middle) >= .5:
            high = middle
        else:
            low = middle
    return high


def summary(frame):
    selected = [row for row in frame if row["side"] in ("OVER", "UNDER")]
    result = {}
    for side in ("OVER", "UNDER", "COMBINED"):
        chosen = selected if side == "COMBINED" else [row for row in selected if row["side"] == side]
        decided = [row for row in chosen if row["grade"] in ("WIN", "LOSS")]
        wins = sum(row["grade"] == "WIN" for row in decided)
        losses = len(decided)-wins
        result[side] = dict(wins=wins if decided else None, losses=losses if decided else None,
                            decided=len(decided), selected=len(chosen), rate=wins/len(decided) if decided else None)
    result.update(eligible=len(frame), available=sum(row["available"] for row in frame),
                  unavailable=sum(not row["available"] for row in frame), selected=len(selected),
                  decided=sum(row["grade"] in ("WIN", "LOSS") for row in selected),
                  unknown=sum(row["grade"] == "UNKNOWN" for row in frame),
                  abstentions=sum(row["side"] == "ABSTAIN" for row in frame),
                  games=len({row["game_id"] for row in frame}),
                  fallback_selected=sum(row["fallback"] for row in selected))
    good = [row for row in frame if row.get("over") is not None and row["actual"] is not None]
    brier = [((row["over"]-int(row["actual"]>row["line"]))**2) for row in good]
    probabilities = [row["over"] if row["actual"] > row["line"] else 1-row["over"] for row in good]
    result["probability"] = dict(events=len(good), strict_binary_Over_Brier=sum(brier)/len(brier) if brier else None,
                                  log_loss=sum(-math.log(p) for p in probabilities)/len(probabilities) if probabilities else None)
    return result


def fallback(value):
    return bool(value) and value not in ("none", "NONE", "NOT_APPLICABLE")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--att-grades", type=Path, required=True)
    parser.add_argument("--cmp-grades", type=Path, required=True)
    parser.add_argument("--evaluation", type=Path, default=BASE/"evaluation-v1")
    parser.add_argument("--predictions", type=Path, default=BASE/"wave-v1/predictions")
    parser.add_argument("--out", type=Path, default=BASE/"independent/GRADE_CHECK_V1.json")
    args = parser.parse_args()
    if args.out.exists() or not args.out.resolve().is_relative_to(BASE.resolve()):
        raise ValueError("Fresh owned public receipt required")
    v = Verify(); exception = None; details = {}; bindings = {}
    try:
        prior = read(ROOT/"reports/targeted-accuracy-w1w9-01/B/evaluation/EXECUTION_INPUT_BINDINGS_V1.json")
        offers = {}
        for target, path, model in (("pass_att", args.att_grades, "COMMON_EXPOSURE"), ("pass_cmp", args.cmp_grades, "B0")):
            required = prior["existing_ATT_grade_sha256" if target == "pass_att" else "existing_CMP_grade_sha256"]
            v.check(sha(path) == required, "approved existing reference hash "+target)
            bindings[target+"_reference"] = dict(sha256=sha(path), bytes=path.stat().st_size,
                                                 reference_model=model, policy="P1_MEAN", private_locator_exported=False)
            body = read(path); rows = body["rows"] if isinstance(body, dict) else body
            rr = [row for row in rows if row.get("category", row.get("target")) == target
                  and str(row.get("model_key", row.get("method", ""))).upper() == model
                  and row.get("policy") == "P1_MEAN"]
            v.check(len(rr) == 142 and len({key(row) for row in rr}) == 142, "exact142 opportunity reference "+target)
            v.check(collections.Counter(row["week"] for row in rr) == {5:28,6:28,7:28,8:28,9:30}, "weekly142 reference "+target)
            for row in rr:
                v.check(row.get("appearance") == "PLAYED" and row.get("position", "QB") == "QB", "qualified physical QB reference")
                actual = row.get("actual"); line = row.get("line")
                v.check(actual is not None and math.isfinite(actual) and actual >= 0 and actual == int(actual), "explicit nonnegative official count")
                v.check(line is not None and math.isfinite(line) and float(line)%1 == .5, "native actual halfpoint threshold")
                v.check(row.get("period") == "FULL_GAME_INCLUDING_OT" and row.get("comparator") == "STRICT_OVER_UNDER", "full-game strict event contract")
            offers[target] = rr
        v.check({key(row)[:2] for row in offers["pass_att"]} == {key(row)[:2] for row in offers["pass_cmp"]}, "ATT/CMP common player-game membership")
        tables = read(args.evaluation/"MAIN_TABLES_V1.json.gz")
        public = [row for row in tables if row["method"] in METHODS]
        predictions = {}; prediction_bindings = []
        for path in sorted(args.predictions.glob("2026-W*.json.gz")):
            prediction_bindings.append(dict(file=path.name, sha256=sha(path)))
            for row in read(path)["rows"]:
                identity = row["method"], key(row)
                v.check(identity not in predictions, "unique frozen prediction")
                predictions[identity] = row
        bound = read(args.evaluation/"EXECUTION_INPUT_BINDINGS_V1.json")
        v.check(bound["prediction_files"] == prediction_bindings, "evaluated exact saved prediction files")
        bindings["prediction_files"] = prediction_bindings
        bindings["main_tables"] = dict(path=str((args.evaluation/"MAIN_TABLES_V1.json.gz").relative_to(ROOT)), sha256=sha(args.evaluation/"MAIN_TABLES_V1.json.gz"))
        own = {}; maximum_mean_difference = 0.
        for target in TARGETS:
            for method in METHODS:
                frames = {policy:[] for policy in ("MEAN", "MEDIAN", "LAW")}
                for offer in offers[target]:
                    prediction = predictions.get((method, key(offer)))
                    if prediction is None:
                        for frame in frames.values():
                            frame.append(dict(game_id=offer["game_id"], week=offer["week"], available=False, side=None,
                                              grade="UNAVAILABLE", actual=offer["actual"], line=offer["line"], over=None, fallback=False))
                        continue
                    v.check(prediction["actual"] == offer["actual"], "frozen label matches explicit qualified reference")
                    payload = prediction["law"]
                    mean = independent_mean(payload)
                    maximum_mean_difference = max(maximum_mean_difference, abs(mean-prediction["mean"]))
                    v.close(mean, prediction["mean"], "independently calculated typed mean", 1e-8)
                    median = independent_median(payload)
                    v.check(median == prediction["lower_median"], "independently calculated lower median")
                    under = independent_cdf(payload, offer["line"]); over = 1.-under
                    v.check(0 <= under <= 1 and 0 <= over <= 1, "valid independent exact halfpoint mass")
                    for policy, point in (("MEAN", mean), ("MEDIAN", median), ("LAW", None)):
                        side = ("OVER" if over > under else "UNDER" if under > over else "ABSTAIN") if point is None else (
                            "OVER" if point > offer["line"] else "UNDER" if point < offer["line"] else "ABSTAIN")
                        grade = "ABSTAIN" if side == "ABSTAIN" else "WIN" if (
                            offer["actual"] > offer["line"] if side == "OVER" else offer["actual"] < offer["line"]) else "LOSS"
                        frames[policy].append(dict(game_id=offer["game_id"], week=offer["week"], available=True, side=side,
                            grade=grade, actual=offer["actual"], line=offer["line"], over=over, fallback=fallback(prediction.get("fallback"))))
                for policy, frame in frames.items():
                    for window in ("ALL", "5", "6", "7", "8", "9"):
                        selected = frame if window == "ALL" else [row for row in frame if row["week"] == int(window)]
                        expected = summary(selected)
                        match = [row for row in public if row["category"] == target and row["method"] == method
                                 and row["policy"] == policy and str(row["window"]) == window]
                        v.check(len(match) == 1, "unique public target/method/policy/week")
                        if not match:
                            continue
                        reported = match[0]
                        for side in ("OVER", "UNDER", "COMBINED"):
                            for field in ("wins", "losses", "decided", "selected", "rate"):
                                v.close(expected[side][field], reported[side][field], "independent own-side "+side+" "+field)
                        for field in ("eligible", "available", "unavailable", "selected", "decided", "unknown", "abstentions", "games", "fallback_selected"):
                            v.check(expected[field] == reported[field], "independent coverage/state "+field)
                        for field in ("events", "strict_binary_Over_Brier", "log_loss"):
                            v.close(expected["probability"][field], reported["probability"][field], "independent exact-event "+field)
                        own[target, method, policy, window] = expected
        # Separate arithmetic across every published main/selected aggregate.
        selective = read(args.evaluation/"SELECTIVE_TABLES_V1.json.gz")
        for row in tables+selective:
            for side in ("OVER", "UNDER", "COMBINED"):
                z = row[side]; wins = z["wins"] or 0; losses = z["losses"] or 0
                v.check(wins+losses == z["decided"], "public aggregate W+L")
                v.close(z["rate"], wins/z["decided"] if z["decided"] else None, "public aggregate rate")
            for field in ("wins", "losses", "decided", "selected"):
                v.check((row["COMBINED"][field] or 0) == (row["OVER"][field] or 0)+(row["UNDER"][field] or 0), "public weighted combined")
            v.check(row["available"]+row["unavailable"] == row["eligible"], "public availability partition")
            v.check(sum(row["selected_by_week"].values()) == row["selected"], "public weekly selections")
        details = dict(independently_recomputed_main_views=len(own), public_main_rows=len(tables),
                       public_selective_arithmetic_rows=len(selective), maximum_typed_mean_difference=maximum_mean_difference,
                       actual_line_weeks=[5,6,7,8,9], eligible_per_target=142,
                       unique_player_games=142, unique_games=71,
                       own_full_board=[dict(target=target, method=method, policy=policy, **values)
                           for (target,method,policy,window),values in own.items() if window == "ALL"],
                       proper_score_contract="Independent binary exact halfpoint Over Brier/log loss, conditional qualified played statistical counts; not venue settlement or EV.",
                       independence="Direct threshold comparisons and SciPy NB/explicit team-T binomial mixture/empirical-geometric thinning. No author law restore/CDF, C status, C summary, common scorer, selector or optimizer called.")
    except Exception as exc:
        message = str(exc)
        for path in (args.att_grades, args.cmp_grades):
            message = message.replace(str(path), "[approved private reference]")
        exception = dict(type=type(exc).__name__, message=message)
        v.problems.append("Execution failure preserved; no automatic retry")
    receipt = dict(id="B_OPPORTUNITY_INDEPENDENT_NATIVE_GRADES_v1", at_UTC=datetime.now(timezone.utc).isoformat(),
        status="PASS_IN_CHECKED_SCOPE" if not v.problems else "FAIL_PRESERVED_NO_AUTOMATIC_RETRY",
        checks=v.checks, problems=v.problems, exception=exception, details=details, bindings=bindings,
        verifier_sha256=sha(__file__), resources=dict(CPU_seconds=time.process_time()-v.start,
            wall_seconds=time.monotonic()-v.wall, CPU_cap_seconds=25, new_fits=0, source_collection=0,
            new_scientific_grading_runs=0, independent_verification_of_frozen_rows=True,
            protected_rows_written=0, peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024),
        limits=["Approved reference rows and public aggregates do not authenticate original quote clocks, historical source vintages or a full pregame roster.",
                "Frozen-output verification is distinct from fit reproduction. Preserve the team-model independent strict failure and share-model pass separately.",
                "Selected-policy records receive public aggregate arithmetic only here; no independent selective membership or website-policy qualification is implied.",
                "No private rows/locators, new source feed, current forecast, C admission or deployment exported."])
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x") as stream:
        json.dump(receipt, stream, indent=2, allow_nan=False); stream.write("\n")
    print(json.dumps({name:receipt[name] for name in ("status", "checks", "problems", "exception", "resources")}))
    raise SystemExit(bool(v.problems))


if __name__ == "__main__":
    main()
