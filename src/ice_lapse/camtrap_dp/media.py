"""Camtrap-DP ``media`` table, optionally linked to published Zenodo records."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from ..ifdo import image_set_header, iter_image_entries, to_utc_iso
from ..zenodo.targets import Target

COLUMNS = [
    "mediaID",
    "deploymentID",
    "captureMethod",
    "timestamp",
    "filePath",
    "filePublic",
    "fileMediatype",
]

# iFDO image-capture-mode -> Camtrap-DP captureMethod.
CAPTURE_METHODS = {"timer": "timeLapse"}

REQUIRED_MANIFEST_COLUMNS = {
    "mediaID", "imageIndex", "doi", "originalFile", "originalFilePath",
    "taggedFile", "taggedFilePath", "recordURL",
}


def _timestamp_or_none(value: Any) -> str | None:
    if not value:
        return None
    try:
        return to_utc_iso(pd.to_datetime(value, utc=True))
    except (TypeError, ValueError):
        return None


def build_media(metadata: dict[str, Any]) -> pd.DataFrame:
    """One media row per iFDO image entry, linking to the iFDO ``image-url``."""
    header = image_set_header(metadata)
    rows = []
    for media_id, entry in iter_image_entries(metadata):
        capture_mode = entry.get("image-capture-mode", header.get("image-capture-mode"))
        rows.append({
            "mediaID": media_id,
            "deploymentID": header.get("image-set-uuid"),
            "captureMethod": CAPTURE_METHODS.get(capture_mode, capture_mode),
            "timestamp": _timestamp_or_none(entry.get("image-datetime")),
            "filePath": entry.get("image-url"),
            "filePublic": "true",
            "fileMediatype": "image/jpeg",
        })
    return pd.DataFrame(rows, columns=COLUMNS)


def _validate_manifest(manifest: pd.DataFrame, media: pd.DataFrame, target: Target) -> None:
    missing = REQUIRED_MANIFEST_COLUMNS - set(manifest.columns)
    if missing:
        raise ValueError(f"Manifest missing columns: {sorted(missing)}")
    if manifest["mediaID"].duplicated().any() or manifest["imageIndex"].duplicated().any():
        raise ValueError("Manifest contains duplicate mediaID or imageIndex")
    if media["mediaID"].duplicated().any() or set(manifest["mediaID"]) != set(media["mediaID"]):
        raise ValueError("Manifest must contain exactly one published record per Camtrap-DP mediaID")
    files_prefix = f"{target.base_url}/api/files/"
    for row in manifest.itertuples(index=False):
        record_id = target.record_id_from_doi(row.doi)
        if record_id is None or row.recordURL != target.record_url(record_id):
            raise ValueError(f"Unexpected DOI/record URL for {row.mediaID}")
        for name, url in ((row.originalFile, row.originalFilePath), (row.taggedFile, row.taggedFilePath)):
            if not name or not url.startswith(files_prefix) or not url.endswith("/" + name):
                raise ValueError(f"Unexpected file URL for {row.mediaID}: {url}")


def apply_zenodo_manifest(media: pd.DataFrame, manifest_path: Path, target: Target) -> pd.DataFrame:
    """Point ``filePath`` at the published original image and record the tagged
    image link and image DOI in ``mediaComments``.

    The manifest must cover every media row exactly once; nothing is changed
    if validation fails.
    """
    manifest = pd.read_csv(manifest_path, dtype=str).fillna("")
    _validate_manifest(manifest, media, target)
    by_media = manifest.set_index("mediaID")
    result = media.copy()
    result["filePath"] = result["mediaID"].map(by_media["originalFilePath"])
    result["mediaComments"] = result["mediaID"].map(
        lambda key: f"taggedFilePath:{by_media.at[key, 'taggedFilePath']} | imageDOI:{by_media.at[key, 'doi']}"
    )
    return result
