"""Bounded independent opportunity design/law checks; no optimizer or grading.

NFL fixtures are software evidence, not new forecast evaluations. Historical
clocks retain the source's seven-day reconstruction, not original publication.
"""
from __future__ import annotations

import argparse
import copy
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
sys.path.insert(0, str(ROOT))
from nfl_v2 import opportunity_information as oi
from nfl_v2.passing_opportunity_profiles import OpportunityHistory
from nfl_v2 import player_context_matchup as ctx
from tools import run_opportunity_information as runner
from tools.run_player_context_wave import read, sha

BASE = ROOT/"reports/information-skill-follow-through-01/B/opportunity-v1"
IDENTITY = ("game_id", "player_id", "season", "week", "team", "opponent", "kickoff")


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def prior_rows(rows, cutoff, **filters):
    return sorted([row for row in rows if row["available"] < cutoff
                   and all(row[key] == value for key, value in filters.items())],
                  key=lambda row: (row["kickoff"], row["game_id"], row.get("player_id", row["team"])))


def independent_design(body, query):
    """Separate direct sums/formulas; no author history/profile methods."""
    cutoff = query.get("cutoff", query["kickoff"])
    teams, qbs = body["team_games"], body["QB_games"]
    prior = prior_rows(teams, cutoff)
    offense = prior_rows(teams, cutoff, team=query["team"])[-16:]
    defense = prior_rows(teams, cutoff, opponent=query["opponent"])[-16:]
    own = prior_rows(qbs, cutoff, player_id=query["player_id"])[-8:]
    result = dict(team_x=None, team_offset=None, share_x=None, share_offset=None,
                  T_reference=None, eligible=False, team_eligible=False, share_eligible=False)
    if not prior:
        return result
    total = lambda rr, field: math.fsum(row["counts"][field] for row in rr)
    pooled_T = total(prior, "opportunities")/len(prior)
    if pooled_T <= 0:
        return result
    offense_T = (total(offense, "opportunities")+4*pooled_T)/(len(offense)+4)
    defense_T = (total(defense, "opportunities")+4*pooled_T)/(len(defense)+4)
    result.update(team_x=[1., math.log(offense_T/pooled_T), math.log(defense_T/pooled_T)],
                  team_offset=math.log(pooled_T), T_reference=offense_T, team_eligible=True)
    if not own:
        return result
    tm = {(row["game_id"], row["team"]): row for row in teams}
    pooled_qb = prior_rows(qbs, cutoff)
    pool_T = math.fsum(tm[row["game_id"], row["team"]]["counts"]["opportunities"] for row in pooled_qb)
    pool_team_A = math.fsum(tm[row["game_id"], row["team"]]["counts"]["credited_attempts"] for row in pooled_qb)
    own_T = math.fsum(tm[row["game_id"], row["team"]]["counts"]["opportunities"] for row in own)
    own_team_A = math.fsum(tm[row["game_id"], row["team"]]["counts"]["credited_attempts"] for row in own)
    if pool_T <= 0 or pool_team_A <= 0:
        return result
    pool_A, own_A = total(pooled_qb, "credited_attempts"), total(own, "credited_attempts")
    fraction = (own_A+100*pool_A/pool_T)/(own_T+100)
    own_share = (own_A+100*pool_A/pool_team_A)/(own_team_A+100)
    team_rate = total(prior, "credited_attempts")/total(prior, "opportunities")
    offense_rate = (total(offense, "credited_attempts")+100*team_rate)/(total(offense, "opportunities")+100)
    last = own[-1]
    last_A = last["counts"]["credited_attempts"]
    last_team_A = tm[last["game_id"], last["team"]]["counts"]["credited_attempts"]
    probabilities = (fraction, own_share, team_rate, offense_rate)
    if last_team_A <= 0 or not 0 <= last_A <= last_team_A or any(not 0 < p < 1 for p in probabilities):
        return result
    latest = (last_A+.5)/(last_team_A+1.)
    result.update(share_x=[1., float(special.logit(offense_rate)-special.logit(team_rate)), 0.,
                           float(special.logit(latest)-special.logit(own_share))],
                  share_offset=float(special.logit(fraction)), share_eligible=True, eligible=True)
    return result


