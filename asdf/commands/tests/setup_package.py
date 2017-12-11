# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-



def get_package_data():  # pragma: no cover
    return {
        str(_PACKAGE_NAME_ + '.commands.tests'): ['data/*.asdf', 'data/*.diff']}
