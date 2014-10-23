# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function


from astropy import modeling

from ....tests import helpers


def test_transforms(tmpdir):
    tree = {
        'identity': modeling.Identity(2)
    }

    def check_asdf(asdf):
        pass

    def check_raw_yaml(content):
        pass

    helpers.assert_roundtrip_tree(tree, tmpdir, check_asdf, check_raw_yaml)
