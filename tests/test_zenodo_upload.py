"""Offline resume, isolation and metadata checks for the Zenodo uploader."""

import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from ice_lapse.zenodo import cli, client as client_module, community, deposit, metadata
from ice_lapse.zenodo.local_files import media_by_image_index, paired_photos
from ice_lapse.zenodo.records import load_state
from ice_lapse.zenodo.targets import TARGETS

SANDBOX = TARGETS["sandbox"]
PRODUCTION = TARGETS["production"]
ROLES = ("original", "tagged", "preview", "raw", "tags", "legend")


class FakeResponse:
    def __init__(self, value):
        self.value = value

    def json(self):
        return self.value


def make_files(root):
    files = {}
    for role in ROLES:
        path = Path(root) / f"{role}.dat"
        path.write_bytes(role.encode())
        files[role] = path
    return files


def remote_listing(files):
    return [{"filename": p.name, "filesize": p.stat().st_size} for p in files.values()]


class CommunityTests(unittest.TestCase):
    def test_community_reconciliation(self):
        community_id = SANDBOX.community_id

        class Client:
            def __init__(self, members=(), requests=(), response=None):
                self.members = members
                self.requests = requests
                self.response = response
                self.posts = 0

            def request(self, method, url, **kwargs):
                if method == "POST":
                    self.posts += 1
                    self.payload = kwargs["json"]
                    return FakeResponse(self.response)
                if url.endswith("/communities"):
                    return FakeResponse({"hits": {"hits": [{"id": id_} for id_ in self.members]}})
                if url.endswith("/requests"):
                    return FakeResponse({"hits": {"hits": self.requests, "total": len(self.requests)}})
                return FakeResponse({"doi": "10.5072/zenodo.123"})

        included = Client(members=[community_id])
        self.assertEqual(community.ensure_community(included, SANDBOX, "123"), "included")
        self.assertEqual(included.posts, 0)
        pending = Client(requests=[{"type": "community-inclusion", "receiver": {"community": community_id},
                                    "status": "submitted"}])
        self.assertEqual(community.ensure_community(pending, SANDBOX, "123"), "pending")
        self.assertEqual(pending.posts, 0)
        fresh = Client(response={"processed": [{"community_id": community_id, "request": {"status": "submitted"}}]})
        self.assertEqual(community.ensure_community(fresh, SANDBOX, "123"), "pending")
        self.assertEqual(fresh.payload, {"communities": [{"id": community_id}]})
        with self.assertRaisesRegex(RuntimeError, "not confirmed"):
            community.ensure_community(Client(response={"errors": [{"message": "Denied"}]}), SANDBOX, "123")

    def test_production_community_and_manifest_prefix(self):
        class Client:
            def request(self, method, url, **kwargs):
                if url.endswith("/communities") and method == "GET":
                    return FakeResponse({"hits": {"hits": []}})
                if url.endswith("/requests"):
                    return FakeResponse({"hits": {"total": 0, "hits": []}})
                if method == "POST":
                    self.payload = kwargs["json"]
                    return FakeResponse({"processed": [{"community_id": PRODUCTION.community_id,
                                                        "request": {"status": "submitted"}}]})
                return FakeResponse({"doi": "10.5281/zenodo.123"})

        client = Client()
        self.assertEqual(community.ensure_community(client, PRODUCTION, "123", "10.5281/zenodo.123"), "pending")
        self.assertEqual(client.payload, {"communities": [{"id": PRODUCTION.community_id}]})
        with tempfile.TemporaryDirectory() as root:
            manifest = Path(root) / "manifest.csv"
            manifest.write_text("imageIndex,doi\n0609,10.5072/zenodo.123\n")
            with self.assertRaisesRegex(ValueError, "Unexpected production DOI"):
                community.reconcile_community_manifest(client, PRODUCTION, manifest)

    def test_community_retry_only_for_interrupted_record(self):
        with tempfile.TemporaryDirectory() as root:
            target = replace(PRODUCTION, state_path=Path(root) / "state.json")
            state = {
                "0609": {"status": "published", "id": 123, "doi": "10.5281/zenodo.123"},
                "0610": {"status": "published", "id": 124, "doi": "10.5281/zenodo.124",
                         "community_status": "needs_reconcile"},
            }
            with patch.object(community, "ensure_community", side_effect=RuntimeError("timeout")) as check:
                community.reconcile_checkpointed_community(None, target, "0609", state)
                check.assert_not_called()
                with self.assertRaisesRegex(RuntimeError, "timeout"):
                    community.reconcile_checkpointed_community(None, target, "0610", state)
            self.assertEqual(state["0610"]["community_status"], "needs_reconcile")
            with patch.object(community, "ensure_community", return_value="pending") as check:
                community.reconcile_checkpointed_community(None, target, "0610", state)
                check.assert_called_once_with(None, target, "124", "10.5281/zenodo.124")
            self.assertEqual(load_state(target)["0610"]["community_status"], "pending")


