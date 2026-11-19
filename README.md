[![DOI](https://zenodo.org/badge/1134925339.svg)](https://doi.org/10.5281/zenodo.24368248)

# ICE-LAPSE dataset

Tools to publish the [ICE-LAPSE image dataset](https://doi.org/10.5281/zenodo.7318531)
as a [Camtrap-DP](https://camtrap-dp.tdwg.org/) package, and to deposit each
annotated image on Zenodo with its own DOI.

## Published dataset

| Where | Link |
|-------|------|
| Camtrap-DP package on the IPT | https://cloud.gbif.org/eca/resource?r=ice-lapse |
| Dataset on GBIF (DOI)         | https://doi.org/10.15468/3gqdpf |

The Camtrap-DP tables in `data/camtrap-dp/` are published as a Camtrap-DP
resource on the GBIF IPT. GBIF converts it automatically into a Darwin Core
Archive during ingestion, and the dataset gets its GBIF DOI there.

## Overview

ICE-LAPSE is a long-term monitoring dataset of Antarctic coastal benthic
fauna. It has 755 images from a non-invasive, autonomous camera on a seabed
lander at 20 m depth in Tethys Bay, near Mario Zucchelli Station (Terra Nova
Bay, Ross Sea). The images cover the Antarctic daylight and dark periods,
including the transitions between them. Every image has the same field of view:
the benthic fauna and part of the water column above it, including fishes.
Expert biologists annotated each organism with a bounding box.

The images were acquired within the project *ICE-LAPSE: Analysis of Antarctic
benthos dynamics by using non-destructive monitoring devices and permanent
stations* (PNRA 2013/AZ1.16), part of the Italian National Antarctic Research
Program (PNRA).

## Data standards

- **iFDO** ([image FAIR Digital Object](https://www.marine-imaging.com/fair/)):
  the source metadata. It describes the deployment, acquisition, annotation
  labels and people (with ORCIDs).
- **Camtrap-DP** ([Camera Trap Data Package](https://camtrap-dp.tdwg.org/)):
  the output format. It is a TDWG standard for camera trap data, built on
  Frictionless Data Packages.

## Layout

```
data/
  raw/            original ICE-LAPSE dataset (not in git; download it, see below)
  taxa/           taxon names matched against WoRMS
  interim/zenodo/
    sandbox/      upload_state.json + image_pairs.csv for sandbox.zenodo.org
    production/   upload_state.json + image_pairs.csv for zenodo.org
  camtrap-dp/     Camtrap-DP resources: deployments.csv, media.csv, observations.csv
src/ice_lapse/
  paths.py        every input/output location
  ifdo.py         iFDO YAML loading
  source_data.py  SpeciesDistribution.csv, Classes.txt, TextualTags readers
  camtrap_dp/     deployments, media, observations builders and the build command
  zenodo/         targets (sandbox/production), API client, deposit metadata,
                  resumable upload, community submission, upload command
tests/            offline unit tests
docs/             Zenodo upload guide
```

### Camtrap-DP tables (`data/camtrap-dp/`)

| File               | Rows   | Content |
|--------------------|--------|---------|
| `deployments.csv`  | 1      | The lander deployment: location, coordinates, start and end, camera, depth, habitat, other iFDO header fields as tags. |
| `media.csv`        | 755    | One row per image: timestamp (UTC), capture method, file URL. When built with `--zenodo-target`, it also has the per-image Zenodo DOI and tagged-image link. |
| `observations.csv` | 23,881 | One row per annotated organism: taxon (or `unclassified`), normalized bounding box, annotators' ORCIDs. |

### Taxa (`data/taxa/`)

- `unique_scientific_name.csv`: the annotation labels and the scientific names
  they map to.
- `unique_scientific_name_matched.csv`: the same names matched against
  [WoRMS](https://www.marinespecies.org/), with AphiaID, LSID and the accepted
  classification. The LSIDs appear as subjects on the Zenodo image records.

## Setup

From the repository root:

```bash
python3 -m pip install -r requirements.txt
```

This installs the dependencies and the `ice_lapse` package in editable mode.

### Get the raw data

The original dataset (about 25 GB of images and annotations) is **not in this
repository**. Download it from [Zenodo](https://doi.org/10.5281/zenodo.7318531)
into `data/raw/`. Follow [data/raw/README.md](data/raw/README.md) for the
download commands and the folder layout the code expects.

The commands below read their inputs from `data/raw/`. The Camtrap-DP tables
in `data/camtrap-dp/` and the Zenodo manifests in `data/interim/` are
committed, so you can use the published tables without downloading anything.

## Build the Camtrap-DP tables

```bash
python3 -m ice_lapse.camtrap_dp --zenodo-target production
```

This rewrites `data/camtrap-dp/{deployments,media,observations}.csv` from
`data/raw`. With `--zenodo-target`, `media.csv` links each image to its
published Zenodo record (`filePath` is the original JPEG and `mediaComments`
holds the tagged JPEG link and image DOI). The manifest must cover all 755
images. Without the flag, `filePath` uses the original iFDO image URLs. The
command makes no network calls. Use `--output-dir` to write somewhere else.

## Upload images to Zenodo

Choose the environment with `--target sandbox` or `--target production`. Each
one has its own token, DOI manifest and resume state.

### 1. Create a token

Sandbox and production need separate tokens, each created on its own site:

| Target       | Create the token at                                                      | Environment variable   |
|--------------|---------------------------------------------------------------------------|------------------------|
| `sandbox`    | https://sandbox.zenodo.org/account/settings/applications/tokens/new/     | `ZENODO_SANDBOX_TOKEN` |
| `production` | https://zenodo.org/account/settings/applications/tokens/new/             | `ZENODO_TOKEN`         |

Tick the `deposit:write` and `deposit:actions` scopes. Copy the token when it
is shown; Zenodo shows it only once.

### 2. Put the token in your shell

Run this in the same terminal you will upload from. It asks for the token
without echoing it, so the token stays out of your shell history:

```bash
read -rsp 'Zenodo sandbox token: ' ZENODO_SANDBOX_TOKEN && echo && export ZENODO_SANDBOX_TOKEN
```

For production, use `ZENODO_TOKEN` instead:

```bash
read -rsp 'Zenodo token: ' ZENODO_TOKEN && echo && export ZENODO_TOKEN
```

Paste the token at the prompt and press Enter. Do not write the token into
source files or commit it. The variable is lost when you close the terminal,
so repeat this step in each new terminal.

### 3. Dry run, then publish

`--dry-run` needs no token and makes no API calls.

```bash
python3 -m ice_lapse.zenodo --target sandbox --dry-run
python3 -m ice_lapse.zenodo --target sandbox --publish --skip-existing
```

```bash
python3 -m ice_lapse.zenodo --target production --dry-run
python3 -m ice_lapse.zenodo --target production --publish
```

Publishing to production asks you to type `production` first (`--yes` skips
the prompt). Uploading only writes the manifest under `data/interim/zenodo/`.
To use the new links, rebuild the Camtrap-DP tables with the matching
`--zenodo-target`. Tokens, recovery and community submission are covered in
[docs/zenodo-upload.md](docs/zenodo-upload.md).

## Tests

```bash
python3 -m unittest discover -s tests
```

The tests make no network calls, but they read the local files in `data/raw/`,
including every image folder. Download the raw data first.

## Citation

If you use this dataset, please cite:

- The dataset: ICE-LAPSE image dataset, https://doi.org/10.5281/zenodo.7318531
- The Camtrap-DP dataset on GBIF: https://doi.org/10.15468/3gqdpf
- The dataset description paper (Scientific Data): https://doi.org/10.1038/s41597-022-01865-7
- The sampling design: Marini et al. (2022), *Long-term automated visual
  monitoring of Antarctic benthic fauna*, Methods in Ecology and Evolution,
  https://doi.org/10.1111/2041-210X.13898

Images annotated by Simone Marini ([0000-0003-0665-7815](https://orcid.org/0000-0003-0665-7815)),
Andrea Peirano ([0000-0001-8847-1760](https://orcid.org/0000-0001-8847-1760)),
Federico Bonofiglio ([0000-0003-4085-9840](https://orcid.org/0000-0003-4085-9840))
and Stefano Schiaparelli ([0000-0002-0137-3605](https://orcid.org/0000-0002-0137-3605)).

## License

The code in this repository is licensed under the MIT License; see
[LICENSE](LICENSE). The dataset and the Zenodo image records are released
under [Creative Commons Attribution 4.0 International (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/).
