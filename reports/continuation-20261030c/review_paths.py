"""Required caller-supplied roots for portable independent review exports."""
import os
from pathlib import Path

def _required(name):
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Set {name} to your approved local evidence root.")
    return Path(value)

def companion_root():
    return _required("NFL_V2_QA_COMPANION_ROOT")

def source_root():
    return _required("NFL_V2_QA_SOURCE_ROOT")
