"""Independent standard-library replay; no imports from V2's primary scorer.

Inputs are local approved evidence supplied by the executor. Outputs contain
aggregates and opaque worked-example IDs, never raw source/player records.
"""
from __future__ import annotations

import argparse
import base64
from collections import Counter, defaultdict
from datetime import datetime
from decimal import Decimal, localcontext
import gzip
import hashlib
import json
from pathlib import Path


def number(value):
    if isinstance(value, bool):
        raise ValueError("boolean_number")
    x = Decimal(str(value))
    if not x.is_finite():
        raise ValueError("nonfinite_number")
    return x


def primary(target, position):
    if target.startswith("pass_"):
        return position == "QB"
    if target in {"rush_yd", "rush_att"}:
        return position == "RB"
    return position in {"RB", "WR", "TE"}


def stamp(x):
    return datetime.fromisoformat(x.replace("Z", "+00:00"))


def replay(forecast_file, outcome_file):
    forecasts = json.loads(gzip.decompress(forecast_file.read_bytes()))["rows"]
    wrappers = json.loads(outcome_file.read_text())
    outcomes = [json.loads(gzip.decompress(base64.b64decode(w["content"])))
                for w in wrappers if not w["error"]]
    identity = lambda x: (x["game_id"], x["player_id"], x["target"])
    oc = Counter(identity(x) for x in outcomes)
    fc = Counter((x["model_id"], *identity(x)) for x in forecasts)
    assert max(oc.values()) == 1 and max(fc.values()) == 1
    assert all(stamp(x["feature_cutoff_utc"]) <= stamp(x["issued_at"])
               < stamp(x["kickoff_utc"]) for x in forecasts)
    source = {identity(x): x for x in outcomes}
    records = defaultdict(dict)
    sums = defaultdict(list)
    for f in forecasts:
        o = source.get(identity(f))
        if o is None or o["actual"] is None or o["participation_state"] != "played":
            continue
        if not primary(f["target"], f["position"]):
            continue
        p, y = number(f["mean"]), number(o["actual"])
        if f["target"] == "anytime_td":
            assert 0 <= p <= 1 and y in {0, 1}
        err = p - y
        loss = err * err if f["target"] == "anytime_td" else abs(err)
        sums[(f["target"], f["model_id"])].append((loss, err, err * err))
        records[identity(f)][f["model_id"]] = (loss, err, err * err)
    result = {"input_hashes": {
        "forecast_gzip_sha256": hashlib.sha256(forecast_file.read_bytes()).hexdigest(),
        "outcome_wrapper_sha256": hashlib.sha256(outcome_file.read_bytes()).hexdigest(),
    }, "checks": {
        "forecast_rows": len(forecasts), "forecast_games": len({x["game_id"] for x in forecasts}),
        "forecast_players": len({x["player_id"] for x in forecasts}),
        "label_rows": len(outcomes), "label_games": len({x["game_id"] for x in outcomes}),
        "supported_labels_all_positions": sum(x["actual"] is not None for x in outcomes),
        "duplicate_forecast_keys": 0, "duplicate_label_keys": 0,
        "internal_chronology_violations": 0,
    }, "summaries": [], "paired": [], "other_method_pairs": [], "worked_redacted_examples": []}
    for (target, model), values in sorted(sums.items()):
        n = Decimal(len(values))
        result["summaries"].append({"target": target, "model": model, "n": len(values),
            "primary": str(sum(x[0] for x in values) / n),
            "mae": str(sum(abs(x[1]) for x in values) / n),
            "mse": str(sum(x[2] for x in values) / n),
            "bias": str(sum(x[1] for x in values) / n)})
    differences = defaultdict(list)
    for key, pair in sorted(records.items()):
        if "lab-v1.1-recent" not in pair or "lab-v1.1-pooled" not in pair:
            continue
        delta = pair["lab-v1.1-recent"][0] - pair["lab-v1.1-pooled"][0]
        differences[key[2]].append(delta)
        kind = "recent_win" if delta < 0 else "recent_loss" if delta > 0 else "tie"
        if kind != "tie" and not any(x["kind"] == kind for x in result["worked_redacted_examples"]):
            result["worked_redacted_examples"].append({
                "opaque_id": hashlib.sha256(repr(key).encode()).hexdigest()[:16],
                "target": key[2], "kind": kind,
                "recent_loss": str(pair["lab-v1.1-recent"][0]),
                "pooled_loss": str(pair["lab-v1.1-pooled"][0]),
                "difference": str(delta),
            })
    for target, ds in sorted(differences.items()):
        result["paired"].append({"target": target, "n": len(ds),
            "recent_minus_pooled": str(sum(ds)/Decimal(len(ds))),
            "recent_wins": sum(x < 0 for x in ds), "recent_losses": sum(x > 0 for x in ds),
            "ties": sum(x == 0 for x in ds)})
    other_differences = defaultdict(list)
    for key, pair in sorted(records.items()):
        if "lab-v1.1-recent" not in pair:
            continue
        baseline = pair["lab-v1.1-recent"][0]
        for model, fields in sorted(pair.items()):
            if model in {"lab-v1.1-recent", "lab-v1.1-pooled"}:
                continue
            delta = fields[0] - baseline
            other_differences[(key[2], model)].append(delta)
            kind = "challenger_win" if delta < 0 else "challenger_loss" if delta > 0 else "tie"
            if kind != "tie" and not any(x["kind"] == kind for x in result["worked_redacted_examples"]):
                result["worked_redacted_examples"].append({
                    "opaque_id": hashlib.sha256(repr((model, key)).encode()).hexdigest()[:16],
                    "target": key[2], "model": model, "kind": kind,
                    "challenger_loss": str(fields[0]), "recent_loss": str(baseline),
                    "difference": str(delta),
                })
    for (target, model), ds in sorted(other_differences.items()):
        result["other_method_pairs"].append({"target": target, "model": model, "n": len(ds),
            "model_minus_recent": str(sum(ds)/Decimal(len(ds))),
            "wins": sum(x < 0 for x in ds), "losses": sum(x > 0 for x in ds),
            "ties": sum(x == 0 for x in ds)})
    return result


