# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-



def get_package_data():  # pragma: no cover
    return {
        str(_PACKAGE_NAME_ + '.tests'):
            ['coveragerc', 'data/*.yaml', 'data/*.json', 'data/*.fits', 'data/*.fits.gz']}
