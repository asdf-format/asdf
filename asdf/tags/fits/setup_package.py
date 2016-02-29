# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function


def get_package_data():  # pragma: no cover
    return {
        str('asdf.tags.fits.tests'): ['data/*.fits']
    }
