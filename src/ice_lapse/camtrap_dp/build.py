"""Regenerate the Camtrap-DP CSV tables.

Reads the iFDO, SpeciesDistribution.csv, Classes.txt and TextualTags from
``data/raw``. With ``--zenodo-target``, media rows link to the published Zenodo
image records listed in that target's manifest. Makes no network calls.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from ..ifdo import load_ifdo_metadata
from ..paths import CAMTRAP_DP_DIR, IFDO_PATH
from ..zenodo.targets import TARGETS
from .deployments import build_deployments
from .media import apply_zenodo_manifest, build_media
from .observations import build_observations


def build_tables(zenodo_target: str | None = None) -> dict[str, pd.DataFrame]:
    """Build every table in memory, so a validation error leaves outputs untouched."""
    metadata = load_ifdo_metadata(IFDO_PATH)
    media = build_media(metadata)
    if zenodo_target:
        target = TARGETS[zenodo_target]
        media = apply_zenodo_manifest(media, target.manifest_path, target)
    return {
        "deployments": build_deployments(metadata),
        "media": media,
        "observations": build_observations(metadata),
    }


def write_tables(tables: dict[str, pd.DataFrame], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, table in tables.items():
        path = output_dir / f"{name}.csv"
        table.to_csv(path, index=False, encoding="utf-8")
        print(f"Saved {len(table):,} {name} rows to {path}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--zenodo-target", choices=TARGETS,
        help="link media to published image records from this Zenodo environment's complete manifest",
    )
    parser.add_argument(
        "--output-dir", type=Path, default=CAMTRAP_DP_DIR,
        help=f"where to write the CSV files (default: {CAMTRAP_DP_DIR})",
    )
    args = parser.parse_args(argv)
    write_tables(build_tables(args.zenodo_target), args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
