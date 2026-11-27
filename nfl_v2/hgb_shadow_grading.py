"""Offline grading of the original HGB shadow packet; no fitting or inference.

Original HGB objectives remain distinct. Captured model bytes are checked without
unpickling them. Labels use the same explicit qualified contract as other shadows.
"""
from __future__ import annotations

import collections
import gzip
import io
import math
from datetime import datetime, timezone
from pathlib import Path

from .scoring import COUNTS, finite, point_metrics
from .shadow_grading import (ARMS, CONTRACTS, HASH, MAX_COMPRESSED, MAX_FORECASTS,
    MAX_JSON, QUERY_FIELDS, _cohort, _labels, _safe_id, canonical, decode, digest, utc)

VERSION = "v2-hgb-immutable-shadow-grading-v1"
CAPTURE_VERSION = "v2-hgb-direct-history-controls-v1"
BINDING_SCHEMA = "v2-hgb-original-capture-bindings-v1"
PRODUCTS = {"absolute_error_point": "absolute_error_point",
            "squared_error_mean": "squared_error_intended_mean",
            "log_loss_probability": "event_probability"}
MAX_ARTIFACT_BYTES = 128 * 1024 * 1024


def objectives(target):
    return ("log_loss_probability",) if target == "anytime_td" else ("absolute_error_point", "squared_error_mean")


def collect_bindings(metadata_root):
    """Collect ORIGINAL receipts into a hashable manifest, without changing them.

    Its resulting hash must be independently retained/trusted before grading.
    Relative artifact names identify retained bytes, never executable pickles.
    """
    root = Path(metadata_root)
    return dict(schema=BINDING_SCHEMA,
        execution=decode((root / "EXECUTION_REGISTRATION.json").read_bytes()),
        run=decode((root / "RUN_RECEIPT.json").read_bytes()),
        fits=[decode(p.read_bytes()) for p in sorted(root.glob("W08-*-FIT.json"))],
        forecasts=[decode(p.read_bytes()) for p in sorted(root.glob("W08-*-FORECAST.json"))])


def _artifact_names(bindings):
    return [a for fit in bindings["fits"] for a in (fit.get("model"), fit.get("query_features")) if a] + [r["packet"] for r in bindings["forecasts"]]


def load_artifacts(bindings, artifact_root):
    root = Path(artifact_root).resolve()
    result, total = {}, 0
    for descriptor in _artifact_names(bindings):
        name = descriptor["name"]
        path = (root / name).resolve()
        if not path.is_relative_to(root) or Path(name).is_absolute():
            raise ValueError("artifact path escapes supplied private root")
        if name in result:
            continue
        size = path.stat().st_size
        total += size
        if size > MAX_JSON or total > MAX_ARTIFACT_BYTES:
            raise ValueError("retained artifact byte budget exceeded")
        result[name] = path.read_bytes()
    return result


def _unzip(blob, expected, size_limit=MAX_JSON):
    if len(blob) != expected.get("bytes") or digest(blob) != expected.get("sha256"):
        raise ValueError("retained artifact compressed hash/size mismatch")
    with gzip.GzipFile(fileobj=io.BytesIO(blob)) as stream:
        body = stream.read(size_limit + 1)
    if len(body) > size_limit or digest(body) != expected.get("uncompressed_sha256"):
        raise ValueError("retained artifact uncompressed hash/budget mismatch")
    return body


