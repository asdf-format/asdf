"""
For external blocks, the previous block management
would cache data opened from external files (to return the
same underlying ndarray if the same external block
was referenced more than once). `ExternalBlockCache` is
used here to allow for the same behavior without requiring
the block manager to have a reference to the `AsdfFile`
(that references the block manager).
"""
import os

from asdf import generic_io, util


class UseInternalType:
    pass


UseInternal = UseInternalType()


class ExternalBlockCache:
    def __init__(self):
        self._cache = {}

    def load(self, base_uri, uri):
        key = util.get_base_uri(uri)
        if key not in self._cache:
            resolved_uri = generic_io.resolve_uri(base_uri, uri)
            if resolved_uri == "" or resolved_uri == base_uri:
                return UseInternal

            from asdf import open as asdf_open

            with asdf_open(resolved_uri, lazy_load=False, copy_arrays=True) as af:
                self._cache[key] = af._blocks.blocks[0].cached_data
        return self._cache[key]


def relative_uri_for_index(uri, index):
    # get the os-native separated path for this uri
    path = util.patched_urllib_parse.urlparse(uri).path
    dirname, filename = os.path.split(path)
    filename = os.path.splitext(filename)[0] + f"{index:04d}.asdf"
    return filename