class Checker:
    def __init__(self):
        self.start = time.process_time()
        self.wall = time.monotonic()
        self.count = 0
        self.failures = []

    def check(self, passed, message):
        self.count += 1
        if not passed:
            self.failures.append(message)
        if time.process_time()-self.start > 55:
            raise RuntimeError("VERIFIER_CPU_COMPLETION_GUARD_55_OF60")

    def equal(self, left, right, label, tolerance=1e-10):
        if left is None or right is None:
            self.check(left is None and right is None, label)
        else:
            # Frozen JSON encodes raw NaN missing features as explicit null.
            # Match their masks before comparing only finite consumed values.
            a, b = np.asarray(left, dtype=float), np.asarray(right, dtype=float)
            valid = a.shape == b.shape and np.array_equal(np.isnan(a), np.isnan(b))
            valid = valid and not np.isinf(a).any() and not np.isinf(b).any()
            self.check(bool(valid and np.allclose(a[np.isfinite(a)], b[np.isfinite(b)],
                                                  rtol=0., atol=tolerance)), label)


def mutated_context(body, rows, cutoff):
    """Keep identities/order/clocks and every eligible prior denominator fixed.

    Nonadmitted outcome vectors are scaled coherently, including their future
    exposure counts. This preserves nesting/ratio identities; those outcomes
    and denominators are prohibited query information, not legitimate priors.
    """
    changed = copy.deepcopy(body)
    for name in ("team_games", "QB_games"):
        for row in changed[name]:
            if row["available"] >= cutoff:
                row["counts"] = {key: 2*value for key, value in row["counts"].items()}
                for cells in row["cells"].values():
                    for cell in cells:
                        for key in cell:
                            cell[key] *= 2
    context = copy.deepcopy(rows)
    for row in context:
        if row["available"] >= cutoff:
            for name in ("attempts", "completions", "official_attempts", "official_completions"):
                if row.get(name) is not None:
                    row[name] *= 2
            for name in ("context_attempts", "context_completions"):
                row[name] = [2*v for v in row[name]]
    return changed, context


def finite_difference(function, point, step=1e-5):
    result = []
    for i in range(len(point)):
        left, right = point.copy(), point.copy()
        left[i] -= step; right[i] += step
        result.append((function(right)[0]-function(left)[0])/(2*step))
    return np.asarray(result)


def gradient_checks(checker, body, history, cutoff):
    team_x, team_o, team_y, share_d, share_n, share_y = [], [], [], [], [], []
    tm = {(row["game_id"], row["team"]): row for row in body["team_games"]}
    # Fixed earliest32 eligible2025 training records; no optimizer or tuning.
    for row in prior_rows(body["team_games"], cutoff):
        if row["season"] != 2025:
            continue
        d = oi.build_design(history, dict(row, player_id="__TEAM_ONLY__"))
        if d["team_eligible"]:
            team_x.append(d["team_x"]); team_o.append(d["team_offset"]); team_y.append(row["counts"]["opportunities"])
        if len(team_y) == 32:
            break
    for row in prior_rows(body["QB_games"], cutoff):
        if row["season"] != 2025:
            continue
        d = oi.build_design(history, row)
        if d["eligible"]:
            share_d.append(d); share_n.append(tm[row["game_id"], row["team"]]["counts"]["opportunities"])
            share_y.append(row["counts"]["credited_attempts"])
        if len(share_y) == 32:
            break
    x, offset, y = np.asarray(team_x), np.asarray(team_o), np.asarray(team_y)
    sx, so, n, sy = oi.build_share_matrix(share_d, share_n), np.asarray([d["share_offset"] for d in share_d]), np.asarray(share_n), np.asarray(share_y)
    theta = np.array([.01, -.02, .03, oi.INITIAL_ETA+.02])
    beta = np.array([.01, -.02, .03, -.04])
    tf = lambda value: oi.team_objective(value, x, offset, y)
    sf = lambda value: oi.share_objective(value, sx, so, n, sy)
    results = []
    for name, point, function in (("team", theta, tf), ("share", beta, sf)):
        loss, analytic = function(point)
        numerical = finite_difference(function, point)
        error = float(np.max(np.abs(analytic-numerical)))
        checker.check(math.isfinite(loss) and np.isfinite(analytic).all(), name+" finite objective")
        checker.check(bool(np.allclose(analytic, numerical, rtol=2e-5, atol=2e-5)), name+" finite-difference gradient")
        results.append(dict(objective=name, NFL_training_rows=len(y) if name == "team" else len(sy),
                            maximum_absolute_gradient_difference=error, optimizer_calls=0))
    expected_x = np.asarray([d["share_x"] for d in share_d])
    expected_x[:, 2] = np.log(n/np.asarray([d["T_reference"] for d in share_d]))
    checker.equal(sx, expected_x, "historical exposure insertion")
    return results


