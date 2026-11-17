"""One-time immutable Week8 research shadows from admitted public snapshots.

No acquisition, scheduler, production writer or historical-engine modification.
Only original empirical arithmetic helpers are reused from the frozen diagnostic.
"""
from __future__ import annotations

import collections
import csv
import gzip
import hashlib
import io
import json
import re
import resource
import time
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from . import empirical_benchmark as empirical
from .identity import GSIS, unique_gsis_bridge

VERSION = "v2-week8-empirical-history-shadow-v1"
TARGETS = tuple(empirical.MAP) + ("rush_rec_yd", "anytime_td")
ARMS = empirical.ARMS


def now():
    return datetime.now(timezone.utc)


def utc(value):
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("aware clock required")
    return result.astimezone(timezone.utc)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def create_json(path, value):
    with Path(path).open("xb") as handle:
        handle.write(canonical(value))
        handle.flush()
        import os
        os.fsync(handle.fileno())


def schedules(path):
    result = {}
    with Path(path).open() as handle:
        for row in csv.DictReader(handle):
            if row["game_type"] != "REG" or row["season"] not in {str(y) for y in range(2022, 2027)}:
                continue
            if row["season"] == "2026" and int(row["week"]) > 8:
                continue
            if not row["gametime"]:
                raise ValueError("unknown schedule clock")
            kickoff = datetime.fromisoformat(row["gameday"]+"T"+row["gametime"]).replace(tzinfo=ZoneInfo("America/New_York"))
            gid = row["game_id"]
            if gid in result:
                raise ValueError("duplicate schedule game")
            result[gid] = dict(game_id=gid, espn=row["espn"], season=int(row["season"]),
                               week=int(row["week"]), kickoff_utc=kickoff.astimezone(timezone.utc).isoformat(),
                               kickoff=kickoff.timestamp(), home=row["home_team"], away=row["away_team"])
    return result