def settlement_math():
    # One coherent discrete law. A half-integer has no push; integer retains mass.
    mass = {0: Decimal("0.5"), 1: Decimal("0.3"), 2: Decimal("0.2")}
    results = []
    for line in [Decimal("0.5"), Decimal(1)]:
        over = sum(p for y, p in mass.items() if y > line)
        under = sum(p for y, p in mass.items() if y < line)
        push = sum(p for y, p in mass.items() if y == line)
        assert over + under + push == 1
        results.append({"line": str(line), "over": str(over), "under": str(under), "push": str(push)})
    # Mirror both probability and outcome; binary Brier/log scores agree exactly
    # in algebra. Decimal verifies Brier to the active 50-digit context.
    p = Decimal("0.7")
    for y in [0, 1]:
        assert (p-y)**2 == ((1-p)-(1-y))**2
    # Refund-on-push: positive EV here even with only 20% unconditional win mass.
    ev = Decimal("0.2") * (Decimal(4)-1) - Decimal("0.5")
    assert ev == Decimal("0.1")
    # Converting to decisive-event conditioning requires multiplying by decisive mass.
    conditional_ev = (Decimal("0.2")/Decimal("0.7"))*4-1
    assert abs(conditional_ev*Decimal("0.7")-ev) < Decimal("1e-48")
    return {"coherent_law": results, "mirrored_binary_brier": "PASS",
            "refund_on_push_example_ev": str(ev), "decisive_mass": "0.7"}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("forecast", type=Path)
    ap.add_argument("outcomes", type=Path)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    with localcontext() as ctx:
        ctx.prec = 50
        result = replay(args.forecast, args.outcomes)
        result["settlement_math"] = settlement_math()
    args.output.write_text(json.dumps(result, indent=2)+"\n")
    print(json.dumps({"summaries": len(result["summaries"]), "paired": len(result["paired"]),
                      "checks": result["checks"]}, indent=2))