def _capture(blob, receipt, protocol, queries_body, bindings, artifacts, expected_sha, asof):
    if not HASH.fullmatch(expected_sha or "") or digest(blob) != expected_sha:
        raise ValueError("captured HGB forecast hash mismatch")
    if len(blob) > MAX_COMPRESSED:
        raise ValueError("captured packet byte budget exceeded")
    if any(x.get("version") != CAPTURE_VERSION for x in (receipt, protocol, bindings["execution"], bindings["run"])):
        raise ValueError("HGB version binding mismatch")
    body = _unzip(blob, receipt["packet"])
    packet = decode(body)
    if packet.get("schema") != CAPTURE_VERSION or bindings.get("schema") != BINDING_SCHEMA:
        raise ValueError("original HGB schema/bindings required")
    if digest(queries_body) != protocol.get("frozen_queries_sha256"):
        raise ValueError("original frozen query document hash mismatch")
    frozen = decode(queries_body).get("week8")
    if not isinstance(frozen, list) or not frozen or digest(canonical(frozen)) != protocol.get("week8_membership_sha256"):
        raise ValueError("original Week8 query membership mismatch")
    queries = {}
    for q in frozen:
        if (not all(k in q for k in QUERY_FIELDS) or not _safe_id(q.get("query_id"))
                or q["target"] not in CONTRACTS or q["query_id"] in queries):
            raise ValueError("duplicate/unknown frozen query identity")
        queries[q["query_id"]] = {k:q[k] for k in QUERY_FIELDS}
        utc(q["kickoff_utc"]); utc(q["owner_input_cutoff_utc"])
    if len(queries) != receipt.get("queries") or len(queries) != protocol.get("week8_query_cells"):
        raise ValueError("frozen query census mismatch")
    expected = {(q["query_id"], arm, objective) for q in queries.values() for arm in ARMS for objective in objectives(q["target"])}
    slots = {f"W08-{q['target']}-{arm}-{objective}" for q in queries.values() for arm in ARMS for objective in objectives(q["target"])}
    fitmap, forecastmap = {}, {}
    for records, mapping in ((bindings.get("fits", []), fitmap), (bindings.get("forecasts", []), forecastmap)):
        for r in records:
            if r.get("slot") not in slots or r["slot"] in mapping:
                raise ValueError("duplicate/unknown HGB fit or persistence receipt")
            mapping[r["slot"]] = r
        if set(mapping) != slots:
            raise ValueError("incomplete original HGB fit/persistence bindings")
    execution, run = bindings["execution"], bindings["run"]
    cutoff = utc(receipt["cutoff_utc"])
    persisted = utc(receipt["actual_completed_at"])
    registered = utc(protocol["registered_at_utc"])
    if (registered > cutoff or cutoff > utc(execution["actual_started_at"]) or persisted > asof
            or utc(execution["actual_week8_feature_origin_utc"]) != cutoff
            or run.get("code_sha256") != protocol.get("code_sha256")
            or receipt.get("official_capture") is not False or receipt.get("website_published") is not False):
        raise ValueError("invalid HGB registration/source/capture clocks or owner scope")
    if len({q["game_id"] for q in queries.values()}) != receipt.get("unique_games"):
        raise ValueError("game census mismatch")
    total = sum(len(b) for b in artifacts.values())
    if total > MAX_ARTIFACT_BYTES:
        raise ValueError("retained artifact byte budget exceeded")
    for d in _artifact_names(bindings):
        if d.get("name") not in artifacts:
            raise ValueError("original retained model/feature/chunk artifact missing")
        _unzip(artifacts[d["name"]], d)
    chunk_rows = {}
    for slot in slots:
        fit, forecast = fitmap[slot], forecastmap[slot]
        if (fit.get("origin") != 8 or utc(fit["fit_cutoff_utc"]) != cutoff
                or fit.get("history_regime") not in ARMS or fit.get("objective") not in objectives(fit.get("target"))
                or slot != f"W08-{fit['target']}-{fit['history_regime']}-{fit['objective']}"):
            raise ValueError("HGB fit procedure/origin identity mismatch")
        for key in ("latest_training_feature_available", "latest_training_label_available"):
            v = fit.get(key)
            if v is not None and (not finite(v) or v >= cutoff.timestamp()):
                raise ValueError("training availability reaches forecast cutoff")
        seasons = fit.get("training_seasons")
        if not isinstance(seasons, list) or any(y not in protocol["history_regimes"][fit["history_regime"]] for y in seasons):
            raise ValueError("training seasons outside registered history arm")
        if fit.get("state") not in {"FITTED_RETAINED", "NO_FIT_INSUFFICIENT_TRAINING", "NO_FIT_SINGLE_CLASS", "FIT_FAILED_FALLBACK"}:
            raise ValueError("unknown original HGB fit state")
        if fit.get("state") == "FITTED_RETAINED":
            if (not fit.get("model") or not registered <= utc(fit["actual_fit_started_at"]) <= utc(fit["actual_fit_completed_at"]) <= persisted):
                raise ValueError("fitted model missing or invalid fit clocks")
        elif fit.get("model") is not None:
            raise ValueError("fallback state cannot claim retained fitted model")
        chunk = decode(_unzip(artifacts[forecast["packet"]["name"]], forecast["packet"]))
        if chunk.get("schema") != CAPTURE_VERSION or not isinstance(chunk.get("rows"), list):
            raise ValueError("original forecast chunk schema mismatch")
        if len(chunk["rows"]) != forecast.get("rows"):
            raise ValueError("original chunk census mismatch")
        if (sum(r.get("status")=="FORECASTED" for r in chunk["rows"]) != forecast.get("forecasted")
                or sum(r.get("status")=="ABSTAIN" for r in chunk["rows"]) != forecast.get("abstained")):
            raise ValueError("original chunk issuance census mismatch")
        chunk_rows[slot] = chunk["rows"]
    rows = packet.get("rows")
    if not isinstance(rows, list) or not 0 < len(rows) <= MAX_FORECASTS or len(rows) != receipt.get("output_views"):
        raise ValueError("captured HGB row census mismatch")
    matrix, by_slot = set(), collections.defaultdict(list)
    for row in rows:
        qid = row.get("query_id")
        if qid not in queries or any(row.get(k) != queries[qid][k] for k in QUERY_FIELDS):
            raise ValueError("captured row differs from original frozen query")
        key = qid, row.get("history_regime"), row.get("objective")
        if key in matrix or key not in expected:
            raise ValueError("duplicate/unsupported HGB objective/history view")
        matrix.add(key)
        slot = f"W08-{row['target']}-{key[1]}-{key[2]}"
        fit, forecast = fitmap[slot], forecastmap[slot]
        issued, kickoff = utc(row["issued_at_utc"]), utc(row["kickoff_utc"])
        chunk_persisted = utc(forecast["actual_persistence_completed_at"])
        owner_cutoff = utc(row["owner_input_cutoff_utc"])
        owner_status = "LATER_THAN_OWNER_INPUT_CUTOFF" if issued > owner_cutoff else "BEFORE_OWNER_INPUT_CUTOFF"
        if (row.get("actual") is not None or "actual" not in row or row.get("run_id") != CAPTURE_VERSION
                or row.get("fit_slot") != slot or row.get("fit_state") != fit["state"]
                or row.get("season") != 2026 or row.get("week") != 8
                or row.get("population") != "original_pregame_feed"
                or row.get("evidence_tier") != "genuine_new_research_pregame_shadow"
                or not finite(row.get("cutoff")) or row["cutoff"] != cutoff.timestamp()
                or not finite(row.get("kickoff")) or row["kickoff"] != kickoff.timestamp()
                or not cutoff <= issued <= chunk_persisted <= persisted
                or utc(row["actual_generated_at"]) != issued
                or row.get("owner_cutoff_status") != owner_status
                or not finite(row.get("actual_horizon_seconds"))
                or abs(row["actual_horizon_seconds"]-(kickoff-issued).total_seconds()) > .001):
            raise ValueError("invalid HGB row/model/capture/availability identity")
        if fit["state"] == "FITTED_RETAINED" and issued < utc(fit["actual_fit_completed_at"]):
            raise ValueError("forecast predates retained fit")
        for field in ("latest_feature_available", "latest_fallback_available"):
            v = row.get(field)
            if v is not None and (not finite(v) or v >= row["cutoff"]):
                raise ValueError("feature/fallback availability reaches cutoff")
        if row.get("status") == "FORECASTED":
            p = row.get("prediction")
            if (row.get("blocked_reason") is not None or row.get("abstention_reason") is not None
                    or not row.get("player_id") or not finite(p) or persisted >= kickoff
                    or (row["target"] in COUNTS and p < 0)
                    or (row["target"] == "anytime_td" and not 0 <= p <= 1)):
                raise ValueError("invalid issued HGB forecast support/identity/clock")
            if ((fit["state"] == "FITTED_RETAINED" and row.get("fallback") != "none")
                    or (fit["state"] != "FITTED_RETAINED" and row.get("fallback") not in {"own_empirical", "position_empirical", "constant_zero"})):
                raise ValueError("forecast fallback does not match retained fit state")
        elif row.get("status") == "ABSTAIN":
            if row.get("prediction") is not None or not row.get("abstention_reason"):
                raise ValueError("HGB abstention must retain null prediction and reason")
        else:
            raise ValueError("unknown HGB forecast state")
        by_slot[slot].append(row)
    if matrix != expected or any(by_slot[s] != chunk_rows[s] for s in slots):
        raise ValueError("incomplete matrix or combined packet differs from original chunk")
    issued_n = sum(r["status"] == "FORECASTED" for r in rows)
    if issued_n != receipt.get("forecasted") or len(rows)-issued_n != receipt.get("abstained"):
        raise ValueError("captured issuance census mismatch")
    return rows, queries


