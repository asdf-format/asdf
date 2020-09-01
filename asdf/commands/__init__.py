import importlib

from .exploded import implode, explode
from .to_yaml import to_yaml
from .defragment import defragment
from .diff import diff
from .tags import list_tags
from .extension import find_extensions
from .info import info
from .edit import edit

__all__ = [
    'defragment', 
    'diff', 
    'edit', 
    'explode', 
    'find_extensions', 
    'implode', 
    'info'
    'list_tags',
    'to_yaml', 
]

# Extracting ASDF-in-FITS files requires Astropy
if importlib.util.find_spec('astropy'):
    from .extract import extract_file
    from .remove_hdu import remove_hdu

    __all__ += ['extract_file', 'remove_hdu']
