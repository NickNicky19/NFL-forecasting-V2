"""Grade immutable Week8 research shadows against supplied qualified final labels.

No acquisition, model execution, label inference, overwrite, sportsbook result or
schedule. This module cannot authenticate a provider's claimed finality itself.
"""
from __future__ import annotations

import collections
import gzip
import hashlib
import io
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path

from .scoring import COUNTS, TARGETS, finite, point_metrics, valid_actual

VERSION = "v2-week8-immutable-shadow-grading-v1"
CAPTURE_VERSION = "v2-week8-empirical-history-shadow-v2"
LABEL_SCHEMA = "v2-qualified-shadow-labels-v1"
ARMS = {"H-CURRENT", "H-RECENT", "H-MULTI"}
CONTRACTS = {t: "nfl-official-full-game-"+t+"-v1" for t in TARGETS if t != "nick-chart-ppr-v1"}
CONTRACTS["anytime_td"] = "nfl-full-game-rushing-or-receiving-at-least-one-td-v1"
QUERY_FIELDS = ("query_id", "sleeper_id", "player_id", "position", "target", "game_id",
                "espn_game_id", "kickoff_utc", "owner_input_cutoff_utc", "blocked_reason")
STATES = {"played", "DNP", "unknown", "missing", "played_missing", "pending", "canceled"}
SOURCE_TIERS = {"authentic_final_snapshot", "qualified_asof_reconstruction", "current_vintage_final_snapshot"}
MAX_COMPRESSED = 8 * 1024 * 1024
MAX_JSON = 64 * 1024 * 1024
MAX_FORECASTS = 18000
ID = re.compile(r"[A-Za-z0-9._:-]{1,160}\Z")
HASH = re.compile(r"[0-9a-f]{64}\Z")


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def digest(body):
    return hashlib.sha256(body).hexdigest()


def utc(value):
    if not isinstance(value, str) or not value:
        raise ValueError("explicit aware clock required")
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError("timezone-aware clock required")
    return result.astimezone(timezone.utc)


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON object key")
        result[key] = value
    return result


def decode(body):
    if len(body) > MAX_JSON:
        raise ValueError("JSON byte budget exceeded")
    def invalid(_):
        raise ValueError("nonfinite JSON constant")
    return json.loads(body, object_pairs_hook=_unique, parse_constant=invalid)


def _safe_id(value):
    return isinstance(value, str) and ID.fullmatch(value) is not None and "://" not in value


def _cohort(queries):
    """Identity-only cohort hash: independent of history, output view and outcome."""
    rows = [{k:q[k] for k in ("query_id", "player_id", "game_id", "target")} for q in queries]
    return digest(canonical(sorted(rows, key=lambda q:q["query_id"])))


