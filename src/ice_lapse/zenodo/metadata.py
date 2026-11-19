"""Zenodo deposit metadata for one ICE-LAPSE image."""

from __future__ import annotations

import csv
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Any

from ..ifdo import image_set_header, load_ifdo_metadata
from ..paths import MATCHED_TAXA_PATH
from ..source_data import annotation_path, load_classes, normalise_whitespace

RELATED_DOI = "10.5281/zenodo.7318531"          # parent ICE-LAPSE image dataset
PAPER_DOI = "10.1038/s41597-022-01865-7"        # Scientific Data dataset paper
METHODS_PAPER_DOI = "10.1111/2041-210X.13898"   # Marini et al. (2022), Methods Ecol. Evol.

LOCALITY = "Tethys Bay, Terra Nova Bay, Ross Sea, Antarctica"
LATITUDE = -74.690167
LONGITUDE = 164.103889
DEPTH_METERS = "20"
CAMERA_MODEL = "Canon EOS 600D"

DC = "http://purl.org/dc/"
TDWG = "http://rs.tdwg.org/"

# Paper author list and affiliations, in paper order
# (https://doi.org/10.1038/s41597-022-01865-7).
AUTHOR_AFFILIATIONS = {
    "Simone Marini": "National Research Council of Italy (CNR), Institute of Marine Sciences, La Spezia; Stazione Zoologica Anton Dohrn, Naples, Italy",
    "Federico Bonofiglio": "National Research Council of Italy (CNR), Institute of Marine Sciences, La Spezia, Italy",
    "Lorenzo Paolo Corgnati": "National Research Council of Italy (CNR), Institute of Marine Sciences, La Spezia, Italy",
    "Andrea Bordone": "ENEA-Marine Environment Research Centre, La Spezia, Italy",
    "Stefano Schiaparelli": "DISTAV, Università di Genova, Genova, Italy",
    "Andrea Peirano": "ENEA-Marine Environment Research Centre, La Spezia, Italy",
}

KEYWORDS = ["ICE-LAPSE", "Antarctica", "Tethys Bay", "benthic fauna", "tagged image", "image annotations"]


def subject(term: Any, uri: str) -> dict[str, str]:
    return {"term": str(term), "identifier": uri}


def creators_from_ifdo(metadata: dict[str, Any] | None = None) -> list[dict[str, str]]:
    """Paper authors as Zenodo creators, with ORCIDs taken from the iFDO."""
    if metadata is None:
        metadata = load_ifdo_metadata()
    header = image_set_header(metadata)
    people = [*header.get("image-creators", []), *header.get("image-annotation-creators", [])]
    orcids = {person["name"]: str(person["orcid"]) for person in people if person.get("orcid")}
    creators = []
    for name, affiliation in AUTHOR_AFFILIATIONS.items():
        given, family = name.rsplit(" ", 1)
        creator = {"name": f"{family}, {given}", "affiliation": affiliation}
        if name in orcids:
            creator["orcid"] = orcids[name]
        creators.append(creator)
    return creators


