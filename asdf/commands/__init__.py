import importlib

from .defragment import defragment
from .diff import diff
from .edit import edit
from .exploded import explode, implode
from .extension import find_extensions
from .info import info
from .tags import list_tags
from .to_yaml import to_yaml

__all__ = ["implode", "explode", "to_yaml", "defragment", "diff", "list_tags", "find_extensions", "info", "edit"]


# Extracting ASDF-in-FITS files requires Astropy
if importlib.util.find_spec("astropy"):
    from .extract import extract_file
    from .remove_hdu import remove_hdu

    __all__ += ["extract_file", "remove_hdu"]
