"""Read the tabular and annotation files of the original ICE-LAPSE dataset."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from .ifdo import iter_image_entries
from .paths import CLASSES_PATH, SPECIES_DISTRIBUTION_PATH, TEXTUAL_TAGS_DIR


def normalise_whitespace(text: str) -> str:
    return " ".join(text.split())


def image_index(value: Any) -> str:
    """Zero-padded four-digit image index, as used in ``IMG_####`` filenames."""
    return str(value).strip().zfill(4)


def load_species_distribution(path: Path = SPECIES_DISTRIBUTION_PATH) -> pd.DataFrame:
    """Per-image taxon counts, one row per image in acquisition order."""
    table = pd.read_csv(path, dtype=str)
    table.columns = [column.strip() for column in table.columns]
    if "Date" not in table.columns or "Image Index" not in table.columns:
        raise ValueError("SpeciesDistribution.csv must contain 'Date' and 'Image Index' columns")
    return table


def load_classes(path: Path = CLASSES_PATH) -> list[str]:
    """Annotation class labels; the list position is the zero-based class ID."""
    with open(path, encoding="utf-8") as source:
        return [line.strip() for line in source if line.strip()]


def annotation_path(index: str) -> Path:
    """YOLO-format bounding-box file for one image."""
    return TEXTUAL_TAGS_DIR / f"IMG_{index}.txt"


def media_in_acquisition_order(metadata: dict[str, Any]) -> list[tuple[str, pd.Timestamp]]:
    """iFDO ``(media_id, timestamp)`` pairs sorted by time; missing times last.

    SpeciesDistribution.csv lists numeric image indices in the same order, which
    is how local ``IMG_####`` files are linked to iFDO media.
    """
    media = [
        (media_id, pd.to_datetime(entry.get("image-datetime"), utc=True, errors="coerce"))
        for media_id, entry in iter_image_entries(metadata)
    ]
    latest = pd.Timestamp.max.tz_localize("UTC")
    media.sort(key=lambda item: item[1] if pd.notna(item[1]) else latest)
    return media