def _capture(blob, receipt, protocol, expected_sha, asof):
    if not HASH.fullmatch(expected_sha or "") or digest(blob) != expected_sha or receipt.get("private_forecast_sha256") != expected_sha:
        raise ValueError("captured forecast hash mismatch")
    if len(blob) > MAX_COMPRESSED:
        raise ValueError("compressed forecast budget exceeded")
    with gzip.GzipFile(fileobj=io.BytesIO(blob)) as stream:
        body = stream.read(MAX_JSON+1)
    if digest(body) != receipt.get("private_uncompressed_sha256"):
        raise ValueError("uncompressed captured body hash mismatch")
    packet = decode(body)
    if packet.get("schema") != CAPTURE_VERSION or receipt.get("version") != CAPTURE_VERSION or protocol.get("version") != CAPTURE_VERSION:
        raise ValueError("unsupported capture version")
    rows = packet.get("rows")
    if not isinstance(rows, list) or not 0 < len(rows) <= MAX_FORECASTS or len(rows) != receipt.get("forecast_output_rows"):
        raise ValueError("captured row census mismatch")
    persisted = utc(receipt["actual_persistence_completed_at"])
    if persisted > asof:
        raise ValueError("capture persistence is after grading asof")
    queries, matrix = {}, set()
    for row in rows:
        if not all(k in row for k in QUERY_FIELDS):
            raise ValueError("incomplete captured query identity")
        query = {k:row[k] for k in QUERY_FIELDS}
        qid, target = query["query_id"], query["target"]
        if not _safe_id(qid) or target not in CONTRACTS:
            raise ValueError("unknown captured query/target contract")
        if qid in queries and queries[qid] != query:
            raise ValueError("conflicting captured query context")
        queries.setdefault(qid, query)
        product = row.get("product")
        products = {"event_probability"} if target == "anytime_td" else {"empirical_mean", "lower_median"}
        key = qid, row.get("history_regime"), product
        if key in matrix or key[1] not in ARMS or product not in products:
            raise ValueError("duplicate or incompatible captured procedure view")
        matrix.add(key)
        kickoff, issued, cutoff = utc(query["kickoff_utc"]), utc(row["issued_at_utc"]), utc(row["feature_cutoff_utc"])
        if cutoff > issued or issued > persisted or row.get("protocol_sha256") != receipt["protocol_sha256"]:
            raise ValueError("captured source/issuance/persistence identity invalid")
        if row.get("status") == "ISSUED_SHADOW":
            prediction = row.get("prediction")
            if (query["blocked_reason"] is not None or row.get("abstention_reason") is not None
                    or not finite(prediction) or issued >= kickoff or persisted >= kickoff
                    or (target in COUNTS and prediction < 0)
                    or (target == "anytime_td" and not 0 <= prediction <= 1)):
                raise ValueError("invalid issued forecast support/clock")
        elif row.get("status") == "ABSTAIN":
            if row.get("prediction") is not None or not row.get("abstention_reason"):
                raise ValueError("abstention cannot contain a replacement prediction")
        else:
            raise ValueError("unknown captured forecast state")
    if len(queries) != receipt.get("query_cells"):
        raise ValueError("capture query census mismatch")
    query_body = canonical(list(queries.values()))
    if digest(query_body) != receipt.get("query_membership_sha256") or digest(query_body) != protocol.get("query_membership_sha256"):
        raise ValueError("frozen query cohort hash mismatch")
    expected = {(q["query_id"], arm, product) for q in queries.values() for arm in ARMS
                for product in (("event_probability",) if q["target"] == "anytime_td" else ("empirical_mean", "lower_median"))}
    if matrix != expected:
        raise ValueError("incomplete captured procedure matrix")
    return rows, queries