class MetadataTests(unittest.TestCase):
    def test_all_six_files_and_metadata(self):
        pairs = paired_photos()
        self.assertEqual(len(pairs), 755)
        self.assertEqual(set(pairs["0609"]), set(ROLES))
        media = media_by_image_index()["0609"]
        result = metadata.deposit_metadata("0609", media, metadata.creators_from_ifdo(), pairs["0609"])
        self.assertEqual(len(result["creators"]), 6)
        self.assertIn("SpeciesColorLabel.jpg", result["description"])
        self.assertIn(metadata.METHODS_PAPER_DOI, result["description"])
        self.assertIn({"identifier": metadata.METHODS_PAPER_DOI, "relation": "isDocumentedBy",
                       "resource_type": "publication-article"}, result["related_identifiers"])
        self.assertTrue(any(s["identifier"].endswith("scientificNameID") for s in result["subjects"]))


class SyncRecordTests(unittest.TestCase):
    def test_resume_existing_draft_without_post_create(self):
        with tempfile.TemporaryDirectory() as root:
            files = make_files(root)
            draft = {"id": 123, "links": {"bucket": "https://sandbox.zenodo.org/api/files/bucket"},
                     "metadata": {"title": "ICE-LAPSE IMG_0609"}, "files": [], "submitted": False}
            complete = {**draft, "files": remote_listing(files)}
            published = {**complete, "submitted": True, "doi": "10.5072/zenodo.123"}

            class Client:
                def __init__(self):
                    self.calls = []
                    self.gets = 0

                def request(self, method, url, **kwargs):
                    self.calls.append(method)
                    if method == "GET":
                        self.gets += 1
                        return FakeResponse(draft if self.gets == 1 else complete)
                    if method == "PUT":
                        return FakeResponse({"links": {"self": url}})
                    if method == "POST" and url.endswith("/actions/publish"):
                        return FakeResponse(published)
                    raise AssertionError("Unexpected create request")

            client = Client()
            target = replace(SANDBOX, state_path=Path(root) / "state.json")
            state = {"0609": {"id": 123, "status": "draft"}}
            row = deposit.sync_record(client, target, "0609", files, state, [], {"mediaID": "m"})
            self.assertEqual(client.calls, ["GET", *(["PUT"] * 6), "GET", "POST"])
            self.assertEqual(row["doi"], "10.5072/zenodo.123")

    def test_ambiguous_create_never_recreates(self):
        with self.assertRaisesRegex(RuntimeError, "create response lost"):
            deposit.sync_record(None, SANDBOX, "0609", {}, {"0609": {"status": "creating"}}, [], {})

    def test_published_record_resumed_without_new_doi(self):
        with tempfile.TemporaryDirectory() as root:
            files = make_files(root)
            deposition = {"id": 123, "submitted": True, "doi": "10.5072/zenodo.123",
                          "links": {"bucket": "https://sandbox.zenodo.org/api/files/bucket"},
                          "metadata": {"title": "ICE-LAPSE IMG_0609"}, "files": remote_listing(files)}

            class Client:
                def request(self, method, url, **kwargs):
                    if method != "GET":
                        raise AssertionError("Cannot create/upload/publish twice")
                    return FakeResponse(deposition)

            target = replace(SANDBOX, state_path=Path(root) / "state.json")
            state = {"0609": {"id": 123, "status": "draft"}}
            row = deposit.sync_record(Client(), target, "0609", files, state, [], {"mediaID": "m"})
            self.assertEqual(row["doi"], "10.5072/zenodo.123")

    def test_production_is_isolated_and_reuses_existing_deposit(self):
        self.assertNotEqual(PRODUCTION.token_env, SANDBOX.token_env)
        self.assertNotEqual(PRODUCTION.state_path, SANDBOX.state_path)
        self.assertNotEqual(PRODUCTION.manifest_path, SANDBOX.manifest_path)
        self.assertNotEqual(PRODUCTION.community_id, SANDBOX.community_id)
        with tempfile.TemporaryDirectory() as root:
            target = replace(PRODUCTION, state_path=Path(root) / "state.json")
            files = make_files(root)
            deposition = {"id": 123, "submitted": True, "doi": "10.5281/zenodo.123",
                          "links": {"bucket": "https://zenodo.org/api/files/bucket"},
                          "metadata": {"title": "ICE-LAPSE IMG_0609"}, "files": remote_listing(files)}

            class Client:
                def request(self, method, url, **kwargs):
                    if method != "GET" or url != "https://zenodo.org/api/deposit/depositions/123":
                        raise AssertionError("Must use production GET, not POST or sandbox")
                    return FakeResponse(deposition)

            state = {"0609": {"id": 123, "status": "draft"}}
            result = deposit.sync_record(Client(), target, "0609", files, state, [], {"mediaID": "m"})
            self.assertEqual(result["doi"], "10.5281/zenodo.123")
            self.assertEqual(result["recordURL"], "https://zenodo.org/records/123")
            self.assertTrue(result["originalFilePath"].startswith("https://zenodo.org/"))
            self.assertEqual(load_state(target)["0609"]["doi"], result["doi"])

    def test_production_create_uses_own_state_and_host(self):
        with tempfile.TemporaryDirectory() as root:
            target = replace(PRODUCTION, state_path=Path(root) / "production.json")
            sandbox_state = Path(root) / "sandbox.json"
            sandbox_state.write_text('{"0609":{"status":"published"}}')
            files = make_files(root)
            draft = {"id": 123, "submitted": False, "links": {"bucket": "https://zenodo.org/api/files/bucket"},
                     "metadata": {"title": "ICE-LAPSE IMG_0609"}, "files": []}
            complete = {**draft, "files": remote_listing(files)}

            class Client:
                def __init__(self):
                    self.gets = 0

                def request(self, method, url, **kwargs):
                    if method == "POST" and url == "https://zenodo.org/api/deposit/depositions":
                        self.pre_create_state = load_state(target).get("0609")
                        return FakeResponse(draft)
                    if method == "GET":
                        self.gets += 1
                        return FakeResponse(draft if self.gets == 1 else complete)
                    if method == "PUT" and url.startswith("https://zenodo.org/api/files/bucket/"):
                        return FakeResponse({"links": {"self": url}})
                    if method == "POST" and url == "https://zenodo.org/api/deposit/depositions/123/actions/publish":
                        return FakeResponse({**complete, "submitted": True, "doi": "10.5281/zenodo.123"})
                    raise AssertionError(f"Unexpected target: {method} {url}")

            client = Client()
            with patch.object(deposit, "deposit_metadata", return_value={"title": "ICE-LAPSE IMG_0609"}):
                row = deposit.sync_record(client, target, "0609", files, {}, [], {"mediaID": "m"})
            self.assertEqual(client.pre_create_state, {"status": "creating"})
            self.assertEqual(row["doi"], "10.5281/zenodo.123")
            self.assertEqual(load_state(target)["0609"]["status"], "published")
            self.assertEqual(sandbox_state.read_text(), '{"0609":{"status":"published"}}')