def prepare(source_root, feed_path, board_path, public_root, private_root):
    """Freeze only identity/query/source metadata before decoding history values."""
    source_root, public_root, private_root = map(Path, (source_root, public_root, private_root))
    public_root.mkdir(parents=True, exist_ok=True)
    private_root.mkdir(parents=True, exist_ok=True)
    games = schedules(source_root/"games.csv")
    by_espn = {g["espn"]: g for g in games.values() if g["season"] == 2026 and g["week"] == 8}
    if len(by_espn) != sum(g["season"] == 2026 and g["week"] == 8 for g in games.values()):
        raise ValueError("ambiguous Week8 ESPN schedule binding")
    feed, board = json.loads(Path(feed_path).read_text()), json.loads(Path(board_path).read_text())
    if (feed["season"], feed["week"], board["season"], board["week"]) != (2026, 8, 2026, 8):
        raise ValueError("wrong query season/week")
    with gzip.open(source_root/"players-week8-identity.csv.gz", "rt") as handle:
        reader = csv.DictReader(handle)
        valid_gsis = {row["gsis_id"] for row in reader if GSIS.fullmatch(row["gsis_id"] or "")}
    with gzip.open(source_root/"roster-week8-identity-2026.csv.gz", "rt") as handle:
        reader = csv.DictReader(handle)
        pairs = [(r["sleeper_id"], r["gsis_id"]) for r in reader
                 if r["season"] == "2026" and int(r["week"]) <= 8
                 and r["sleeper_id"] and r["gsis_id"]]
    bridge = unique_gsis_bridge(pairs, source_id="NFLVERSE_ROSTER_CURRENT_20261029_WEEK8_IDENTITY")
    board_rows = collections.defaultdict(list)
    for row in board["players"]:
        board_rows[(str(row["id"]), str(row["game_id"]))].append(row)
    queries, seen, counts = [], set(), collections.Counter()
    for row in feed["rows"]:
        sid, espn, target = str(row["player_id"]), str(row["game_id"]), row["category"]
        key = (sid, espn, target)
        if key in seen:
            raise ValueError("duplicate frozen query")
        seen.add(key)
        if target not in TARGETS:
            raise ValueError("unregistered feed target")
        game = by_espn.get(espn)
        if not game or utc(row["kickoff_utc"]).timestamp() != game["kickoff"]:
            raise ValueError("feed/schedule identity or kickoff mismatch")
        metadata = board_rows.get((sid, espn), [])
        reason, gsis, position = None, bridge.get(sid), None
        if len(metadata) != 1:
            reason = "MISSING_OR_AMBIGUOUS_FROZEN_BOARD_CONTEXT"
        else:
            b = metadata[0]
            position = b["pos"]
            if position not in {"QB", "RB", "FB", "WR", "TE"}:
                reason = "UNSUPPORTED_POSITION"
            elif (b["team"], b["opp"]) not in ((game["home"], game["away"]), (game["away"], game["home"])):
                reason = "BOARD_TEAM_OPPONENT_MISMATCH"
        if gsis is None:
            reason = reason or "NO_UNIQUE_QUALIFIED_GSIS_BRIDGE"
        elif gsis not in valid_gsis:
            reason = reason or "GSIS_NOT_IN_CURRENT_PLAYER_REGISTRY"
        counts[reason or "IDENTITY_QUERY_ADMITTED"] += 1
        queries.append(dict(query_id=hashlib.sha256(canonical(key)).hexdigest(), sleeper_id=sid,
                            player_id=gsis, position=position, target=target, game_id=game["game_id"],
                            espn_game_id=espn, kickoff_utc=game["kickoff_utc"],
                            owner_input_cutoff_utc=row["source_cutoff_utc"], blocked_reason=reason))
    query_body = canonical(queries)
    with (private_root/"frozen-queries.json").open("xb") as handle:
        handle.write(query_body)
    source_names = [f"stats_player_week_{y}.csv" for y in range(2022, 2027)] + ["games.csv", "players-week8-identity.csv.gz", "roster-week8-identity-2026.csv.gz"]
    protocol = dict(version=VERSION, state="REGISTERED_BEFORE_SHADOW_INFERENCE",
        registered_at_utc=now().isoformat(), query_membership_sha256=hashlib.sha256(query_body).hexdigest(),
        frozen_feed_sha256=sha(feed_path), frozen_board_sha256=sha(board_path),
        source_ids=[dict(name=name, bytes=(source_root/name).stat().st_size, sha256=sha(source_root/name)) for name in source_names],
        code_sha256=sha(__file__), helper_code_sha256=sha(empirical.__file__),
        targets=list(TARGETS), blocked_target="nick-chart-ppr-v1 incomplete rare primitive/zero/attribution contract",
        histories={"H-CURRENT":[2026], "H-RECENT":[2025,2026], "H-MULTI":[2022,2023,2024,2025,2026]},
        products="numeric empirical mean and lower median; anytimeTD Bernoulli empirical mean only",
        fallback="same arm same position empirical summary; then literal0; never used to conceal unknown identity",
        history_cutoff="one actual current origin recorded before numericdecode; kickoff+7days strictly before origin; REG2026W<=7",
        source_tier="current-vintage earlier-season reconstruction and actual current identity/query snapshots",
        feature_memory="no football predictors or old fitted priors; same current query identity/position across arms",
        target_support="explicit finite values only after positive official physical-event proof; blanks never0; signedyards retained",
        eligibility="all1951 original publicfeed rows; no forecast values, odds, injuries or realized target-game labels consumed",
        identity="exact1to1SleeperGSIS roster bridge week<=8; GSISregistryvalid; boardposition/team exact; no namejoins; failuresABSTAIN",
        timing="new researchshadows at actual capture clock, never official sharedcapture; tag afterownerinputdeadline pergame",
        budget=dict(wall_seconds=180, cpu_seconds=180, max_peak_memory_bytes=536870912,
                    max_source_bytes=67108864, max_source_rows=200000, max_query_cells=3000,
                    max_forecast_rows=18000, max_private_output_bytes=8388608, threads=1),
        query_cells=len(queries), identity_counts=dict(counts), new_optimization_fits=0,
        history_positions_by_target={target:sorted({q['position'] for q in queries if q['target'] == target and not q['blocked_reason']}) for target in TARGETS},
        scope="one empirical mechanism/threehistoryregimes; views not independent learners; no claim all complex methods captured")
    create_json(public_root/"FROZEN_PROTOCOL.json", protocol)
    return protocol


