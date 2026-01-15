# Python
from typing import Dict, Any, List

import os
import pandas as pd

# Reuse existing utilities from other modules
from utils_path import here  # moved to shared utility to avoid circular import
from ifdo import load_ifdo_metadata


def image_items_to_media_df(metadata: Dict[str, Any]) -> pd.DataFrame:
    """
    Build a media DataFrame from image-set-items with fields:
    - mediaID       = key of each image-set-items
    - deploymentID  = image-set-uuid
    - captureMethod = image-capture-mode
    - timestamp     = image-datetime (UTC, ISO8601 Z)
    - filePath      = image-url
    - filePublic    = true
    - fileMediatype = image/jpeg
    """
    header = metadata.get("image-set-header", {}) or {}
    items = metadata.get("image-set-items", {}) or {}

    deployment_id = header.get("image-set-uuid")

    rows: List[Dict[str, Any]] = []

    for key, entries in items.items():
        # key is the mediaID (e.g., a filename)
        media_id = key
        if not isinstance(entries, list):
            continue

        for entry in entries:
            if not isinstance(entry, dict):
                continue

            capture_method = entry.get("image-capture-mode", header.get("image-capture-mode"))

            ts = entry.get("image-datetime")
            ts_iso = None
            if ts:
                try:
                    ts_iso = pd.to_datetime(ts, utc=True).isoformat().replace("+00:00", "Z")
                except Exception:
                    pass

            file_path = entry.get("image-url")

            rows.append(
                {
                    "mediaID": media_id,
                    "deploymentID": deployment_id,
                    "captureMethod": capture_method,
                    "timestamp": ts_iso,
                    "filePath": file_path,
                    "filePublic": "true",
                    "fileMediatype": "image/jpeg",
                }
            )

    columns = [
        "mediaID",
        "deploymentID",
        "captureMethod",
        "timestamp",
        "filePath",
        "filePublic",
        "fileMediatype",
    ]
    return pd.DataFrame(rows, columns=columns)


def save_media_csv_from_ifdo():
    """
    Read the iFDO YAML (using here()) and save the media CSV to data/camtrap-dp/media.csv.
    """
    file_path = here(
        "data",
        "zenodo",
        "Deployment in Tethys bay - Mario Zucchelli Station- 2015_GUARD1-PNRA-2015_iFDO.yaml",
    )

    ifdo_metadata = load_ifdo_metadata(file_path)
    media_df = image_items_to_media_df(ifdo_metadata)

    out_path = here("data", "camtrap-dp", "media.csv")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    media_df.to_csv(out_path, index=False, encoding="utf-8")
    print(f"Saved media CSV to: {out_path}")