def prefit(checker):
    rows, history, qb, parents, _ = runner.context()
    body = read(runner.SOURCE)
    queries = [row for row in rows if row["season"] == 2026]
    checker.check(len(queries) == 315 and len(body["QB_games"]) == 2901, "source row domains")
    tm = {(row["game_id"], row["team"]): row for row in body["team_games"]}
    canonical = {(row["game_id"], row["player_id"]): row for row in rows}
    outside = 0
    for row in body["QB_games"]:
        team = tm[row["game_id"], row["team"]]
        checker.check(row["counts"]["credited_attempts"] <= team["counts"]["opportunities"], "A<=T source nesting")
        checker.check(row["available"] == team["available"] and row["kickoff"] == team["kickoff"], "QB/team effective clock")
        c = canonical[row["game_id"], row["player_id"]]
        checker.check(c["official_attempts"] == row["counts"]["credited_attempts"], "qualified official ATT match")
        outside += max(0, row["counts"]["credited_attempts"]-row["counts"]["dropbacks"])
    trace = read(runner.OUT/"QUERY_TRACE_V1.json.gz")["rows"]
    checker.check(len(trace) == 315, "all315 sealed query trace")
    for entry in trace:
        q = entry["query"]
        x = qb.base_history.get(q["player_id"], "QB", "pass_att", q["kickoff"])[0]
        checker.equal(x, entry["direct_features"], "all315 consumed direct feature order")
        for key in ("latest_team_source", "latest_defense_source", "latest_pooled_source", "latest_own_source"):
            clock = entry["design"]["support"].get(key)
            checker.check(clock is None or clock < q["kickoff"], "all315 strict source admission")
    candidates = sorted(queries, key=lambda r: (r["kickoff"], r["game_id"], r["player_id"]))
    chosen = []
    predicates = [lambda r: True,
                  lambda r: not history.rows(r["kickoff"], player=r["player_id"]),
                  lambda r: r["official_attempts"] == 0,
                  lambda r: bool(history.rows(r["kickoff"], player=r["player_id"])) and history.rows(r["kickoff"], player=r["player_id"])[-1]["team"] != r["team"],
                  lambda r: r["week"] == 9]
    for predicate in predicates:
        selected = next((r for r in candidates if predicate(r) and r not in chosen), None)
        if selected is None:
            selected = next(r for r in reversed(candidates) if r not in chosen)
        chosen.append(selected)
    cases = []
    fields = ("team_x", "team_offset", "share_x", "share_offset", "T_reference", "team_eligible", "share_eligible", "eligible")
    for row in chosen:
        q = runner.query(row); d = oi.build_design(history, q); independent = independent_design(body, q)
        for field in fields:
            checker.equal(d[field], independent[field], "independent NFL design "+field)
        altered, altered_rows = mutated_context(body, rows, q["kickoff"])
        for name in ("team_games", "QB_games"):
            oldprior = [r for r in body[name] if r["available"] < q["kickoff"]]
            newprior = [r for r in altered[name] if r["available"] < q["kickoff"]]
            checker.check(digest(oldprior) == digest(newprior), "legitimate prior full rows/denominators fixed")
            checker.check([tuple(r.get(k) for k in IDENTITY) for r in body[name]] == [tuple(r.get(k) for k in IDENTITY) for r in altered[name]], "full history identity/order preserved")
        mh = OpportunityHistory(altered["team_games"], altered["QB_games"])
        md = oi.build_design(mh, dict(q, actual_attempts=99999, official_attempts=99999, opportunities=99999, counts={"opportunities":99999}))
        for field in fields:
            checker.equal(d[field], md[field], "full-context prohibited outcome mutation "+field)
        mq = ctx.ContextHistory(altered_rows, 8, 20.)
        checker.equal(qb.base_history.get(q["player_id"], "QB", "pass_att", q["kickoff"])[0],
                      mq.base_history.get(q["player_id"], "QB", "pass_att", q["kickoff"])[0], "direct consumed transformed history mutation")
        checker.check(d["support"] == md["support"], "full denominator/support trace invariant")
        cases.append(dict(query_sha256=digest(q), week=row["week"], own_prior_games=len(history.rows(q["kickoff"], player=q["player_id"])),
                          eligible=d["eligible"], fallback_reason=d["fallback_reason"], explicit_zero_attempt_fixture=row["official_attempts"] == 0,
                          changed_team_from_latest_prior=bool(history.rows(q["kickoff"], player=q["player_id"])) and history.rows(q["kickoff"], player=q["player_id"])[-1]["team"] != q["team"]))
    q = runner.query(chosen[-1]); edge = max(r["available"] for r in body["team_games"] if r["available"] < q["kickoff"])
    before = history.rows(edge); after = history.rows(np.nextafter(edge, math.inf))
    checker.check(all(r["available"] < edge for r in before), "exact source equality excluded")
    checker.check(len(after)-len(before) == sum(r["available"] == edge for r in body["team_games"]), "next representable cutoff admits boundary rows only")
    bad = copy.deepcopy(body); bad["team_games"][0]["available"] = None
    try:
        OpportunityHistory(bad["team_games"], bad["QB_games"])
        checker.check(False, "explicit unknown source clock rejected")
    except ValueError:
        checker.check(True, "explicit unknown source clock rejected")
    return dict(stage="PREFIT", source_QB_rows=len(body["QB_games"]), source_team_rows=len(body["team_games"]),
                all315_direct_and_source_trace_checked=True, full_context_NFL_fixture_cases=cases,
                prior_denominator_contract="Every eligible prior record/count/cell, identity/order and clock fixed. Only unavailable target/future outcome vectors were coherently scaled; no eligible denominator or teammate universe changed.",
                credited_attempts_outside_dropbacks_preserved=outside,
                objective_gradient_checks=gradient_checks(checker, body, history, min(r["kickoff"] for r in candidates)),
                inference_or_optimizer_calls=0, source_vintage_authenticated=False)