def _labels(packet, queries, asof):
    if packet.get("schema") != LABEL_SCHEMA or not _safe_id(packet.get("label_version_id")):
        raise ValueError("qualified versioned label packet required")
    sources = {}
    for source in packet.get("source_admissions", []):
        sid = source.get("source_id")
        if not _safe_id(sid) or sid in sources or source.get("source_tier") not in SOURCE_TIERS:
            raise ValueError("invalid/duplicate source admission")
        for field in ("identity_contract_id", "statistic_contract_id", "participation_contract_id", "finality_contract_id", "availability_basis_id"):
            if not _safe_id(source.get(field)):
                raise ValueError("explicit public-safe source contracts required")
        sources[sid] = source
    rows = packet.get("labels")
    if not isinstance(rows, list) or len(rows) > len(queries):
        raise ValueError("label census exceeds frozen queries")
    result = {}
    for label in rows:
        qid = label.get("query_id")
        if qid not in queries or qid in result:
            raise ValueError("duplicate/wrong frozen label query identity")
        query = queries[qid]
        if any(label.get(k) != query[k] for k in ("player_id", "game_id", "target")):
            raise ValueError("label player/game/target identity mismatch")
        if label.get("contract_id") != CONTRACTS[query["target"]]:
            raise ValueError("target/scoring contract mismatch")
        if label.get("source_id") not in sources:
            raise ValueError("label source not admitted")
        if label.get("state") not in STATES or type(label.get("game_completed")) is not bool:
            raise ValueError("explicit participation/completion states required")
        if "actual" not in label:
            raise ValueError("explicit actual or null required; missing never zero")
        if label.get("finality") not in {"final", "pending", "unverified", "canceled"}:
            raise ValueError("explicit finality state required")
        kickoff = utc(query["kickoff_utc"])
        available, observed = utc(label.get("available_utc")), utc(label.get("observed_utc"))
        canceled = label["state"] == "canceled" and label["finality"] == "canceled"
        if (label["state"] == "canceled" or label["finality"] == "canceled") and not canceled:
            raise ValueError("cancellation state/finality must agree")
        # A qualified official cancellation can be published before kickoff;
        # it resolves game status without fabricating a numeric outcome.
        if not available <= observed <= asof or (not canceled and available <= kickoff):
            raise ValueError("future/unknown/pre-kickoff label availability")
        value = label.get("actual")
        if canceled and value is not None:
            raise ValueError("cancellation cannot contain numeric outcome")
        if value is not None:
            if (label["state"] != "played" or label["game_completed"] is not True or label["finality"] != "final"
                    or not isinstance(query["player_id"], str) or not query["player_id"]
                    or not valid_actual(query["target"], value)):
                raise ValueError("numeric label requires final completed played support")
        if label.get("revision_id") is not None and not _safe_id(label["revision_id"]):
            raise ValueError("public-safe revision ID or explicit null required")
        result[qid] = label
    return result, sources


