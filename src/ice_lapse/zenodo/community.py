"""Submit published records to the ICE-LAPSE Zenodo community, without duplicates."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .client import RateLimitedClient
from .records import read_manifest, save_state
from .targets import Target

OPEN_REQUEST_STATUSES = ("created", "submitted", "accepted")


def ensure_community(client: RateLimitedClient, target: Target, record_id: str,
                     expected_doi: str | None = None) -> str:
    """Return ``"included"`` or ``"pending"`` for a published record.

    Existing membership and inclusion requests are checked first, so a second
    request is never created (including after a lost response).
    """
    url = f"{target.base_url}/api/records/{record_id}"
    record = client.request("GET", url, timeout=60).json()
    if not record.get("doi"):
        raise ValueError(f"Record {record_id} not published")
    if expected_doi and record["doi"] != expected_doi:
        raise ValueError(f"Record {record_id} DOI mismatch: expected {expected_doi}")

    communities = client.request("GET", f"{url}/communities", timeout=60).json()
    if any(hit.get("id") == target.community_id for hit in communities["hits"]["hits"]):
        return "included"

    requests = client.request("GET", f"{url}/requests", params={"size": 100}, timeout=60).json()
    if requests["hits"]["total"] > len(requests["hits"]["hits"]):
        raise RuntimeError(f"Record {record_id}: request list incomplete; refusing duplicate submission")
    for request in requests["hits"]["hits"]:
        if (request.get("type") == "community-inclusion"
                and request.get("receiver", {}).get("community") == target.community_id
                and (request.get("is_open") or request.get("status") in OPEN_REQUEST_STATUSES)):
            return "included" if request.get("status") == "accepted" else "pending"

    result = client.request(
        "POST", f"{url}/communities",
        json={"communities": [{"id": target.community_id}]}, timeout=60,
    ).json()
    processed = [item for item in result.get("processed", []) if item.get("community_id") == target.community_id]
    if not processed:
        raise RuntimeError(f"Record {record_id}: community submission not confirmed: {result.get('errors', result)}")
    return "included" if processed[0].get("request", {}).get("status") == "accepted" else "pending"


def reconcile_community_manifest(client: RateLimitedClient, target: Target, manifest_path: Path | None = None) -> None:
    """Check every record in the manifest (defaults to the target's manifest)."""
    rows = read_manifest(manifest_path or target.manifest_path)
    for position, row in enumerate(rows, 1):
        record_id = target.record_id_from_doi(row["doi"])
        if record_id is None:
            raise ValueError(f"Unexpected {target.name} DOI for IMG_{row['imageIndex']}: {row['doi']}")
        result = ensure_community(client, target, record_id, row["doi"])
        print(f"{position}/{len(rows)} IMG_{row['imageIndex']}: {result}", flush=True)


def reconcile_checkpointed_community(client: RateLimitedClient, target: Target, index: str,
                                     state: dict[str, Any]) -> None:
    """Retry the community submission only if it was interrupted after publishing."""
    record = state[index]
    if record.get("community_status") != "needs_reconcile":
        return
    doi = record["doi"]
    record_id = target.record_id_from_doi(doi)
    if record_id is None or str(record["id"]) != record_id:
        raise ValueError(f"IMG_{index}: community checkpoint DOI/ID mismatch")
    record["community_status"] = ensure_community(client, target, record_id, doi)
    save_state(state, target)
