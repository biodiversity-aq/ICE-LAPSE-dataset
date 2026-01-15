# Python
import os
from utils_path import here  # moved to shared utility to avoid circular import
from ifdo import load_ifdo_metadata
from transform_data_to_deployments import header_to_deployments_df
from transform_data_to_media import image_items_to_media_df
from transform_data_to_observations import save_observations_csv  # NEW


def main():
    # Source iFDO YAML
    file_path = here(
        "data",
        "zenodo",
        "Deployment in Tethys bay - Mario Zucchelli Station- 2015_GUARD1-PNRA-2015_iFDO.yaml",
    )
    print(f"Loading: {file_path}")

    # Load metadata
    ifdo_metadata = load_ifdo_metadata(file_path)

    # Build and save deployments DataFrame
    deployments = header_to_deployments_df(ifdo_metadata)
    print("\nDeployments (preview):")
    print(deployments)
    deployments_out = here("data", "camtrap-dp", "deployments.csv")
    os.makedirs(os.path.dirname(deployments_out), exist_ok=True)
    deployments.to_csv(deployments_out, index=False, encoding="utf-8")
    print(f"\nSaved deployments CSV to: {deployments_out}")

    # Build and save media DataFrame
    media_df = image_items_to_media_df(ifdo_metadata)
    print("\nMedia (preview):")
    print(media_df.head())
    media_out = here("data", "camtrap-dp", "media.csv")
    os.makedirs(os.path.dirname(media_out), exist_ok=True)
    media_df.to_csv(media_out, index=False, encoding="utf-8")
    print(f"\nSaved media CSV to: {media_out}")

    # Build and save observations DataFrame
    save_observations_csv()


if __name__ == "__main__":
    main()