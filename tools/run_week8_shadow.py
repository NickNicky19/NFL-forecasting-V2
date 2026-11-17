"""One-time capture or offline byte verification; never contacts a data provider."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nfl_v2.week8_shadow import prepare, run


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("operation", choices=["capture", "verify-inputs"])
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--public-root", type=Path, required=True)
    parser.add_argument("--private-root", type=Path, required=True)
    parser.add_argument("--feed", type=Path)
    parser.add_argument("--board", type=Path)
    args = parser.parse_args()
    if args.operation == "capture":
        if args.feed is None or args.board is None:
            parser.error("capture requires --feed and --board")
        # Existing protocol/output paths fail closed. A new run uses its actual
        # inference clock; this command cannot backdate original issuance.
        prepare(args.source_root, args.feed, args.board, args.public_root, args.private_root)
        result = run(args.source_root, args.public_root, args.private_root)
        print(json.dumps(result, indent=2))
        return
    protocol_path = args.public_root/"FROZEN_PROTOCOL.json"
    receipt = json.loads((args.public_root/"CAPTURE_RECEIPT.json").read_text())
    protocol = json.loads(protocol_path.read_text())
    digest = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
    assert digest(protocol_path) == receipt["protocol_sha256"]
    assert digest(args.private_root/"frozen-queries.json") == protocol["query_membership_sha256"]
    for source in protocol["source_ids"]:
        assert digest(args.source_root/source["name"]) == source["sha256"]
    forecast = args.private_root/"shadow-forecasts.json.gz"
    assert digest(forecast) == receipt["private_forecast_sha256"]
    body = gzip.decompress(forecast.read_bytes())
    assert hashlib.sha256(body).hexdigest() == receipt["private_uncompressed_sha256"]
    assert len(json.loads(body)["rows"]) == receipt["forecast_output_rows"]
    if args.feed:
        assert digest(args.feed) == protocol["frozen_feed_sha256"]
    if args.board:
        assert digest(args.board) == protocol["frozen_board_sha256"]
    print("Frozen source/query/forecast bytes verified offline; no inference or acquisition.")


if __name__ == "__main__":
    main()
