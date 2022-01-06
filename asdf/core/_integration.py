from pathlib import Path
import sys

import asdf
from asdf.resource import DirectoryResourceMapping, JsonschemaResourceMapping

if sys.version_info < (3, 9):
    import importlib_resources
else:
    import importlib.resources as importlib_resources


def get_extensions():
    """
    Get the extension instances for the core extensions.  This method is registered with the
    asdf.extensions entry point.

    Returns
    -------
    list of asdf.extension.Extension
    """
    from . import _extensions
    return _extensions.EXTENSIONS


def get_resource_mappings():
    """
    Get the resource mapping instances for the core schemas.
    This method is registered with the asdf.resource_mappings entry point.
    """
    schemas_root = importlib_resources.files(asdf)/"schemas"/"stsci.edu"
    if not schemas_root.is_dir():
        # In an editable install, the schemas can be found in the
        # asdf-standard submodule.
        schemas_root = Path(__file__).parent.parent.parent/"asdf-standard"/"schemas"/"stsci.edu"
        if not schemas_root.is_dir():
            raise RuntimeError("Unable to locate schemas")

    resources_root = importlib_resources.files(asdf)/"resources"
    if not resources_root.is_dir():
        # In an editable install, the resources can be found in the
        # asdf-standard submodule.
        resources_root = Path(__file__).parent.parent.parent/"asdf-standard"/"resources"
        if not resources_root.is_dir():
            raise RuntimeError("Unable to locate resources")

    return [
        DirectoryResourceMapping(schemas_root, "http://stsci.edu/schemas", recursive=True),
        DirectoryResourceMapping(resources_root / "asdf-format.org", "asdf://asdf-format.org", recursive=True),
        JsonschemaResourceMapping(),
    ]
