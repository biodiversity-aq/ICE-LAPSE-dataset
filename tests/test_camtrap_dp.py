"""Offline checks for building Camtrap-DP tables."""

import tempfile
import unittest
from pathlib import Path

import pandas as pd

from ice_lapse.camtrap_dp.deployments import build_deployments
from ice_lapse.camtrap_dp.media import apply_zenodo_manifest, build_media
from ice_lapse.ifdo import load_ifdo_metadata
from ice_lapse.zenodo.targets import TARGETS


class CamtrapDPTests(unittest.TestCase):
    def test_ifdo_timer_maps_to_camtrap_dp_enum(self):
        source = {"image-set-header": {"image-set-uuid": "deployment", "image-capture-mode": "timer"},
                  "image-set-items": {"image.jpg": [{"image-datetime": "2017-01-23 23:15:14"}]}}
        result = build_media(source)
        self.assertEqual(result.iloc[0]["captureMethod"], "timeLapse")
        self.assertEqual(result.iloc[0]["timestamp"], "2017-01-23T23:15:14Z")

    def test_underwater_deployment_omits_terrestrial_feature_type(self):
        row = build_deployments(load_ifdo_metadata()).iloc[0]
        self.assertNotIn("featureType", row.index)
        self.assertEqual(row["habitat"], "Coastal seafloor")
        self.assertIn("image-marine-zone:seafloor", row["deploymentTags"])
        self.assertLess(row["latitude"], 0)

    def test_production_links_and_complete_coverage(self):
        media = pd.DataFrame({"mediaID": ["a", "b"], "filePath": ["old-a", "old-b"]})
        with tempfile.TemporaryDirectory() as folder:
            manifest = Path(folder) / "manifest.csv"
            manifest.write_text(
                "imageIndex,mediaID,doi,recordURL,originalFile,originalFilePath,taggedFile,taggedFilePath\n"
                "0609,a,10.5281/zenodo.123,https://zenodo.org/records/123,IMG_a.jpg,https://zenodo.org/api/files/x/IMG_a.jpg,IMG_a_tagged.jpg,https://zenodo.org/api/files/x/IMG_a_tagged.jpg\n"
                "0610,b,10.5281/zenodo.124,https://zenodo.org/records/124,IMG_b.jpg,https://zenodo.org/api/files/y/IMG_b.jpg,IMG_b_tagged.jpg,https://zenodo.org/api/files/y/IMG_b_tagged.jpg\n"
            )
            result = apply_zenodo_manifest(media, manifest, TARGETS["production"])
            self.assertEqual(result.loc[0, "filePath"], "https://zenodo.org/api/files/x/IMG_a.jpg")
            self.assertEqual(result.loc[1, "mediaComments"],
                             "taggedFilePath:https://zenodo.org/api/files/y/IMG_b_tagged.jpg | imageDOI:10.5281/zenodo.124")
            self.assertEqual(media.loc[0, "filePath"], "old-a")
            with self.assertRaisesRegex(ValueError, "Unexpected DOI"):
                apply_zenodo_manifest(media, manifest, TARGETS["sandbox"])
            with self.assertRaisesRegex(ValueError, "exactly one"):
                apply_zenodo_manifest(media.iloc[:1], manifest, TARGETS["production"])


if __name__ == "__main__":
    unittest.main()
