"""Deposit each ICE-LAPSE image on Zenodo with its six related files.

Choose the environment with --target sandbox or --target production. Each
environment uses its own token, DOI manifest and resume state under
data/interim/zenodo/<target>/. Start with --dry-run (no API calls), then run
--publish. Re-running the same command resumes safely after an interruption.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .client import create_client
from .community import reconcile_checkpointed_community, reconcile_community_manifest
from .deposit import sync_record
from .local_files import FILE_ROLES, media_by_image_index, paired_photos
from .metadata import creators_from_ifdo
from .records import load_state, read_manifest, write_manifest
from .targets import TARGETS, Target

REQUESTS_PER_IMAGE = 9


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--target", choices=TARGETS, required=True,
                        help="Zenodo environment to deposit to")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true",
                      help="check local files and image/media pairing; make no API calls")
    mode.add_argument("--publish", action="store_true",
                      help="create, upload and publish every image not yet in the manifest")
    mode.add_argument("--community-only", action="store_true",
                      help="submit every published manifest record to the ice-lapse community; upload nothing")
    parser.add_argument("--skip-existing", action="store_true",
                        help="sandbox: leave the earlier two-file records unchanged and process only new images")
    parser.add_argument("--yes", action="store_true",
                        help="do not ask for confirmation before publishing to production")
    return parser.parse_args(argv)


def _confirm_production() -> bool:
    print("This mints permanent production DOIs on https://zenodo.org.")
    try:
        return input("Type 'production' to continue: ").strip() == "production"
    except EOFError:
        return False


def _check_existing(target: Target, completed: dict[str, dict[str, str]], state: dict,
                    image_ids: set[str], skip_existing: bool) -> None:
    if not completed.keys() <= image_ids:
        raise ValueError("Existing upload manifest contains image IDs absent from current photo folders")
    if target.name == "sandbox" and completed and not skip_existing:
        raise RuntimeError(
            f"{len(completed)} pairs already published with only two files. Cannot add four more "
            "without a new version DOI. Use --skip-existing to preserve them and process remaining pairs."
        )
    for index in state.keys() & completed.keys():
        if state[index].get("status") != "published" or state[index].get("doi") != completed[index]["doi"]:
            raise ValueError(f"State/manifest conflict for IMG_{index}; resolve manually before upload")


def publish(client, target: Target, pairs: dict[str, dict[str, Path]], media: dict[str, dict],
            skip_existing: bool = False) -> None:
    """Publish every image missing from the manifest, checkpointing after each one.

    Images already in the manifest are skipped without remote checks; only
    community submissions interrupted after publishing are retried.
    """
    completed = {row["imageIndex"]: row for row in read_manifest(target.manifest_path)}
    state = load_state(target)
    _check_existing(target, completed, state, set(pairs), skip_existing)

    for index in sorted(state.keys() & completed.keys()):
        reconcile_checkpointed_community(client, target, index, state)

    creators = creators_from_ifdo()
    for position, (index, files) in enumerate(pairs.items(), start=1):
        if index in completed:
            continue
        completed[index] = sync_record(client, target, index, files, state, creators, media[index])
        write_manifest(target.manifest_path, [completed[key] for key in sorted(completed)])
        reconcile_checkpointed_community(client, target, index, state)
        if position % 10 == 0 or position == len(pairs):
            print(f"Published {len(completed)}/{len(pairs)} image records; latest DOI {completed[index]['doi']}")

    print(f"All image DOIs and URLs saved to {target.manifest_path}")
    print(f"To link Camtrap-DP media to them: python -m ice_lapse.camtrap_dp --zenodo-target {target.name}")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    target = TARGETS[args.target]

    if args.community_only:
        reconcile_community_manifest(create_client(target), target)
        return 0

    pairs = paired_photos()
    media = media_by_image_index()
    if pairs.keys() != media.keys():
        raise ValueError("JPEG image IDs do not match SpeciesDistribution.csv and Camtrap-DP media IDs")
    total_bytes = sum(path.stat().st_size for files in pairs.values() for path in files.values())
    print(
        f"Images: {len(pairs)}; files: {len(FILE_ROLES) * len(pairs)}; bytes: {total_bytes:,}; "
        f"API requests: about {REQUESTS_PER_IMAGE * len(pairs):,}; paced <=80/min, <=4,800/hour; "
        f"{target.name}: {target.base_url}"
    )

    if args.dry_run:
        existing = read_manifest(target.manifest_path)
        if existing:
            print(f"Existing {target.name} records: {len(existing)}; "
                  "existing published files cannot be changed under same DOI")
        print("Dry run passed; no upload performed.")
        return 0

    if target.name == "production" and not args.yes and not _confirm_production():
        print("Aborted; nothing uploaded.")
        return 1
    publish(create_client(target), target, pairs, media, args.skip_existing)
    return 0


def run() -> None:
    """Console entry point: report errors without a traceback."""
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"Error: {error}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    run()
