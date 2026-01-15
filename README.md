# ICE-LAPSE Dataset

## Overview

The ICE-LAPSE (Image Collection for Ecosystem Long-term Antarctic Periodic Survey and Evaluation) dataset is a long-term monitoring dataset of Antarctic coastal benthic fauna. It consists of 755 images acquired using a non-invasive, autonomous imaging device over an extended period encompassing both Antarctic daylight and dark periods, including transition phases.

All images feature a fixed field of view showing benthic fauna and part of the water column above, including fishes present during the monitoring period. Images have been manually annotated by expert biologists, making this dataset valuable for:

- Studying dynamics of long-term Antarctic underwater fauna
- Developing and testing algorithms for automated image analysis
- Recognition and classification of Antarctic organisms
- Automated analysis of long-term ecological dynamics

## Project Organization

This repository follows the [Cookiecutter Data Science](https://cookiecutter-data-science.drivendata.org/) project structure:

```
.
├── LICENSE              <- MIT License
├── README.md            <- This file - top-level README for using this project
├── data/                <- Data directory organized by source and format
│   ├── camtrap-dp/      <- Camera Trap Data Package (Camtrap-DP) formatted output
│   │   ├── datapackage.json  <- Frictionless Data Package descriptor
│   │   ├── deployments.csv   <- Camera deployment metadata
│   │   ├── media.csv         <- Media file metadata (images)
│   │   └── observations.csv  <- Species observation records
│   ├── taxa/            <- Taxonomic information
│   │   ├── unique_scientific_name.csv         <- Extracted unique species names
│   │   └── unique_scientific_name_matched.csv <- Species names matched to taxonomic databases
│   └── zenodo/          <- Source data from Zenodo repository
│       ├── Classes.txt                        <- List of species classes in the dataset
│       ├── Deployment in Tethys bay - Mario Zucchelli Station- 2015_GUARD1-PNRA-2015_iFDO.yaml
│       │                                      <- iFDO (image FAIR Digital Object) metadata
│       ├── SpeciesColorLabel.jpg              <- Visual reference of species labels
│       └── SpeciesDistribution.csv            <- Raw species distribution counts per image
└── src/                 <- Source code for data processing
    ├── create_camtrap_dp_files.py         <- Main script to generate all Camtrap-DP files
    ├── create_datapackage_json.py         <- Generate datapackage.json metadata
    ├── ifdo.py                            <- iFDO YAML loading utilities
    ├── transform_data_to_deployments.py   <- Transform iFDO to deployments.csv
    ├── transform_data_to_media.py         <- Transform iFDO to media.csv
    ├── transform_data_to_observations.py  <- Transform species data to observations.csv
    └── utils_path.py                      <- Path utility functions
```

## Data Description

### Source Data (data/zenodo/)

The source data follows the **iFDO (image FAIR Digital Object)** standard for image metadata:

- **iFDO YAML file**: Contains comprehensive metadata about the image collection including:
  - Deployment location and coordinates (Tethys Bay, Mario Zucchelli Station, Antarctica)
  - Image acquisition parameters
  - Taxonomic annotation labels
  - Creator and contributor information (with ORCIDs)
  - Temporal coverage
  
- **SpeciesDistribution.csv**: Contains manual species counts per image with columns for:
  - Date and Image Index
  - Count values for each identified species
  
- **Classes.txt**: List of all species present in the dataset

- **SpeciesColorLabel.jpg**: Visual reference showing color-coded species labels

### Output Data (data/camtrap-dp/)

The processed data conforms to the **Camtrap-DP (Camera Trap Data Package)** standard, which is a Frictionless Data Package profile for camera trap data:

1. **datapackage.json**: Frictionless Data Package descriptor containing:
   - Dataset metadata (title, description, license)
   - Contributor information with ORCIDs
   - Taxonomic coverage
   - Temporal coverage
   - References to the three CSV resources

2. **deployments.csv**: Camera deployment information (1 row):
   - Deployment location and coordinates
   - Deployment start/end dates
   - Camera specifications
   - Habitat and environmental parameters

3. **media.csv**: Image file metadata (755 rows):
   - Media identifiers
   - Timestamps (ISO 8601 UTC)
   - File paths and capture methods

4. **observations.csv**: Species observation records (long format):
   - One row per species per image (where count > 0)
   - Scientific names
   - Observation counts
   - Classification metadata

### Taxonomic Data (data/taxa/)

- **unique_scientific_name.csv**: Extracted unique species names from the dataset
- **unique_scientific_name_matched.csv**: Species names matched against taxonomic databases (e.g., WoRMS) with full taxonomic hierarchy

## Requirements

This project uses Python 3 and requires the following packages:

```
pandas
pyyaml
```

You can install the dependencies using:

```bash
pip install pandas pyyaml
```

## Reproducing the Dataset

### Step 1: Clone the Repository

```bash
git clone https://github.com/biodiversity-aq/ICE-LAPSE-dataset.git
cd ICE-LAPSE-dataset
```

### Step 2: Install Dependencies

```bash
pip install pandas pyyaml
```

### Step 3: Generate Camtrap-DP Files

The main script processes the source iFDO metadata and species distribution data to generate all Camtrap-DP formatted files:

```bash
python src/create_camtrap_dp_files.py
```

This will create:
- `data/camtrap-dp/deployments.csv`
- `data/camtrap-dp/media.csv`
- `data/camtrap-dp/observations.csv`

### Step 4: Generate Data Package Metadata

Create the Frictionless Data Package descriptor:

```bash
python src/create_datapackage_json.py
```

This will create:
- `data/camtrap-dp/datapackage.json`

### Running Individual Transformation Scripts

You can also run individual transformation scripts:

```bash
# Transform to deployments
python src/transform_data_to_deployments.py

# Transform to media
python src/transform_data_to_media.py

# Transform to observations
python src/transform_data_to_observations.py
```

## Data Standards

### iFDO (image FAIR Digital Object)

The source metadata follows the iFDO standard for making image data FAIR (Findable, Accessible, Interoperable, and Reusable). iFDO provides a standardized way to describe image collections with rich metadata.

### Camtrap-DP (Camera Trap Data Package)

The output data follows the Camtrap-DP standard (https://camtrap-dp.tdwg.org/), which is:
- A Frictionless Data Package profile specifically designed for camera trap data
- A TDWG (Biodiversity Information Standards) ratified standard
- Compatible with analysis tools and data repositories that support standardized ecological data

### Frictionless Data

The `datapackage.json` file follows the Frictionless Data Package specification, making the dataset:
- Machine-readable with clear data schemas
- Validatable against the Camtrap-DP profile
- Interoperable with data processing tools

## Citation

If you use this dataset, please cite the original publication describing the sampling design:

**Sampling design methodology:**
https://doi.org/10.1111/2041-210X.13898

**Dataset creators:**
- Simone Marini (ORCID: 0000-0003-0665-7815)
- Andrea Peirano (ORCID: 0000-0001-8847-1760)
- Federico Bonofiglio (ORCID: 0000-0003-4085-9840)
- Stefano Schiaparelli (ORCID: 0000-0002-0137-3605)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

The dataset is made available under Creative Commons Attribution 4.0 International (CC-BY-4.0) license.

## Contact

For questions or issues, please contact:
- Simone Marini: simone.marini@cnr.it

## Acknowledgments

This dataset was collected at:
- **Location**: Tethys Bay, Mario Zucchelli Station, Antarctica
- **Coordinates**: See deployment metadata in `data/camtrap-dp/deployments.csv`
- **Project**: Antarctic Biodiversity Portal

The monitoring was conducted using autonomous underwater imaging equipment with fixed field of view to capture long-term ecological dynamics.
