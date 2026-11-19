"""Camtrap-DP ``deployments`` table from the iFDO header and image entries."""

from __future__ import annotations

import json
from typing import Any, Iterable

import pandas as pd

from ..ifdo import image_set_header, iter_image_entries, to_utc_iso

LOCATION_NAME = "Tethys bay - Mario Zucchelli Station- 2015"
CAMERA_MODEL = "Canon EOS 600D"

COLUMNS = [
    "deploymentID",
    "locationName",
    "latitude",
    "longitude",
    "deploymentStart",
    "deploymentEnd",
    "setupBy",
    "cameraModel",
    "cameraHeight",
    "cameraDepth",
    "cameraID",
    "habitat",
    "deploymentGroups",
    "deploymentTags",
]

# Header keys that already fill a dedicated column.
MAPPED_HEADER_KEYS = {
    "image-set-uuid",            # deploymentID
    "image-pi",                  # setupBy
    "image-sensor",              # cameraID
    "image-target-environment",  # habitat
    "image-event",               # deploymentGroups
}
# Verbose header keys left out of deploymentTags.
EXCLUDED_HEADER_KEYS = {
    "image-abstract",
    "image-creators",
    "image-annotation-labels",
    "image-annotation-creators",
    "image-copyright",
    "image-objective",
    "image-project",
}


def _first_float(entries: Iterable[dict[str, Any]], key: str) -> float | None:
    """First value of ``key`` that parses as a float."""
    for entry in entries:
        value = entry.get(key)
        if value is None:
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return None


def _timestamps(entries: Iterable[dict[str, Any]]) -> list[pd.Timestamp]:
    result = []
    for entry in entries:
        value = entry.get("image-datetime")
        if not value:
            continue
        try:
            result.append(pd.to_datetime(value, utc=True))
        except (TypeError, ValueError):
            continue
    return result


def _compact(value: Any) -> str:
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return str(value)


def _deployment_tags(header: dict[str, Any]) -> str | None:
    """Remaining header fields as ``key:value`` pairs joined by `` | ``."""
    pairs = [
        f"{key}:{_compact(value)}"
        for key, value in header.items()
        if key not in MAPPED_HEADER_KEYS | EXCLUDED_HEADER_KEYS and value not in (None, "")
    ]
    return " | ".join(pairs) if pairs else None


def build_deployments(metadata: dict[str, Any]) -> pd.DataFrame:
    """One-row deployments table.

    Coordinates, camera height and depth come from the first image entry that
    has them; start and end are the earliest and latest image timestamps.
    """
    header = image_set_header(metadata)
    entries = [entry for _, entry in iter_image_entries(metadata)]

    latitude = _first_float(entries, "image-latitude")
    # The iFDO stores this Antarctic site as unsigned degrees; the paper places
    # it at 74° 41.410′ S (southern hemisphere).
    if latitude is not None and latitude > 0:
        latitude = -latitude

    timestamps = _timestamps(entries)
    image_pi = header.get("image-pi")
    image_event = header.get("image-event")

    row = {
        "deploymentID": header.get("image-set-uuid"),
        "locationName": LOCATION_NAME,
        "latitude": latitude,
        "longitude": _first_float(entries, "image-longitude"),
        "deploymentStart": to_utc_iso(min(timestamps)) if timestamps else None,
        "deploymentEnd": to_utc_iso(max(timestamps)) if timestamps else None,
        "setupBy": image_pi.get("orcid") if isinstance(image_pi, dict) else None,
        "cameraModel": CAMERA_MODEL,
        "cameraHeight": _first_float(entries, "image-meters-above-ground"),
        "cameraDepth": _first_float(entries, "image-depth"),
        "cameraID": header.get("image-sensor"),
        "habitat": header.get("image-target-environment"),
        "deploymentGroups": f"image-event:{image_event}" if image_event is not None else None,
        "deploymentTags": _deployment_tags(header),
    }
    return pd.DataFrame([row], columns=COLUMNS)
