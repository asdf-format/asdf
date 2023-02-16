import os
import sys

import numpy as np
import pytest
from astropy.io.fits import HDUList, ImageHDU

import asdf
from asdf.commands import extract
from asdf.exceptions import AsdfDeprecationWarning

with pytest.warns(AsdfDeprecationWarning, match="AsdfInFits has been deprecated.*"):
    # asdf.fits_embed is imported here
    if "asdf.fits_embed" in sys.modules:
        del sys.modules["asdf.fits_embed"]
    import asdf.fits_embed
    from asdf.fits_embed import AsdfInFits

from asdf.tests.helpers import assert_tree_match


def test_extract(tmpdir):
    hdulist = HDUList()

    image = ImageHDU(np.random.random((25, 25)))
    hdulist.append(image)

    tree = {
        "some_words": "These are some words",
        "nested": {"a": 100, "b": 42},
        "list": list(range(10)),
        "image": image.data,
    }

    asdf_in_fits = str(tmpdir.join("asdf.fits"))
    with AsdfInFits(hdulist, tree) as aif:
        aif.write_to(asdf_in_fits)

    pure_asdf = str(tmpdir.join("extract.asdf"))
    extract.extract_file(asdf_in_fits, pure_asdf)

    assert os.path.exists(pure_asdf)

    with asdf.open(pure_asdf) as af:
        assert not isinstance(af, AsdfInFits)
        assert_tree_match(tree, af.tree)
