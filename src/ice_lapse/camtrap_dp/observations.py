"""Camtrap-DP ``observations`` table: one row per tagged organism.

Bounding boxes come from the YOLO-format TextualTags files. Per-image counts are
checked against SpeciesDistribution.csv before any row is accepted.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

import pandas as pd

from ..ifdo import image_set_header, to_utc_iso
from ..source_data import (
    annotation_path,
    image_index,
    load_classes,
    load_species_distribution,
    media_in_acquisition_order,
    normalise_whitespace,
)

# Labels are rounded to six decimals; allow that much drift past the image edge.
BOX_TOLERANCE = 1e-6


def _classified_by(header: dict[str, Any]) -> str | None:
    """ORCIDs of the annotation creators joined by `` | ``."""
    orcids = [
        str(creator["orcid"])
        for creator in header.get("image-annotation-creators") or []
        if isinstance(creator, dict) and creator.get("orcid")
    ]
    return " | ".join(orcids) if orcids else None


def _class_columns(classes: list[str], distribution: pd.DataFrame) -> dict[int, str]:
    """Map each class ID to its SpeciesDistribution.csv taxon column."""
    taxon_columns = {normalise_whitespace(column): column for column in distribution.columns[2:]}
    mapping = {class_id: taxon_columns.get(normalise_whitespace(name)) for class_id, name in enumerate(classes)}
    if any(column is None for column in mapping.values()):
        raise ValueError("Classes.txt labels do not match SpeciesDistribution.csv taxon columns")
    return mapping


def _read_boxes(path, class_ids) -> list[tuple[int, int, float, float, float, float]]:
    """Parse ``(line_number, class_id, x, y, width, height)`` with top-left x/y."""
    boxes = []
    with open(path, encoding="utf-8") as annotations:
        for line_number, line in enumerate(annotations, start=1):
            parts = line.split()
            if not parts:
                continue
            if len(parts) != 5:
                raise ValueError(f"Malformed annotation {path}:{line_number}")
            class_id = int(parts[0])
            if class_id not in class_ids:
                raise ValueError(f"Unknown class {class_id} in {path}:{line_number}")
            center_x, center_y, width, height = map(float, parts[1:])
            x, y = center_x - width / 2, center_y - height / 2
            if (min(x, y, width, height) < -BOX_TOLERANCE
                    or x + width > 1 + BOX_TOLERANCE or y + height > 1 + BOX_TOLERANCE):
                raise ValueError(f"Bounding box outside normalized image in {path}:{line_number}")
            # Clamp rounding-only drift back inside the image.
            x = min(1 - width, max(0.0, x))
            y = min(1 - height, max(0.0, y))
            boxes.append((line_number, class_id, x, y, width, height))
    return boxes


def _expected_counts(source: pd.Series, class_columns: dict[int, str]) -> Counter:
    counts = Counter()
    for class_id, column in class_columns.items():
        value = pd.to_numeric(source[column], errors="coerce")
        counts[class_id] = int(value) if pd.notna(value) else 0
    return +counts  # drop zero counts


def build_observations(metadata: dict[str, Any]) -> pd.DataFrame:
    header = image_set_header(metadata)
    classified_by = _classified_by(header)
    deployment_id = header.get("image-set-uuid")

    distribution = load_species_distribution()
    media = media_in_acquisition_order(metadata)
    if len(media) != len(distribution):
        raise ValueError(
            f"Cannot align observations: {len(distribution)} distribution rows "
            f"but {len(media)} iFDO media items"
        )
    classes = load_classes()
    class_columns = _class_columns(classes, distribution)

    records = []
    for (media_id, timestamp), (_, source) in zip(media, distribution.iterrows()):
        if pd.isna(timestamp):
            raise ValueError(f"Missing iFDO timestamp for {media_id}")
        event_time = to_utc_iso(timestamp)
        index = image_index(source["Image Index"])
        path = annotation_path(index)
        if not path.is_file():
            raise FileNotFoundError(f"Missing annotation file: {path}")

        boxes = _read_boxes(path, class_columns)
        observed = Counter(class_id for _, class_id, *_ in boxes)
        if _expected_counts(source, class_columns) != +observed:
            raise ValueError(f"TextualTags counts disagree with SpeciesDistribution.csv for IMG_{index}")

        for line_number, class_id, x, y, width, height in boxes:
            unclassified = classes[class_id].strip().lower() == "unclassified"
            records.append({
                "observationID": f"{media_id}#{line_number:04d}",
                "deploymentID": deployment_id,
                "mediaID": media_id,
                "eventStart": event_time,
                "eventEnd": event_time,
                "observationLevel": "media",
                "observationType": "unclassified" if unclassified else "animal",
                "scientificName": "" if unclassified else classes[class_id],
                "count": 1,
                "bboxX": x,
                "bboxY": y,
                "bboxWidth": width,
                "bboxHeight": height,
                "classificationMethod": "human",
                "classifiedBy": classified_by,
            })
    return pd.DataFrame(records)
