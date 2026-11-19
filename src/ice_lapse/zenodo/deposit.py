"""Create, fill and publish one Zenodo deposition per image, resumably."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any
from urllib.parse import quote

from .client import RateLimitedClient
from .metadata import deposit_metadata
from .records import save_state
from .targets import Target

# requests/urllib3 apply the connect timeout while sending the request body.
UPLOAD_TIMEOUT_SECONDS = (300, 3600)


def upload_file(client: RateLimitedClient, bucket: str, path: Path) -> str:
    url = f"{bucket.rstrip('/')}/{quote(path.name)}"
    with path.open("rb") as file_obj:
        response = client.request("PUT", url, data=file_obj, timeout=UPLOAD_TIMEOUT_SECONDS)
    return response.json()["links"]["self"]


def _md5(path: Path) -> str:
    digest = hashlib.md5()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _check_remote_file(path: Path, remote: dict[str, Any]) -> None:
    if int(remote.get("filesize", remote.get("size", -1))) != path.stat().st_size:
        raise ValueError(f"Remote file size mismatch for {path.name}; manual inspection required")
    checksum = remote.get("checksum", "")
    if checksum and checksum.split(":")[-1] != _md5(path):
        raise ValueError(f"Remote checksum mismatch for {path.name}; manual inspection required")


def _file_names(deposition: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {item.get("filename", item.get("name")): item for item in deposition.get("files", [])}


def _create_draft(client: RateLimitedClient, target: Target, index: str, files: dict[str, Path],
                  state: dict[str, Any], creators: list[dict[str, str]], media: dict[str, str]) -> None:
    # Persist intent before POST: if the response is lost, never mint another DOI.
    state[index] = {"status": "creating"}
    save_state(state, target)
    created = client.request(
        "POST", target.deposition_url(),
        json={"metadata": deposit_metadata(index, media, creators, files)}, timeout=60,
    ).json()
    state[index] = {"status": "draft", "id": created["id"]}
    save_state(state, target)


def _manifest_row(target: Target, index: str, media: dict[str, str], files: dict[str, Path],
                  bucket: str, deposit_id: int, doi: str) -> dict[str, str]:
    urls = {role: f"{bucket.rstrip('/')}/{quote(path.name)}" for role, path in files.items()}
    return {
        "imageIndex": index, "mediaID": media["mediaID"], "doi": doi,
        "recordURL": target.record_url(deposit_id),
        "originalFile": files["original"].name, "originalFilePath": urls["original"],
        "taggedFile": files["tagged"].name, "taggedFilePath": urls["tagged"],
        "previewFilePath": urls["preview"], "rawFilePath": urls["raw"],
        "tagsFilePath": urls["tags"], "legendFilePath": urls["legend"],
    }


def sync_record(client: RateLimitedClient, target: Target, index: str, files: dict[str, Path],
                state: dict[str, Any], creators: list[dict[str, str]],
                media: dict[str, str]) -> dict[str, str]:
    """Bring one image's deposition to ``published`` and return its manifest row.

    Safe to re-run: an existing draft is reused, files already uploaded are
    verified by size and MD5, and an ambiguous create stops for manual review.
    """
    if not state.get(index):
        _create_draft(client, target, index, files, state, creators, media)
    record = state[index]
    if record["status"] == "creating":
        raise RuntimeError(
            f"IMG_{index}: create response lost. Search {target.name} account drafts for IMG_{index}, "
            f"then set id and status=draft in {target.state_path}; never retry creation blindly."
        )

    deposit_id = record["id"]
    deposition = client.request("GET", target.deposition_url(deposit_id), timeout=60).json()
    if str(index) not in deposition.get("metadata", {}).get("title", ""):
        raise ValueError(f"Deposit {deposit_id} title does not match IMG_{index}")
    bucket = deposition["links"]["bucket"]
    if not bucket.startswith(f"{target.base_url}/api/files/"):
        raise ValueError(f"Deposit {deposit_id} bucket points outside {target.name}")

    remote_files = _file_names(deposition)
    for path in files.values():
        remote = remote_files.get(path.name)
        if remote is not None:
            _check_remote_file(path, remote)
        elif deposition.get("submitted"):
            raise RuntimeError(f"Published IMG_{index} missing {path.name}; cannot modify published DOI")
        else:
            upload_file(client, bucket, path)

    if not deposition.get("submitted"):
        # Re-fetch after uploading; publish only when every file is present.
        deposition = client.request("GET", target.deposition_url(deposit_id), timeout=60).json()
        if set(_file_names(deposition)) != {path.name for path in files.values()}:
            raise RuntimeError(f"IMG_{index}: uploaded file list incomplete; draft {deposit_id} retained")
        # If this POST fails on the network it may still have succeeded; the next
        # run's GET detects that.
        deposition = client.request(
            "POST", f"{target.deposition_url(deposit_id)}/actions/publish", timeout=120,
        ).json()

    doi = deposition.get("doi") or deposition.get("metadata", {}).get("doi")
    if not doi or not deposition.get("submitted"):
        raise RuntimeError(f"Published deposit {deposit_id} returned no confirmed DOI")
    if doi != f"{target.doi_prefix}{deposit_id}":
        raise ValueError(f"Deposit {deposit_id} returned unexpected {target.name} DOI: {doi}")
    state[index] = {
        "status": "published", "id": deposit_id, "doi": doi,
        "community_status": record.get("community_status", "needs_reconcile"),
    }
    save_state(state, target)
    return _manifest_row(target, index, media, files, bucket, deposit_id, doi)
