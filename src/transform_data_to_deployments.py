# Python
import json
from typing import Dict, List, Any, Optional

import pandas as pd

# Note: iFDO metadata loading utilities have been moved to src/ifdo.py
# This module now focuses solely on transforming metadata into deployments.


def header_to_deployments_df(metadata: Dict[str, Any]) -> pd.DataFrame:
    """
    Build a one-row deployments DataFrame with fields:
    - deploymentID = image-set-uuid
    - locationName = "Tethys bay - Mario Zucchelli Station- 2015"
    - latitude/longitude from image-set-items (first non-null)
    - deploymentStart = earliest UTC timestamp from image-datetime
    - deploymentEnd   = latest UTC timestamp from image-datetime
    - setupBy = orcid of image-pi
    - cameraModel = "Canon EOS 600D"
    - cameraHeight = image-meters-above-ground from image-set-items
    - cameraDepth  = image-depth from image-set-items
    - featureType = image-marine-zone
    - cameraID = image-sensor
    - habitat = image-target-environment
    - deploymentGroups = "image-event:<value>"
    - deploymentTags = remaining header fields as "key:value" joined by " | "
                       excluding verbose fields.
    """
    header = metadata.get("image-set-header", {}) or {}
    items = metadata.get("image-set-items", {}) or {}

    # Gather values from image-set-items
    latitudes: List[Optional[float]] = []
    longitudes: List[Optional[float]] = []
    heights: List[Optional[float]] = []
    depths: List[Optional[float]] = []
    datetimes: List[pd.Timestamp] = []

    for entries in items.values():
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            lat = entry.get("image-latitude")
            lon = entry.get("image-longitude")
            h = entry.get("image-meters-above-ground")
            d = entry.get("image-depth")
            dt = entry.get("image-datetime")

            if lat is not None:
                try:
                    latitudes.append(float(lat))
                except (TypeError, ValueError):
                    pass
            if lon is not None:
                try:
                    longitudes.append(float(lon))
                except (TypeError, ValueError):
                    pass
            if h is not None:
                try:
                    heights.append(float(h))
                except (TypeError, ValueError):
                    pass
            if d is not None:
                try:
                    depths.append(float(d))
                except (TypeError, ValueError):
                    pass
            if dt:
                try:
                    datetimes.append(pd.to_datetime(dt, utc=True))
                except Exception:
                    pass

    def first_or_none(vals: List[Optional[float]]) -> Optional[float]:
        for v in vals:
            if v is not None:
                return v
        return None

    deployment_start = datetimes and min(datetimes) or None
    deployment_end = datetimes and max(datetimes) or None
    deployment_start_iso = deployment_start.isoformat().replace("+00:00", "Z") if deployment_start is not None else None
    deployment_end_iso = deployment_end.isoformat().replace("+00:00", "Z") if deployment_end is not None else None

    # setupBy (orcid)
    setup_by = None
    image_pi = header.get("image-pi")
    if isinstance(image_pi, dict):
        setup_by = image_pi.get("orcid")

    # Base fields
    deployments_row = {
        "deploymentID": header.get("image-set-uuid"),
        "locationName": "Tethys bay - Mario Zucchelli Station- 2015",
        "latitude": first_or_none(latitudes),
        "longitude": first_or_none(longitudes),
        "deploymentStart": deployment_start_iso,
        "deploymentEnd": deployment_end_iso,
        "setupBy": setup_by,
        "cameraModel": "Canon EOS 600D",
        "cameraHeight": first_or_none(heights),
        "cameraDepth": first_or_none(depths),
        "featureType": header.get("image-marine-zone"),
        "cameraID": header.get("image-sensor"),
        "habitat": header.get("image-target-environment"),
        "deploymentGroups": None,
        "deploymentTags": None,
    }

    # deploymentGroups: "image-event:<value>"
    image_event = header.get("image-event")
    if image_event is not None:
        deployments_row["deploymentGroups"] = f"image-event:{image_event}"

    # Build deploymentTags from remaining header keys
    mapped_keys = {
        "image-set-uuid",            # deploymentID
        "image-marine-zone",         # featureType
        "image-pi",                  # setupBy (orcid)
        "image-sensor",              # cameraID
        "image-target-environment",  # habitat
        "image-event",               # deploymentGroups
    }
    excluded_from_tags = {
        "image-abstract",
        "image-creators",
        "image-annotation-labels",
        "image-annotation-creators",
        "image-copyright",
        "image-objective",
        "image-project",
    }

    def compact(v: Any) -> str:
        if isinstance(v, (dict, list)):
            return json.dumps(v, ensure_ascii=False, separators=(",", ":"))
        return str(v)

    tag_pairs: List[str] = []
    for k, v in header.items():
        if k in mapped_keys or k in excluded_from_tags:
            continue
        if v is None or v == "":
            continue
        tag_pairs.append(f"{k}:{compact(v)}")

    deployments_row["deploymentTags"] = " | ".join(tag_pairs) if tag_pairs else None

    columns = [
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
        "featureType",
        "cameraID",
        "habitat",
        "deploymentGroups",
        "deploymentTags",
    ]
    return pd.DataFrame([deployments_row], columns=columns)
