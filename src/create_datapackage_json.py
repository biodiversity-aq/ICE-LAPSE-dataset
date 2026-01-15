# Create datapackage.json for Camtrap-DP by mapping iFDO YAML metadata
#
# Outputs: data/camtrap-dp/datapackage.json
#
# This script reads the iFDO YAML for the ICE-LAPSE deployment and builds a
# Frictionless Data Package descriptor that references the three Camtrap-DP CSV
# resources (deployments.csv, media.csv, observations.csv). It maps relevant
# YAML fields to top-level data package metadata and sets the profile to the
# Camtrap-DP profile schema URL requested in the issue.

from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Optional

from utils_path import here
from ifdo import load_ifdo_metadata


CAMTRAP_DP_PROFILE_URL = (
    "https://raw.githubusercontent.com/tdwg/camtrap-dp/refs/heads/main/camtrap-dp-profile.json"
)


def _slugify(value: Optional[str]) -> Optional[str]:
    if not value:
        return value
    # Lowercase, replace non-alphanum with dash, collapse dashes
    v = value.strip().lower()
    v = re.sub(r"[^a-z0-9]+", "-", v)
    v = re.sub(r"-+", "-", v).strip("-")
    return v or None


def _license_from_header(image_license: Optional[str]) -> Optional[Dict[str, Any]]:
    if not image_license:
        return None
    val = str(image_license).strip().upper()
    # Map common values; default to CC-BY 4.0 when CC-BY present without version
    if val in {"CC-BY", "CCBY", "CC BY"}:
        return {
            "name": "CC-BY-4.0",
            "title": "Creative Commons Attribution 4.0 International",
            "path": "https://creativecommons.org/licenses/by/4.0/",
        }
    if val in {"CC0", "CC-0", "CC0-1.0"}:
        return {
            "name": "CC0-1.0",
            "title": "Creative Commons Zero v1.0 Universal",
            "path": "https://creativecommons.org/publicdomain/zero/1.0/",
        }
    # Fallback generic
    return {
        "name": val,
        "title": val,
    }


def _contributors_from_header(header: Dict[str, Any]) -> List[Dict[str, Any]]:
    contribs: List[Dict[str, Any]] = []

    def add_people(people: Any, role: str):
        if not isinstance(people, list):
            return
        for p in people:
            if not isinstance(p, dict):
                continue
            title = p.get("name") or p.get("email") or p.get("orcid")
            if not title:
                continue
            c: Dict[str, Any] = {"title": str(title), "roles": [role]}
            if p.get("email"):
                c["email"] = str(p.get("email"))
            if p.get("orcid"):
                c["identifier"] = f"https://orcid.org/{p.get('orcid')}"
            contribs.append(c)

    # Authors/creators of the dataset
    add_people(header.get("image-creators"), role="author")
    # Annotators
    add_people(header.get("image-annotation-creators"), role="annotator")

    # Principal Investigator as contributor
    pi = header.get("image-pi")
    if isinstance(pi, dict):
        title = pi.get("name") or pi.get("email") or pi.get("orcid")
        if title:
            c: Dict[str, Any] = {"title": str(title), "roles": ["principalInvestigator"]}
            if pi.get("email"):
                c["email"] = str(pi.get("email"))
            if pi.get("orcid"):
                c["identifier"] = f"https://orcid.org/{pi.get('orcid')}"
            contribs.append(c)

    return contribs


def _temporal_coverage_from_items(items: Dict[str, Any]) -> Dict[str, Optional[str]]:
    import pandas as pd

    timestamps: List[Optional[str]] = []
    for entries in items.values():
        if not isinstance(entries, list):
            continue
        for e in entries:
            if isinstance(e, dict) and e.get("image-datetime"):
                try:
                    ts = pd.to_datetime(e.get("image-datetime"), utc=True)
                    timestamps.append(ts.isoformat().replace("+00:00", "Z"))
                except Exception:
                    pass
    start = min(timestamps) if timestamps else None
    end = max(timestamps) if timestamps else None
    return {"start": start, "end": end}


