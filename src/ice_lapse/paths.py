"""Locations of every input and output file, relative to the repository root."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"

# Original ICE-LAPSE dataset (https://doi.org/10.5281/zenodo.7318531).
RAW_DIR = DATA_DIR / "raw"
IFDO_PATH = RAW_DIR / "Deployment in Tethys bay - Mario Zucchelli Station- 2015_GUARD1-PNRA-2015_iFDO.yaml"
SPECIES_DISTRIBUTION_PATH = RAW_DIR / "SpeciesDistribution.csv"
CLASSES_PATH = RAW_DIR / "Classes.txt"
TEXTUAL_TAGS_DIR = RAW_DIR / "TextualTags"
SPECIES_LEGEND_PATH = RAW_DIR / "SpeciesColorLabel.jpg"

# Taxon names matched against WoRMS.
MATCHED_TAXA_PATH = DATA_DIR / "taxa" / "unique_scientific_name_matched.csv"

# Working files written by the Zenodo uploader (resume state and DOI manifests).
ZENODO_INTERIM_DIR = DATA_DIR / "interim" / "zenodo"

# Camtrap-DP resources (https://camtrap-dp.tdwg.org/).
CAMTRAP_DP_DIR = DATA_DIR / "camtrap-dp"
