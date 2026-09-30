"""Portable and installed layouts share this resolver with the native host."""
import os
from pathlib import Path


def is_installed(root: Path) -> bool:
    return (root/"installation.json").is_file()


def default_data_dir(root: Path) -> Path:
    if is_installed(root):
        base=Path(os.environ.get("LOCALAPPDATA",str(Path.home()/"AppData"/"Local")))
        return base/"ArtworkLocalStudio"
    return root/"data"


def resource_base(root: Path) -> Path:
    return default_data_dir(root) if is_installed(root) else root
