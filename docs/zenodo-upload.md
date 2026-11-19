# Depositing ICE-LAPSE images on Zenodo

`python3 -m ice_lapse.zenodo` creates one Zenodo deposition per annotated image
(755 in total) and publishes it. Each deposition holds six files:

| Role     | File                               | Source folder        |
|----------|------------------------------------|----------------------|
| original | `IMG_####_CR2_embedded.jpg`        | `data/raw/jpgImages` |
| tagged   | `IMG_####_CR2_embedded_tagged.jpg` | `data/raw/taggedImages` |
| preview  | `IMG_####_CR2_embedded_640x480.jpg`| `data/raw/640x427`   |
| raw      | `IMG_####.CR2`                     | `data/raw/rawImages` |
| tags     | `IMG_####.txt`                     | `data/raw/TextualTags` |
| legend   | `SpeciesColorLabel.jpg` (shared)   | `data/raw`           |

The record's subjects include the image, deployment, date and location, and the
taxa annotated in that image, with WoRMS LSIDs from
`data/taxa/unique_scientific_name_matched.csv`. Creator affiliations come from
the [Scientific Data paper](https://doi.org/10.1038/s41597-022-01865-7). Each
record is documented by that paper and by Marini et al. (2022),
[Long-term automated visual monitoring of Antarctic benthic fauna](https://doi.org/10.1111/2041-210X.13898).

## Choosing sandbox or production

`--target` is required.

|                | `--target sandbox`                          | `--target production`                        |
|----------------|---------------------------------------------|----------------------------------------------|
| Host           | https://sandbox.zenodo.org                  | https://zenodo.org                           |
| Token variable | `ZENODO_SANDBOX_TOKEN`                      | `ZENODO_TOKEN`                               |
| DOI prefix     | `10.5072` (testing only)                    | `10.5281` (permanent)                        |
| Community      | sandbox `ice-lapse`                         | production `ice-lapse`                       |
| Working files  | `data/interim/zenodo/sandbox/`              | `data/interim/zenodo/production/`            |

The two environments never share tokens, state or manifests. Production never
falls back to the sandbox token.

Create the token at *Account → Applications → Personal access tokens* on the
matching host, with the `deposit:write` and `deposit:actions` scopes. Pass it
through the environment and never put it in source code:

```bash
read -rsp 'Zenodo token: ' ZENODO_TOKEN && echo && export ZENODO_TOKEN
```

(For sandbox, use `ZENODO_SANDBOX_TOKEN` instead.)

## Commands

| Mode               | What it does                                                                 |
|--------------------|------------------------------------------------------------------------------|
| `--dry-run`        | Checks that all six files exist for every image and that images pair with Camtrap-DP media. Needs no token and makes no API calls. |
| `--publish`        | Creates, uploads and publishes every image not yet in the manifest. In production it asks for confirmation; `--yes` skips it. |
| `--community-only` | Submits every record in the manifest to the `ice-lapse` community. Uploads nothing and leaves the state unchanged. |

```bash
python3 -m ice_lapse.zenodo --target production --dry-run
python3 -m ice_lapse.zenodo --target production --publish
python3 -m ice_lapse.zenodo --target production --community-only
```

After publishing, link the Camtrap-DP media to the new records:

```bash
python3 -m ice_lapse.camtrap_dp --zenodo-target production
```

The uploader never edits `data/camtrap-dp/`.

## Working files and recovery

- `upload_state.json`: per-image progress (`creating` → `draft` → `published`).
  The `creating` entry is saved **before** each create request.
- `image_pairs.csv`: one row per published deposit with its DOI, record URL
  and file URLs. It is written after each publication.

If a run is interrupted, re-run the same command. An existing draft is reused,
and files already uploaded are checked against the local size and MD5. If a
create response was lost, the state stays `creating` and the run stops so no
duplicate DOI is minted. Find the draft in your account, then set its entry to
`{"status": "draft", "id": <draft ID>}`.

Never delete the state or manifest to force a retry. Keep backups of both, and
do not run two uploads against the same target at once. Zenodo rate limits are
shared per token.

`--publish` skips every image already in the manifest without re-checking it
remotely. It retries only community submissions marked `needs_reconcile`
after an interruption. For a full community audit, run `--community-only`. It
checks membership and open requests before submitting, so it never creates a
duplicate request. Curators still have to accept pending requests.

Requests are paced to at most 80 per minute and 4,800 per hour, and they send
the `ICE-LAPSE-Uploader/1.0` User-Agent. Large file uploads allow 300 s for
socket writes and 3600 s for the response.

## Sandbox: the earlier two-file records

The sandbox manifest already contains published records, and 67 of them were
published with only two files. A published deposit cannot take more files
without a new version DOI. On sandbox, `--publish` therefore refuses to run
unless you pass `--skip-existing`, which leaves those records unchanged and
processes only the remaining images. The sandbox may be cleared periodically.