def grade_bytes(forecasts_gzip, receipt_bytes, protocol_bytes, queries_bytes, bindings_bytes, labels_bytes, *,
                artifacts, expected_forecast_sha256, expected_capture_receipt_sha256,
                expected_protocol_sha256, expected_bindings_sha256, asof_utc, run_id):
    """Grade supplied labels only; original capture and objective are never replaced."""
    if not _safe_id(run_id):
        raise ValueError("public-safe new grading run ID required")
    for body, expected in ((receipt_bytes, expected_capture_receipt_sha256),
                           (protocol_bytes, expected_protocol_sha256), (bindings_bytes, expected_bindings_sha256)):
        if not HASH.fullmatch(expected or "") or digest(body) != expected:
            raise ValueError("trusted receipt/protocol/bindings hash mismatch")
    receipt, protocol, bindings, packet = map(decode, (receipt_bytes, protocol_bytes, bindings_bytes, labels_bytes))
    if any(bindings[k].get("protocol_sha256") != expected_protocol_sha256 for k in ("execution", "run")):
        raise ValueError("original execution/run protocol hash binding mismatch")
    asof = utc(asof_utc)
    if asof > datetime.now(timezone.utc):
        raise ValueError("grading asof cannot be in the future")
    rows, queries = _capture(forecasts_gzip, receipt, protocol, queries_bytes, bindings,
                            artifacts, expected_forecast_sha256, asof)
    labels, sources = _labels(packet, queries, asof)
    states = {}
    for qid, q in queries.items():
        label = labels.get(qid)
        if label is None: state = "pending_no_label"
        elif label["state"] == "canceled" and label["finality"] == "canceled": state = "qualified_final_canceled"
        elif not label["game_completed"] or label["finality"] != "final": state = "pending_or_unverified_finality"
        elif label["state"] == "played" and label["actual"] is not None: state = "qualified_final_played"
        elif label["state"] == "DNP" and q["player_id"]: state = "qualified_final_DNP"
        elif label["state"] in {"played", "played_missing"}: state = "played_missing_target"
        else: state = "unresolved_" + label["state"]
        states[qid] = state
    groups, errors = collections.defaultdict(list), []
    label_sha = digest(labels_bytes)
    for original in rows:
        row = dict(original)
        qid = row["query_id"]; label = labels.get(qid)
        scored = row["status"] == "FORECASTED" and states[qid] == "qualified_final_played"
        row.update(grading_run_id=run_id, outcome_state=states[qid], scored=scored,
            contract_id=CONTRACTS[row["target"]], actual=label.get("actual") if label else None,
            source_id=label.get("source_id") if label else None,
            source_revision_id=label.get("revision_id") if label else None,
            label_available_utc=label.get("available_utc") if label else None,
            signed_error=row["prediction"]-label["actual"] if scored else None,
            absolute_error=abs(row["prediction"]-label["actual"]) if scored else None)
        errors.append(row)
        groups[(row["target"], row["history_regime"], row["objective"])].append(row)
    scores = []
    for (target, arm, objective), view in sorted(groups.items()):
        scored = [r for r in view if r["scored"]]
        metrics = point_metrics([r["prediction"] for r in scored], [r["actual"] for r in scored], target)
        if math.isinf(metrics.get("log_loss", 0)):
            metrics["log_loss"] = "Infinity"
            metrics["infinite_NLL"] = sum((r["prediction"] if r["actual"] else 1-r["prediction"]) == 0 for r in scored)
        coverage_states = dict(collections.Counter("abstention" if r["status"] == "ABSTAIN" else r["outcome_state"] for r in view))
        scores.append(dict(record_id=f"{run_id}:{target}:{arm}:{objective}",
            procedure_id=CAPTURE_VERSION+":"+objective, procedure_family_id="hgb-direct-history-controls",
            target=target, history_regime=arm, objective=objective, product_id=PRODUCTS[objective],
            evaluation_panel_id="immutable-hgb-week8-shadow:"+expected_forecast_sha256[:16]+":"+label_sha[:16],
            population="frozen_owner_feed_queries_conditional_on_qualified_appearance", season=2026, week=8, period="full_game",
            unique_games=len({r["game_id"] for r in scored}), forecast_rows=len(view),
            fallback_rows=sum(r["fallback"] not in (None,"none") for r in view),
            scored_fallback_rows=sum(r["fallback"] not in (None,"none") for r in scored),
            coverage=dict(offered_rows=len(view), scored_rows=len(scored), scored_games=len({r["game_id"] for r in scored}),
                forecast_games=len({r["game_id"] for r in view}),abstention_rows=sum(r["status"]=="ABSTAIN" for r in view),states=coverage_states),
            frozen_prediction_query_cohort_sha256=_cohort([queries[r["query_id"]] for r in view]),
            scored_query_cohort_sha256=_cohort([queries[r["query_id"]] for r in scored]),
            capture_query_membership_sha256=protocol["week8_membership_sha256"],
            capture_forecast_sha256=expected_forecast_sha256,capture_receipt_sha256=expected_capture_receipt_sha256,
            capture_protocol_sha256=expected_protocol_sha256,capture_bindings_sha256=expected_bindings_sha256,
            label_packet_sha256=label_sha,label_version_id=packet["label_version_id"],target_contract_id=CONTRACTS[target],
            label_source_ids=sorted({r["source_id"] for r in scored}),
            label_source_tiers=sorted({sources[r["source_id"]]["source_tier"] for r in scored}),
            actual_capture_feature_cutoff_utc=receipt["cutoff_utc"],
            actual_capture_persistence_completed_utc=receipt["actual_completed_at"],
            actual_capture_first_issued_utc=min(r["issued_at_utc"] for r in view),
            actual_capture_last_issued_utc=max(r["issued_at_utc"] for r in view),
            inference_clock_limit="Original rows record post-prediction issuance, not a separately measured inference-start clock",
            owner_cutoff_status_counts=dict(collections.Counter(r["owner_cutoff_status"] for r in view)),
            source_vintage=protocol.get("availability"),history_policy=protocol.get("history_regimes"),
            feature_memory=protocol.get("feature_memory"),output_contract=protocol.get("output_contract"),
            evidence="SAVED_ROW_FINAL_LABEL_REPLAY",status="SCORED_PARTIAL" if scored else "PENDING_OR_UNRESOLVED_NO_SCORE",
            official_capture=False,website_published=False,
            uncertainty="not_estimated_by_this_grader; paired identical rows and game/week dependence required",
            cohort_limit="Frozen partial research-shadow queries; conditional appearance; no odds, ROI or website-comparison claim",**metrics))
    complete = all(s.startswith("qualified_final_") for s in states.values())
    summary = dict(version=VERSION,run_id=run_id,asof_utc=asof.isoformat(),
        actually_graded_at_utc=datetime.now(timezone.utc).isoformat(),
        capture_forecast_sha256=expected_forecast_sha256,capture_receipt_sha256=expected_capture_receipt_sha256,
        capture_protocol_sha256=expected_protocol_sha256,capture_bindings_sha256=expected_bindings_sha256,
        label_packet_sha256=label_sha,label_version_id=packet["label_version_id"],
        capture_model_artifacts_verified=len({f["model"]["name"] for f in bindings["fits"] if f.get("model")}),
        forecast_rows=len(rows),unique_queries=len(queries),unique_games=len({q["game_id"] for q in queries.values()}),
        scored_forecast_rows=sum(r["scored"] for r in errors),scored_unique_games=len({r["game_id"] for r in errors if r["scored"]}),
        abstention_forecast_rows=sum(r["status"]=="ABSTAIN" for r in rows),query_states=dict(collections.Counter(states.values())),
        whole_week_complete=complete,aggregate_views=len(scores),new_fits=0,new_forecasts=0,
        original_predictions_modified=False,official_capture=False,website_published=False,
        status="ALL_FROZEN_QUERIES_HAVE_QUALIFIED_TERMINAL_LABELS" if complete else "PARTIAL_OR_PENDING_REMAINING_QUERIES_EXPLICIT",
        limits="Supplied finality/source contracts checked, not authenticated by software; no imputation, numeric law or betting result")
    return scores, errors, summary