def build_datapackage(ifdo_metadata: Dict[str, Any]) -> Dict[str, Any]:
    header = ifdo_metadata.get("image-set-header", {}) or {}
    items = ifdo_metadata.get("image-set-items", {}) or {}

    dataset_id = header.get("image-set-uuid")
    title = header.get("image-event") or header.get("image-set-name")
    name = _slugify(header.get("image-set-name") or header.get("image-event") or dataset_id)
    description = header.get("image-abstract")
    homepage = header.get("image-set-handle")

    coverage = _temporal_coverage_from_items(items)

    package: Dict[str, Any] = {
        "profile": CAMTRAP_DP_PROFILE_URL,
        "name": name or "ice-lapse",
        "title": title,
        "id": dataset_id,
        "description": description,
        "homepage": homepage,
        "licenses": [l for l in [_license_from_header(header.get("image-license"))] if l],
        "contributors": _contributors_from_header(header),
        # Add a simple source referencing the project and the sampling design DOI if present
        "sources": (
            ([{"title": str(header.get("image-project"))}] if header.get("image-project") else [])
            + [{"title": "Sampling design methodology", "path": "https://doi.org/10.1111/2041-210X.13898"}]
        ),
        # Minimal temporal coverage extension (not strictly part of Frictionless spec, but helpful)
        "temporal": {k: v for k, v in coverage.items() if v},
        "resources": [
            {
                "name": "deployments",
                "path": "deployments.csv",
                "profile": "tabular-data-resource",
                "format": "csv",
            },
            {
                "name": "media",
                "path": "media.csv",
                "profile": "tabular-data-resource",
                "format": "csv",
            },
            {
                "name": "observations",
                "path": "observations.csv",
                "profile": "tabular-data-resource",
                "format": "csv",
            },
        ],
    }

    # Add project entity per Camtrap-DP guidance, leveraging iFDO header
    project_obj: Dict[str, Any] = {}
    proj_title = header.get("image-project") or header.get("image-set-name")
    if proj_title or dataset_id or description:
        project_obj["title"] = proj_title
        if dataset_id:
            project_obj["identifier"] = dataset_id
        if description:
            project_obj["description"] = description
        project_obj["samplingDesign"] = {
            "description": "Sampling design and methods are described in the referenced publication.",
            "citation": "https://doi.org/10.1111/2041-210X.13898",
        }
        package["project"] = project_obj

    # Add keywords from a few header fields if available
    keywords: List[str] = []
    for key in (
        "image-target-environment",
        "image-marine-zone",
        "image-platform",
        "image-spectral-resolution",
    ):
        v = header.get(key)
        if v and isinstance(v, str):
            keywords.append(v)
    if keywords:
        package["keywords"] = keywords

    # Build taxonomic coverage from pre-matched CSV (no external taxonomy lookups)
    import pandas as pd

    taxa: List[Dict[str, Any]] = []
    csv_path = here("data", "taxa", "unique_scientific_name_matched.csv")
    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path)
        # Map lowercase to original column names for flexible access
        cols = {c.lower(): c for c in df.columns}
        # Define rank columns in hierarchical order (high to low)
        rank_cols = [
            "kingdom",
            "phylum",
            "class",
            "order",
            "family",
            "genus",
            "subgenus",
            "species",
            "subspecies",
        ]
        seen_lsids = set()
        for _, row in df.iterrows():
            lsid_col = cols.get("lsid", "LSID")
            lsid = str(row.get(lsid_col) or "").strip()
            if not lsid:
                continue
            # Skip duplicates by LSID
            if lsid in seen_lsids:
                continue
            # Determine a scientific name preference order
            sn_acc_col = cols.get("scientificname_accepted", "ScientificName_accepted")
            sn_col_title = cols.get("scientificname", "ScientificName")
            sn_lower_col = cols.get("scientificname", "scientificName")  # in case lowercase variant exists
            sn_verbatim_col = cols.get("verbatimidentification", "verbatimIdentification")
            sn_candidates = [
                str(row.get(sn_acc_col) or "").strip(),
                str(row.get(sn_col_title) or "").strip(),
                str(row.get(sn_lower_col) or "").strip(),
                str(row.get(sn_verbatim_col) or "").strip(),
            ]
            scientific_name = next((s for s in sn_candidates if s), "")
            if scientific_name.lower() == "unclassified":
                continue
            # Determine lowest non-empty rank
            lowest_rank = None
            for r in reversed(rank_cols):
                col_name = cols.get(r, r)
                val = str(row.get(col_name) or "").strip()
                if val:
                    lowest_rank = r
                    break
            entry: Dict[str, Any] = {
                "taxonID": lsid,
                "scientificName": scientific_name or None,
            }
            if lowest_rank:
                entry["taxonRank"] = lowest_rank.lower()
            # Include allowed classification fields if present
            for fld in ["kingdom", "phylum", "class", "order", "family", "genus"]:
                col_name = cols.get(fld, fld)
                val = str(row.get(col_name) or "").strip()
                if val:
                    entry[fld] = val
            taxa.append(entry)
            seen_lsids.add(lsid)
    if taxa:
        package["taxa"] = taxa

    return package


def save_datapackage_json(out_dir: Optional[str] = None) -> str:
    if out_dir is None:
        out_dir = here("data", "camtrap-dp")
    os.makedirs(out_dir, exist_ok=True)

    # Source YAML path
    yaml_path = here(
        "data",
        "zenodo",
        "Deployment in Tethys bay - Mario Zucchelli Station- 2015_GUARD1-PNRA-2015_iFDO.yaml",
    )

    ifdo_metadata = load_ifdo_metadata(yaml_path)
    dp = build_datapackage(ifdo_metadata)

    out_path = os.path.join(out_dir, "datapackage.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(dp, f, ensure_ascii=False, indent=2)
    print(f"Saved datapackage.json to: {out_path}")
    return out_path


def main():
    save_datapackage_json()


if __name__ == "__main__":
    main()
