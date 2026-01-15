# Shared iFDO YAML loading utilities
from typing import Dict, Any

import yaml


class IFDOSafeLoader(yaml.SafeLoader):
    """
    A safe YAML loader that handles iFDO metadata files with special tags.

    This class extends yaml.SafeLoader to provide secure loading of YAML files
    containing specific Python tags, particularly "!!python/name:builtins.id"
    which is sometimes used in YAML anchors. Instead of executing potentially
    unsafe code, it replaces these tags with a safe "id" string.

    Usage:
        yaml.load(file, Loader=IFDOSafeLoader)
    """
    pass


def _construct_python_name_builtins_id(loader, node):
    """Safely handle !!python/name:builtins.id by returning the string "id"."""
    return "id"


# Register the custom constructor on our safe loader
IFDOSafeLoader.add_constructor(
    "tag:yaml.org,2002:python/name:builtins.id",
    _construct_python_name_builtins_id,
)


def load_ifdo_metadata(path: str) -> Dict[str, Any]:
    """
    Load and parse an iFDO metadata file in YAML format using the IFDOSafeLoader.

    Args:
        path: Path to the iFDO metadata YAML file to be loaded.

    Returns:
        Dictionary containing the parsed iFDO metadata.
    """
    with open(path, "r", encoding="utf-8") as yaml_file:
        return yaml.load(yaml_file, Loader=IFDOSafeLoader)