@lru_cache(maxsize=1)
def _taxon_lookup(path: Path = MATCHED_TAXA_PATH) -> dict[str, dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as source:
        return {normalise_whitespace(row["verbatimIdentification"]): row for row in csv.DictReader(source)}


def taxa_for_image(index: str) -> list[dict[str, str]]:
    """Accepted name and WoRMS LSID of each taxon annotated in the image."""
    classes = load_classes()
    with open(annotation_path(index), encoding="utf-8") as source:
        class_ids = {int(line.split()[0]) for line in source if line.strip()}
    taxa = []
    for class_id in sorted(class_ids):
        if class_id >= len(classes):
            raise ValueError(f"Unknown class {class_id} in IMG_{index}.txt")
        name = classes[class_id]
        if name == "Unclassified":
            continue
        match = _taxon_lookup().get(normalise_whitespace(name))
        if not match or not match.get("LSID"):
            raise ValueError(f"No taxon LSID for {name} in IMG_{index}")
        taxa.append({"name": match["ScientificName_accepted"], "lsid": match["LSID"]})
    return taxa


def _subjects(title: str, media: dict[str, str], taxa: list[dict[str, str]]) -> list[dict[str, str]]:
    subjects = [
        subject(title, f"{DC}terms/title"),
        subject(media["mediaID"], f"{TDWG}dwc/terms/associatedMedia"),
        subject(media["deploymentID"], f"{TDWG}dwc/terms/parentEventID"),
        subject(media["timestamp"], f"{TDWG}dwc/terms/eventDate"),
        subject(LOCALITY, f"{TDWG}dwc/terms/verbatimLocality"),
        subject(str(LATITUDE), f"{TDWG}dwc/terms/decimalLatitude"),
        subject(str(LONGITUDE), f"{TDWG}dwc/terms/decimalLongitude"),
        subject(DEPTH_METERS, f"{TDWG}dwc/terms/minimumDepthInMeters"),
        subject(DEPTH_METERS, f"{TDWG}dwc/terms/maximumDepthInMeters"),
        subject("StillImage", f"{DC}elements/1.1/type"),
        subject(f"{DC}dcmitype/StillImage", f"{DC}terms/type"),
        subject("Photograph", f"{TDWG}ac/terms/subtypeLiteral"),
        subject("eng", f"{TDWG}ac/terms/metadataLanguageLiteral"),
        subject(CAMERA_MODEL, f"{TDWG}ac/terms/captureDevice"),
    ]
    for taxon in taxa:
        subjects.append(subject(taxon["name"], f"{TDWG}dwc/terms/scientificName"))
        subjects.append(subject(taxon["lsid"], f"{TDWG}dwc/terms/scientificNameID"))
    return subjects


def _description(index: str, timestamp: str, files: dict[str, Path]) -> str:
    return (
        f"Expert-annotated ICE-LAPSE underwater photograph IMG_{index}, captured {timestamp} "
        f"at Tethys Bay, Antarctica (20 m depth). Part of https://doi.org/{RELATED_DOI}. "
        f"Dataset description: https://doi.org/{PAPER_DOI}. "
        f"Related methods publication: Marini et al. (2022), Long-term automated visual "
        f"monitoring of Antarctic benthic fauna, Methods in Ecology and Evolution, "
        f"https://doi.org/{METHODS_PAPER_DOI}. "
        f"Files: {files['original'].name} = full-resolution untagged JPEG; "
        f"{files['tagged'].name} = JPEG with expert-drawn coloured boxes and class numbers; "
        f"{files['preview'].name} = low-resolution JPEG preview (source directory 640x427); "
        f"{files['raw'].name} = original Canon CR2 camera raw image; "
        f"{files['tags'].name} = one class ID and normalized box centre x/y and width/height per organism; "
        f"{files['legend'].name} = shared colour/class label legend. "
        "Classes.txt in the parent dataset defines the zero-based class IDs. "
        "Each scientificName/scientificNameID subject denotes a taxon annotated in this image, "
        "not a unique specimen."
    )


def deposit_metadata(index: str, media: dict[str, str], creators: list[dict[str, str]],
                     files: dict[str, Path]) -> dict[str, Any]:
    title = f"ICE-LAPSE Antarctic benthic fauna image IMG_{index}"
    timestamp = media["timestamp"]
    return {
        "upload_type": "image",
        "image_type": "photo",
        "title": title,
        "description": _description(index, timestamp, files),
        "creators": creators,
        "publication_date": date.today().isoformat(),
        "access_right": "open",
        "license": "cc-by-4.0",
        "keywords": KEYWORDS,
        "subjects": _subjects(title, media, taxa_for_image(index)),
        "locations": [{"place": LOCALITY, "lat": LATITUDE, "lon": LONGITUDE}],
        "method": "Fixed Canon EOS 600D underwater camera on a seabed lander at 20 m; 9-hour time-lapse; organisms visually tagged by experts.",
        "notes": "ICE-LAPSE project PNRA 2013/AZ1.16; Italian National Antarctic Program. Metadata derived from iFDO, paper, and per-image annotation files.",
        "related_identifiers": [
            {"identifier": RELATED_DOI, "relation": "isPartOf", "resource_type": "dataset"},
            {"identifier": PAPER_DOI, "relation": "isDocumentedBy", "resource_type": "publication-article"},
            {"identifier": METHODS_PAPER_DOI, "relation": "isDocumentedBy", "resource_type": "publication-article"},
        ],
        "dates": [{"start": timestamp[:10], "end": timestamp[:10], "type": "Collected"}],
    }