def grade_bytes(forecasts_gzip, receipt_bytes, protocol_bytes, labels_bytes, *,
                expected_forecast_sha256, expected_capture_receipt_sha256, asof_utc, run_id):
    """Return aggregates and private errors; do not execute against actual labels on import."""
    if not _safe_id(run_id) or not HASH.fullmatch(expected_capture_receipt_sha256 or ""):
        raise ValueError("new grading run and trusted capture receipt hash required")
    if digest(receipt_bytes) != expected_capture_receipt_sha256:
        raise ValueError("capture receipt hash mismatch")
    receipt, protocol, packet = decode(receipt_bytes), decode(protocol_bytes), decode(labels_bytes)
    if digest(protocol_bytes) != receipt.get("protocol_sha256"):
        raise ValueError("frozen capture protocol hash mismatch")
    asof = utc(asof_utc)
    if asof > datetime.now(timezone.utc):
        raise ValueError("grading asof cannot be in the future")
    rows, queries = _capture(forecasts_gzip, receipt, protocol, expected_forecast_sha256, asof)
    labels, sources = _labels(packet, queries, asof)
    label_sha = digest(labels_bytes)
    groups, errors = collections.defaultdict(list), []
    query_states = {}
    for qid, query in queries.items():
        label = labels.get(qid)
        if label is None:
            state = "pending_no_label"
        elif label["state"] == "canceled" and label["finality"] == "canceled":
            state = "qualified_final_canceled"
        elif not label["game_completed"] or label["finality"] not in {"final", "canceled"}:
            state = "pending_or_unverified_finality"
        elif label["state"] == "played" and label["actual"] is not None:
            state = "qualified_final_played"
        elif label["state"] == "DNP" and query["player_id"]:
            state = "qualified_final_"+label["state"]
        elif label["state"] in {"played", "played_missing"}:
            state = "played_missing_target"
        else:
            state = "unresolved_"+label["state"]
        query_states[qid] = state
    for row in rows:
        qid = row["query_id"]
        label = labels.get(qid)
        scored = row["status"] == "ISSUED_SHADOW" and query_states[qid] == "qualified_final_played"
        error = {k:row.get(k) for k in (*QUERY_FIELDS, "history_regime", "product", "prediction", "status", "abstention_reason", "fallback", "owner_cutoff_status", "feature_cutoff_utc", "issued_at_utc", "actual_horizon_seconds", "run_id", "protocol_sha256")}
        error.update(grading_run_id=run_id, contract_id=CONTRACTS[row["target"]],
                     outcome_state=query_states[qid], scored=scored, actual=label.get("actual") if label else None,
                     source_id=label.get("source_id") if label else None,
                     source_revision_id=label.get("revision_id") if label else None,
                     label_available_utc=label.get("available_utc") if label else None,
                     signed_error=row["prediction"]-label["actual"] if scored else None,
                     absolute_error=abs(row["prediction"]-label["actual"]) if scored else None)
        errors.append(error)
        groups[(row["target"], row["history_regime"], row["product"])].append(error)
    scores = []
    for (target, arm, product), view in sorted(groups.items()):
        scored = [r for r in view if r["scored"]]
        metrics = point_metrics([r["prediction"] for r in scored], [r["actual"] for r in scored], target)
        if math.isinf(metrics.get("log_loss", 0)):
            metrics["log_loss"] = "Infinity"
            metrics["infinite_NLL"] = sum((r["prediction"] if r["actual"] else 1-r["prediction"]) == 0 for r in scored)
        forecast_queries = [queries[r["query_id"]] for r in view]
        scored_queries = [queries[r["query_id"]] for r in scored]
        fallback_n = sum(r["fallback"] not in (None, "none") for r in view)
        states = dict(collections.Counter("abstention" if r["status"] == "ABSTAIN" else r["outcome_state"] for r in view))
        scores.append(dict(record_id=run_id+":"+target+":"+arm+":"+product,
            procedure_id=CAPTURE_VERSION, procedure_family_id="empirical-player-history-control",
            target=target, history_regime=arm, product_id=product,
            evaluation_panel_id="immutable-week8-shadow:"+expected_forecast_sha256[:16]+":"+label_sha[:16],
            population="frozen_owner_feed_queries_conditional_on_qualified_appearance", season=2026, week=8, period="full_game",
            unique_games=len({r["game_id"] for r in scored}), forecast_rows=len(view),
            fallback_rows=fallback_n, scored_fallback_rows=sum(r["fallback"] not in (None,"none") for r in scored),
            coverage=dict(scored_rows=len(scored),offered_rows=len(view),scored_games=len({r["game_id"] for r in scored}),
                          forecast_games=len({r["game_id"] for r in view}),abstention_rows=sum(r["status"] == "ABSTAIN" for r in view),states=states),
            frozen_prediction_query_cohort_sha256=_cohort(forecast_queries), scored_query_cohort_sha256=_cohort(scored_queries),
            capture_query_membership_sha256=receipt["query_membership_sha256"],
            capture_forecast_sha256=expected_forecast_sha256, capture_protocol_sha256=receipt["protocol_sha256"],
            capture_receipt_sha256=expected_capture_receipt_sha256, label_packet_sha256=label_sha,
            label_version_id=packet["label_version_id"], target_contract_id=CONTRACTS[target],
            label_source_ids=sorted({r["source_id"] for r in scored}),
            label_source_tiers=sorted({sources[r["source_id"]]["source_tier"] for r in scored}),
            actual_capture_feature_cutoff_utc=receipt.get("actual_feature_cutoff_utc"),
            actual_capture_inference_started_utc=receipt.get("actual_inference_started_at"),
            actual_capture_inference_completed_utc=receipt.get("actual_inference_completed_at"),
            actual_capture_persistence_completed_utc=receipt["actual_persistence_completed_at"],
            source_vintage=protocol.get("source_tier"), history_policy=protocol.get("histories"),
            feature_memory=protocol.get("feature_memory"), evidence="SAVED_ROW_FINAL_LABEL_REPLAY",
            status="SCORED_PARTIAL" if scored else "PENDING_OR_UNRESOLVED_NO_SCORE",
            cohort_limit="Frozen partial issued/abstained research-shadow population; conditional appearance; no odds, ROI or full website comparison",
            uncertainty="not_estimated_by_this_grader; use paired identical scored cohort and game/week dependence",
            **metrics))
    complete = all(s.startswith("qualified_final_") for s in query_states.values())
    summary = dict(version=VERSION, run_id=run_id, asof_utc=asof.isoformat(),
        actually_graded_at_utc=datetime.now(timezone.utc).isoformat(),
        capture_forecast_sha256=expected_forecast_sha256, capture_receipt_sha256=expected_capture_receipt_sha256,
        capture_protocol_sha256=receipt["protocol_sha256"], label_packet_sha256=label_sha,
        source_admission_ids=sorted(sources), forecast_rows=len(rows), unique_queries=len(queries),
        unique_games=len({q["game_id"] for q in queries.values()}), scored_forecast_rows=sum(r["scored"] for r in errors),
        unique_player_games=len({(q["player_id"] or q["sleeper_id"],q["game_id"]) for q in queries.values()}),
        scored_unique_games=len({r["game_id"] for r in errors if r["scored"]}),
        scored_unique_player_games=len({(r["player_id"],r["game_id"]) for r in errors if r["scored"]}),
        abstention_forecast_rows=sum(r["status"] == "ABSTAIN" for r in rows),
        query_states=dict(collections.Counter(query_states.values())), whole_week_complete=complete,
        status="ALL_FROZEN_QUERIES_HAVE_QUALIFIED_TERMINAL_LABELS" if complete else "PARTIAL_OR_PENDING_REMAINING_QUERIES_EXPLICIT",
        aggregate_views=len(scores), new_fits=0, new_forecasts=0, original_predictions_modified=False,
        contracts=CONTRACTS, capture_source_ids=receipt.get("source_ids"),
        limits="Supplied finality/source contracts are checked, not independently authenticated by software; no silent zero or DNP inference")
    return scores, errors, summary


