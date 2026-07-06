"""
Disk persistence for the blockchain using atomic JSON writes.
"""

import json
import os

from .block import Blockchain


def save_chain(blockchain: Blockchain, filepath: str) -> None:
    tmp = filepath + ".tmp"
    with open(tmp, "w") as f:
        json.dump(blockchain.to_dict(), f)
    os.replace(tmp, filepath)   # atomic on POSIX


def load_chain(filepath: str) -> Blockchain | None:
    if not os.path.exists(filepath):
        return None
    try:
        with open(filepath) as f:
            data = json.load(f)
        return Blockchain.from_dict(data)
    except (json.JSONDecodeError, KeyError):
        return None
