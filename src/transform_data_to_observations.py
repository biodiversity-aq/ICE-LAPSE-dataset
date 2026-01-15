# Python
from typing import Dict, Any, List, Optional
import os
import pandas as pd

from utils_path import here
from ifdo import load_ifdo_metadata


def species_distribution_to_observations_df(ifdo_metadata: Dict[str, Any]) -> pd.DataFrame:
    """
    Build observations (long table) from data/zenodo/SpeciesDistribution.csv.

    Columns in output:
    - mediaID = Image Index
    - eventStart = Date (UTC, ISO8601 Z)
    - eventEnd = eventStart
    - observationLevel = "media"
    - scientificName = taxon column name except "Unclassified"; blank for "Unclassified"
    - observationType = "animal" for all records; "unclassified" if scientificName is blank
    - count = numeric value for the taxon; include only records where count > 0
    - classificationMethod = "human"
    - classifiedBy = ORCIDs of image-annotation-creators joined by " | "
    """
    header = ifdo_metadata.get("image-set-header", {}) or {}
    creators = header.get("image-annotation-creators", []) or []

    # Collect ORCIDs
    orcids: List[str] = []
    for c in creators:
        if isinstance(c, dict):
            o = c.get("orcid")
            if o:
                orcids.append(str(o))
    classified_by: Optional[str] = " | ".join(orcids) if orcids else None

    # Load SpeciesDistribution.csv as strings to preserve leading zeros in Image Index
    spdist_path = here("data", "zenodo", "SpeciesDistribution.csv")
    df = pd.read_csv(spdist_path, dtype=str)
    df.columns = [c.strip() for c in df.columns]

    # Basic validation
    if "Date" not in df.columns or "Image Index" not in df.columns:
        raise ValueError("SpeciesDistribution.csv must contain 'Date' and 'Image Index' columns")

    # Identify taxa columns
    taxa_cols = [c for c in df.columns if c not in ("Date", "Image Index")]

    # Melt to long
    long_df = df.melt(
        id_vars=["Date", "Image Index"],
        value_vars=taxa_cols,
        var_name="taxon",
        value_name="count",
    )

    # Keep only rows with count > 0
    long_df["count"] = pd.to_numeric(long_df["count"], errors="coerce").fillna(0).astype(int)
    long_df = long_df[long_df["count"] > 0].copy()

    # Timestamps
    def to_iso_utc_z(val: str) -> Optional[str]:
        ts = pd.to_datetime(val, utc=True, errors="coerce")
        return ts.isoformat().replace("+00:00", "Z") if pd.notnull(ts) else None

    long_df["eventStart"] = long_df["Date"].apply(to_iso_utc_z)
    long_df["eventEnd"] = long_df["eventStart"]

    # scientificName and observationType rules
    is_unclassified = long_df["taxon"].str.strip().str.lower().eq("unclassified")
    long_df["scientificName"] = long_df["taxon"].mask(is_unclassified, "").astype(str)
    long_df["observationType"] = is_unclassified.map({True: "unclassified", False: "animal"})

    # Other fixed fields
    long_df["mediaID"] = long_df["Image Index"].astype(str)
    long_df["observationLevel"] = "media"
    long_df["classificationMethod"] = "human"
    long_df["classifiedBy"] = classified_by

    # Final selection and order
    observations = long_df[
        [
            "mediaID",
            "eventStart",
            "eventEnd",
            "observationLevel",
            "scientificName",
            "observationType",
            "count",
            "classificationMethod",
            "classifiedBy",
        ]
    ].reset_index(drop=True)

    return observations


def save_observations_csv():
    """
    Read iFDO metadata + SpeciesDistribution.csv and save observations to data/camtrap-dp/observations.csv.
    """
    file_path = here(
        "data",
        "zenodo",
        "Deployment in Tethys bay - Mario Zucchelli Station- 2015_GUARD1-PNRA-2015_iFDO.yaml",
    )
    ifdo_metadata = load_ifdo_metadata(file_path)

    observations_df = species_distribution_to_observations_df(ifdo_metadata)

    out_path = here("data", "camtrap-dp", "observations.csv")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    observations_df.to_csv(out_path, index=False, encoding="utf-8")
    print(f"Saved observations CSV to: {out_path}")