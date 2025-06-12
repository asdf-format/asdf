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
import urllib

import numpy as np

from asdf import generic_io, util


class UseInternalType:
    pass


UseInternal = UseInternalType()


class ExternalBlockCache:
    def __init__(self):
        self.clear()

    def load(self, base_uri, uri, memmap=False, validate_checksums=False):
        key = util.get_base_uri(uri)
        if key not in self._cache:
            resolved_uri = generic_io.resolve_uri(base_uri, uri)
            # if the uri only has a trailing "#" fragment, strip it
            # this deals with python 3.14 changes where in prior versions
            # urljoin removed this type of fragment
            if resolved_uri.endswith("#"):
                resolved_uri = resolved_uri[:-1]
            if resolved_uri == "" or resolved_uri == base_uri:
                return UseInternal

            from asdf import open as asdf_open

            with asdf_open(
                resolved_uri, "r", lazy_load=False, memmap=False, validate_checksums=validate_checksums
            ) as af:
                blk = af._blocks.blocks[0]
                if memmap and blk.header["compression"] == b"\0\0\0\0":
                    parsed_url = util._patched_urllib_parse.urlparse(resolved_uri)
                    if parsed_url.scheme == "file":
                        # deal with leading slash for windows file://
                        filename = urllib.request.url2pathname(parsed_url.path)
                        arr = np.memmap(filename, np.uint8, "r", blk.data_offset, blk.cached_data.nbytes)
                    else:
                        arr = blk.cached_data
                else:
                    arr = blk.cached_data
            self._cache[key] = arr
        return self._cache[key]

    def clear(self):
        self._cache = {}


def relative_uri_for_index(uri, index):
    # get the os-native separated path for this uri
    path = util._patched_urllib_parse.urlparse(uri).path
    dirname, filename = os.path.split(path)
    filename = os.path.splitext(filename)[0] + f"{index:04d}.asdf"
    return filename
