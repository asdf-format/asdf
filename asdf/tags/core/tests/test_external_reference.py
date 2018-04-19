# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from asdf.tags.core.external_reference import ExternalArrayReference
from asdf.tests import helpers


def test_roundtrip_external_array(tmpdir):
    ref = ExternalArrayReference("./nonexistant.fits", 1,
                                 "np.float64", (100, 100))

    tree = {'nothere': ref}

    helpers.assert_roundtrip_tree(tree, tmpdir)