def grade_files(*, forecasts, capture_receipt, capture_protocol, frozen_queries, capture_bindings,
                artifact_root, labels, public_output, private_output, **kwargs):
    public_output, private_output = Path(public_output), Path(private_output)
    repo = Path(__file__).resolve().parents[1]
    if private_output.resolve().is_relative_to(repo):
        raise ValueError("private errors must remain outside public repository")
    if public_output.exists() or private_output.exists() or public_output.resolve() == private_output.resolve():
        raise ValueError("fresh immutable public/private output directories required")
    paths = list(map(Path,(forecasts,capture_receipt,capture_protocol,frozen_queries,capture_bindings,labels)))
    if any(p.stat().st_size > MAX_JSON for p in paths):
        raise ValueError("input byte budget exceeded")
    bodies = [p.read_bytes() for p in paths]
    artifacts = load_artifacts(decode(bodies[4]), artifact_root)
    scores, errors, summary = grade_bytes(*bodies,artifacts=artifacts,**kwargs)
    public_output.mkdir(parents=True,exist_ok=False);private_output.mkdir(parents=True,exist_ok=False)
    error_body=gzip.compress(canonical(dict(schema=VERSION,rows=errors)),mtime=0)
    error_file=private_output/"player-errors.json.gz";error_file.write_bytes(error_body)
    if error_file.read_bytes()!=error_body:
        raise ValueError("private player-error readback failed")
    summary.update(private_player_errors_sha256=digest(error_body),private_player_errors_bytes=len(error_body),
        private_durability="local_readback_only_until_separate_approved_private_store_receipt")
    score_body=canonical(scores);(public_output/"SCORES.json").write_bytes(score_body)
    summary["public_score_sha256"]=digest(score_body)
    (public_output/"GRADING_RECEIPT.json").write_bytes(canonical(summary))
    return summary
