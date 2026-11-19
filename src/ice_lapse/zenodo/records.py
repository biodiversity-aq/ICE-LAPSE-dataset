"""Local resume state and published-record manifest, written atomically.

State is keyed by image index; each entry moves through
``creating`` -> ``draft`` -> ``published``. The manifest holds one row per
published deposit with its DOI and file URLs.
"""

from __future__ import annotations

import csv
import json
import os
from pathlib import Path
from typing import Any

from .targets import Target

MANIFEST_FIELDS = [
    "imageIndex", "mediaID", "doi", "recordURL",
    "originalFile", "originalFilePath", "taggedFile", "taggedFilePath",
    "previewFilePath", "rawFilePath", "tagsFilePath", "legendFilePath",
]


def load_state(target: Target) -> dict[str, Any]:
    if not target.state_path.exists():
        return {}
    with target.state_path.open(encoding="utf-8") as source:
        return json.load(source)


def save_state(state: dict[str, Any], target: Target) -> None:
    target.state_path.parent.mkdir(parents=True, exist_ok=True)
    temp = target.state_path.with_suffix(".json.tmp")
    with temp.open("w", encoding="utf-8") as output:
        json.dump(state, output, indent=2)
        output.flush()
        os.fsync(output.fileno())
    os.replace(temp, target.state_path)


def read_manifest(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as source:
        return list(csv.DictReader(source))


def write_manifest(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    with temp.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=MANIFEST_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    os.replace(temp, path)