class CommandLineTests(unittest.TestCase):
    def test_target_must_be_chosen(self):
        with patch("sys.stderr"), self.assertRaises(SystemExit):
            cli.main(["--dry-run"])

    def test_production_does_not_fall_back_to_sandbox_token(self):
        with patch.dict("os.environ", {"ZENODO_SANDBOX_TOKEN": "sandbox-only"}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "Set ZENODO_TOKEN"):
                cli.main(["--target", "production", "--community-only"])

    def test_production_publish_requires_confirmation(self):
        with patch.object(cli, "paired_photos", return_value={}), \
                patch.object(cli, "media_by_image_index", return_value={}), \
                patch.object(cli, "publish") as publish, \
                patch("builtins.input", return_value="no"), patch("builtins.print"):
            self.assertEqual(cli.main(["--target", "production", "--publish"]), 1)
            publish.assert_not_called()

    def test_user_agent_and_large_upload_timeout(self):
        class Session:
            def __init__(self):
                self.headers = {}

        session = Session()
        with patch.dict("os.environ", {"ZENODO_TOKEN": "test-production-token"}, clear=True), \
                patch("requests.Session", return_value=session), \
                patch.object(cli, "reconcile_community_manifest"):
            self.assertEqual(cli.main(["--target", "production", "--community-only"]), 0)
        self.assertEqual(session.headers["User-Agent"], client_module.USER_AGENT)
        self.assertEqual(session.headers["Authorization"], "Bearer test-production-token")

        class Client:
            def request(self, method, url, **kwargs):
                self.timeout = kwargs["timeout"]
                return FakeResponse({"links": {"self": url}})

        client = Client()
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "image.jpg"
            path.write_bytes(b"test")
            deposit.upload_file(client, "https://zenodo.org/api/files/bucket", path)
        self.assertEqual(client.timeout, (300, 3600))


if __name__ == "__main__":
    unittest.main()
