# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

import os

import numpy as np

import pytest

astropy = pytest.importorskip('astropy')
from astropy.io import fits

from asdf.fits_embed import AsdfInFits
from .. import remove_hdu


def test_remove_hdu(tmpdir):
    hdulist = fits.HDUList()

    image = fits.ImageHDU(np.random.random((25, 25)))
    hdulist.append(image)

    tree = {
        'some_words': 'These are some words',
        'nested': {
            'a': 100,
            'b': 42
        },
        'list': [x for x in range(10)],
        'image': image.data
    }

    asdf_in_fits = str(tmpdir.join('asdf.fits'))
    with AsdfInFits(hdulist, tree) as aif:
        aif.write_to(asdf_in_fits)

    with fits.open(asdf_in_fits) as hdul:
        assert 'ASDF' in hdul

    new_fits = str(tmpdir.join('remove.fits'))
    remove_hdu(asdf_in_fits, new_fits)

    assert os.path.exists(new_fits)

    with fits.open(new_fits) as hdul:
        assert 'ASDF' not in hdul