def grade_files(*, forecasts, capture_receipt, capture_protocol, labels, expected_forecast_sha256,
                expected_capture_receipt_sha256, asof_utc, run_id, public_output, private_output):
    public_output, private_output = Path(public_output), Path(private_output)
    repo = Path(__file__).resolve().parents[1]
    if private_output.resolve().is_relative_to(repo):
        raise ValueError("private player errors must remain outside the public repository")
    if public_output.exists() or private_output.exists() or public_output.resolve() == private_output.resolve():
        raise ValueError("new immutable output directories required")
    paths = [Path(p) for p in (forecasts,capture_receipt,capture_protocol,labels)]
    if any(p.stat().st_size > MAX_JSON for p in paths):
        raise ValueError("input byte bound exceeded")
    scores, errors, summary = grade_bytes(*(p.read_bytes() for p in paths),
        expected_forecast_sha256=expected_forecast_sha256,
        expected_capture_receipt_sha256=expected_capture_receipt_sha256,
        asof_utc=asof_utc,run_id=run_id)
    public_output.mkdir(parents=True,exist_ok=False)
    private_output.mkdir(parents=True,exist_ok=False)
    error_body = gzip.compress(canonical(dict(schema=VERSION,rows=errors)),mtime=0)
    (private_output/"player-errors.json.gz").write_bytes(error_body)
    if gzip.decompress((private_output/"player-errors.json.gz").read_bytes()) != canonical(dict(schema=VERSION,rows=errors)):
        raise ValueError("private error readback failed")
    summary["private_player_errors_sha256"] = digest(error_body)
    summary["private_player_errors_bytes"] = len(error_body)
    summary["private_durability"] = "local_readback_only_until_separate_approved_private_store_receipt"
    score_body = canonical(scores)
    (public_output/"SCORES.json").write_bytes(score_body)
    summary["public_score_sha256"] = digest(score_body)
    (public_output/"GRADING_RECEIPT.json").write_bytes(canonical(summary))
    return summary
