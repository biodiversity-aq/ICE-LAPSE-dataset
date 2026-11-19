# Raw data (not in git)

This folder holds the original ICE-LAPSE image dataset. It is about 25 GB, so
it is not committed. Download it from Zenodo:
[ICE-LAPSE image dataset, v1.1.0](https://doi.org/10.5281/zenodo.7318531).

## Files in the Zenodo record

| File | Size | Needed for |
|------|------|------------|
| `Deployment in Tethys bay - Mario Zucchelli Station- 2015_GUARD1-PNRA-2015_iFDO.yaml` | 0.4 MB | everything |
| `ICE-LAPSE_Tags.tgz` | 2.7 GB | everything (expert tags and tagged images) |
| `640x427.tgz` | 72 MB | Zenodo upload, tests |
| `jpgImages.tgz` | 2.0 GB | Zenodo upload, tests |
| `rawImages.tgz` | 18.6 GB | Zenodo upload, tests |
| `iFDO_Dataset.tgz` | 2.0 GB | not used |

To **build the Camtrap-DP tables**, you need only the iFDO YAML and
`ICE-LAPSE_Tags.tgz`. The image archives are needed to **upload to Zenodo**
(`python3 -m ice_lapse.zenodo`) and to run the full test suite.

## Download and extract

From the repository root:

```bash
cd data/raw
```

```bash
curl -L "https://zenodo.org/api/records/7318531/files/Deployment%20in%20Tethys%20bay%20-%20Mario%20Zucchelli%20Station-%202015_GUARD1-PNRA-2015_iFDO.yaml/content" -o "Deployment in Tethys bay - Mario Zucchelli Station- 2015_GUARD1-PNRA-2015_iFDO.yaml"
```

```bash
for f in ICE-LAPSE_Tags 640x427 jpgImages rawImages; do curl -L -C - -o "$f.tgz" "https://zenodo.org/api/records/7318531/files/$f.tgz/content" && tar -xzf "$f.tgz"; done
```

`curl -C -` resumes an interrupted download if you run the command again.
Delete the `.tgz` files after extracting if you need the disk space.

## Expected layout

The folder names inside the archives may not match exactly. After extracting,
move files if needed so this folder looks like this:

```
data/raw/
  Deployment in Tethys bay - Mario Zucchelli Station- 2015_GUARD1-PNRA-2015_iFDO.yaml
  Classes.txt                 annotation class labels (line number = class ID)
  SpeciesDistribution.csv     per-image taxon counts
  SpeciesColorLabel.jpg       colour/class legend
  TextualTags/IMG_####.txt                      755 YOLO-format box files
  taggedImages/IMG_####_CR2_embedded_tagged.jpg 755 images with drawn boxes
  jpgImages/IMG_####_CR2_embedded.jpg           755 full-size JPEGs
  640x427/IMG_####_CR2_embedded_640x480.jpg     755 small JPEGs
  rawImages/IMG_####.CR2                        Canon raw images (759; 755 used)
```

The paths are defined in `src/ice_lapse/paths.py`. To check that everything
is in place, run:

```bash
python3 -m ice_lapse.zenodo --target sandbox --dry-run
```

It makes no network calls and reports any missing or extra image files.
