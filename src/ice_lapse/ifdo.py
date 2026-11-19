"""Read the ICE-LAPSE iFDO metadata file (https://www.marine-imaging.com/fair/)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterator

import pandas as pd
import yaml

from .paths import IFDO_PATH


class IFDOSafeLoader(yaml.SafeLoader):
    """Safe YAML loader that tolerates the ``!!python/name:builtins.id`` tag.

    The tag appears in the iFDO file's YAML anchors. Instead of resolving it to
    a Python object, it is read as the plain string ``"id"``.
    """


IFDOSafeLoader.add_constructor(
    "tag:yaml.org,2002:python/name:builtins.id",
    lambda loader, node: "id",
)


def load_ifdo_metadata(path: str | Path = IFDO_PATH) -> dict[str, Any]:
    """Parse an iFDO YAML file (defaults to the ICE-LAPSE deployment)."""
    with open(path, encoding="utf-8") as source:
        return yaml.load(source, Loader=IFDOSafeLoader)


def image_set_header(metadata: dict[str, Any]) -> dict[str, Any]:
    return metadata.get("image-set-header") or {}


def iter_image_entries(metadata: dict[str, Any]) -> Iterator[tuple[str, dict[str, Any]]]:
    """Yield ``(media_id, entry)`` for every image entry in ``image-set-items``.

    ``media_id`` is the item key (the iFDO image filename).
    """
    for media_id, entries in (metadata.get("image-set-items") or {}).items():
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if isinstance(entry, dict):
                yield media_id, entry


def to_utc_iso(timestamp: pd.Timestamp) -> str:
    """Format a UTC timestamp as ISO 8601 with a ``Z`` suffix."""
    return timestamp.isoformat().replace("+00:00", "Z")
