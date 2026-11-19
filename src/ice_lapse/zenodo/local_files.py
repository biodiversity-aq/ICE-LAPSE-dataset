"""Find the six local files deposited for each image, and link image indices to media."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from ..camtrap_dp.media import build_media
from ..ifdo import load_ifdo_metadata
from ..paths import RAW_DIR, SPECIES_LEGEND_PATH
from ..source_data import image_index, load_species_distribution

# File role -> (folder under data/raw, glob pattern). Every role is per image
# except "legend", which is one shared file.
FILE_PATTERNS = {
    "original": ("jpgImages", "IMG_*_CR2_embedded.jpg"),
    "tagged": ("taggedImages", "IMG_*_CR2_embedded_tagged.jpg"),
    "preview": ("640x427", "IMG_*_CR2_embedded_640x480.jpg"),
    "raw": ("rawImages", "IMG_*.CR2"),
    "tags": ("TextualTags", "IMG_*.txt"),
}
FILE_ROLES = (*FILE_PATTERNS, "legend")


def _files_by_index(folder: str, pattern: str, role: str) -> dict[str, Path]:
    files: dict[str, Path] = {}
    for path in (RAW_DIR / folder).glob(pattern):
        index = image_index(re.match(r"IMG_(\d+)", path.name).group(1))
        if index in files:
            raise ValueError(f"Duplicate {role} files for IMG_{index}")
        files[index] = path
    return files


def paired_photos() -> dict[str, dict[str, Path]]:
    """``{image_index: {role: path}}`` for every annotated image, sorted by index."""
    files = {role: _files_by_index(folder, pattern, role) for role, (folder, pattern) in FILE_PATTERNS.items()}
    expected = set(files["original"])
    for role in ("tagged", "preview", "tags"):
        if set(files[role]) != expected:
            missing = sorted(expected - files[role].keys())[:5]
            extra = sorted(files[role].keys() - expected)[:5]
            raise ValueError(f"{role} images missing={missing}; extra={extra}")
    # The raw archive includes some extra frames outside the 755-image annotated set.
    if expected - files["raw"].keys():
        raise ValueError(f"Missing raw images: {sorted(expected - files['raw'].keys())[:5]}")
    if not SPECIES_LEGEND_PATH.is_file():
        raise FileNotFoundError(SPECIES_LEGEND_PATH)
    return {
        index: {**{role: files[role][index] for role in FILE_PATTERNS}, "legend": SPECIES_LEGEND_PATH}
        for index in sorted(expected)
    }


def media_by_image_index(metadata: dict[str, Any] | None = None) -> dict[str, dict[str, Any]]:
    """Camtrap-DP media row for each image index.

    SpeciesDistribution.csv lists image indices in acquisition order, so rows
    are paired with media sorted by timestamp.
    """
    if metadata is None:
        metadata = load_ifdo_metadata()
    distribution = load_species_distribution()
    media = build_media(metadata).sort_values("timestamp", kind="stable").to_dict("records")
    if len(distribution) != len(media):
        raise ValueError("SpeciesDistribution.csv and iFDO media counts differ")
    return {image_index(index): row for index, row in zip(distribution["Image Index"], media)}