def run(source_root, public_root, private_root):
    start, cpu = time.monotonic(), time.process_time()
    source_root, public_root, private_root = map(Path, (source_root, public_root, private_root))
    protocol_path = public_root/"FROZEN_PROTOCOL.json"
    protocol = json.loads(protocol_path.read_text())
    if protocol["version"] != VERSION or protocol["code_sha256"] != sha(__file__) or protocol["helper_code_sha256"] != sha(empirical.__file__):
        raise ValueError("unregistered or changed code")
    query_path = private_root/"frozen-queries.json"
    if sha(query_path) != protocol["query_membership_sha256"]:
        raise ValueError("query membership changed")
    for item in protocol["source_ids"]:
        if sha(source_root/item["name"]) != item["sha256"]:
            raise ValueError("source bytes changed")
    if sum(x["bytes"] for x in protocol["source_ids"]) > protocol["budget"]["max_source_bytes"]:
        raise ValueError("source byte budget")
    origin = now()
    create_json(public_root/"EXECUTION_REGISTRATION.json", dict(version=VERSION, protocol_sha256=sha(protocol_path),
                actual_feature_cutoff_utc=origin.isoformat(), registered_before_numeric_decode=True))
    queries = json.loads(query_path.read_text())
    games = schedules(source_root/"games.csv")
    observations, states, seen = [], collections.Counter(), set()
    needed = set(empirical.MAP.values()) | set(empirical.PHYSICAL_COUNTS) | set(empirical.PHYSICAL_YARDS) | {"rushing_tds", "receiving_tds"}
    for year in range(2022, 2027):
        with (source_root/f"stats_player_week_{year}.csv").open() as handle:
            reader = csv.DictReader(handle)
            if not needed <= set(reader.fieldnames):
                raise ValueError("incomplete statistics schema")
            for row in reader:
                states["source_rows"] += 1
                if states["source_rows"] > protocol["budget"]["max_source_rows"]:
                    raise ValueError("source row budget")
                if row["season_type"] != "REG" or int(row["season"]) != year or (year == 2026 and int(row["week"]) > 7):
                    continue
                game = games.get(row["game_id"])
                if not game or game["season"] != year or game["week"] != int(row["week"]):
                    raise ValueError("history schedule mismatch")
                available = game["kickoff"]+7*86400
                if available >= origin.timestamp():
                    states["unavailable_before_numeric_decode"] += 1
                    continue
                if row["position"] not in {"QB", "RB", "FB", "WR", "TE"} or not GSIS.fullmatch(row["player_id"]):
                    continue
                if (row["team"], row["opponent_team"]) not in ((game["home"], game["away"]), (game["away"], game["home"])):
                    raise ValueError("history team/opponent mismatch")
                identity = (row["game_id"], row["player_id"])
                if identity in seen:
                    raise ValueError("duplicate history identity")
                seen.add(identity)
                values = {k:empirical.numeric(row[k]) for k in needed}
                played = any(empirical.valid_count(values[k]) and values[k] > 0 for k in empirical.PHYSICAL_COUNTS) or any(values[k] is not None and values[k] != 0 for k in empirical.PHYSICAL_YARDS)
                if not played:
                    states["participation_unknown"] += 1
                    continue
                for target in TARGETS:
                    if row["position"] not in protocol["history_positions_by_target"][target]:
                        continue
                    value = empirical.target_value(target, values)
                    if value is not None:
                        observations.append((year, target, row["position"], row["player_id"], available, identity, value))
                states["supported_played_history_rows"] += 1
                if time.monotonic()-start > protocol["budget"]["wall_seconds"]:
                    raise RuntimeError("wall budget")
    indexes = {}
    for arm, years in protocol["histories"].items():
        groups = collections.defaultdict(list)
        for year, target, position, pid, available, identity, value in observations:
            if year in years:
                item = (available, identity, value)
                groups[(target, position, pid)].append(item)
                groups[(target, position, None)].append(item)
        indexes[arm] = {key:empirical.Series(values) for key, values in groups.items()}
    if len(queries) > protocol["budget"]["max_query_cells"]:
        raise ValueError("query budget")
    matrix, rows = collections.Counter(), []
    inference_started = now()
    for query in queries:
        for arm in ARMS:
            own = indexes[arm].get((query["target"], query["position"], query["player_id"]))
            values = own.at(origin.timestamp()) if own else (0,None,None,None)
            own_n, fallback = values[0], "none"
            if not own_n:
                prior = indexes[arm].get((query["target"], query["position"], None))
                values = prior.at(origin.timestamp()) if prior else (0,None,None,None)
                fallback = "position_empirical" if values[0] else "constant_zero"
            products = [("event_probability", values[1])] if query["target"] == "anytime_td" else [("empirical_mean",values[1]), ("lower_median", values[2])]
            for product, value in products:
                issued = now()
                blocked = query["blocked_reason"] or ("GAME_ALREADY_STARTED" if issued >= utc(query["kickoff_utc"]) else None)
                status = "ABSTAIN" if blocked else "ISSUED_SHADOW"
                if values[3] is not None and values[3] >= origin.timestamp():
                    raise AssertionError("training chronology")
                record = dict(query, run_id=VERSION, history_regime=arm, product=product,
                              prediction=None if blocked else value if values[0] else 0.,
                              status=status, abstention_reason=blocked, fallback=None if blocked else fallback,
                              own_n=own_n if not blocked else None, used_n=values[0] if not blocked else None,
                              latest_training_available_utc=datetime.fromtimestamp(values[3],timezone.utc).isoformat() if values[3] is not None and not blocked else None,
                              feature_cutoff_utc=origin.isoformat(), issued_at_utc=issued.isoformat(),
                              actual_horizon_seconds=(utc(query["kickoff_utc"])-issued).total_seconds(),
                              owner_cutoff_status="LATER_THAN_OWNER_INPUT_CUTOFF" if issued > utc(query["owner_input_cutoff_utc"]) else "BEFORE_OWNER_INPUT_CUTOFF",
                              protocol_sha256=sha(protocol_path))
                rows.append(record)
                matrix[(query["target"],arm,product,status,blocked or fallback)] += 1
    inference_completed = now()
    if len(rows) > protocol["budget"]["max_forecast_rows"]:
        raise ValueError("forecast row budget")
    prediction_body = canonical(dict(schema=VERSION, rows=rows))
    compressed = gzip.compress(prediction_body, mtime=0)
    if len(compressed) > protocol["budget"]["max_private_output_bytes"]:
        raise ValueError("output byte budget")
    output = private_root/"shadow-forecasts.json.gz"
    with output.open("xb") as handle:
        handle.write(compressed)
        handle.flush()
        import os
        os.fsync(handle.fileno())
    persistence_completed = now()
    if gzip.decompress(output.read_bytes()) != prediction_body:
        raise ValueError("immutable readback mismatch")
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
    if time.monotonic()-start > protocol["budget"]["wall_seconds"] or time.process_time()-cpu > protocol["budget"]["cpu_seconds"] or rss > protocol["budget"]["max_peak_memory_bytes"]:
        raise RuntimeError("resource budget exceeded; retained output is failed evidence")
    census = [dict(target=k[0],history_regime=k[1],product=k[2],state=k[3],reason_or_fallback=k[4],rows=v) for k,v in sorted(matrix.items())]
    create_json(public_root/"PROCEDURE_MATRIX.json", census)
    issued_rows = [r for r in rows if r["status"] == "ISSUED_SHADOW"]
    receipt = dict(version=VERSION,state="NEW_RESEARCH_SHADOW_CAPTURED_LOCAL_READBACK_PASS_PRIVATE_OFFHOST_UPLOAD_PENDING",
        protocol_sha256=sha(protocol_path),query_membership_sha256=protocol["query_membership_sha256"],
        code_sha256=protocol["code_sha256"],helper_code_sha256=protocol["helper_code_sha256"],
        source_ids=protocol["source_ids"],actual_feature_cutoff_utc=origin.isoformat(),
        actual_inference_started_at=inference_started.isoformat(),actual_inference_completed_at=inference_completed.isoformat(),
        actual_persistence_completed_at=persistence_completed.isoformat(),
        private_forecast_sha256=sha(output),private_forecast_bytes=output.stat().st_size,
        private_uncompressed_sha256=hashlib.sha256(prediction_body).hexdigest(),
        query_cells=len(queries),unique_player_games=len({(q['player_id'] or q['sleeper_id'],q['game_id']) for q in queries}),
        unique_games=len({q['game_id'] for q in queries}),forecast_output_rows=len(rows),issued_shadow_rows=len(issued_rows),
        abstention_rows=len(rows)-len(issued_rows),identity_counts=protocol["identity_counts"],
        owner_cutoff_status=dict(collections.Counter(r["owner_cutoff_status"] for r in issued_rows)),
        all_issued_persisted_before_kickoff=all(persistence_completed < utc(r["kickoff_utc"]) for r in issued_rows),
        minimum_actual_horizon_seconds=min((r['actual_horizon_seconds'] for r in issued_rows),default=None),
        source_row_counts=dict(states),empirical_series_constructed=sum(len(v) for v in indexes.values()),
        new_optimization_fits=0,new_NFL_scores=0,model_families=1,history_regimes=3,
        chart_PPR="BLOCKED_EXACT_RARE_COMPONENTS",complex_original_methods="NOT_CAPTURED_BY_THIS_NEW_CONTROL_ADAPTER",
        official_capture=False,website_published=False,original_forecasts_modified=False,
        resource=dict(cpu_seconds=time.process_time()-cpu,wall_seconds=time.monotonic()-start,peak_rss_bytes=rss,threads=1))
    create_json(public_root/"CAPTURE_RECEIPT.json",receipt)
    return receipt
