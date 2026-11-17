"""Restore only the published UTF-8/CSV or existing forecast bytes in a manifest.

No model loading, source collection, inference, grading or repository writes.
"""
import argparse
import hashlib
import json
from pathlib import Path
import urllib.request

parser = argparse.ArgumentParser()
parser.add_argument("manifest", type=Path)
parser.add_argument("--output", required=True, type=Path)
args = parser.parse_args()
document = json.loads(args.manifest.read_text())
records = document if isinstance(document, list) else document.get(
    "readbacks", document.get("primary_2026_W1_W5_exact_readback", [])
)
if not records:
    raise ValueError("Manifest contains no verified public readback bindings")
restored = 0
for record in records:
    if record.get("readback") not in ("EXACT_GITHUB_PUBLIC_BYTES", "EXACT_PUBLIC_GITHUB_BYTES"):
        continue
    repository = record["repository"]
    commit = record.get("commit", record.get("producer_commit"))
    member = Path(record["path"])
    if member.is_absolute() or ".." in member.parts:
        raise ValueError("Manifest path is not a repository-relative member")
    target = args.output / repository.split("/")[-1] / commit / member
    if target.exists():
        raw = target.read_bytes()
    else:
        url = f"https://raw.githubusercontent.com/{repository}/{commit}/{member.as_posix()}"
        with urllib.request.urlopen(url, timeout=45) as response:
            raw = response.read()
    if len(raw) != record["bytes"] or hashlib.sha256(raw).hexdigest() != record["sha256"]:
        raise ValueError("Immutable public member failed exact readback: " + member.as_posix())
    if not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
    restored += 1
print("Verified", restored, "published members; no inference or scoring")