def postfit(checker):
    rows, _, _, parents, _ = runner.context()
    forecasts = [row for path in sorted((runner.OUT/"predictions").glob("2026-*.json.gz")) for row in read(path)["rows"]]
    checker.check(len(forecasts) == 2520, "four arms two targets315 queries")
    lookup = {(row["method"], row["game_id"], row["player_id"], row["target"]):row for row in forecasts}
    checker.check(len(lookup) == len(forecasts), "unique saved forecast identity")
    samples = {}
    for row in forecasts:
        parent = parents[row["game_id"], row["player_id"]]
        p = parent["components"]["integrated_completion_probability"]
        checker.check(row["components"]["conversion_fixed"] == p, "fixed conversion parent binding")
        checker.check(row["components"]["parent_attempt_law"] == parent["components"]["attempt_law"], "parent attempt control binding")
        if row["target"] == "pass_cmp":
            other = lookup[row["method"], row["game_id"], row["player_id"], "pass_att"]
            checker.equal(row["mean"], other["mean"]*p, "CMP mean from same ATT and fixed conversion", 2e-9)
        samples.setdefault((row["week"], row["method"], row["target"]), row)
    restored = []
    for key, row in sorted(samples.items()):
        law = oi.restore_law(row["law"])
        checker.equal(law.mean, row["mean"], "restored exact typed mean", 1e-9)
        checker.check(law.quantile(.5) == row["lower_median"], "restored median")
        ks = [-1, 0, 10, 20, 40, 80, 160]
        cdf = [law.cdf(k) for k in ks]
        checker.check(all(math.isfinite(v) and -1e-12 <= v <= 1+1e-12 for v in cdf), "finite valid CDF")
        checker.check(all(a <= b+1e-12 for a,b in zip(cdf,cdf[1:])), "monotonic CDF")
        # A bounded numerical grid is not a structural maximum. Respect its
        # declared domain and test its explicit out-of-grid exception below.
        mass_limit = min(160, law.grid_max) if isinstance(law, oi.OpportunityMixture) else 160
        mass = [law.pmf(k) for k in range(mass_limit+1)]
        checker.check(all(math.isfinite(v) and v >= 0 for v in mass), "nonnegative integer mass")
        checker.equal(sum(mass), law.cdf(mass_limit), "PMF/CDF finite-region mass", 2e-9)
        at = ctx.exact_probabilities(law, 20.)
        half = ctx.exact_probabilities(law, 20.5)
        checker.equal(sum(at.values()), 1., "integer event/push total", 2e-12)
        checker.equal(at["push"], law.pmf(20), "integer push equality", 1e-10)
        checker.equal(half["push"], 0., "halfpoint no push")
        if isinstance(law, oi.OpportunityMixture):
            checker.check(law.omitted_team_mass <= oi.TAIL_TOL and law.omitted_mean_bound <= oi.MEAN_TAIL_TOL, "frozen integration bounds")
            checker.check(law.joint_pmf(5,6,0) == 0 and law.joint_pmf(5,3,4) == 0, "C<=A<=T invalid support zero")
            checker.check(law.parameters()["renormalized"] is False, "no renormalization")
            if law.team_mean > 0 and law.conversion > 0:
                try:
                    law.pmf(law.grid_max+1)
                    checker.check(False, "positive out-of-grid event has explicit numerical limitation")
                except oi.IntegrationError:
                    checker.check(True, "positive out-of-grid event has explicit numerical limitation")
            else:
                checker.equal(law.pmf(law.grid_max+1), 0., "genuine zero-workload/conversion structural zero")
        restored.append(dict(week=key[0], method=key[1], target=key[2], case_sha256=digest([row[k]for k in IDENTITY]), law_kind=row["law"]["kind"]))
    return dict(stage="POSTFIT", saved_rows_checked=len(forecasts), restored_samples=restored,
                actual_line_grading=False, new_NFL_observations=0, optimizer_calls=0,
                fit_reproduction=False, source_vintage_authenticated=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("prefit", "postfit"))
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    out = args.out or BASE/"independent"/(args.stage.upper()+"_CHECK_V1.json")
    if not out.resolve().is_relative_to(BASE.resolve()) or out.exists():
        raise ValueError("Fresh versioned owned receipt required")
    checker = Checker()
    details = {}
    error = None
    try:
        details = prefit(checker) if args.stage == "prefit" else postfit(checker)
    except Exception as exc:
        error = dict(type=type(exc).__name__, message=str(exc))
        checker.failures.append("Execution exception; no automatic retry or relaxed tolerances")
    receipt = dict(id="B_OPPORTUNITY_"+args.stage.upper()+"_INDEPENDENT_CHECK_v1",
        at_UTC=datetime.now(timezone.utc).isoformat(),
        status="PASS_IN_CHECKED_SCOPE" if not checker.failures else "FAIL_PRESERVED_NO_AUTOMATIC_RETRY",
        checks=checker.count, failures=checker.failures, error=error, details=details,
        bindings={str(path.relative_to(ROOT)):sha(path) for path in
                  (Path(__file__), ROOT/"nfl_v2/opportunity_information.py", Path(runner.INPUT), Path(runner.SOURCE))},
        resources=dict(CPU_seconds=time.process_time()-checker.start, wall_seconds=time.monotonic()-checker.wall,
                       CPU_cap_seconds=60, new_fits=0, new_scoring=0, source_reads=0,
                       peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024),
        scope="Independent direct arithmetic/source admission/mutation and pure likelihood gradients or saved-law checks. No optimizer, protected offer rows, original clocks, grading, model-fit reproduction or website admission.")
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("x") as stream:
        json.dump(receipt, stream, indent=2, allow_nan=False); stream.write("\n")
    print(json.dumps({key:receipt[key]for key in ("status", "checks", "failures", "error", "resources")}))
    raise SystemExit(bool(checker.failures))


if __name__ == "__main__":
    main()
