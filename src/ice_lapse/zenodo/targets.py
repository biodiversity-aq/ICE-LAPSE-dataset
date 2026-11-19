"""The two Zenodo environments. Each has its own token, community, DOI prefix,
resume state and manifest; nothing is shared between them."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from ..paths import ZENODO_INTERIM_DIR


@dataclass(frozen=True)
class Target:
    name: str
    base_url: str
    token_env: str
    state_path: Path
    manifest_path: Path
    community_id: str
    doi_prefix: str

    def record_id_from_doi(self, doi: str) -> str | None:
        """Numeric record ID of a DOI minted by this environment, else None."""
        match = re.fullmatch(re.escape(self.doi_prefix) + r"(\d+)", doi)
        return match.group(1) if match else None

    def record_url(self, record_id: str | int) -> str:
        return f"{self.base_url}/records/{record_id}"

    def deposition_url(self, deposit_id: str | int | None = None) -> str:
        url = f"{self.base_url}/api/deposit/depositions"
        return url if deposit_id is None else f"{url}/{deposit_id}"


def _target(name: str, base_url: str, token_env: str, community_id: str, doi_prefix: str) -> Target:
    folder = ZENODO_INTERIM_DIR / name
    return Target(
        name=name,
        base_url=base_url,
        token_env=token_env,
        state_path=folder / "upload_state.json",
        manifest_path=folder / "image_pairs.csv",
        community_id=community_id,
        doi_prefix=doi_prefix,
    )


TARGETS = {
    "sandbox": _target(
        "sandbox", "https://sandbox.zenodo.org", "ZENODO_SANDBOX_TOKEN",
        community_id="c6d40d20-e605-4647-a9b5-99f224406003", doi_prefix="10.5072/zenodo.",
    ),
    "production": _target(
        "production", "https://zenodo.org", "ZENODO_TOKEN",
        community_id="52064744-ea5e-4134-b4ca-da8ce0c40141", doi_prefix="10.5281/zenodo.",
    ),
}
