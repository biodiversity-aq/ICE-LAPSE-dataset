# utils_paths.py (new file)
import os


def here(*paths: str) -> str:
    """
    Construct an absolute path relative to the project root directory.
    The project root is assumed to be one level up from this file's directory.
    """
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    return os.path.join(project_root, *paths)
