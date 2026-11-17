#!/usr/bin/env python3
"""Metadata/forecast-presence census; no outcomes or direction grades."""
import argparse
import collections
import gzip
import hashlib
import json
import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from nfl_v2.prop_evidence_metadata_v2 import object_spans_in_array

TARGETS = ("pass_yd", "pass_td", "pass_cmp", "pass_att", "pass_int", "rush_yd",
           "rush_att", "rec", "rec_yd", "rush_rec_yd")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def main(args):
    receipt = json.loads(args.metadata_receipt.read_text())
    binding = next(r for r in receipt["private_artifacts"] if r["artifact_id"] == "V2-PROP-W7-ALL-ORIGINAL-METADATA-V1")
    if sha(args.metadata_source) != binding["sha256"] or sha(args.original_forward) != receipt["source_gzip_sha256"]:
        raise ValueError("original metadata/source hash changed")
    metadata = json.loads(gzip.decompress(args.metadata_source.read_bytes()))["rows"]
    eligible = {r["source_row_index"]: r for r in metadata
                if r["metadata_panel_status"] != "SERVER_RETENTION_NOT_BEFORE_T90"
                and r["category"] in TARGETS}
    if len(eligible) != 1419:
        raise ValueError("original source scope changed")
    states = collections.Counter()
    per_target = collections.Counter()
    summary = collections.defaultdict(collections.Counter)
    raw = gzip.decompress(args.original_forward.read_bytes()).decode()
    for index, span in enumerate(object_spans_in_array(raw, "rows")):
        row = eligible.get(index)
        if row is None:
            continue
        match = re.search(r'"adjusted_projection"\s*:\s*', span)
        point = json.JSONDecoder().raw_decode(span[match.end():])[0] if match else None
        flags = (finite(row.get("line")), row.get("lean") in ("over", "under"), finite(point))
        source = str(row.get("line_from"))
        states[(source, *flags)] += 1
        per_target[(row["category"], source, *flags)] += 1
        s = summary[source]
        s["source_rows"] += 1
        s["finite_line_rows"] += flags[0]
        s["original_side_present_rows"] += flags[1]
        s["adjusted_point_present_rows"] += flags[2]
        s["finite_line_and_point_rows"] += flags[0] and flags[2]
        s["finite_line_and_saved_side_rows"] += flags[0] and flags[1]
    result = dict(
        state="COMPLETE_METADATA_AND_FORECAST_PRESENCE_CENSUS",
        code_sha256=sha(__file__), metadata_source_sha256=sha(args.metadata_source),
        original_source_sha256=sha(args.original_forward), eligible_original_source_rows=1419,
        games=13, targets=10, adjusted_point_field="adjusted_projection",
        by_line_from=[dict(line_from=k, **dict(v)) for k, v in sorted(summary.items())],
        cross_states=[dict(line_from=k[0], finite_line=k[1], original_side_present=k[2],
                           adjusted_point_present=k[3], n=n) for k, n in sorted(states.items())],
        target_cross_states=[dict(target=k[0], line_from=k[1], finite_line=k[2],
                                  original_side_present=k[3], adjusted_point_present=k[4], n=n)
                             for k, n in sorted(per_target.items())],
        provider_labelled_finite_threshold_rows=sum(n for (s, line, _, _), n in states.items() if s in ("dk", "sleeper") and line),
        site_generated_finite_threshold_rows=sum(n for (s, line, _, _), n in states.items() if s == "ours" and line),
        source_contract="DK-labelled thresholds and Sleeper contest thresholds are preserved source labels, not authenticated quote times, side prices or venue settlement. Ours thresholds are site-generated. None is asserted to be an exhaustive bookmaker offer universe.",
        selected_comparison_scope="285 original saved-side+finite-line rows only; point-derived control on those same285, not all1419feedrows or allprovider-labelledthresholds.",
        target_outcome_values_decoded=0, new_fits=0, new_forecasts=0,
        CURRENT_2026_Week8_outcomes_read=0)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False)+"\n")
    print(json.dumps({k: v for k, v in result.items() if k not in ("cross_states", "target_cross_states")}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("metadata-source", "metadata-receipt", "original-forward", "output"):
        parser.add_argument("--"+name, type=Path, required=True)
    main(parser.parse_args())
